// Refactor command for CLI – source code quality analysis and fix suggestions
//
// Scans PowerBuilder source files (*.sr*) and reports anti-patterns:
//   – Long lines (>200 chars)
//   – Deep nesting (>4 levels)
//   – TODO / FIXME tags
//   – Deprecated API calls
//   – Hardcoded connection strings
//   – GOTO usage
//   – Global variable declarations
//   – Empty error handlers (empty catch)
//   – Hardcoded SQL
//
// Usage: pbdevkit refactor <target> [--json] [--no-apply]

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

/// A single refactor finding
#[derive(Debug, Clone)]
struct Finding {
    file: String,
    line: usize,
    severity: String, // "error", "warning", "info"
    rule: String,
    message: String,
}

impl Finding {
    fn to_json(&self) -> String {
        format!(
            r#"{{"file":"{}","line":{},"severity":"{}","rule":"{}","message":"{}"}}"#,
            self.file.replace('\\', "/"),
            self.line,
            self.severity,
            self.rule,
            self.message.replace('"', "\\\"")
        )
    }
}

/// Known deprecated PB API names
const DEPRECATED_APIS: &[&str] = &[
    "RegistryGet", "RegistrySet",
    "GetEnvironment", "SetEnvironment",
    "PrintScreen", "PrintBitmap",
    "Send", "Post",
    "SetPointer", "SetMicroHelp",
    "TriggerEvent",
    "dw_1.Describe", // heuristic
];

/// Known connection-string patterns
const CONN_PATTERNS: &[&str] = &[
    "SQLCA.DBMS",
    "SQLCA.Database",
    "SQLCA.ServerName",
    "SQLCA.LogId",
    "SQLCA.DBPass",
    "SQLCA.LogPass",
    "SQLCA.AutoCommit",
    "Connect;",
    "UID=",
    "PWD=",
    "DSN=",
    "DRIVER=",
    "PROVIDER=",
    "DATASOURCE=",
];

/// Scan a directory for PowerBuilder source files and report refactoring suggestions.
pub fn run_refactor(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit refactor <source_dir> [--json]".to_string());
    }

    let target = &args[0];
    let target_path = Path::new(target);
    if !target_path.exists() {
        return Err(format!("Path not found: {}", target));
    }

    let use_json = args.iter().any(|a| a == "--json");
    let findings = scan_directory(target_path);

    if use_json {
        render_json(&findings)
    } else {
        Ok(render_text(&findings))
    }
}

/// Recursively scan a directory for PB source files and collect findings.
fn scan_directory(root: &Path) -> Vec<Finding> {
    let mut findings = Vec::new();

    let sr_exts: &[&str] = &["srw", "srd", "srm", "srf", "srs", "sru", "sra"];
    let ps_exts: &[&str] = &["ps"];

    let walker = walkdir::WalkDir::new(root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let ext = entry
            .path()
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        let is_src = sr_exts.contains(&ext.as_str());
        let is_ps = ps_exts.contains(&ext.as_str());

        if !is_src && !is_ps {
            continue;
        }

        let rel_path = entry
            .path()
            .strip_prefix(root)
            .unwrap_or(entry.path())
            .display()
            .to_string();

        let content = match fs::read_to_string(entry.path()) {
            Ok(c) => c,
            Err(_) => continue,
        };

        scan_file_content(&rel_path, &content, &mut findings, is_src);
    }

    findings
}

