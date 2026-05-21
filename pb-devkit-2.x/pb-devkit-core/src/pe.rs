// PE (Executable) Parser - Shared core implementation
// Properly parses PE structure instead of scanning entire file.
//
// PowerBuilder EXE embedding strategy (PB 6~12):
//   The PBL data (starting with HDR* magic) is **appended** after all PE
//   sections, not placed inside the .rsrc Resource Directory.
//   Detection algorithm:
//     1. Parse DOS/PE/COFF/Section headers to find end-of-sections offset.
//     2. Scan from that offset (± small alignment) for HDR* magic.
//     3. Validate the found block by confirming HDR* at position 0.
//
//   Note: Some tools scan for PBD* (compiled libraries), but embedded PBLs
//   use the HDR* (PBL header) signature, not PBD*.

use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use thiserror::Error;

use crate::types::{PeInfoResult, ResourceInfo, FileTypeResult, ExtractResult};

#[derive(Error, Debug)]
pub enum PeError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid PE file")]
    InvalidFormat,
    #[error("Not a PowerBuilder executable")]
    NotPbExe,
    #[error("Resource not found: {0}")]
    NotFound(String),
}

const PE_MAGIC: &[u8; 2] = b"MZ";
const PE_SIGNATURE: &[u8; 4] = b"PE\0\0";
/// PBL header magic – embedded PBLs start with this (ANSI and Unicode variants)
const HDR_MAGIC: &[u8; 4] = b"HDR*";

#[derive(Debug, Clone)]
pub struct PeResource {
    pub name: String,
    pub offset: u64,
    pub size: u64,
    pub resource_type: String,
}

#[derive(Debug, Clone)]
pub struct PeInfo {
    pub is_pb_exe: bool,
    pub is_64bit: bool,
    pub machine_type: String,
    pub timestamp: Option<String>,
    pub resources: Vec<PeResource>,
    pub embedded_pbl_count: usize,
}

pub struct PeParser {
    path: String,
    is_pb_exe: bool,
    is_64bit: bool,
    machine_type: String,
    timestamp_str: Option<String>,
    resources: Vec<PeResource>,
    /// File offset where the last PE section ends (start of appended area)
    sections_end_offset: u64,
}

impl PeParser {
    pub fn new(path: &str) -> Result<Self, PeError> {
        let mut parser = PeParser {
            path: path.to_string(),
            is_pb_exe: false,
            is_64bit: false,
            machine_type: "unknown".to_string(),
            timestamp_str: None,
            resources: vec![],
            sections_end_offset: 0,
        };

        parser.analyze()?;
        Ok(parser)
    }

    fn analyze(&mut self) -> Result<(), PeError> {
        let mut file = File::open(&self.path)?;

        // ── DOS Header (64 bytes) ──
        let mut dos_header = [0u8; 64];
        file.read_exact(&mut dos_header)?;

        if &dos_header[0..2] != PE_MAGIC {
            return Err(PeError::InvalidFormat);
        }

        let pe_offset = u32::from_le_bytes([
            dos_header[60], dos_header[61], dos_header[62], dos_header[63],
        ]) as u64;

        // ── PE Signature ──
        file.seek(SeekFrom::Start(pe_offset))?;
        let mut pe_sig = [0u8; 4];
        file.read_exact(&mut pe_sig)?;
        if &pe_sig != PE_SIGNATURE {
            return Err(PeError::InvalidFormat);
        }

        // ── COFF Header (20 bytes) ──
        let mut coff = [0u8; 20];
        file.read_exact(&mut coff)?;

        let machine = u16::from_le_bytes([coff[0], coff[1]]);
        self.machine_type = match machine {
            0x14c => "x86".to_string(),
            0x8664 => {
                self.is_64bit = true;
                "x64".to_string()
            }
            0x1c0 => "ARM".to_string(),
            0xaa64 => {
                self.is_64bit = true;
                "ARM64".to_string()
            }
            _ => format!("unknown(0x{:x})", machine),
        };

        let num_sections = u16::from_le_bytes([coff[2], coff[3]]) as usize;
        let optional_header_size = u16::from_le_bytes([coff[16], coff[17]]) as usize;

        // COFF TimeDateStamp (bytes 4-7)
        let ts_seconds = u32::from_le_bytes([coff[4], coff[5], coff[6], coff[7]]);
        self.timestamp_str = Some(format_rfc2822(ts_seconds));

        // ── Skip Optional Header, parse Section Table ──
        let sections_start = pe_offset + 24 + optional_header_size as u64;
        file.seek(SeekFrom::Start(sections_start))?;

        let mut max_section_end: u64 = 0;

        for _ in 0..num_sections {
            let mut section = [0u8; 40];
            file.read_exact(&mut section)?;

            let raw_offset = u32::from_le_bytes([section[20], section[21], section[22], section[23]]) as u64;
            let raw_size   = u32::from_le_bytes([section[16], section[17], section[18], section[19]]) as u64;

            if raw_offset > 0 && raw_size > 0 {
                let end = raw_offset + raw_size;
                if end > max_section_end {
                    max_section_end = end;
                }
            }
        }

        self.sections_end_offset = max_section_end;

        // ── Scan for appended HDR* PBL data ──
        self.scan_appended_hdr(&mut file)?;

        Ok(())
    }

