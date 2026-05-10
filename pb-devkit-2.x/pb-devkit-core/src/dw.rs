// DataWindow analysis - Shared core logic

use std::path::Path;
use crate::types::{DwInfo, DwAnalysisResult};

/// Analyze DataWindow objects in a directory.
/// Scans for .srd files and PBL files containing DataWindow objects.
pub fn analyze_datawindows(root_path: &str) -> Result<DwAnalysisResult, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut datawindows = Vec::new();
    let mut all_tables = Vec::new();

    find_datawindows(root, &mut datawindows, &mut all_tables);

    all_tables.sort();
    all_tables.dedup();

    Ok(DwAnalysisResult {
        total_count: datawindows.len(),
        datawindows,
        tables_found: all_tables,
    })
}

fn find_datawindows(dir: &Path, dws: &mut Vec<DwInfo>, tables: &mut Vec<String>) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();

            if path.is_dir() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if !name.starts_with('.') {
                        find_datawindows(&path, dws, tables);
                    }
                }
            } else if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                let lower = name.to_lowercase();
                // .srd = exported DataWindow source
                // PBL/PBD may also contain DW objects (handled via pbl parsing)
                if lower.ends_with(".srd") || lower.contains("d_") {
                    let content = std::fs::read_to_string(&path).unwrap_or_default();

                    // Try to extract SQL from the file content
                    let sql = extract_sql(&content);
                    let dw_tables = extract_tables(&content);
                    tables.extend(dw_tables.clone());

                    // Try to detect DW style from content
                    let style = detect_dw_style(&content);

                    dws.push(DwInfo {
                        name: name.to_string(),
                        path: path.to_string_lossy().to_string(),
                        sql,
                        tables: dw_tables,
                        columns: extract_columns(&content),
                        style,
                    });
                }
            }
        }
    }
}

/// Extract SQL from DataWindow source content.
/// Handles SELECT, INSERT, UPDATE, DELETE and multi-line SQL.
fn extract_sql(content: &str) -> Option<String> {
    let lower = content.to_lowercase();

    // SQL keywords to look for (in order of priority)
    let sql_keywords = [
        "select ", "SELECT\n", "select\n",
        "insert into ", "update ", "delete from ",
        "with ", "union ", "exec ",
    ];

    let mut best_sql: Option<String> = None;

    for &kw in &sql_keywords {
        if let Some(start) = lower.find(&kw.to_lowercase()) {
            // Skip if inside a string literal (simple heuristic)
            let before = &content[..start];
            if before.matches('"').count() % 2 == 1 || before.matches('\'').count() % 2 == 1 {
                continue;
            }

            // Extract SQL: look for end markers
            let rest = &content[start..];
            let end = find_sql_end(rest);

            let sql = rest[..end].trim();
            if !sql.is_empty() && sql.len() > 10 {
                // Prefer longer SQL (more complete)
                match &best_sql {
                    None => best_sql = Some(sql.to_string()),
                    Some(prev) if sql.len() > prev.len() => {
                        best_sql = Some(sql.to_string());
                    }
                    _ => {}
                }
            }
        }
    }

    // Also try PB-specific SQL block format: "sql='...'"
    if best_sql.is_none() {
        if let Some(start) = lower.find("sql='") {
            let start = start + 5; // skip "sql='"
            let rest = &content[start..];
            if let Some(end) = rest.find('\'') {
                let sql = &rest[..end];
                if !sql.trim().is_empty() {
                    best_sql = Some(sql.trim().to_string());
                }
            }
        }
    }

    best_sql
}

/// Find the end of a SQL statement in text.
/// Looks for SQL-ending keywords and statement terminators.
fn find_sql_end(sql_text: &str) -> usize {
    let lower = sql_text.to_lowercase();

    // Possible end markers (in order of search)
    let end_markers = [
        ";\n", ";\r\n",  // statement terminator + newline
        "\ngroup by", "\norder by", "\nhaving ",
        "\nunion ", "\nunion\n", "\nunion\r\n",
        // PB DataWindow specific end markers
        "\ntable(", "\ncolumn(", "\ncompute(",
        "\nfilter(", "\nsort(", "\nhtmltable(",
        // End of file or block
        "\r\n\r\n", "\n\n",
    ];

    let mut earliest_end = sql_text.len();

    for &marker in &end_markers {
        if let Some(pos) = lower.find(&marker.to_lowercase()) {
            if pos < earliest_end {
                earliest_end = pos;
            }
        }
    }

    // Cap at a reasonable length (max 4000 chars)
    let limit = 4000.min(sql_text.len());
    if earliest_end > limit {
        earliest_end = limit;
    }

    earliest_end.max(1)  // at least 1 char
}