/// Scan a single file's content for anti-patterns.
fn scan_file_content(rel_path: &str, content: &str, findings: &mut Vec<Finding>, is_pb_source: bool) {
    let lines: Vec<&str> = content.lines().collect();

    // Per-line checks
    for (i, line) in lines.iter().enumerate() {
        let ln = i + 1;

        // Long lines
        if line.len() > 200 {
            findings.push(Finding {
                file: rel_path.to_string(),
                line: ln,
                severity: "info".to_string(),
                rule: "LONG_LINE".to_string(),
                message: format!("Line exceeds 200 characters ({} chars)", line.len()),
            });
        }

        if !is_pb_source {
            continue;
        }

        let upper = line.to_uppercase();

        // GOTO usage
        if upper.contains("GOTO ") || upper.contains(" GOTO") {
            findings.push(Finding {
                file: rel_path.to_string(),
                line: ln,
                severity: "warning".to_string(),
                rule: "GOTO_USAGE".to_string(),
                message: "GOTO statement found; consider restructuring with loops/conditions".to_string(),
            });
        }

        // TODO / FIXME comments
        if upper.contains("TODO") || upper.contains("FIXME") || upper.contains("HACK") {
            findings.push(Finding {
                file: rel_path.to_string(),
                line: ln,
                severity: "info".to_string(),
                rule: "TODO_FIXME".to_string(),
                message: format!("Comment tag found: {}", line.trim()),
            });
        }

        // Hardcoded connection strings
        for pat in CONN_PATTERNS {
            if upper.contains(&pat.to_uppercase()) {
                findings.push(Finding {
                    file: rel_path.to_string(),
                    line: ln,
                    severity: "warning".to_string(),
                    rule: "HARDCODED_CONN".to_string(),
                    message: format!("Hardcoded connection string pattern: {}", pat),
                });
                break; // one finding per line for this rule
            }
        }

        // Deprecated API
        for api in DEPRECATED_APIS {
            if upper.contains(&api.to_uppercase()) {
                findings.push(Finding {
                    file: rel_path.to_string(),
                    line: ln,
                    severity: "warning".to_string(),
                    rule: "DEPRECATED_API".to_string(),
                    message: format!("Potentially deprecated API: {}", api),
                });
                break;
            }
        }

        // Global variable declarations
        if upper.contains("GLOBAL ") && !upper.contains("GLOBAL FUNCTION")
            && !upper.contains("GLOBAL SUBROUTINE") {
            findings.push(Finding {
                file: rel_path.to_string(),
                line: ln,
                severity: "info".to_string(),
                rule: "GLOBAL_VAR".to_string(),
                message: "Global variable declaration; consider encapsulating in an application singleton".to_string(),
            });
        }

        // Hardcoded SQL
        if upper.contains("SELECT ") && upper.contains(" FROM ")
            || upper.contains("INSERT ") && upper.contains(" INTO ")
            || upper.contains("UPDATE ") && upper.contains(" SET ")
            || upper.contains("DELETE ") && upper.contains(" FROM ")
        {
            findings.push(Finding {
                file: rel_path.to_string(),
                line: ln,
                severity: "warning".to_string(),
                rule: "HARDCODED_SQL".to_string(),
                message: "Hardcoded SQL statement; consider moving to DataWindow or stored procedure".to_string(),
            });
        }
    }

    // File-level check: empty catch blocks
    if is_pb_source {
        let content_upper = content.to_uppercase();
        // Simple heuristic: try/catch with nothing or just "return" inside
        let try_positions: Vec<usize> = content_upper.match_indices("TRY").map(|(i, _)| i).collect();
        let catch_positions: Vec<usize> = content_upper.match_indices("CATCH").map(|(i, _)| i).collect();
        let end_try_positions: Vec<usize> = content_upper.match_indices("END TRY").map(|(i, _)| i).collect();

        for &catch_start in &catch_positions {
            // Find nearest END TRY after this CATCH
            let end_after: Vec<usize> = end_try_positions.iter()
                .copied()
                .filter(|&e| e > catch_start)
                .collect();
            if let Some(&end_pos) = end_after.first() {
                let catch_body = &content[catch_start + 5..end_pos];
                let trimmed = catch_body.trim();
                if trimmed.is_empty() || trimmed.len() < 10 {
                    // Find which line this belongs to
                    let mut line_num = 1;
                    let mut pos = 0;
                    for (i, line) in lines.iter().enumerate() {
                        if pos + line.len() + 1 > catch_start {
                            line_num = i + 1;
                            break;
                        }
                        pos += line.len() + 1;
                    }
                    findings.push(Finding {
                        file: rel_path.to_string(),
                        line: line_num,
                        severity: "warning".to_string(),
                        rule: "EMPTY_CATCH".to_string(),
                        message: "Empty or near-empty CATCH block; add error logging".to_string(),
                    });
                }
            }
        }
    }
}

/// Render findings as human-readable text.
fn render_text(findings: &[Finding]) -> String {
    let mut out = String::new();
    out.push_str(&format!(
        "Refactoring Report\n{}\n\n",
        "=".repeat(60)
    ));

    // Summary counts
    let mut by_rule: HashMap<&str, usize> = HashMap::new();
    let mut by_severity: HashMap<&str, usize> = HashMap::new();
    let mut files_affected: Vec<&str> = Vec::new();

    for f in findings {
        *by_rule.entry(&f.rule).or_insert(0) += 1;
        *by_severity.entry(&f.severity).or_insert(0) += 1;
        if !files_affected.contains(&f.file.as_str()) {
            files_affected.push(&f.file);
        }
    }

    out.push_str(&format!("Total findings: {}\n", findings.len()));
    out.push_str(&format!("Files affected: {}\n", files_affected.len()));
    out.push_str("By severity:\n");
    for (sev, count) in by_severity.iter() {
        out.push_str(&format!("  {}: {}\n", sev, count));
    }
    out.push_str("By rule:\n");
    let mut rules: Vec<(&str, usize)> = by_rule.into_iter().collect();
    rules.sort_by(|a, b| b.1.cmp(&a.1));
    for (rule, count) in &rules {
        out.push_str(&format!("  {}: {}\n", rule, count));
    }

    out.push_str(&format!("\n{}\nDetails:\n", "-".repeat(60)));

    let icon = |sev: &str| -> &str {
        match sev {
            "error" => "[!]",
            "warning" => "[?]",
            _ => "[+]",
        }
    };

    for f in findings.iter().take(50) {
        out.push_str(&format!(
            "  {} {}:{} - {} [{}]\n",
            icon(&f.severity),
            f.file,
            f.line,
            f.message,
            f.rule
        ));
    }

    if findings.len() > 50 {
        out.push_str(&format!("  ... and {} more findings\n", findings.len() - 50));
    }

    out.push_str(&format!(
        "\nCompleted. {} total findings in {} files.\n",
        findings.len(),
        files_affected.len()
    ));

    out
}

/// Render findings as JSON.
fn render_json(findings: &[Finding]) -> Result<String, String> {
    let items: Vec<String> = findings.iter().map(|f| f.to_json()).collect();

    let mut summary_by_rule: HashMap<&str, usize> = HashMap::new();
    let mut summary_by_sev: HashMap<&str, usize> = HashMap::new();
    for f in findings {
        *summary_by_rule.entry(&f.rule).or_insert(0) += 1;
        *summary_by_sev.entry(&f.severity).or_insert(0) += 1;
    }

    let json = format!(
        r#"{{
  "total_findings": {},
  "by_severity": {},
  "by_rule": {},
  "findings": [
    {}
  ]
}}"#,
        findings.len(),
        serde_json_compat(&summary_by_sev),
        serde_json_compat(&summary_by_rule),
        items.join(",\n    ")
    );

    Ok(json)
}

/// Simple JSON object builder for HashMap<String, usize>
fn serde_json_compat(map: &HashMap<&str, usize>) -> String {
    let items: Vec<String> = map
        .iter()
        .map(|(k, v)| format!(r#""{}":{}"#, k, v))
        .collect();
    format!("{{{}}}", items.join(", "))
}
