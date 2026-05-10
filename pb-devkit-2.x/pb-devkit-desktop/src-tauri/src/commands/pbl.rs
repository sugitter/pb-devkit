// PBL parsing commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::{PblEntryInfo, PblInfo, ExportResult};

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct ParseResult {
    pub success: bool,
    pub entries: Vec<PblEntryInfo>,
    pub is_unicode: bool,
    pub pb_version: String,
    pub total_count: usize,
    pub source_count: usize,
    pub compiled_count: usize,
    pub error: Option<String>,
}

/// Parse a PBL file and return entry list
#[tauri::command]
pub fn parse_pbl(path: String) -> ParseResult {
    match core::pbl::PblParser::new(&path) {
        Ok(parser) => {
            let entries: Vec<PblEntryInfo> = parser.entries()
                .iter()
                .map(|e| e.to_info())
                .collect();

            let total_count = entries.len();
            let source_count = entries.iter().filter(|e| e.is_source).count();
            let compiled_count = total_count - source_count;

            ParseResult {
                success: true,
                entries,
                is_unicode: parser.is_unicode(),
                pb_version: parser.version().as_str().to_string(),
                total_count,
                source_count,
                compiled_count,
                error: None,
            }
        }
        Err(e) => ParseResult {
            success: false,
            entries: vec![],
            is_unicode: false,
            pb_version: "Unknown".to_string(),
            total_count: 0,
            source_count: 0,
            compiled_count: 0,
            error: Some(e.to_string()),
        },
    }
}

/// Get PBL file information
#[tauri::command]
pub fn get_pbl_info(path: String) -> Result<PblInfo, String> {
    let parser = core::pbl::PblParser::new(&path).map_err(|e| e.to_string())?;
    parser.get_info().map_err(|e| e.to_string())
}

/// List all entries in a PBL file
#[tauri::command]
pub fn list_entries(path: String) -> Result<Vec<PblEntryInfo>, String> {
    let parser = core::pbl::PblParser::new(&path).map_err(|e| e.to_string())?;

    Ok(parser.entries()
        .iter()
        .map(|e| e.to_info())
        .collect())
}

/// Export a single entry source code
#[tauri::command]
pub fn export_entry(pbl_path: String, entry_name: String) -> Result<ExportResult, String> {
    let parser = core::pbl::PblParser::new(&pbl_path).map_err(|e| e.to_string())?;

    match parser.export_entry(&entry_name) {
        Ok(source) => Ok(ExportResult {
            success: true,
            name: entry_name,
            size: source.len(),
            source: Some(source),
            error: None,
        }),
        Err(e) => Ok(ExportResult {
            success: false,
            name: entry_name,
            source: None,
            size: 0,
            error: Some(e.to_string()),
        }),
    }
}

/// Export all source entries from a PBL file
#[tauri::command]
pub fn export_pbl(pbl_path: String, output_dir: String, by_type: bool) -> Result<String, String> {
    let parser = core::pbl::PblParser::new(&pbl_path).map_err(|e| e.to_string())?;

    match parser.export_pbl(&output_dir, by_type) {
        Ok(count) => Ok(format!("Exported {} entries to {}", count, output_dir)),
        Err(e) => Err(e.to_string()),
    }
}
