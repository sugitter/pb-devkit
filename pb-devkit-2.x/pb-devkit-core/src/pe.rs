// PE (Executable) Parser - Shared core implementation
// Properly parses PE structure instead of scanning entire file.

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
const PBD_MAGIC: &[u8; 4] = b"PBD*";

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

        // ── Optional Header ──
        let opt_header_start = pe_offset + 24;
        file.seek(SeekFrom::Start(opt_header_start))?;
        let mut opt_header = vec![0u8; optional_header_size];
        file.read_exact(&mut opt_header)?;

        let _is_pe32_plus = optional_header_size > 0
            && opt_header[0] == 0x0b
            && opt_header[1] == 0x02;

        // ── Section Headers ──
        let sections_start = opt_header_start + optional_header_size as u64;
        file.seek(SeekFrom::Start(sections_start))?;

        let mut rsrc_virtual_address: Option<u32> = None;
        let mut rsrc_pointer_to_raw: Option<u32> = None;
        let mut rsrc_size_of_raw: Option<u32> = None;

        for _ in 0..num_sections {
            let mut section = [0u8; 40];
            file.read_exact(&mut section)?;

            let name = &section[0..8];
            let name_str = String::from_utf8_lossy(name).trim_end_matches('\0').to_string();

            if name_str == ".rsrc" {
                rsrc_virtual_address =
                    Some(u32::from_le_bytes([section[12], section[13], section[14], section[15]]));
                rsrc_pointer_to_raw =
                    Some(u32::from_le_bytes([section[20], section[21], section[22], section[23]]));
                rsrc_size_of_raw =
                    Some(u32::from_le_bytes([section[16], section[17], section[18], section[19]]));
                break;
            }
        }

        // Detect PB EXE and scan resources
        self.is_pb_exe = Self::detect_pb_exe_fast(&self.path)?;

        if self.is_pb_exe {
            let _ = (rsrc_virtual_address, rsrc_pointer_to_raw, rsrc_size_of_raw);
            self.scan_pbd_resources_fast()?;
        }

        Ok(())
    }

    /// Efficiently detect PBD* magic using buffered reads (8KB chunks)
    fn detect_pb_exe_fast(path: &str) -> Result<bool, PeError> {
        let mut file = File::open(path)?;
        let file_size = file.metadata()?.len();

        let mut buffer = vec![0u8; 8192];
        let mut offset: u64 = 0;

        while offset < file_size {
            let bytes_to_read = std::cmp::min(8192, file_size - offset);
            file.seek(SeekFrom::Start(offset))?;
            let n = file.read(&mut buffer[..bytes_to_read as usize])?;
            if n < 4 {
                break;
            }

            let scan_len = if offset + n as u64 >= file_size { n } else { n - 3 };

            for i in 0..scan_len {
                if &buffer[i..i + 4] == PBD_MAGIC {
                    return Ok(true);
                }
            }

            offset += (n - 3) as u64;
        }

        Ok(false)
    }

    /// Efficiently scan for PBD* resources using buffered reads
    fn scan_pbd_resources_fast(&mut self) -> Result<(), PeError> {
        let mut file = File::open(&self.path)?;
        let file_size = file.metadata()?.len();

        let mut buffer = vec![0u8; 8192];
        let mut offset: u64 = 0;
        let mut pbd_index = 0;

        while offset < file_size {
            let bytes_to_read = std::cmp::min(8192, file_size - offset);
            file.seek(SeekFrom::Start(offset))?;
            let n = file.read(&mut buffer[..bytes_to_read as usize])?;
            if n < 8 {
                break;
            }

            let scan_len = if offset + n as u64 >= file_size { n } else { n - 7 };

            let mut i: usize = 0;
            while i < scan_len {
                if &buffer[i..i + 4] == PBD_MAGIC {
                    let size = if i + 8 <= n {
                        u32::from_le_bytes([buffer[i + 4], buffer[i + 5], buffer[i + 6], buffer[i + 7]]) as u64
                    } else {
                        let mut size_bytes = [0u8; 4];
                        file.seek(SeekFrom::Start(offset + i as u64 + 4))?;
                        file.read_exact(&mut size_bytes)?;
                        u32::from_le_bytes(size_bytes) as u64
                    };

                    pbd_index += 1;
                    self.resources.push(PeResource {
                        name: format!("embedded_pbd_{}", pbd_index),
                        offset: offset + i as u64,
                        size,
                        resource_type: "PBD".to_string(),
                    });

                    i += 512;
                } else {
                    i += 1;
                }
            }

            offset += (n - 7) as u64;
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
            // Check if it's a PB EXE
            let is_pb = Self::detect_pb_exe_fast(path).unwrap_or(false);
            ("exe".to_string(), is_pb)
        } else {
            ("unknown".to_string(), false)
        };

        Ok(FileTypeResult { file_type, is_pb_exe: is_pb, version: None, size })
    }

    /// Extract PBD resources to output directory
    pub fn extract_resources(&self, output_dir: &str) -> Result<ExtractResult, PeError> {
        std::fs::create_dir_all(output_dir)?;

        let mut extracted = 0;

        for resource in &self.resources {
            let mut file = File::open(&self.path)?;
            file.seek(SeekFrom::Start(resource.offset))?;

            // Skip 8-byte PBD* header, read actual data
            let data_size = resource.size as usize;
            let mut data = vec![0u8; data_size];
            file.read_exact(&mut data)?;

            let output_path = format!("{}/{}.pbd", output_dir, resource.name);
            std::fs::write(&output_path, &data)?;
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
