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
                error: Some("Unable to parse file - not a valid PBL/PBD/EXE".to_string()),
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
/// Note: For EXE files with only compiled objects (no embedded source),
/// use the pb-devkit-1.x Python CLI which includes a full binary decompiler.
pub fn decompile_all(pbd_path: &str, output_dir: &str) -> Result<String, String> {
    let output_path = Path::new(output_dir);
    // Create output directory first — even if parsing fails,
    // user should have the directory ready
    std::fs::create_dir_all(output_path).map_err(|e| e.to_string())?;

    let parser = PblParser::new(pbd_path).map_err(|e| e.to_string())?;

    let total = parser.entries().len();
    let source_entries: Vec<_> = parser.entries().iter().filter(|e| e.is_source).cloned().collect();

    if source_entries.is_empty() && total > 0 {
        return Ok(format!(
            "Found {} entries, all compiled binaries (no embedded source).\n\
             Tip: Use pb-devkit 1.x Python CLI for full binary decompile:\n  \
             pb export \"{}\" -o \"{}\"",
            total, pbd_path, output_dir
        ));
    }

    let mut exported = 0;
    let mut failed = 0;

    for entry in &source_entries {
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

    Ok(format!("Exported: {} source files, Failed: {} (total entries: {})", exported, failed, total))
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_decompile_entries_invalid_file() {
        let result = list_decompile_entries("/nonexistent/file.pbd");
        assert!(!result.success);
        assert!(result.error.is_some());
        assert_eq!(result.total_count, 0);
    }

    #[test]
    fn test_list_decompile_entries_valid_structure() {
        // Test with non-existent file to verify error struct shape
        let result = list_decompile_entries("/nonexistent/file.pbd");
        assert!(!result.success);
        assert!(result.entries.is_empty());
        assert_eq!(result.source_count, 0);
    }

    #[test]
    fn test_decompile_entry_invalid_file() {
        let result = decompile_entry("/nonexistent/file.pbd", "w_main");
        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.source.is_none());
    }

    #[test]
    fn test_decompile_entry_name_preserved() {
        let result = decompile_entry("/nonexistent/file.pbd", "w_login");
        assert!(!result.success);
        assert_eq!(result.name, "w_login");
        assert_eq!(result.size, 0);
    }

    #[test]
    fn test_decompile_all_invalid_file() {
        let tmp = tempfile::tempdir().unwrap();
        let result = decompile_all("/nonexistent/file.pbd", tmp.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_decompile_all_creates_output_dir() {
        let tmp = tempfile::tempdir().unwrap();
        let out = tmp.path().join("output");
        // Invalid file but output dir should NOT be created because
        // PblParser::new fails before create_dir_all
        let result = decompile_all("/nonexistent/file.pbd", out.to_str().unwrap());
        assert!(result.is_err());
        // Output dir was created before the parser error
        assert!(out.exists(), "output dir should be created before parsing");
    }

    #[test]
    fn test_decompile_entry_empty_name() {
        let result = decompile_entry("/nonexistent/file.pbd", "");
        assert!(!result.success);
        assert_eq!(result.name, "");
        assert!(result.error.is_some());
    }
}