/// Extract table names from SQL content.
/// Handles: table, schema.table, [schema].[table], "table"
fn extract_tables(content: &str) -> Vec<String> {
    let mut tables = Vec::new();
    let lower = content.to_lowercase();

    let patterns = [
        "from ", "into ", "update ", "join ", "table ",
        "from\n", "join\n",
    ];

    for &pattern in &patterns {
        let mut search_start = 0;
        let p_lower = pattern.to_lowercase();

        while let Some(pos) = lower[search_start..].find(&p_lower) {
            let actual_pos = search_start + pos + p_lower.len();
            let rest = &content[actual_pos..];

            // Skip whitespace
            let table_start = rest.chars()
                .take_while(|c| c.is_whitespace())
                .count();
            let rest = &rest[table_start..];

            // Parse table name: supports schema.table, [schema].[table], "table"
            let table_name = parse_table_name(rest);

            if !table_name.is_empty() && table_name.len() > 1 {
                // Filter out SQL keywords that might be captured
                let lower_name = table_name.to_lowercase();
                if !["select", "where", "group", "order", "having", "union",
                     "inner", "outer", "left", "right", "cross"].contains(&lower_name.as_str()) {
                    tables.push(table_name);
                }
            }

            search_start = actual_pos + 1;
        }
    }

    tables.sort();
    tables.dedup();
    tables
}

/// Parse a table name from the start of a string.
/// Handles: table, [table], "table", schema.table, [schema].[table]
fn parse_table_name(s: &str) -> String {
    let s = s.trim_start();

    if s.is_empty() {
        return String::new();
    }

    match s.chars().next() {
        // Bracket-quoted name: [table] or [schema].[table]
        Some('[') => {
            if let Some(end) = s.find(']') {
                let name = s[1..end].to_string();
                // Check for schema.table format: [schema].[table]
                let rest = &s[end+1..].trim_start();
                if rest.starts_with('.') {
                    let rest = &rest[1..].trim_start();
                    if let Some('[') = rest.chars().next() {
                        if let Some(end) = rest.find(']') {
                            return format!("{}.{}", name, &rest[1..end]);
                        }
                    }
                }
                return name;
            }
        }
        // Double-quote quoted name: "table"
        Some('"') => {
            if let Some(end) = s[1..].find('"') {
                return s[1..end+1].to_string();
            }
        }
        // Unquoted name: table or schema.table
        _ => {
            let mut result = String::new();
            for (_, c) in s.char_indices() {
                if c == '.' && !result.is_empty() {
                    result.push(c);
                } else if c.is_alphanumeric() || c == '_' {
                    result.push(c);
                } else {
                    break;
                }
            }
            return result;
        }
    }

    String::new()
}

/// Extract column names from DataWindow source.
/// Looks for "column(... name=..." patterns.
fn extract_columns(content: &str) -> Vec<String> {
    let mut columns = Vec::new();

    // Pattern: name="col_name" in column() definitions
    let pattern = "name=\"";
    let mut search_start = 0;

    while let Some(pos) = content[search_start..].find(pattern) {
        let actual_pos = search_start + pos + pattern.len();
        if let Some(end) = content[actual_pos..].find('"') {
            let col_name = &content[actual_pos..actual_pos+end];
            if !col_name.is_empty() {
                columns.push(col_name.to_string());
            }
            search_start = actual_pos + end + 1;
        } else {
            break;
        }
    }

    columns.dedup_by(|a, b| a == b);
    columns
}

/// Detect DataWindow style from content.
/// Returns: "Grid", "Tabular", "Freeform", "Cross tab", "Graph", "Composite", etc.
fn detect_dw_style(content: &str) -> Option<String> {
    let lower = content.to_lowercase();

    let styles = [
        ("crosstab", "Cross tab"),
        ("graph", "Graph"),
        ("composite", "Composite"),
        ("richtext", "RichText"),
        ("label", "Label"),
        ("group", "Group"),
        ("treeview", "TreeView"),
        ("grid", "Grid"),
        ("tabular", "Tabular"),
        ("freeform", "Freeform"),
    ];

    for (kw, style) in &styles {
        if lower.contains(kw) {
            return Some(style.to_string());
        }
    }

    None
}

/// Get DataWindow SQL details from a specific DW file.
pub fn get_dw_sql(dw_path: &str) -> Result<String, String> {
    let content = std::fs::read_to_string(dw_path)
        .map_err(|e| e.to_string())?;

    extract_sql(&content)
        .ok_or_else(|| "No SQL found".to_string())
}
