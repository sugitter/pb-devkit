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
                if let Some(rest_stripped) = rest.strip_prefix('.') {
                let rest = rest_stripped.trim_start();
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
                if (c == '.' && !result.is_empty()) || c.is_alphanumeric() || c == '_' {
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

    // Support both formats:
    //   name="col_name"   (PB DataWindow source)
    //   name=col_name     (PB exported column definitions)
    let patterns = ["name=\"", "name="];
    
    for pattern in &patterns {
        let mut search_start = 0;
        while let Some(pos) = content[search_start..].find(pattern) {
            let actual_pos = search_start + pos + pattern.len();
            // For quoted: stop at closing "; for unquoted: stop at ), \n, or comma
            let end_char = if pattern.ends_with('"') { '"' } else { '\0' };
            
            if end_char == '"' {
                if let Some(end) = content[actual_pos..].find('"') {
                    let col_name = &content[actual_pos..actual_pos+end];
                    if !col_name.is_empty() {
                        columns.push(col_name.to_string());
                    }
                    search_start = actual_pos + end + 1;
                } else {
                    break;
                }
            } else {
                // Unquoted: extract until ), \n, comma, or end
                let end = content[actual_pos..].find([')', '\n', ','])
                    .unwrap_or(content.len() - actual_pos);
                let col_name = content[actual_pos..actual_pos + end].trim();
                if !col_name.is_empty() {
                    columns.push(col_name.to_string());
                }
                search_start = actual_pos + end + 1;
            }
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

    let rest = &sql[group_idx + "group by ".len()..]; // skip "group by "
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

#[cfg(test)]
mod tests {
    use super::*;

    // ── extract_sql ──

    #[test]
    fn test_extract_sql_basic_select() {
        let content = "SELECT id, name FROM users\ncolumn(name=id)";
        let sql = extract_sql(content);
        assert!(sql.is_some());
        let s = sql.unwrap().to_lowercase();
        assert!(s.contains("select"));
        assert!(s.contains("from"));
    }

    #[test]
    fn test_extract_sql_with_where() {
        let content = "SELECT * FROM employees WHERE dept_id = 1\ncolumn(name=id)";
        let sql = extract_sql(content).unwrap();
        assert!(sql.to_lowercase().contains("where"));
    }

    #[test]
    fn test_extract_sql_no_sql() {
        let content = "release 12.5;\ntable(name=d_emp)";
        let sql = extract_sql(content);
        assert!(sql.is_none());
    }

    #[test]
    fn test_extract_sql_pb_formatted() {
        let content = r#"release 12.5;
datawindow(units=0 timer_interval=0 processing=0)
sql='SELECT name, salary FROM emp WHERE salary > 50000'
table(name=emp)"#;
        let sql = extract_sql(content).unwrap();
        assert!(sql.contains("SELECT") || sql.contains("select"));
    }

    // ── parse_table_name ──

    #[test]
    fn test_parse_simple_table() {
        assert_eq!(parse_table_name("employees"), "employees");
    }

    #[test]
    fn test_parse_table_with_alias() {
        assert_eq!(parse_table_name("employees e"), "employees");
    }

    #[test]
    fn test_parse_table_with_comma() {
        assert_eq!(parse_table_name("employees,"), "employees");
    }

    #[test]
    fn test_parse_bracketed_table() {
        assert_eq!(parse_table_name("[dbo].[employees]"), "dbo.employees");
    }

    #[test]
    fn test_parse_quoted_table() {
        assert_eq!(parse_table_name("\"my_table\""), "my_table");
    }

    #[test]
    fn test_parse_empty_table() {
        assert_eq!(parse_table_name(""), "");
    }

    #[test]
    fn test_parse_table_with_join() {
        assert_eq!(parse_table_name("employees\n"), "employees");
    }

    // ── extract_tables ──

    #[test]
    fn test_extract_tables_from_simple_select() {
        let content = "SELECT * FROM users";
        let tables = extract_tables(content);
        assert!(tables.contains(&"users".to_string()));
    }

    #[test]
    fn test_extract_tables_from_join() {
        let content = "SELECT * FROM orders JOIN customers ON orders.cid = customers.id";
        let tables = extract_tables(content);
        assert!(tables.contains(&"orders".to_string()));
        assert!(tables.contains(&"customers".to_string()));
    }

    #[test]
    fn test_extract_tables_filter_keywords() {
        let content = "SELECT * FROM employees WHERE salary > 10000";
        let tables = extract_tables(content);
        // "where" should not appear as a table
        assert!(!tables.contains(&"where".to_string()));
    }

    // ── find_sql_end ──

    #[test]
    fn test_find_sql_end_at_group_by() {
        let text = "SELECT * FROM t\nGROUP BY id";
        let end = find_sql_end(text);
        assert!(end > 0);
        assert!(end <= text.len());
    }

    #[test]
    fn test_find_sql_end_at_order_by() {
        let text = "SELECT a, b FROM t\nORDER BY a";
        let end = find_sql_end(text);
        assert!(end > 0);
        assert!(end <= text.len());
    }

    // ── extract_columns ──

    #[test]
    fn test_extract_columns_basic() {
        let content = r#"column(name=id)
column(name=emp_name)
column(name=salary)"#;
        let cols = extract_columns(content);
        assert!(cols.contains(&"id".to_string()));
        assert!(cols.contains(&"emp_name".to_string()));
        assert!(cols.contains(&"salary".to_string()));
    }

    #[test]
    fn test_extract_columns_no_columns() {
        let content = "some text without column definitions";
        let cols = extract_columns(content);
        assert!(cols.is_empty());
    }

    // ── detect_dw_style ──

    #[test]
    fn test_detect_grid_style() {
        let style = detect_dw_style("release 12.5;\nprocessing=0\nGrid\ntable(...)");
        assert_eq!(style, Some("Grid".to_string()));
    }

    #[test]
    fn test_detect_tabular_style() {
        let style = detect_dw_style("Tabular\ntable(emp)");
        assert_eq!(style, Some("Tabular".to_string()));
    }

    #[test]
    fn test_detect_freeform_style() {
        let style = detect_dw_style("Freeform\ncolumn(...)");
        assert_eq!(style, Some("Freeform".to_string()));
    }

    #[test]
    fn test_detect_composite_style() {
        let style = detect_dw_style("Composite\nreport(...)");
        assert_eq!(style, Some("Composite".to_string()));
    }

    #[test]
    fn test_detect_no_style() {
        let style = detect_dw_style("some random content");
        assert_eq!(style, None);
    }

    // ── extract_where_clause ──

    #[test]
    fn test_extract_where_simple() {
        let sql = "SELECT * FROM t WHERE a = 1";
        let wc = extract_where_clause(sql);
        assert_eq!(wc, Some("a = 1".to_string()));
    }

    #[test]
    fn test_extract_where_with_order_by() {
        let sql = "SELECT * FROM t WHERE a = 1 ORDER BY b";
        let wc = extract_where_clause(sql);
        assert_eq!(wc, Some("a = 1".to_string()));
    }

    #[test]
    fn test_extract_where_with_group_by() {
        let sql = "SELECT * FROM t WHERE x > 0 GROUP BY y";
        let wc = extract_where_clause(sql);
        assert_eq!(wc, Some("x > 0".to_string()));
    }

    #[test]
    fn test_extract_where_none() {
        let sql = "SELECT * FROM t";
        assert_eq!(extract_where_clause(sql), None);
    }

    // ── extract_order_by_clause ──

    #[test]
    fn test_extract_order_by_simple() {
        let sql = "SELECT * FROM t ORDER BY name ASC";
        let ob = extract_order_by_clause(sql);
        assert_eq!(ob, Some("name ASC".to_string()));
    }

    #[test]
    fn test_extract_order_by_multiple() {
        let sql = "SELECT * FROM t ORDER BY dept, salary DESC";
        let ob = extract_order_by_clause(sql);
        assert_eq!(ob, Some("dept, salary DESC".to_string()));
    }

    #[test]
    fn test_extract_order_by_none() {
        assert_eq!(extract_order_by_clause("SELECT * FROM t"), None);
    }

    // ── extract_group_by_clause ──

    #[test]
    fn test_extract_group_by_simple() {
        let sql = "SELECT dept, COUNT(*) FROM t GROUP BY dept";
        let gb = extract_group_by_clause(sql);
        assert_eq!(gb, Some("dept".to_string()));
    }

    #[test]
    fn test_extract_group_by_with_having() {
        let sql = "SELECT dept, COUNT(*) FROM t GROUP BY dept HAVING COUNT(*) > 5";
        let gb = extract_group_by_clause(sql);
        assert_eq!(gb, Some("dept".to_string()));
    }

    #[test]
    fn test_extract_group_by_none() {
        assert_eq!(extract_group_by_clause("SELECT * FROM t"), None);
    }

    // ── extract_arguments ──

    #[test]
    fn test_extract_arguments_from_arguments_section() {
        let content = "arguments=(dept_id integer, start_date date)";
        let args = extract_arguments(content);
        assert!(!args.is_empty());
        assert!(args.iter().any(|a| a.name == "dept_id"));
        assert!(args.iter().any(|a| a.name == "start_date"));
    }

    #[test]
    fn test_extract_arguments_from_argument_block() {
        let content = r#"argument(name="dept_id" type=long)"#;
        let args = extract_arguments(content);
        assert!(!args.is_empty());
        assert!(args.iter().any(|a| a.name == "dept_id"));
    }

    #[test]
    fn test_extract_arguments_none() {
        let args = extract_arguments("no arguments here");
        assert!(args.is_empty());
    }

    // ── extract_computed_columns ──

    #[test]
    fn test_extract_computed_columns_basic() {
        let content = r#"compute(name="total" expression="price * quantity")"#;
        let cols = extract_computed_columns(content);
        assert!(!cols.is_empty());
        assert_eq!(cols[0].name, "total");
        assert_eq!(cols[0].expression, "price * quantity");
    }

    #[test]
    fn test_extract_computed_columns_none() {
        let cols = extract_computed_columns("no compute here");
        assert!(cols.is_empty());
    }

    // ── detect_union ──

    #[test]
    fn test_detect_union_found() {
        let content = "SELECT a FROM t1 UNION SELECT b FROM t2";
        let (has_union, _) = detect_union(content);
        assert!(has_union);
    }

    #[test]
    fn test_detect_union_all() {
        let content = "SELECT a FROM t1 UNION ALL SELECT b FROM t2";
        let (has_union, _) = detect_union(content);
        assert!(has_union);
    }

    #[test]
    fn test_detect_union_none() {
        let (has_union, _) = detect_union("SELECT a FROM t1");
        assert!(!has_union);
    }

    // ── detect_subqueries ──

    #[test]
    fn test_detect_in_subquery() {
        let content = "SELECT * FROM orders WHERE cid IN (SELECT id FROM customers)";
        let sq = detect_subqueries(content);
        assert!(!sq.is_empty());
        assert!(sq.iter().any(|s| s.query_type == "in"));
    }

    #[test]
    fn test_detect_exists_subquery() {
        let content = "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t.id = t2.fk)";
        let sq = detect_subqueries(content);
        assert!(!sq.is_empty());
        assert!(sq.iter().any(|s| s.query_type == "exists"));
    }

    #[test]
    fn test_detect_subqueries_none() {
        let sq = detect_subqueries("SELECT * FROM t");
        assert!(sq.is_empty());
    }

    // ── get_dw_sql (edge case) ──

    #[test]
    fn test_get_dw_sql_file_not_found() {
        let result = get_dw_sql("/nonexistent/path.dw");
        assert!(result.is_err());
    }
}
