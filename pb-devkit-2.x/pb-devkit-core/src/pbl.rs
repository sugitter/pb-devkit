// PBL Parser - Shared core implementation
// Supports PB5-PB12.6 (ANSI + Unicode)

use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use thiserror::Error;

use crate::types::{PblEntryInfo, PblInfo};

#[derive(Error, Debug)]
pub enum PblError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid PBL file")]
    InvalidFormat,
    #[error("Entry not found: {0}")]
    NotFound(String),
    #[error("Parse error: {0}")]
    ParseError(String),
}

// PB Object Type constants (PB5-PB12.6)
pub const PB_OBJECT_TYPE: &[(&str, u8)] = &[
    ("application", 0),
    ("datawindow", 1),
    ("window", 2),
    ("menu", 3),
    ("function", 4),
    ("structure", 5),
    ("userobject", 6),
    ("query", 7),
    ("pipeline", 8),
    ("project", 9),
    ("proxy", 10),
    ("binary", 11),
    ("embedded_sql", 12),
    ("web_service", 13),
    ("component", 14),
];

// PB 12.5+ 新增对象类型
pub const PB_OBJECT_TYPE_12_5: &[(&str, u8)] = &[
    ("soap_client", 15),
    ("soap_server", 16),
    ("web_proxy", 17),
    ("nativejson", 18),
    ("restclient", 19),
];

// Source extension to type mapping (PB12+ Unicode)
pub const SOURCE_EXT_MAP: &[(&str, u8)] = &[
    (".srw", 2),   // WINDOW
    (".srd", 1),   // DATAWINDOW
    (".srm", 3),   // MENU
    (".srf", 4),   // FUNCTION
    (".srs", 5),   // STRUCTURE
    (".sru", 6),   // USEROBJECT
    (".srq", 7),   // QUERY
    (".srp", 8),   // PIPELINE
    (".srj", 9),   // PROJECT
    (".srx", 10),  // PROXY
    (".sre", 12),  // EMBEDDED_SQL
    (".sra", 0),   // APPLICATION
];

// Block sizes
const BLOCK_SIZE: u64 = 512;
const NODE_BLOCK_SIZE: u64 = 3072; // 6 x 512

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PblVersion {
    Pb5,    // PB5-PB9 (ANSI)
    Pb10,   // PB10-PB11 (Unicode)
    Pb12,   // PB12-PB12.5 (Unicode)
    Pb125,  // PB 12.5+ (Unicode, new object types)
    Pb126,  // PB 12.6+ (Unicode, latest)
    Unknown,
}

