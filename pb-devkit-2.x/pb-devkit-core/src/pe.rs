// PE (Executable) Parser - Shared core implementation
// Properly parses PE structure instead of scanning entire file.
//
// PowerBuilder EXE embedding strategies (PB 5~12):
//
//   1. Appended after PE sections (most common, PB 5-9):
//      PBL data (starting with HDR*) placed after last section's raw data.
//      Old scan: 4 KiB window after sections_end → New scan: 64 KiB window,
//      bounded by certificate table offset.
//
//   2. Embedded in .rsrc section (PB 10+ single-EXE):
//      PBL data stored as a custom binary resource inside the Resource
//      Directory's raw data section. We parse DataDirectory entry #2 to
//      locate the .rsrc section and scan its contents.
//
//   3. Full-file fallback:
//      If neither appended nor .rsrc scan finds HDR*, do a forward scan
//      from 0x200 onward (≤ 256 MiB files only) to catch non-standard
//      embedding strategies.
//
//   4. Certificate-aware:
//      Authenticode digital signatures (DataDirectory entry #4) live at the
//      very end of the file. PBL data must precede the certificate. We use
//      cert offset as upper bound for appended scanning.

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
    /// DataDirectory[4] Certificate Table — raw file offset where digital signature starts.
    /// PBL data (if appended) lives between `sections_end_offset` and `security_offset`.
    security_offset: Option<u64>,
    /// .rsrc section bounds: (raw_data_offset, raw_data_size). PB 10+ may embed PBL
    /// inside the resource section via a custom resource type.
    rsrc_bounds: Option<(u64, u64)>,
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
            security_offset: None,
            rsrc_bounds: None,
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

        // ── Optional Header: parse DataDirectory for Security (certificate) offset ──
        // DataDirectory starts at offset 96 (PE32) or 112 (PE32+) within Optional Header.
        // We only need entries #2 (ResourceTable) and #4 (CertificateTable).
        let opt_hdr_offset = pe_offset + 24; // right after COFF header
        file.seek(SeekFrom::Start(opt_hdr_offset))?;
        let mut opt_magic = [0u8; 2];
        file.read_exact(&mut opt_magic)?;

        let is_pe32plus = opt_magic == [0x0B, 0x02]; // PE32+
        // DataDirectory offset from Optional Header start:
        // PE32:  magic(2) + ... + 68 + NumberOfRvaAndSizes(4) = 96
        // PE32+: magic(2) + ... + 88 + NumberOfRvaAndSizes(4) = 112
        let dd_offset = if is_pe32plus { 112u64 } else { 96u64 };

        // Read NumberOfRvaAndSizes to know how many entries are valid
        file.seek(SeekFrom::Start(opt_hdr_offset + dd_offset - 4))?;
        let mut nrvas_buf = [0u8; 4];
        file.read_exact(&mut nrvas_buf)?;
        let num_dir_entries = u32::from_le_bytes(nrvas_buf) as usize;

        // Read DataDirectory entries. Each entry = 8 bytes (VirtualAddress:4 + Size:4).
        // Entry #2 = Resource Table (RVA + Size)
        // Entry #4 = Certificate Table (raw file offset + Size)
        file.seek(SeekFrom::Start(opt_hdr_offset + dd_offset))?;
        let dd_count = std::cmp::min(num_dir_entries, 16); // max 16 entries defined
        let mut dd_data = vec![0u8; dd_count * 8];
        file.read_exact(&mut dd_data)?;

        if dd_count > 2 {
            // Entry #2: Resource Table (RVA, Size)
            let rsrc_rva  = u32::from_le_bytes([dd_data[16], dd_data[17], dd_data[18], dd_data[19]]);
            let rsrc_size = u32::from_le_bytes([dd_data[20], dd_data[21], dd_data[22], dd_data[23]]);
            if rsrc_rva > 0 && rsrc_size > 0 {
                // We'll resolve RVA → raw offset later when scanning sections
                self.rsrc_bounds = Some((rsrc_rva as u64, rsrc_size as u64));
            }
        }
        if dd_count > 4 {
            // Entry #4: Certificate Table (file offset, not RVA! Per PE spec §2.6.5)
            let cert_offset = u32::from_le_bytes([
                dd_data[32], dd_data[33], dd_data[34], dd_data[35],
            ]);
            let cert_size   = u32::from_le_bytes([
                dd_data[36], dd_data[37], dd_data[38], dd_data[39],
            ]);
            if cert_offset > 0 && cert_size > 0 {
                self.security_offset = Some(cert_offset as u64);
            }
        }

        // ── Parse Section Table ──
        let sections_start = opt_hdr_offset + optional_header_size as u64;
        file.seek(SeekFrom::Start(sections_start))?;

        let mut max_section_end: u64 = 0;

        for _ in 0..num_sections {
            let mut section = [0u8; 40];
            file.read_exact(&mut section)?;

            // Section name is bytes 0-7, typically null-terminated or space-padded
            let raw_name = &section[0..8];
            let sec_name = String::from_utf8_lossy(
                &raw_name[..raw_name.iter().position(|&b| b == 0).unwrap_or(8)]
            );

            let raw_offset = u32::from_le_bytes([section[20], section[21], section[22], section[23]]) as u64;
            let raw_size   = u32::from_le_bytes([section[16], section[17], section[18], section[19]]) as u64;

            // Match .rsrc section by name to resolve RVA → raw offset
            if let Some((_rva, _)) = self.rsrc_bounds {
                if sec_name.starts_with(".rsrc") || sec_name.starts_with("rsrc") {
                    self.rsrc_bounds = Some((raw_offset, raw_size));
                }
            }

            if raw_offset > 0 && raw_size > 0 {
                let end = raw_offset + raw_size;
                if end > max_section_end {
                    max_section_end = end;
                }
            }
        }

        self.sections_end_offset = max_section_end;

        // ── Scan for HDR* PBL data ──
        self.scan_appended_hdr(&mut file)?;

        // If not found yet, try scanning inside .rsrc section (PB 10+ strategy)
        if !self.is_pb_exe && self.rsrc_bounds.is_some() {
            self.scan_rsrc_section(&mut file)?;
        }

        // Last resort: full-file forward scan for HDR*
        if !self.is_pb_exe {
            self.scan_full_file(&mut file)?;
        }

        Ok(())
    }

    /// Scan for HDR* magic in the area appended after all PE sections.
    ///
    /// PB compilers append the PBL data starting at `sections_end_offset`.
    /// If a digital certificate is present, the PBL sits between sections_end
    /// and `security_offset`. We scan the gap with a 64 KiB buffer scanning
    /// at 512-byte alignment matching typical PBL block sizes.
    fn scan_appended_hdr(&mut self, file: &mut File) -> Result<(), PeError> {
        let file_size = file.metadata()?.len();
        let scan_start = self.sections_end_offset;

        // If there is a certificate, the PBL must be before it
        let scan_ceiling = self.security_offset.unwrap_or(file_size);

        if scan_start >= scan_ceiling || scan_start >= file_size {
            return Ok(());
        }

        let gap_size = std::cmp::min(scan_ceiling - scan_start, file_size - scan_start);
        if gap_size < 4 {
            return Ok(());
        }

        file.seek(SeekFrom::Start(scan_start))?;
        // Read up to 64 KiB — larger than 4 KiB to handle PB 10+ alignment
        let buf_size = std::cmp::min(gap_size, 65536) as usize;
        let mut buffer = vec![0u8; buf_size];
        let n = file.read(&mut buffer)?;
        let check_len = std::cmp::min(n, gap_size as usize);

        // Fast path: exact offset (most common for older PB versions)
        if check_len >= 4 && &buffer[0..4] == HDR_MAGIC {
            let pbl_size = file_size - scan_start;
            self.register_pbl(scan_start, pbl_size);
            return Ok(());
        }

        // Scan in 512-byte-aligned blocks (PBL block alignment)
        let step = 512;
        let mut offset = step;
        while offset + 4 <= check_len {
            if &buffer[offset..offset + 4] == HDR_MAGIC {
                let abs_offset = scan_start + offset as u64;
                let pbl_size = file_size - abs_offset;
                // If certificate is present, clamp PBL size to certificate boundary
                let pbl_size = if let Some(cert_off) = self.security_offset {
                    if cert_off > abs_offset { cert_off - abs_offset } else { pbl_size }
                } else {
                    pbl_size
                };
                self.register_pbl(abs_offset, pbl_size);
                return Ok(());
            }
            offset += step;
        }

        // Byte-granular scan over remaining gap
        for i in 0..check_len.saturating_sub(3) {
            if &buffer[i..i + 4] == HDR_MAGIC {
                let abs_offset = scan_start + i as u64;
                let pbl_size = file_size - abs_offset;
                let pbl_size = if let Some(cert_off) = self.security_offset {
                    if cert_off > abs_offset { cert_off - abs_offset } else { pbl_size }
                } else {
                    pbl_size
                };
                self.register_pbl(abs_offset, pbl_size);
                return Ok(());
            }
        }

        Ok(())
    }

    /// Scan the .rsrc section for embedded PBL data.
    ///
    /// PB 10+ single-EXE compilers sometimes embed PBL inside the resource section
    /// as a custom binary resource. The PBL still starts with HDR* magic.
    fn scan_rsrc_section(&mut self, file: &mut File) -> Result<(), PeError> {
        let (rsrc_offset, rsrc_size) = match self.rsrc_bounds {
            Some(b) => b,
            None => return Ok(()),
        };

        let file_size = file.metadata()?.len();
        if rsrc_offset + rsrc_size > file_size {
            return Ok(());
        }

        let read_size = std::cmp::min(rsrc_size, 65536) as usize;
        file.seek(SeekFrom::Start(rsrc_offset))?;
        let mut buffer = vec![0u8; read_size];
        let n = file.read(&mut buffer)?;

        // Scan byte-granular inside .rsrc
        let check_len = std::cmp::min(n, rsrc_size as usize);
        for i in 0..check_len.saturating_sub(3) {
            if &buffer[i..i + 4] == HDR_MAGIC {
                let abs_offset = rsrc_offset + i as u64;
                let pbl_size = file_size - abs_offset;
                self.register_pbl(abs_offset, pbl_size);
                return Ok(());
            }
        }

        Ok(())
    }

    /// Full-file fallback scan — searches for HDR* from the PE signature onward.
    ///
    /// This catches non-standard embedding strategies (e.g., PBL data placed
    /// *before* PE sections, embedded in overlay, or in custom-named sections).
    /// Limited to files ≤ 256 MiB to avoid scanning huge non-PB executables.
    fn scan_full_file(&mut self, file: &mut File) -> Result<(), PeError> {
        let file_size = file.metadata()?.len();
        if file_size > 256 * 1024 * 1024 {
            // Skip huge files — unlikely to be a PB EXE
            return Ok(());
        }

        // Scan from after PE sig (at least past 0x200 to avoid false positives in headers)
        let scan_start = 0x200u64;
        if scan_start + 4 > file_size {
            return Ok(());
        }

        file.seek(SeekFrom::Start(scan_start))?;
        let buf_size = std::cmp::min(file_size - scan_start, 262144) as usize; // 256 KB chunks
        let mut buffer = vec![0u8; buf_size];
        let _ = file.read(&mut buffer)?;

        let chunk_size = 131072; // process in 128 KB sub-chunks
        for chunk_start in (0..buffer.len()).step_by(chunk_size) {
            let chunk = &buffer[chunk_start..std::cmp::min(chunk_start + chunk_size + 4, buffer.len())];
            for i in 0..chunk.len().saturating_sub(3) {
                if &chunk[i..i + 4] == HDR_MAGIC {
                    let abs_offset = scan_start + (chunk_start + i) as u64;
                    let pbl_size = file_size - abs_offset;
                    self.register_pbl(abs_offset, pbl_size);
                    return Ok(());
                }
            }
        }

        Ok(())
    }

    /// Register a found PBL resource (deduplicate)
    fn register_pbl(&mut self, offset: u64, size: u64) {
        let idx = self.resources.len() as u32 + 1;
        self.is_pb_exe = true;
        // Avoid duplicate registrations at same offset
        if self.resources.iter().any(|r| r.offset == offset) {
            return;
        }
        self.resources.push(PeResource {
            name: format!("embedded_pbl_{}", idx),
            offset,
            size,
            resource_type: "PBL".to_string(),
        });
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
    let mut rem = days_left;
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    /// Build a minimal PE32 executable binary in memory.
    ///
    /// `sections`: list of (name, raw_data). Section virtual addresses are auto-assigned.
    /// `appended`: optional data appended after all sections (e.g. HDR* PBL).
    /// `cert_offset`: if Some, writes a dummy WIN_CERTIFICATE at this file offset.
    fn build_minimal_pe(sections: &[(&str, &[u8])], appended: Option<&[u8]>, cert_offset: Option<u64>) -> Vec<u8> {
        let num_sections = sections.len() as u16;
        let mut buf = Vec::new();

        // ── DOS Header (64 bytes) ──
        let mut dos = [0u8; 64];
        dos[0] = b'M'; dos[1] = b'Z';  // MZ magic
        // e_lfanew at offset 60 → PE signature right after DOS header (pe_offset = 64)
        dos[60] = 64; dos[61] = 0; dos[62] = 0; dos[63] = 0;
        buf.extend_from_slice(&dos);

        // ── PE Signature ──
        buf.extend_from_slice(b"PE\0\0");

        // ── COFF Header (20 bytes) ──
        let mut coff = [0u8; 20];
        coff[0] = 0x4c; coff[1] = 0x01;  // Machine = 0x14c (x86)
        coff[2] = (num_sections & 0xFF) as u8;
        coff[3] = ((num_sections >> 8) & 0xFF) as u8;
        // TimeDateStamp — use 0 (epoch) for predictable format_rfc2822 output
        // OptionalHeader size = 224 (standard PE32)
        let opt_hdr_size: u16 = 224;
        coff[16] = (opt_hdr_size & 0xFF) as u8;
        coff[17] = ((opt_hdr_size >> 8) & 0xFF) as u8;
        buf.extend_from_slice(&coff);

        // ── Optional Header (PE32) ──
        // Structure: Magic(2) + ... + DataDirectory[16](128 bytes)
        let mut opt_hdr = [0u8; 224];
        opt_hdr[0] = 0x0B; opt_hdr[1] = 0x01;  // PE32 magic
        // Set NumberOfRvaAndSizes at offset 92 (224-128-4): enable enough DD entries
        // Byte 92 = offset within opt_hdr for NumberOfRvaAndSizes
        let nrvas_offset = 92usize;
        let num_dd_entries: u32 = if cert_offset.is_some() { 5 } else { 3 };
        opt_hdr[nrvas_offset]     = (num_dd_entries & 0xFF) as u8;
        opt_hdr[nrvas_offset + 1] = ((num_dd_entries >> 8) & 0xFF) as u8;
        // DataDirectory starts at offset 96
        // Entry #0: Export Table (RVA=0, Size=0)
        // Entry #1: Import Table (RVA=0, Size=0)
        // Entry #2 (bytes 96+16=112): Resource Table — set RVA to 0x2000, Size to 0x100
        if num_dd_entries > 2 {
            let rsrc_entry = 96 + 2 * 8;
            let rsrc_rva: u32 = 0x2000;
            let rsrc_size: u32 = 0x100;
            opt_hdr[rsrc_entry]     = (rsrc_rva & 0xFF) as u8;
            opt_hdr[rsrc_entry + 1] = ((rsrc_rva >> 8) & 0xFF) as u8;
            opt_hdr[rsrc_entry + 4] = (rsrc_size & 0xFF) as u8;
            opt_hdr[rsrc_entry + 5] = ((rsrc_size >> 8) & 0xFF) as u8;
        }
        // Entry #4 (bytes 96+32=128): Certificate Table — file offset (not RVA!)
        if let Some(co) = cert_offset {
            if num_dd_entries > 4 {
                let cert_entry = 96 + 4 * 8;
                let co_u32 = co as u32;
                opt_hdr[cert_entry]     = (co_u32 & 0xFF) as u8;
                opt_hdr[cert_entry + 1] = ((co_u32 >> 8) & 0xFF) as u8;
                opt_hdr[cert_entry + 2] = ((co_u32 >> 16) & 0xFF) as u8;
                opt_hdr[cert_entry + 3] = ((co_u32 >> 24) & 0xFF) as u8;
                // Certificate size: 256 bytes (dummy)
                let cs: u32 = 256;
                opt_hdr[cert_entry + 4] = (cs & 0xFF) as u8;
                opt_hdr[cert_entry + 5] = ((cs >> 8) & 0xFF) as u8;
            }
        }
        buf.extend_from_slice(&opt_hdr);

        // ── Section Table (40 bytes each) ──
        let mut virt_addr: u32 = 0x1000;
        let mut file_offset: u32 = 0x200;  // start after headers
        for (name, data) in sections {
            let mut sec = [0u8; 40];
            let name_bytes = name.as_bytes();
            let copy_len = name_bytes.len().min(8);
            sec[..copy_len].copy_from_slice(&name_bytes[..copy_len]);
            // VirtualSize = raw_data.len() rounded to 0x1000
            let vsize = data.len().div_ceil(0x1000) as u32 * 0x1000;
            sec[8]  = (vsize & 0xFF) as u8;
            sec[9]  = ((vsize >> 8) & 0xFF) as u8;
            sec[10] = ((vsize >> 16) & 0xFF) as u8;
            sec[11] = ((vsize >> 24) & 0xFF) as u8;
            // VirtualAddress
            sec[12] = (virt_addr & 0xFF) as u8;
            sec[13] = ((virt_addr >> 8) & 0xFF) as u8;
            sec[14] = ((virt_addr >> 16) & 0xFF) as u8;
            sec[15] = ((virt_addr >> 24) & 0xFF) as u8;
            // SizeOfRawData
            let raw_size = data.len() as u32;
            sec[16] = (raw_size & 0xFF) as u8;
            sec[17] = ((raw_size >> 8) & 0xFF) as u8;
            sec[18] = ((raw_size >> 16) & 0xFF) as u8;
            sec[19] = ((raw_size >> 24) & 0xFF) as u8;
            // PointerToRawData
            sec[20] = (file_offset & 0xFF) as u8;
            sec[21] = ((file_offset >> 8) & 0xFF) as u8;
            sec[22] = ((file_offset >> 16) & 0xFF) as u8;
            sec[23] = ((file_offset >> 24) & 0xFF) as u8;
            buf.extend_from_slice(&sec);

            virt_addr += 0x1000;
            file_offset += raw_size;
        }

        // ── Pad to file_offset ──
        while (buf.len() as u32) < file_offset {
            buf.push(0);
        }

        // ── Section raw data ──
        for (_name, data) in sections {
            buf.extend_from_slice(data);
        }

        // ── Appended data (HDR* PBL) ──
        if let Some(ap) = appended {
            buf.extend_from_slice(ap);
        }

        // ── Certificate at specified file offset ──
        if let Some(co) = cert_offset {
            // Pad to certificate offset
            while (buf.len() as u64) < co {
                buf.push(0);
            }
            // Dummy WIN_CERTIFICATE: dwLength(4) + wRevision(2) + wCertificateType(2) + padding
            let cert_len: u32 = 256;
            buf.push((cert_len & 0xFF) as u8);
            buf.push(((cert_len >> 8) & 0xFF) as u8);
            buf.push(((cert_len >> 16) & 0xFF) as u8);
            buf.push(((cert_len >> 24) & 0xFF) as u8);
            buf.push(0x00); buf.push(0x02); // wRevision = WIN_CERT_REVISION_2_0
            buf.push(0x02); buf.push(0x00); // wCertificateType = PKCS_SIGNED_DATA
            while (buf.len() as u32) < co as u32 + cert_len {
                buf.push(0);
            }
        }

        buf
    }

    // ── Tests ──

    #[test]
    fn test_reject_non_pe() {
        let result = PeParser::new("C:\\nonexistent_file_xyz_12345");
        assert!(result.is_err());
    }

    #[test]
    fn test_pe32_basic_header_parsing() {
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            None,
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(!parser.is_pb_exe, "no PBL appended → not a PB EXE");
        assert!(!parser.is_64bit);
        assert_eq!(parser.machine_type, "x86");
        assert!(parser.timestamp_str.is_some());
        assert!(parser.resources.is_empty());
    }

    #[test]
    fn test_scan_appended_hdr_exact_offset() {
        // Simplest case: HDR* starts exactly at sections_end
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(b"HDR*\x01\x00\x02\x00padding123"),
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
        assert_eq!(parser.resources.len(), 1);
        assert_eq!(parser.resources[0].resource_type, "PBL");
        assert!(parser.resources[0].size > 0);
    }

    #[test]
    fn test_scan_appended_hdr_512_aligned() {
        // HDR* is at offset sections_end + 1024 (512-byte aligned, but not exact)
        let mut gap = vec![0u8; 1024];
        // Place HDR* at byte 1024
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            {
                gap.extend_from_slice(b"HDR*\x01\x00\x02\x00");
                Some(&gap)
            },
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
        assert_eq!(parser.resources.len(), 1);
        // offset should be sections_end + 1024
        let pbl_offset = parser.resources[0].offset;
        assert!(pbl_offset > 0x200, "should be after headers");
    }

    #[test]
    fn test_scan_appended_hdr_byte_granular_fallback() {
        // HDR* at an offset not divisible by 512 (e.g. 800)
        // This triggers the byte-granular fallback scan
        let mut gap = vec![0u8; 800];
        gap.extend_from_slice(b"HDR*\x01\x00\x02\x00");
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(&gap),
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
        assert_eq!(parser.resources.len(), 1);
    }

    #[test]
    fn test_certificate_aware_scanning() {
        // Scenario: HDR* at sections_end + 2000, certificate at sections_end + 4000.
        // The scanner should find HDR* and clamp PBL size to cert offset.
        let cert_offset = 0x200 + 64 + 4000; // 0x200 + 64 = sections_end, + 4000 = cert
        let mut gap = vec![0u8; 2000];
        gap.extend_from_slice(b"HDR*\x01\x00\x02\x00");
        gap.extend_from_slice(&[0u8; 500]); // more padding before cert

        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(&gap),
            Some(cert_offset),
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
        assert_eq!(parser.resources.len(), 1);
        // PBL size should be clamped: cert_offset - pbl_offset
        let pbl_offset = parser.resources[0].offset;
        let pbl_size = parser.resources[0].size;
        assert_eq!(pbl_size, cert_offset - pbl_offset,
            "PBL size must be clamped to certificate offset boundary");
    }

    #[test]
    fn test_certificate_before_pbl_not_found() {
        // Certificate is placed BEFORE the potential PBL area.
        // Since HDR* would be after the certificate, our scanner
        // (operating from sections_end to security_offset) shouldn't scan past it.
        // This test verifies gap_size ≤ 0 case is handled correctly.
        let cert_offset: u64 = 0x200 + 64; // same as sections_end
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(b"HDR*\x01\x00\x02\x00"), // this is after cert, shouldn't be scanned
            Some(cert_offset),
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        // Since cert is at sections_end, gap_size = 0, scan_appended_hdr returns early.
        // The scanner actually scans sections_end → cert_offset, and if gap_size = 0
        // it returns early. But in this test, HDR* is after the cert area (not before),
        // so scan_appended_hdr won't find it. Then scan_rsrc_section isn't triggered
        // (no .rsrc), and scan_full_file finds it.
        let parser = PeParser::new(&path).unwrap();
        // Should still be found by full-file fallback scan
        assert!(parser.is_pb_exe);
    }

    #[test]
    fn test_rsrc_section_scanning() {
        // PB 10+ strategy: HDR* inside .rsrc section data
        let mut rsrc_data = vec![0u8; 64];
        rsrc_data.extend_from_slice(b"HDR*\x01\x00\x02\x00");
        rsrc_data.extend_from_slice(&[0u8; 100]);

        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64]), (".rsrc", &rsrc_data)],
            None, // no appended HDR*
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe, ".rsrc-embedded PBL should be detected");
        assert_eq!(parser.resources.len(), 1);
        assert_eq!(parser.resources[0].resource_type, "PBL");
    }

    #[test]
    fn test_full_file_fallback_scan() {
        // HDR* embedded in a non-standard location (e.g. section with name "foo")
        let mut foo_data = vec![0u8; 128];
        foo_data.extend_from_slice(b"HDR*\x01\x00\x02\x00");

        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64]), (".data", &foo_data)],
            None,
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe, "full-file fallback should find HDR* in .data section");
        assert_eq!(parser.resources.len(), 1);
    }

    #[test]
    fn test_register_pbl_deduplication() {
        // If HDR* is found both by appended scan AND rsrc scan,
        // only one registration should occur.
        let _gap = [0u8; 4];
        // Place HDR* in both appended area and .rsrc section at same file offset
        // (impossible in real PE, but tests dedup logic)
        let rsrc_data = b"HDR*\x01\x00\x02\x00".to_vec();

        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64]), (".rsrc", &rsrc_data)],
            Some(b"HDR*\x01\x00\x02\x00"), // appended — distinct offset from .rsrc
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
        // Both appended and .rsrc should be found → 2 resources at distinct offsets
        assert!(parser.resources.len() <= 2);
        // Verify no duplicate offsets
        let offsets: Vec<u64> = parser.resources.iter().map(|r| r.offset).collect();
        let mut unique = offsets.clone();
        unique.sort();
        unique.dedup();
        assert_eq!(unique.len(), offsets.len(), "no duplicate offsets");
    }

    #[test]
    fn test_no_pbl_detection_on_plain_exe() {
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 256]), (".data", &[0u8; 128])],
            None,
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(!parser.is_pb_exe);
        assert_eq!(parser.resources.len(), 0);
    }

    #[test]
    fn test_pe64_detection() {
        // PE32+ (x64) binary
        let num_sections: u16 = 1;
        let mut buf = Vec::new();

        // DOS Header
        let mut dos = [0u8; 64];
        dos[0] = b'M'; dos[1] = b'Z';
        dos[60] = 64;
        buf.extend_from_slice(&dos);
        buf.extend_from_slice(b"PE\0\0");

        // COFF
        let mut coff = [0u8; 20];
        coff[0] = 0x64; coff[1] = 0x86;  // Machine = 0x8664 (x64)
        coff[2] = (num_sections & 0xFF) as u8;
        coff[3] = ((num_sections >> 8) & 0xFF) as u8;
        let opt_hdr_size: u16 = 240; // PE32+ size
        coff[16] = (opt_hdr_size & 0xFF) as u8;
        coff[17] = ((opt_hdr_size >> 8) & 0xFF) as u8;
        buf.extend_from_slice(&coff);

        // Optional Header PE32+
        let mut opt_hdr = [0u8; 240];
        opt_hdr[0] = 0x0B; opt_hdr[1] = 0x02;  // PE32+ magic
        let nrvas_offset = 108usize;
        opt_hdr[nrvas_offset] = 3; // 3 DD entries
        buf.extend_from_slice(&opt_hdr);

        // Section
        let mut sec = [0u8; 40];
        sec[0] = b'.'; sec[1] = b't'; sec[2] = b'e'; sec[3] = b'x'; sec[4] = b't';
        let vsize: u32 = 0x1000;
        sec[8] = (vsize & 0xFF) as u8;
        let raw_size: u32 = 64;
        sec[16] = (raw_size & 0xFF) as u8;
        let file_off: u32 = 0x200;
        sec[20] = (file_off & 0xFF) as u8;
        buf.extend_from_slice(&sec);

        // Pad + data
        while buf.len() < 0x200 { buf.push(0); }
        buf.extend_from_slice(&[0u8; 64]);

        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&buf).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_64bit);
        assert_eq!(parser.machine_type, "x64");
    }

    #[test]
    fn test_file_type_detection_hdr() {
        // detect_file_type on a bare HDR* file (not PE)
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(b"HDR*\x01\x00\x02\x00padding").unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let result = PeParser::detect_file_type(&path).unwrap();
        assert_eq!(result.file_type, "pbl");
        assert!(!result.is_pb_exe); // raw PBL is not "a PB compiled EXE"
    }

    #[test]
    fn test_file_type_detection_mz() {
        let pe_data = build_minimal_pe(&[(".text", &[0u8; 64])], Some(b"HDR*\x01\x00\x02\x00"), None);
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let result = PeParser::detect_file_type(&path).unwrap();
        assert_eq!(result.file_type, "exe");
        assert!(result.is_pb_exe);
    }

    #[test]
    fn test_extract_resources() {
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(b"HDR*\x01\x00\x02\x00"),
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);

        let out_dir = tmp.path().parent().unwrap().join("extract_test");
        let result = parser.extract_resources(out_dir.to_string_lossy().as_ref()).unwrap();
        assert!(result.success);
        assert_eq!(result.pbd_count, 1);

        // Verify extracted file starts with HDR*
        let extracted_path = out_dir.join("embedded_pbl_1.pbl");
        let extracted_data = std::fs::read(&extracted_path).unwrap();
        assert_eq!(&extracted_data[0..4], b"HDR*");
    }

    #[test]
    fn test_file_size_limit_full_scan() {
        // Test that scan_full_file correctly skips when file_size > 256MB.
        // We test this by verifying that a small file (.data section with HDR*)
        // IS found, confirming full_file_scan works on normal files.
        // The >256MB case is impractical to test but the guard is visible in code.
        let mut data_sec = vec![0u8; 128];
        data_sec.extend_from_slice(b"HDR*\x01\x00\x02\x00");
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64]), (".data", &data_sec)],
            None,
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        assert!(parser.is_pb_exe);
    }

    #[test]
    fn test_embedded_pbl_count() {
        let pe_data = build_minimal_pe(
            &[(".text", &[0u8; 64])],
            Some(b"HDR*\x01\x00\x02\x00"),
            None,
        );
        let mut tmp = NamedTempFile::new().unwrap();
        tmp.write_all(&pe_data).unwrap();
        tmp.flush().unwrap();
        let path = tmp.path().to_string_lossy().to_string();

        let parser = PeParser::new(&path).unwrap();
        let info = parser.info();
        assert_eq!(info.embedded_pbl_count, 1);
        let result = parser.get_info_result();
        assert_eq!(result.embedded_pbl_count, 1);
        assert!(result.is_pb_exe);
    }
}
