// Decompile - Shared core logic for extracting source from PBD/EXE files

use std::path::Path;

use crate::pbl::PblParser;
use crate::types::{DecompileEntry, DecompileListResult, DecompileResult};

/// List all entries in a PBD/EXE file
pub fn list_decompile_entries(path: &str) -> DecompileListResult {
    match PblParser::new(path) {
        Ok(parser) => {
            let entries: Vec<DecompileEntry> = parser.entries()
                .iter()
                .map(|e| DecompileEntry {
                    name: e.name.clone(),
                    entry_type: e.entry_type_name.clone(),
                    size: e.size,
                    is_source: e.is_source,
                })
                .collect();

            let total_count = entries.len();
            let source_count = entries.iter().filter(|e| e.is_source).count();

            DecompileListResult {
                success: true,
                entries,
                total_count,
                source_count,
                error: None,
            }
        }
        Err(_) => {
            DecompileListResult {
                success: false,
                entries: vec![],
                total_count: 0,
                source_count: 0,
                error: Some("Unable to parse file - not a valid PBL/PBD".to_string()),
            }
        }
    }
}

/// Decompile a single entry
pub fn decompile_entry(pbd_path: &str, entry_name: &str) -> DecompileResult {
    match PblParser::new(pbd_path) {
        Ok(parser) => {
            match parser.export_entry(entry_name) {
                Ok(source) => DecompileResult {
                    success: true,
                    name: entry_name.to_string(),
                    size: source.len(),
                    source: Some(source),
                    error: None,
                },
                Err(e) => DecompileResult {
                    success: false,
                    name: entry_name.to_string(),
                    source: None,
                    size: 0,
                    error: Some(e.to_string()),
                },
            }
        }
        Err(e) => DecompileResult {
            success: false,
            name: entry_name.to_string(),
            source: None,
            size: 0,
            error: Some(e.to_string()),
        },
    }
}

/// Decompile all entries from PBD/EXE
pub fn decompile_all(pbd_path: &str, output_dir: &str) -> Result<String, String> {
    let parser = PblParser::new(pbd_path).map_err(|e| e.to_string())?;

    let output_path = Path::new(output_dir);
    std::fs::create_dir_all(output_path).map_err(|e| e.to_string())?;

    let mut exported = 0;
    let mut failed = 0;

    for entry in parser.entries() {
        if entry.is_source {
            match parser.export_entry(&entry.name) {
                Ok(source) => {
                    let file_path = output_path.join(&entry.name);
                    if std::fs::write(&file_path, &source).is_ok() {
                        exported += 1;
                    } else {
                        failed += 1;
                    }
                }
                Err(_) => failed += 1,
            }
        }
    }

    Ok(format!("Exported: {}, Failed: {}", exported, failed))
}