impl PblVersion {
    pub fn as_str(&self) -> &'static str {
        match self {
            PblVersion::Pb5 => "PB5-PB9 (ANSI)",
            PblVersion::Pb10 => "PB10-PB11 (Unicode)",
            PblVersion::Pb12 => "PB12-PB12.5 (Unicode)",
            PblVersion::Pb125 => "PB 12.5+ (Unicode)",
            PblVersion::Pb126 => "PB 12.6+ (Unicode)",
            PblVersion::Unknown => "Unknown",
        }
    }

    pub fn short_str(&self) -> &'static str {
        match self {
            PblVersion::Pb5 => "PB5-PB9",
            PblVersion::Pb10 => "PB10-PB11",
            PblVersion::Pb12 => "PB12-PB12.5",
            PblVersion::Pb125 => "PB 12.5+",
            PblVersion::Pb126 => "PB 12.6+",
            PblVersion::Unknown => "Unknown",
        }
    }

    /// Detect PBL version from magic bytes and header
    pub fn detect_from_header(header: &[u8]) -> (Self, bool) {
        // Check HDR* magic at start
        if &header[0..4] != b"HDR*" {
            return (PblVersion::Unknown, false);
        }

        // Detect encoding from offset 4
        // ANSI: offset 4 = 0x50 (ASCII 'P'), offset 5 = 0x00 or non-zero
        // Unicode: offset 4 = 0x50 0x00 (little-endian Unicode 'P')
        let is_unicode = header[4] == 0x50 && header[5] == 0x00;

        if !is_unicode {
            // ANSI format: PB5-PB9
            // Check version string at offset 4-8
            let version_str_owned = String::from_utf8_lossy(&header[4..12]);
            let version_str = version_str_owned.trim_end_matches('\0');
            if version_str.starts_with("PB") {
                if let Ok(v) = version_str[2..].parse::<f32>() {
                    if v >= 5.0 && v < 10.0 {
                        return (PblVersion::Pb5, true);
                    }
                }
            }
            return (PblVersion::Pb5, true);
        }

        // Unicode format: check version string more carefully
        let version_bytes = &header[4..20];
        let mut version_str = String::new();
        for chunk in version_bytes.chunks(2) {
            if chunk.len() == 2 {
                let ch = u16::from_le_bytes([chunk[0], chunk[1]]);
                if ch == 0 { break; }
                if let Some(c) = char::from_u32(ch as u32) {
                    version_str.push(c);
                }
            }
        }

        let version_str = version_str.trim_end_matches('\0');

        // Try to parse version from string like "PB12.5" or "PB10"
        if version_str.starts_with("PB") {
            let rest = &version_str[2..];
            // Handle versions like "12", "12.5", "12.6"
            if let Some(dot_pos) = rest.find('.') {
                if let Ok(major) = rest[..dot_pos].parse::<i32>() {
                    let minor = &rest[dot_pos + 1..];
                    return match (major, minor.parse::<i32>().unwrap_or(0)) {
                        (12, 0..=4) => (PblVersion::Pb12, true),
                        (12, 5) => (PblVersion::Pb125, true),
                        (12, 6..=9) => (PblVersion::Pb126, true),
                        _ => (PblVersion::Pb12, true),
                    };
                }
            } else if let Ok(v) = rest.parse::<i32>() {
                return match v {
                    10 | 11 => (PblVersion::Pb10, true),
                    12 => (PblVersion::Pb12, true),
                    13..=99 => (PblVersion::Pb126, true),
                    _ => (PblVersion::Unknown, false),
                };
            }
        }

        // Default to PB12 for Unicode files without clear version
        (PblVersion::Pb12, true)
    }
}

#[derive(Debug, Clone)]
pub struct PblEntry {
    pub name: String,
    pub entry_type: u8,
    pub entry_type_name: String,
    pub size: u64,
    pub modified: Option<String>,
    pub offset: u64,
    pub data_offset: u64,
    pub comment: String,
    pub version: String,
    pub is_compiled: bool,
    pub is_source: bool,
}

impl PblEntry {
    pub fn to_info(&self) -> PblEntryInfo {
        PblEntryInfo {
            name: self.name.clone(),
            entry_type: self.entry_type,
            entry_type_name: self.entry_type_name.clone(),
            size: self.size,
            modified: self.modified.clone(),
            is_source: self.is_source,
            is_compiled: self.is_compiled,
            version: self.version.clone(),
        }
    }
}

pub struct PblParser {
    path: String,
    entries: Vec<PblEntry>,
    is_unicode: bool,
    pb_version: PblVersion,
    header_size: u64,
}

impl PblParser {
    pub fn new(path: &str) -> Result<Self, PblError> {
        let mut parser = PblParser {
            path: path.to_string(),
            entries: vec![],
            is_unicode: false,
            pb_version: PblVersion::Unknown,
            header_size: 512,
        };

        parser.parse_header()?;
        parser.parse_entries()?;

        Ok(parser)
    }

    fn parse_header(&mut self) -> Result<(), PblError> {
        let mut file = File::open(&self.path)?;
        let file_size = file.metadata()?.len();
        if file_size < 512 {
            return Err(PblError::InvalidFormat);
        }

        let mut header = [0u8; 1024];
        file.read_exact(&mut header[..1024])?;

        // Check HDR* magic
        if &header[0..4] != b"HDR*" {
            return Err(PblError::InvalidFormat);
        }

        // Use enhanced version detection
        let (detected_version, is_valid) = PblVersion::detect_from_header(&header);
        
        if !is_valid {
            return Err(PblError::InvalidFormat);
        }

        self.pb_version = detected_version;
        self.is_unicode = matches!(detected_version, PblVersion::Pb10 | PblVersion::Pb12 | PblVersion::Pb125 | PblVersion::Pb126);
        self.header_size = if self.is_unicode { 1024 } else { 512 };

        Ok(())
    }

