// DataWindow analysis - Shared core logic
// Enhanced v2.1: Supports nested SELECT, UNION, subqueries, arguments, computed columns

use std::path::Path;
use crate::types::{DwInfo, DwAnalysisResult, DwArgument, ComputedColumn, SubQuery};

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

                    // Extract SQL from the file content
                    let sql = extract_sql(&content);
                    let dw_tables = extract_tables(&content);
                    tables.extend(dw_tables.clone());

                    // Detect DW style from content
                    let style = detect_dw_style(&content);

                    // Enhanced SQL parsing (v2.1+)
                    let where_clause = sql.as_ref().and_then(|s| extract_where_clause(s));
                    let order_by_clause = sql.as_ref().and_then(|s| extract_order_by_clause(s));
                    let group_by_clause = sql.as_ref().and_then(|s| extract_group_by_clause(s));
                    let arguments = extract_arguments(&content);
                    let computed_columns = extract_computed_columns(&content);
                    let (has_union, union_sql) = detect_union(&content);
                    let subqueries = detect_subqueries(&content);

                    dws.push(DwInfo {
                        name: name.to_string(),
                        path: path.to_string_lossy().to_string(),
                        sql,
                        tables: dw_tables,
                        columns: extract_columns(&content),
                        style,
                        // Enhanced fields (v2.1+)
                        where_clause,
                        order_by_clause,
                        group_by_clause,
                        arguments,
                        computed_columns,
                        has_union,
                        union_sql,
                        subqueries,
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

// ─── Enhanced SQL Parsing (v2.1+) ───

/// Extract WHERE clause from SQL statement
pub fn extract_where_clause(sql: &str) -> Option<String> {
    let lower = sql.to_lowercase();
    let where_idx = lower.find("where ")?;

    // Find the end of WHERE clause (look for GROUP BY, ORDER BY, HAVING, UNION)
    let rest = &sql[where_idx + 6..]; // skip "where "
    let end_markers = [" group by ", " order by ", " having ", " union ", " where "];
    let mut end_pos = rest.len();

    for marker in &end_markers {
        if let Some(pos) = rest.to_lowercase().find(marker) {
            if pos < end_pos {
                end_pos = pos;
            }
        }
    }

    let where_clause = rest[..end_pos].trim();
    if where_clause.is_empty() {
        None
    } else {
        Some(where_clause.to_string())
    }
}

/// Extract ORDER BY clause from SQL statement
pub fn extract_order_by_clause(sql: &str) -> Option<String> {
    let lower = sql.to_lowercase();
    let order_idx = lower.find("order by ")?;

    let rest = &sql[order_idx + 9..]; // skip "order by "
    // ORDER BY ends at end of string or before UNION
    let end_markers = [" union "];
    let mut end_pos = rest.len();

    for marker in &end_markers {
        if let Some(pos) = rest.to_lowercase().find(marker) {
            if pos < end_pos {
                end_pos = pos;
            }
        }
    }

    let order_clause = rest[..end_pos].trim();
    if order_clause.is_empty() {
        None
    } else {
        Some(order_clause.to_string())
    }
}

/// Extract GROUP BY clause from SQL statement
pub fn extract_group_by_clause(sql: &str) -> Option<String> {
    let lower = sql.to_lowercase();
    let group_idx = lower.find("group by ")?;

    let rest = &sql[group_idx + 10..]; // skip "group by "
    let end_markers = [" having ", " order by ", " union "];
    let mut end_pos = rest.len();

    for marker in &end_markers {
        if let Some(pos) = rest.to_lowercase().find(marker) {
            if pos < end_pos {
                end_pos = pos;
            }
        }
    }

    let group_clause = rest[..end_pos].trim();
    if group_clause.is_empty() {
        None
    } else {
        Some(group_clause.to_string())
    }
}

/// Extract Retrieve arguments from DataWindow source
/// Looks for argument() or arguments in the DataWindow syntax
pub fn extract_arguments(content: &str) -> Vec<DwArgument> {
    let mut args = Vec::new();

    // Pattern 1: Arguments in "arguments=..." or "argument()"
    let arg_patterns = [
        r#"arguments="([^"]+)""#,
        r#"argument\s*\(\s*name\s*=\s*"([^"]+)""#,
        r#"retrieve\s+args\s*=\s*"([^"]+)""#,
    ];

    // Try to find argument definitions in various formats
    for pattern in &arg_patterns {
        if let Ok(re) = regex::Regex::new(pattern) {
            for cap in re.captures_iter(content) {
                if let Some(name_match) = cap.get(1) {
                    let name = name_match.as_str().to_string();
                    if !name.is_empty() {
                        args.push(DwArgument {
                            name,
                            data_type: None,
                            initial_value: None,
                            description: None,
                        });
                    }
                }
            }
        }
    }

    // Pattern 2: Look for "arguments" section in PB syntax
    // Format: arguments=(name type, ...)
    if args.is_empty() {
        if let Some(start) = content.to_lowercase().find("arguments=(") {
            let rest = &content[start + 11..]; // skip "arguments=("
            if let Some(end) = rest.find(')') {
                let arg_str = &rest[..end];
                // Parse comma-separated arguments
                for arg in arg_str.split(',') {
                    let arg = arg.trim();
                    if !arg.is_empty() {
                        // Try to extract name (first part before type)
                        let parts: Vec<&str> = arg.split_whitespace().collect();
                        if let Some(name) = parts.first() {
                            args.push(DwArgument {
                                name: name.to_string(),
                                data_type: parts.get(1).map(|s| s.to_string()),
                                initial_value: None,
                                description: None,
                            });
                        }
                    }
                }
            }
        }
    }

    args
}

/// Extract computed columns from DataWindow source
/// Looks for "compute(... name=... expression=...)"
pub fn extract_computed_columns(content: &str) -> Vec<ComputedColumn> {
    let mut cols = Vec::new();

    // Pattern: compute(... name="col_name" expression="..." ...
    let compute_patterns = [
        r#"compute\s*\([^)]*name\s*=\s*"([^"]+)"[^)]*expression\s*=\s*"([^"]+)""#,
        r#"compute\s*\([^)]*expression\s*=\s*"([^"]+)"[^)]*name\s*=\s*"([^"]+)""#,
    ];

    for pattern in &compute_patterns {
        if let Ok(re) = regex::Regex::new(pattern) {
            for cap in re.captures_iter(content) {
                let name = cap.get(1).map(|m| m.as_str()).unwrap_or("");
                let expression = cap.get(2).map(|m| m.as_str()).unwrap_or("");

                if !name.is_empty() && !expression.is_empty() {
                    cols.push(ComputedColumn {
                        name: name.to_string(),
                        expression: expression.to_string(),
                        data_type: None,
                    });
                }
            }
        }
    }

    // Also try simpler pattern: compute(name="..." expression="...")
    if cols.is_empty() {
        let simple_re = regex::Regex::new(r#"compute\s*\(\s*name\s*=\s*"([^"]+)".*?expression\s*=\s*"([^"]+)""#).ok();
        if let Some(re) = simple_re {
            for cap in re.captures_iter(content) {
                if let (Some(name_m), Some(expr_m)) = (cap.get(1), cap.get(2)) {
                    cols.push(ComputedColumn {
                        name: name_m.as_str().to_string(),
                        expression: expr_m.as_str().to_string(),
                        data_type: None,
                    });
                }
            }
        }
    }

    cols
}

/// Detect UNION queries in DataWindow
/// Returns: (has_union, union_sql)
pub fn detect_union(content: &str) -> (bool, Option<String>) {
    let lower = content.to_lowercase();

    // Check for UNION keyword
    if !lower.contains("union") {
        return (false, None);
    }

    // Try to extract the UNION SQL
    if let Some(start) = lower.find("select ") {
        let rest = &content[start..];
        // Find UNION ALL or UNION
        if let Some(union_pos) = rest.to_lowercase().find("union ") {
            let union_sql = rest[..union_pos + 6].to_string(); // include "union "
            // Try to find the second SELECT
            if let Some(second_sel) = rest[union_pos + 6..].to_lowercase().find("select ") {
                let second_part = &rest[union_pos + 6 + second_sel..];
                // Find end of second SELECT
                let end_markers = [" group by", " order by", " having", "\ntable(", "\ncolumn("];
                let mut end_pos = second_part.len();
                for marker in &end_markers {
                    if let Some(pos) = second_part.to_lowercase().find(marker) {
                        if pos < end_pos {
                            end_pos = pos;
                        }
                    }
                }
                let full_union = format!("{}{}", union_sql, &second_part[..end_pos]);
                return (true, Some(full_union));
            }
        }
    }

    (true, None)
}

/// Detect subqueries in DataWindow source
pub fn detect_subqueries(content: &str) -> Vec<SubQuery> {
    let mut subqueries = Vec::new();
    let lower = content.to_lowercase();

    // Look for common subquery patterns
    let patterns = [
        // IN (SELECT ...)
        (r#"in\s*\(\s*select\s+[^)]+\s+from\s+([^ ]+)"#, "in"),
        // EXISTS (SELECT ...)
        (r#"exists\s*\(\s*select\s+[^)]+\s+from\s+([^ ]+)"#, "exists"),
        // = (SELECT ...) or > (SELECT ...) etc
        (r#"=\s*\(\s*select\s+[^)]+\s+from\s+([^ ]+)"#, "scalar"),
        // NOT IN
        (r#"not\s+in\s*\(\s*select\s+[^)]+\s+from\s+([^ ]+)"#, "in"),
    ];

    for (pattern, query_type) in &patterns {
        if let Ok(re) = regex::Regex::new(pattern) {
            for cap in re.captures_iter(&lower) {
                // Extract table name as alias hint
                let table = cap.get(1).map(|m| m.as_str()).unwrap_or("unknown");

                // Try to get more context for the subquery
                if let Some(m) = re.find(&lower) {
                    let start = m.start().saturating_sub(50);
                    let end = (m.end() + 200).min(content.len());
                    let sql_snippet = &content[start..end];

                    subqueries.push(SubQuery {
                        alias: Some(table.to_string()),
                        sql: sql_snippet.to_string(),
                        query_type: query_type.to_string(),
                    });
                }
            }
        }
    }

    subqueries
}
