// Search - Shared core logic for full-text search in PowerBuilder source files

use std::path::Path;

use crate::types::{SearchResult, SearchResults};

/// Search for text in source files
pub fn search_in_files(
    root_path: &str,
    query: &str,
    case_sensitive: bool,
    file_types: &[String],
) -> Result<SearchResults, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut matches = Vec::new();
    let mut files_searched = 0;

    let search_query = if case_sensitive {
        query.to_string()
    } else {
        query.to_lowercase()
    };

    let types = if file_types.is_empty() {
        vec![
            ".srw".to_string(), ".srd".to_string(), ".srm".to_string(),
            ".srf".to_string(), ".srs".to_string(), ".sru".to_string(),
            ".txt".to_string(), ".ps".to_string(),
        ]
    } else {
        file_types.to_vec()
    };

    search_directory(root, &search_query, case_sensitive, &types, &mut matches, &mut files_searched);

    let total_matches = matches.len();

    Ok(SearchResults {
        query: query.to_string(),
        matches,
        files_count: files_searched,
        total_matches,
    })
}

fn search_directory(
    dir: &Path,
    query: &str,
    case_sensitive: bool,
    file_types: &[String],
    results: &mut Vec<SearchResult>,
    files_count: &mut usize,
) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();

            if path.is_dir() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if !name.starts_with('.') && name != "node_modules" && name != "target" {
                        search_directory(&path, query, case_sensitive, file_types, results, files_count);
                    }
                }
            } else if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                let ext_with_dot = format!(".{}", ext.to_lowercase());
                if file_types.iter().any(|t| t.to_lowercase() == ext_with_dot) {
                    *files_count += 1;
                    search_file(&path, query, case_sensitive, results);
                }
            }
        }
    }
}

fn search_file(path: &Path, query: &str, case_sensitive: bool, results: &mut Vec<SearchResult>) {
    if let Ok(content) = std::fs::read_to_string(path) {
        for (line_num, line) in content.lines().enumerate() {
            let search_line = if case_sensitive {
                line.to_string()
            } else {
                line.to_lowercase()
            };

            if search_line.contains(query) {
                let match_pos = search_line.find(query).unwrap_or(0);

                results.push(SearchResult {
                    file: path.to_string_lossy().to_string(),
                    line_number: line_num + 1,
                    line_content: line.to_string(),
                    match_start: match_pos,
                    match_length: query.len(),
                });
            }
        }
    }
}

/// Search by object type
pub fn search_by_type(root_path: &str, object_type: &str) -> Result<Vec<String>, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut matches = Vec::new();
    let ext = match object_type.to_lowercase().as_str() {
        "window" => ".srw",
        "datawindow" => ".srd",
        "menu" => ".srm",
        "function" => ".srf",
        "structure" => ".srs",
        "userobject" => ".sru",
        "query" => ".srq",
        "pipeline" => ".srp",
        "project" => ".srj",
        "proxy" => ".srx",
        "application" => ".sra",
        _ => return Ok(vec![]),
    };

    find_files_by_ext(root, ext, &mut matches);

    Ok(matches)
}

fn find_files_by_ext(dir: &Path, ext: &str, results: &mut Vec<String>) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();

            if path.is_dir() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if !name.starts_with('.') {
                        find_files_by_ext(&path, ext, results);
                    }
                }
            } else if let Some(file_ext) = path.extension().and_then(|e| e.to_str()) {
                if format!(".{}", file_ext.to_lowercase()) == ext.to_lowercase() {
                    results.push(path.to_string_lossy().to_string());
                }
            }
        }
    }
}
