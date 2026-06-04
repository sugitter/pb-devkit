// Search - Shared core logic for full-text search in PowerBuilder source files
// Enhanced v2.1: Parallel search with rayon, index file support

use std::path::Path;
use rayon::prelude::*;

use crate::types::{SearchResult, SearchResults};

/// Search for text in source files (enhanced with parallel search)
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

    // Collect all file paths first (for parallel processing)
    let files: Vec<_> = collect_files(root, &types);
    let files_count = files.len();

    // Parallel search using rayon
    let matches: Vec<SearchResult> = files
        .par_iter()
        .flat_map(|path| {
            search_file_parallel(path, &search_query, case_sensitive)
        })
        .collect();

    let total_matches = matches.len();

    Ok(SearchResults {
        query: query.to_string(),
        matches,
        files_count,
        total_matches,
    })
}

/// Collect all files matching the types in the directory tree
fn collect_files(dir: &Path, file_types: &[String]) -> Vec<std::path::PathBuf> {
    let mut files = Vec::new();

    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();

            if path.is_dir() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if !name.starts_with('.') && name != "node_modules" && name != "target" {
                        files.extend(collect_files(&path, file_types));
                    }
                }
            } else if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                let ext_with_dot = format!(".{}", ext.to_lowercase());
                if file_types.iter().any(|t| t.to_lowercase() == ext_with_dot) {
                    files.push(path);
                }
            }
        }
    }

    files
}

/// Search a single file (parallel version - returns all matches)
fn search_file_parallel(path: &Path, query: &str, case_sensitive: bool) -> Vec<SearchResult> {
    let mut results = Vec::new();

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

    results
}

/// Search using regex pattern (v2.1+)
pub fn search_with_regex(
    root_path: &str,
    pattern: &str,
    case_sensitive: bool,
    file_types: &[String],
) -> Result<SearchResults, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    // Compile regex pattern
    let regex_pattern = if case_sensitive {
        regex::Regex::new(pattern)
    } else {
        regex::Regex::new(&format!("(?i){}", pattern))
    }.map_err(|e| format!("Invalid regex pattern: {}", e))?;

    let types = if file_types.is_empty() {
        vec![
            ".srw".to_string(), ".srd".to_string(), ".srm".to_string(),
            ".srf".to_string(), ".srs".to_string(), ".sru".to_string(),
            ".txt".to_string(), ".ps".to_string(),
        ]
    } else {
        file_types.to_vec()
    };

    // Collect all file paths
    let files: Vec<_> = collect_files(root, &types);
    let files_count = files.len();

    // Parallel regex search
    let matches: Vec<SearchResult> = files
        .par_iter()
        .flat_map(|path| {
            search_file_with_regex(path, &regex_pattern)
        })
        .collect();

    let total_matches = matches.len();

    Ok(SearchResults {
        query: format!("regex:{}", pattern),
        matches,
        files_count,
        total_matches,
    })
}