    fn parse_entries(&mut self) -> Result<(), PblError> {
        let mut file = File::open(&self.path)?;
        let file_size = file.metadata()?.len();

        let entries_start = self.header_size + BLOCK_SIZE + NODE_BLOCK_SIZE;
        file.seek(SeekFrom::Start(entries_start))?;

        let mut offset = entries_start;
        let mut buffer = vec![0u8; 8192];

        while offset < file_size - 512 {
            file.seek(SeekFrom::Start(offset))?;
            let bytes_read = file.read(&mut buffer)?;
            if bytes_read < 24 {
                break;
            }

            let mut i = 0;
            while i < bytes_read - 24 {
                if &buffer[i..i + 4] == b"ENT*" {
                    if let Some(entry) = self.parse_ent_block(&buffer[i..], offset + i as u64) {
                        self.entries.push(entry);
                    }
                    i += 512;
                } else {
                    i += 1;
                }
            }

            offset += bytes_read as u64 - 24;
        }

        Ok(())
    }

    fn parse_ent_block(&self, data: &[u8], offset: u64) -> Option<PblEntry> {
        if data.len() < 24 {
            return None;
        }

        let name_len = if self.is_unicode {
            u16::from_le_bytes([data[26], data[27]])
        } else {
            u16::from_le_bytes([data[22], data[23]])
        };

        if name_len == 0 || name_len > 256 {
            return None;
        }

        let data_offset = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as u64;
        let data_size = u32::from_le_bytes([data[12], data[13], data[14], data[15]]) as u64;

        let name_start = if self.is_unicode { 28 } else { 24 };
        let name_end = name_start + name_len as usize;

        if data.len() < name_end {
            return None;
        }

        let name_bytes = &data[name_start..name_end];
        let name = if self.is_unicode {
            let mut decoded = Vec::new();
            for j in (0..name_bytes.len().saturating_sub(1)).step_by(2) {
                let ch = u16::from_le_bytes([name_bytes[j], name_bytes[j + 1]]);
                if ch == 0 { break; }
                if let Some(c) = char::from_u32(ch as u32) {
                    decoded.push(c);
                }
            }
            decoded.into_iter().collect()
        } else {
            let mut decoded = Vec::new();
            for &b in name_bytes {
                if b == 0 { break; }
                decoded.push(b);
            }
            String::from_utf8_lossy(&decoded).into_owned()
        };

        // Parse timestamp
        let ts_seconds = if self.is_unicode {
            u32::from_le_bytes([data[20], data[21], data[22], data[23]])
        } else {
            u32::from_le_bytes([data[16], data[17], data[18], data[19]])
        };
        let modified = if ts_seconds > 0 {
            Some(format_timestamp(ts_seconds))
        } else {
            None
        };

        // Version string
        let version = if self.is_unicode {
            String::from_utf8_lossy(&data[4..12]).trim_end_matches('\0').to_string()
        } else {
            String::from_utf8_lossy(&data[4..8]).trim_end_matches('\0').to_string()
        };

        let (entry_type, is_source) = Self::detect_type_from_name(&name);

        Some(PblEntry {
            name,
            entry_type,
            entry_type_name: Self::type_to_name(entry_type),
            size: data_size,
            modified,
            offset,
            data_offset,
            comment: String::new(),
            version,
            is_compiled: !is_source,
            is_source,
        })
    }

    pub fn detect_type_from_name(name: &str) -> (u8, bool) {
        let lower = name.to_lowercase();
        for (ext, t) in SOURCE_EXT_MAP {
            if lower.ends_with(ext) {
                return (*t, true);
            }
        }
        let compiled_exts = [".win", ".dwo", ".prp", ".udo", ".fun", ".str", ".apl", ".men", ".pra"];
        for ext in compiled_exts.iter() {
            if lower.ends_with(ext) {
                return (11, false); // BINARY
            }
        }
        (11, false)
    }