    /// Scan for HDR* magic in the area appended after all PE sections.
    ///
    /// PB compilers append the PBL data starting at `sections_end_offset`.
    /// We allow up to 4 KiB of alignment padding before giving up.
    fn scan_appended_hdr(&mut self, file: &mut File) -> Result<(), PeError> {
        let file_size = file.metadata()?.len();
        let scan_start = self.sections_end_offset;

        if scan_start >= file_size {
            return Ok(());
        }

        // Fast path: check exact offset first (most common case)
        file.seek(SeekFrom::Start(scan_start))?;
        let mut magic_buf = [0u8; 4];
        if file.read(&mut magic_buf)? >= 4 && &magic_buf == HDR_MAGIC {
            let pbl_size = file_size - scan_start;
            self.is_pb_exe = true;
            self.resources.push(PeResource {
                name: "embedded_pbl_1".to_string(),
                offset: scan_start,
                size: pbl_size,
                resource_type: "PBL".to_string(),
            });
            return Ok(());
        }

        // Slow path: scan up to 4096 bytes with 512-byte blocks (section alignment)
        let scan_end = std::cmp::min(scan_start + 4096, file_size.saturating_sub(4));
        let mut pbl_index = 0u32;

        file.seek(SeekFrom::Start(scan_start))?;
        let mut buffer = vec![0u8; 4096];
        let n = file.read(&mut buffer)?;

        let check_len = std::cmp::min(n, (scan_end - scan_start) as usize + 4);

        // Scan in 512-byte aligned increments first (matches PBL block size)
        let mut i = 0usize;
        while i + 4 <= check_len {
            if &buffer[i..i + 4] == HDR_MAGIC {
                let abs_offset = scan_start + i as u64;
                let pbl_size = file_size - abs_offset;
                pbl_index += 1;
                self.is_pb_exe = true;
                self.resources.push(PeResource {
                    name: format!("embedded_pbl_{}", pbl_index),
                    offset: abs_offset,
                    size: pbl_size,
                    resource_type: "PBL".to_string(),
                });
                // One contiguous appended PBL expected; stop here
                return Ok(());
            }
            // Advance by 512 (PBL block alignment), then byte-by-byte as fallback
            if i == 0 {
                i += 512;
            } else {
                i += 1;
            }
        }

        // Byte-granular fallback over the first 4096 bytes
        for i in 0..check_len.saturating_sub(3) {
            if &buffer[i..i + 4] == HDR_MAGIC {
                let abs_offset = scan_start + i as u64;
                let pbl_size = file_size - abs_offset;
                pbl_index += 1;
                self.is_pb_exe = true;
                self.resources.push(PeResource {
                    name: format!("embedded_pbl_{}", pbl_index),
                    offset: abs_offset,
                    size: pbl_size,
                    resource_type: "PBL".to_string(),
                });
                return Ok(());
            }
        }

        Ok(())
    }

    // ── Public accessors ──