/// Search a single file with regex
fn search_file_with_regex(path: &Path, pattern: &regex::Regex) -> Vec<SearchResult> {
    let mut results = Vec::new();

    if let Ok(content) = std::fs::read_to_string(path) {
        for (line_num, line) in content.lines().enumerate() {
            if let Some(m) = pattern.find(line) {
                results.push(SearchResult {
                    file: path.to_string_lossy().to_string(),
                    line_number: line_num + 1,
                    line_content: line.to_string(),
                    match_start: m.start(),
                    match_length: m.len(),
                });
            }
        }
    }

    results
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

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    // ── search_in_files ──
    #[test]
    fn test_search_in_files_path_not_exists() {
        let result = search_in_files("/nonexistent", "test", false, &[]);
        assert!(result.is_err());
    }

    #[test]
    fn test_search_in_files_empty_dir() {
        let tmp = tempfile::tempdir().unwrap();
        let result = search_in_files(tmp.path().to_str().unwrap(), "hello", false, &[]).unwrap();
        assert_eq!(result.files_count, 0);
        assert_eq!(result.total_matches, 0);
    }

    #[test]
    fn test_search_in_files_finds_text() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("w_main.srw"), b"hello world\nfoo bar").unwrap();
        let result = search_in_files(tmp.path().to_str().unwrap(), "hello", false, &[]).unwrap();
        assert!(result.files_count > 0);
        assert!(result.total_matches > 0);
    }

    #[test]
    fn test_search_in_files_case_sensitive() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("w_main.srw"), b"Hello World").unwrap();
        // Case-insensitive (default)
        let r1 = search_in_files(tmp.path().to_str().unwrap(), "hello", false, &[]).unwrap();
        assert!(r1.total_matches > 0);
        // Case-sensitive
        let r2 = search_in_files(tmp.path().to_str().unwrap(), "hello", true, &[]).unwrap();
        assert_eq!(r2.total_matches, 0);
    }

    #[test]
    fn test_search_in_files_custom_file_types() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("readme.txt"), b"hello world").unwrap();
        fs::write(tmp.path().join("data.csr"), b"not matched").unwrap();
        let result = search_in_files(
            tmp.path().to_str().unwrap(), "hello", false,
            &[".txt".into()],
        ).unwrap();
        assert!(result.total_matches > 0);
    }

    // ── search_file_parallel ──
    #[test]
    fn test_search_file_parallel_match() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.srw");
        fs::write(&f, b"line one\nline two\nline three").unwrap();
        let results = search_file_parallel(&f, "two", false);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].line_number, 2);
    }

    #[test]
    fn test_search_file_parallel_no_match() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.srw");
        fs::write(&f, b"aaa bbb ccc").unwrap();
        let results = search_file_parallel(&f, "zzz", false);
        assert!(results.is_empty());
    }

    #[test]
    fn test_search_file_parallel_multiple_matches() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.srw");
        fs::write(&f, b"foo foo foo\nbar bar").unwrap();
        let results = search_file_parallel(&f, "foo", false);
        assert_eq!(results.len(), 1); // per-line match, line 1 matches
    }

    // ── search_with_regex ──
    #[test]
    fn test_search_with_regex_path_not_exists() {
        let result = search_with_regex("/nonexistent", r"\d+", false, &[]);
        assert!(result.is_err());
    }

    #[test]
    fn test_search_with_regex_invalid_pattern() {
        let tmp = tempfile::tempdir().unwrap();
        let result = search_with_regex(tmp.path().to_str().unwrap(), "[invalid", false, &[]);
        assert!(result.is_err());
    }

    #[test]
    fn test_search_with_regex_valid() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("test.srw"), b"phone: 12345\ncode: ABC").unwrap();
        let result = search_with_regex(tmp.path().to_str().unwrap(), r"\d+", false, &[]).unwrap();
        assert!(result.total_matches > 0);
    }

    // ── search_file_with_regex ──
    #[test]
    fn test_search_file_with_regex_match() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.srw");
        fs::write(&f, b"price=100\ntotal=200").unwrap();
        let re = regex::Regex::new(r"\d+").unwrap();
        let results = search_file_with_regex(&f, &re);
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_search_file_with_regex_no_match() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("test.srw");
        fs::write(&f, b"abc def").unwrap();
        let re = regex::Regex::new(r"\d+").unwrap();
        let results = search_file_with_regex(&f, &re);
        assert!(results.is_empty());
    }

    // ── search_by_type ──
    #[test]
    fn test_search_by_type_path_not_exists() {
        let result = search_by_type("/nonexistent", "window");
        assert!(result.is_err());
    }

    #[test]
    fn test_search_by_type_finds_srw() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("w_main.srw"), b"").unwrap();
        fs::write(tmp.path().join("d_emp.srd"), b"").unwrap();
        let result = search_by_type(tmp.path().to_str().unwrap(), "window").unwrap();
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn test_search_by_type_unknown_type() {
        let tmp = tempfile::tempdir().unwrap();
        let result = search_by_type(tmp.path().to_str().unwrap(), "unknown_type").unwrap();
        assert!(result.is_empty());
    }

    #[test]
    fn test_search_by_type_all_known_types() {
        let tmp = tempfile::tempdir().unwrap();
        // Create one file per known type
        for (ext, _fname) in &[
            (".srw", "window"), (".srd", "datawindow"), (".srm", "menu"),
            (".srf", "function"), (".srs", "structure"), (".sru", "userobject"),
            (".srq", "query"), (".srp", "pipeline"), (".srj", "project"),
            (".srx", "proxy"), (".sra", "application"),
        ] {
            fs::write(tmp.path().join(format!("obj{}", ext)), b"").unwrap();
        }
        // Each type should find exactly 1 file
        for obj_type in &["window", "datawindow", "menu", "function", "structure",
            "userobject", "query", "pipeline", "project", "proxy", "application"] {
            let result = search_by_type(tmp.path().to_str().unwrap(), obj_type).unwrap();
            assert_eq!(result.len(), 1, "Failed for type: {}", obj_type);
        }
    }

    // ── collect_files ──
    #[test]
    fn test_collect_files_empty_dir() {
        let tmp = tempfile::tempdir().unwrap();
        let files = collect_files(tmp.path(), &[".srw".into()]);
        assert!(files.is_empty());
    }

    #[test]
    fn test_collect_files_only_matching_exts() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("a.srw"), b"").unwrap();
        fs::write(tmp.path().join("b.txt"), b"").unwrap();
        let files = collect_files(tmp.path(), &[".srw".into()]);
        assert_eq!(files.len(), 1);
    }

    #[test]
    fn test_collect_files_skips_hidden_and_special_dirs() {
        let tmp = tempfile::tempdir().unwrap();
        let node_modules = tmp.path().join("node_modules");
        fs::create_dir(&node_modules).unwrap();
        fs::write(node_modules.join("x.srw"), b"").unwrap();
        let target = tmp.path().join("target");
        fs::create_dir(&target).unwrap();
        fs::write(target.join("y.srw"), b"").unwrap();
        fs::write(tmp.path().join("visible.srw"), b"").unwrap();
        let files = collect_files(tmp.path(), &[".srw".into()]);
        assert_eq!(files.len(), 1);
    }

    // ── find_files_by_ext ──
    #[test]
    fn test_find_files_by_ext_nested() {
        let tmp = tempfile::tempdir().unwrap();
        let sub = tmp.path().join("sub");
        fs::create_dir(&sub).unwrap();
        fs::write(tmp.path().join("a.srw"), b"").unwrap();
        fs::write(sub.join("b.srw"), b"").unwrap();
        let mut results = Vec::new();
        find_files_by_ext(tmp.path(), ".srw", &mut results);
        assert_eq!(results.len(), 2);
    }
}