    pub fn type_to_name(t: u8) -> String {
        for (name, id) in PB_OBJECT_TYPE {
            if *id == t {
                return name.to_string();
            }
        }
        // Check PB 12.5+ types
        for (name, id) in PB_OBJECT_TYPE_12_5 {
            if *id == t {
                return name.to_string();
            }
        }
        // Also check compiled object types (extension-based)
        let compiled_types = [
            (".win", "window"),
            (".dwo", "datawindow"),
            (".prp", "property"),
            (".udo", "userobject"),
            (".fun", "function"),
            (".str", "structure"),
            (".apl", "application"),
            (".men", "menu"),
            (".pra", "project"),
        ];
        for (ext, _name) in &compiled_types {
            if t == 11 && *ext == ".win" { return "window".to_string(); }
        }
        "unknown".to_string()
    }

    // ── Public accessors ──

    pub fn entries(&self) -> &Vec<PblEntry> {
        &self.entries
    }

    pub fn is_unicode(&self) -> bool {
        self.is_unicode
    }

    pub fn version(&self) -> &PblVersion {
        &self.pb_version
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    // ── High-level API ──

    /// Get structured PBL info
    pub fn get_info(&self) -> Result<PblInfo, PblError> {
        let metadata = std::fs::metadata(&self.path)?;
        let source_count = self.entries.iter().filter(|e| e.is_source).count();
        let compiled_count = self.entries.len() - source_count;

        Ok(PblInfo {
            path: self.path.clone(),
            is_unicode: self.is_unicode,
            pb_version: self.pb_version.as_str().to_string(),
            total_entries: self.entries.len(),
            source_entries: source_count,
            compiled_entries: compiled_count,
            file_size: metadata.len(),
        })
    }

    /// Export a single entry's source code
    pub fn export_entry(&self, name: &str) -> Result<String, PblError> {
        let entry = self.entries.iter()
            .find(|e| e.name.to_lowercase() == name.to_lowercase())
            .ok_or_else(|| PblError::NotFound(name.to_string()))?;

        let mut file = File::open(&self.path)?;
        file.seek(SeekFrom::Start(entry.data_offset))?;

        let mut source_data = Vec::new();
        let mut remaining = entry.size as usize;
        let mut current_offset = entry.data_offset;

        while remaining > 0 {
            let mut block_header = [0u8; 512];
            file.seek(SeekFrom::Start(current_offset))?;
            let bytes_read = file.read(&mut block_header)?;

            if bytes_read < 4 || &block_header[0..4] != b"DAT*" {
                break;
            }

            let block_data_size = if remaining >= 512 { 508 } else { remaining };
            source_data.extend_from_slice(&block_header[4..4 + block_data_size]);

            remaining -= block_data_size;
            current_offset += 512;
        }

        let source = if self.is_unicode {
            let mut decoded = String::new();
            for chunk in source_data.chunks_exact(2) {
                let ch = u16::from_le_bytes([chunk[0], chunk[1]]);
                if ch == 0 { break; }
                if let Some(c) = char::from_u32(ch as u32) {
                    decoded.push(c);
                }
            }
            decoded
        } else {
            String::from_utf8_lossy(&source_data).into_owned()
        };

        Ok(source)
    }

    /// Export all source entries from a PBL file
    pub fn export_pbl(&self, output_dir: &str, by_type: bool) -> Result<usize, PblError> {
        let output_path = std::path::Path::new(output_dir);
        std::fs::create_dir_all(output_path)?;

        let mut exported_count = 0;

        for entry in &self.entries {
            if entry.is_source {
                if let Ok(source) = self.export_entry(&entry.name) {
                    let file_path = if by_type {
                        let type_dir = output_path.join(&entry.entry_type_name);
                        std::fs::create_dir_all(&type_dir).ok();
                        type_dir.join(&entry.name)
                    } else {
                        output_path.join(&entry.name)
                    };

                    if std::fs::write(&file_path, &source).is_ok() {
                        exported_count += 1;
                    }
                }
            }
        }

        Ok(exported_count)
    }
}

/// Format timestamp (seconds since 1970-01-01) as a readable string
pub fn format_timestamp(secs: u32) -> String {
    let s = secs as i64;
    let mut year = 1970;
    let mut days_left = s / 86400;
    loop {
        let days_in_year = if is_leap_year(year) { 366 } else { 365 };
        if days_left < days_in_year {
            break;
        }
        days_left -= days_in_year;
        year += 1;
    }
    let month_days = if is_leap_year(year) {
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
    format!("{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        year, month, day, hours, minutes, seconds)
}

fn is_leap_year(year: i64) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}