    pub fn info(&self) -> PeInfo {
        PeInfo {
            is_pb_exe: self.is_pb_exe,
            is_64bit: self.is_64bit,
            machine_type: self.machine_type.clone(),
            timestamp: self.timestamp_str.clone(),
            resources: self.resources.clone(),
            embedded_pbl_count: self.resources.len(),
        }
    }

    // ── High-level API ──

    /// Get structured PE info result
    pub fn get_info_result(&self) -> PeInfoResult {
        let info = self.info();
        PeInfoResult {
            is_pb_exe: info.is_pb_exe,
            is_64bit: info.is_64bit,
            machine_type: info.machine_type,
            timestamp: info.timestamp,
            embedded_pbl_count: info.embedded_pbl_count,
            resources: info.resources.iter().map(|r| ResourceInfo {
                name: r.name.clone(),
                offset: r.offset,
                size: r.size,
                resource_type: r.resource_type.clone(),
            }).collect(),
        }
    }

    /// Detect file type from magic bytes
    pub fn detect_file_type(path: &str) -> Result<FileTypeResult, PeError> {
        let mut file = File::open(path)?;
        let mut header = [0u8; 1024];
        let bytes_read = file.read(&mut header)?;
        let metadata = std::fs::metadata(path)?;
        let size = metadata.len();

        let (file_type, is_pb) = if bytes_read >= 4 && &header[0..4] == b"HDR*" {
            ("pbl".to_string(), false)
        } else if bytes_read >= 4 && &header[0..4] == b"PBD*" {
            ("pbd".to_string(), false)
        } else if bytes_read >= 2 && &header[0..2] == b"MZ" {
            // Try full PE parse to detect appended PBL
            let is_pb = Self::quick_detect_pb_exe(path).unwrap_or(false);
            ("exe".to_string(), is_pb)
        } else {
            ("unknown".to_string(), false)
        };

        Ok(FileTypeResult { file_type, is_pb_exe: is_pb, version: None, size })
    }

    /// Quick check: parse sections, scan appended area for HDR*
    fn quick_detect_pb_exe(path: &str) -> Result<bool, PeError> {
        match PeParser::new(path) {
            Ok(parser) => Ok(parser.is_pb_exe),
            Err(_) => Ok(false),
        }
    }

    /// Extract embedded PBL resources to output directory
    pub fn extract_resources(&self, output_dir: &str) -> Result<ExtractResult, PeError> {
        std::fs::create_dir_all(output_dir)?;

        let mut extracted = 0;

        for resource in &self.resources {
            let mut file = File::open(&self.path)?;
            file.seek(SeekFrom::Start(resource.offset))?;

            let data_size = resource.size as usize;
            let mut data = vec![0u8; data_size];
            file.read_exact(&mut data)?;

            // Name with .pbl extension so downstream PBL parsers recognise it
            let out_name = if resource.resource_type == "PBL" {
                format!("{}/{}.pbl", output_dir, resource.name)
            } else {
                format!("{}/{}.bin", output_dir, resource.name)
            };
            std::fs::write(&out_name, &data)?;
            extracted += 1;
        }

        Ok(ExtractResult {
            success: true,
            pbd_count: extracted,
            output_path: Some(output_dir.to_string()),
            error: None,
        })
    }
}

/// Format PE COFF timestamp as a readable string
fn format_rfc2822(secs: u32) -> String {
    let s = secs as i64;
    let mut year = 1970;
    let mut days_left = s / 86400;
    loop {
        let days_in_year = if (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0) { 366 } else { 365 };
        if days_left < days_in_year {
            break;
        }
        days_left -= days_in_year;
        year += 1;
    }
    let month_days = if (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut month = 1;
    let mut rem = days_left as i64;
    for &md in month_days.iter() {
        if rem < md {
            break;
        }
        rem -= md;
        month += 1;
    }
    let day = rem + 1;
    let r = s % 86400;
    let hours = r / 3600;
    let minutes = (r % 3600) / 60;
    let seconds = r % 60;
    format!("{:04}-{:02}-{:02} {:02}:{:02}:{:02} UTC",
        year, month, day, hours, minutes, seconds)
}
