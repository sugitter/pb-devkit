// Review command for CLI – comprehensive PowerBuilder project review
//
// Performs a multi-phase analysis and generates REVIEW.md:
//   1. Project structure (PBL/EXE inventory, object counts per type)
//   2. Code quality scan (GOTO, globals, empty catch, hardcoded SQL, etc.)
//   3. DataWindow inventory (SQL extraction, table usage map)
//   4. Dependency mapping (cross-PBL references)
//   5. Improvement suggestions
//
// Usage: pbdevkit review <project_dir> [--output <file>] [--json] [--no-dw] [--no-quality]

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ─────────────────────────────────────────────────────────────────────────────
// Public entry point
// ─────────────────────────────────────────────────────────────────────────────

pub fn run_review(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit review <project_dir> [--output <file>] [--json] [--no-dw] [--no-quality]".to_string());
    }

    let target = Path::new(&args[0]);
    if !target.exists() {
        return Err(format!("Path not found: {}", target.display()));
    }

    let use_json   = args.iter().any(|a| a == "--json");
    let no_dw      = args.iter().any(|a| a == "--no-dw");
    let no_quality = args.iter().any(|a| a == "--no-quality");
    let output_path: Option<PathBuf> = args.iter().position(|a| a == "--output")
        .and_then(|i| args.get(i + 1))
        .map(PathBuf::from);

    let mut log = Vec::<String>::new();
    log.push(format!("================================================================="));
    log.push(format!("  pb review — PowerBuilder Project Review"));
    log.push(format!("================================================================="));
    log.push(format!("  Target: {}", target.display()));
    log.push(String::new());

    // ── Phase 1: structure ──
    log.push("[1/4] Scanning project structure ...".to_string());
    let src_dir = find_source_dir(target);
    let project = scan_project(target, src_dir.as_deref());
    log.push(format!("  Objects: {}  Lines: {}", project.total_objects, project.total_lines));

    // ── Phase 2: quality ──
    let quality = if !no_quality {
        if let Some(ref sd) = src_dir {
            log.push(format!("[2/4] Analysing code quality in {} ...", sd.display()));
            let q = analyze_quality(sd);
            log.push(format!("  Findings: {} ({} warnings)",
                q.total_findings, q.by_severity.get("warning").copied().unwrap_or(0)));
            q
        } else {
            log.push("[2/4] Code quality skipped (no source dir).".to_string());
            QualityReport::default()
        }
    } else {
        log.push("[2/4] Code quality skipped (--no-quality).".to_string());
        QualityReport::default()
    };

    // ── Phase 3: DataWindow ──
    let dw = if !no_dw {
        if let Some(ref sd) = src_dir {
            log.push("[3/4] Scanning DataWindow objects ...".to_string());
            let d = analyze_datawindows(sd);
            log.push(format!("  DW count: {}  Tables: {}", d.total, d.tables_usage.len()));
            d
        } else {
            log.push("[3/4] DataWindow skipped (no source dir).".to_string());
            DwReport::default()
        }
    } else {
        log.push("[3/4] DataWindow skipped (--no-dw).".to_string());
        DwReport::default()
    };

    // ── Phase 4: dependencies ──
    let deps = if let Some(ref sd) = src_dir {
        log.push("[4/4] Mapping PBL dependencies ...".to_string());
        let d = analyze_dependencies(sd);
        log.push(format!("  Cross-PBL edges: {}", d.pbl_deps.len()));
        d
    } else {
        log.push("[4/4] Dependency mapping skipped.".to_string());
        DepReport::default()
    };

    // ── Generate report ──
    let suggestions = generate_suggestions(&project, &quality, &dw, &deps);

    let report_md = render_markdown(&project, &quality, &dw, &deps, &suggestions);

    // Determine output file
    let out = output_path.unwrap_or_else(|| target.join("REVIEW.md"));
    fs::write(&out, &report_md).map_err(|e| format!("Failed to write report: {}", e))?;

    log.push(String::new());
    log.push(format!("  Report written: {}", out.display()));
    log.push(format!("================================================================="));
    log.push(format!(
        "  Summary: {} objects | {} quality findings | {} DataWindows | {} tables",
        project.total_objects, quality.total_findings, dw.total, dw.tables_usage.len()
    ));
    log.push(format!("================================================================="));

    if use_json {
        // Return simple JSON summary
        let json = format!(
            r#"{{"status":"ok","report":"{}","total_objects":{},"total_findings":{},"dw_count":{},"tables":{}}}"#,
            out.display(),
            project.total_objects,
            quality.total_findings,
            dw.total,
            dw.tables_usage.len()
        );
        return Ok(json);
    }

    Ok(log.join("\n"))
}

// ─────────────────────────────────────────────────────────────────────────────
// Data structures
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Default)]
struct ProjectInfo {
    root: String,
    src_dir: Option<String>,
    pbl_files: Vec<String>,
    exe_files: Vec<String>,
    pbd_files: Vec<String>,
    /// object type -> count
    object_counts: HashMap<String, usize>,
    total_objects: usize,
    total_lines: usize,
    /// pbl_name -> (type -> count)
    pbl_object_counts: HashMap<String, HashMap<String, usize>>,
}

#[derive(Debug, Default)]
struct QualityFinding {
    file: String,
    line: usize,
    severity: String,
    #[allow(dead_code)]
    rule: String,
    message: String,
}

#[derive(Debug, Default)]
struct QualityReport {
    total_findings: usize,
    by_severity: HashMap<String, usize>,
    by_rule: HashMap<String, usize>,
    findings: Vec<QualityFinding>,
}

#[derive(Debug, Default)]
struct DwInfo {
    name: String,
    style: String,
    tables: Vec<String>,
    column_count: usize,
    arg_count: usize,
    has_sql: bool,
}

#[derive(Debug, Default)]
struct DwReport {
    total: usize,
    /// table_name -> list of DW names
    tables_usage: HashMap<String, Vec<String>>,
    datawindows: Vec<DwInfo>,
}

#[derive(Debug, Default)]
struct DepReport {
    /// pbl_name -> list of dependent pbl names
    pbl_deps: HashMap<String, Vec<String>>,
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 1: Project structure
// ─────────────────────────────────────────────────────────────────────────────

fn find_source_dir(target: &Path) -> Option<PathBuf> {
    // Check if target itself contains .sr* files
    if has_source_files(target) {
        return Some(target.to_path_buf());
    }
    // Check src/ subdirectory
    let src = target.join("src");
    if src.is_dir() && has_source_files(&src) {
        return Some(src);
    }
    None
}

fn has_source_files(dir: &Path) -> bool {
    if let Ok(rd) = fs::read_dir(dir) {
        for entry in rd.flatten() {
            let ext = entry.path().extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();
            if matches!(ext.as_str(), "srw" | "srd" | "srm" | "srf" | "srs" | "sru" | "sra") {
                return true;
            }
        }
    }
    // Also check sub-directories one level deep (pbl sub-dirs)
    if let Ok(rd) = fs::read_dir(dir) {
        for entry in rd.flatten() {
            if entry.path().is_dir() && has_source_files(&entry.path()) {
                return true;
            }
        }
    }
    false
}

fn scan_project(target: &Path, src_dir: Option<&Path>) -> ProjectInfo {
    let mut info = ProjectInfo {
        root: target.display().to_string(),
        src_dir: src_dir.map(|p| p.display().to_string()),
        ..Default::default()
    };

    // Binary files in target root
    if let Ok(rd) = fs::read_dir(target) {
        for entry in rd.flatten() {
            let fname = entry.file_name().to_string_lossy().to_lowercase();
            if fname.ends_with(".pbl") { info.pbl_files.push(fname); }
            else if fname.ends_with(".exe") { info.exe_files.push(fname); }
            else if fname.ends_with(".pbd") { info.pbd_files.push(fname); }
        }
    }

    // Source file inventory
    if let Some(src) = src_dir {
        walk_source_files(src, src, &mut info);
    }

    info
}

fn walk_source_files(src_root: &Path, dir: &Path, info: &mut ProjectInfo) {
    let ext_map: &[(&str, &str)] = &[
        ("srw", "Window"), ("srd", "DataWindow"), ("srm", "Menu"),
        ("srf", "Function"), ("srs", "Structure"), ("sru", "UserObject"),
        ("sra", "Application"), ("srq", "Query"),
    ];

    if let Ok(rd) = fs::read_dir(dir) {
        for entry in rd.flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk_source_files(src_root, &path, info);
                continue;
            }
            let ext = path.extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();

            let obj_type = ext_map.iter()
                .find(|(e, _)| *e == ext.as_str())
                .map(|(_, t)| *t);

            if let Some(otype) = obj_type {
                info.total_objects += 1;
                *info.object_counts.entry(otype.to_string()).or_insert(0) += 1;

                // Per-PBL: first sub-directory of src_root
                let rel = path.strip_prefix(src_root).unwrap_or(&path);
                let pbl_name = rel.components().next()
                    .map(|c| c.as_os_str().to_string_lossy().to_string())
                    .unwrap_or_else(|| "(root)".to_string());

                let has_ext = pbl_name.contains('.');
                let pbl_label = if has_ext { pbl_name } else { pbl_name };
                let pbl_entry = info.pbl_object_counts.entry(pbl_label).or_default();
                *pbl_entry.entry(otype.to_string()).or_insert(0) += 1;

                // Line count
                if let Ok(content) = fs::read_to_string(&path) {
                    info.total_lines += content.lines().count();
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 2: Code quality
// ─────────────────────────────────────────────────────────────────────────────

const DEPRECATED_APIS: &[&str] = &[
    "RegistryGet", "RegistrySet", "GetEnvironment", "SetEnvironment",
    "PrintScreen", "SetPointer", "SetMicroHelp", "TriggerEvent",
];

const CONN_PATTERNS: &[&str] = &[
    "SQLCA.DBMS", "SQLCA.Database", "SQLCA.ServerName",
    "SQLCA.LogId", "SQLCA.DBPass", "SQLCA.LogPass",
    "UID=", "PWD=", "DSN=", "DRIVER=",
];

fn analyze_quality(src_dir: &Path) -> QualityReport {
    let mut report = QualityReport::default();
    walk_quality(src_dir, src_dir, &mut report);
    report
}

fn walk_quality(src_root: &Path, dir: &Path, report: &mut QualityReport) {
    if let Ok(rd) = fs::read_dir(dir) {
        for entry in rd.flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk_quality(src_root, &path, report);
                continue;
            }
            let ext = path.extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();
            let is_src = matches!(ext.as_str(), "srw"|"srd"|"srm"|"srf"|"srs"|"sru"|"sra");
            if !is_src { continue; }

            let rel = path.strip_prefix(src_root).unwrap_or(&path);
            let rel_str = rel.display().to_string();

            if let Ok(content) = fs::read_to_string(&path) {
                scan_quality_file(&rel_str, &content, report);
            }
        }
    }
}

fn scan_quality_file(rel: &str, content: &str, report: &mut QualityReport) {
    for (i, line) in content.lines().enumerate() {
        let ln = i + 1;
        let upper = line.to_uppercase();

        // Long line
        if line.len() > 200 {
            push_finding(report, rel, ln, "info", "LONG_LINE",
                &format!("Line exceeds 200 chars ({})", line.len()));
        }

        // GOTO
        if upper.contains("GOTO ") || upper.contains(" GOTO") {
            push_finding(report, rel, ln, "warning", "GOTO_USAGE",
                "GOTO statement – consider restructuring");
        }

        // TODO/FIXME
        if upper.contains("TODO") || upper.contains("FIXME") || upper.contains("HACK") {
            push_finding(report, rel, ln, "info", "TODO_FIXME",
                &format!("Comment tag: {}", line.trim()));
        }

        // Hardcoded conn
        for pat in CONN_PATTERNS {
            if upper.contains(&pat.to_uppercase()) {
                push_finding(report, rel, ln, "warning", "HARDCODED_CONN",
                    &format!("Hardcoded connection pattern: {}", pat));
                break;
            }
        }

        // Deprecated API
        for api in DEPRECATED_APIS {
            if upper.contains(&api.to_uppercase()) {
                push_finding(report, rel, ln, "warning", "DEPRECATED_API",
                    &format!("Deprecated API: {}", api));
                break;
            }
        }

        // Global var
        if upper.contains("GLOBAL ") && !upper.contains("GLOBAL FUNCTION")
            && !upper.contains("GLOBAL SUBROUTINE") {
            push_finding(report, rel, ln, "info", "GLOBAL_VAR",
                "Global variable declaration");
        }

        // Hardcoded SQL
        if (upper.contains("SELECT ") && upper.contains(" FROM "))
            || (upper.contains("INSERT ") && upper.contains(" INTO "))
            || (upper.contains("UPDATE ") && upper.contains(" SET "))
            || (upper.contains("DELETE ") && upper.contains(" FROM "))
        {
            push_finding(report, rel, ln, "warning", "HARDCODED_SQL",
                "Hardcoded SQL – consider DataWindow or stored procedure");
        }
    }

    // Empty catch heuristic
    let cu = content.to_uppercase();
    let catch_indices: Vec<usize> = cu.match_indices("CATCH").map(|(i, _)| i).collect();
    let end_try_indices: Vec<usize> = cu.match_indices("END TRY").map(|(i, _)| i).collect();
    for &ci in &catch_indices {
        if let Some(&ei) = end_try_indices.iter().find(|&&e| e > ci) {
            let body = &content[ci + 5..ei].trim().to_string();
            if body.len() < 10 {
                let line_num = content[..ci].matches('\n').count() + 1;
                push_finding(report, rel, line_num, "warning", "EMPTY_CATCH",
                    "Empty CATCH block – add error logging");
            }
        }
    }
}

fn push_finding(report: &mut QualityReport, file: &str, line: usize,
    severity: &str, rule: &str, msg: &str) {
    *report.by_severity.entry(severity.to_string()).or_insert(0) += 1;
    *report.by_rule.entry(rule.to_string()).or_insert(0) += 1;
    report.total_findings += 1;
    report.findings.push(QualityFinding {
        file: file.to_string(),
        line,
        severity: severity.to_string(),
        rule: rule.to_string(),
        message: msg.to_string(),
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3: DataWindow
// ─────────────────────────────────────────────────────────────────────────────

fn analyze_datawindows(src_dir: &Path) -> DwReport {
    let mut report = DwReport::default();
    walk_dw(src_dir, src_dir, &mut report);
    report
}

fn walk_dw(src_root: &Path, dir: &Path, report: &mut DwReport) {
    if let Ok(rd) = fs::read_dir(dir) {
        for entry in rd.flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk_dw(src_root, &path, report);
                continue;
            }
            let ext = path.extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();
            if ext != "srd" { continue; }

            let name = path.file_stem()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default();

            if let Ok(content) = fs::read_to_string(&path) {
                let info = parse_dw_source(&name, &content);
                for tbl in &info.tables {
                    report.tables_usage.entry(tbl.clone()).or_default().push(name.clone());
                }
                report.datawindows.push(info);
                report.total += 1;
            }
        }
    }
}

fn parse_dw_source(name: &str, content: &str) -> DwInfo {
    let mut info = DwInfo { name: name.to_string(), ..Default::default() };

    // Table names: "table name=xxx"
    for line in content.lines() {
        let upper = line.to_uppercase();
        if upper.contains("TABLE NAME=") {
            if let Some(pos) = upper.find("TABLE NAME=") {
                let rest = &line[pos + 11..];
                let tbl: String = rest.split_whitespace().next()
                    .unwrap_or("")
                    .trim_matches('"')
                    .to_string();
                if !tbl.is_empty() && !info.tables.contains(&tbl) {
                    info.tables.push(tbl);
                }
            }
        }
        // Style
        if upper.contains("STYLE TYPE=") {
            if let Some(pos) = upper.find("STYLE TYPE=") {
                let s: String = line[pos + 11..].split_whitespace().next()
                    .unwrap_or("").to_string();
                info.style = s;
            }
        }
        // SQL presence
        if upper.contains("RETRIEVE=") { info.has_sql = true; }
        // Column count heuristic
        if upper.contains("COLUMN TYPE=") { info.column_count += 1; }
        // Arg count
        if upper.contains("ARGUMENTS=(") { info.arg_count += 1; }
    }

    // FROM clause in SQL (simple)
    if let Some(from_pos) = content.to_uppercase().find("FROM ") {
        let rest = &content[from_pos + 5..];
        let end = rest.find(|c: char| c == '\n' || c == '\r' || c == '"')
            .unwrap_or(rest.len().min(80));
        for word in rest[..end].split(|c: char| !c.is_alphanumeric() && c != '_') {
            let w = word.trim().to_string();
            if w.len() > 1 && !w.eq_ignore_ascii_case("WHERE")
                && !w.eq_ignore_ascii_case("ORDER")
                && !w.eq_ignore_ascii_case("GROUP")
                && !info.tables.contains(&w) {
                info.tables.push(w);
                break; // take only first table from FROM clause
            }
        }
    }

    info
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 4: Dependencies
// ─────────────────────────────────────────────────────────────────────────────

fn analyze_dependencies(src_dir: &Path) -> DepReport {
    let mut report = DepReport::default();
    // Enumerate top-level subdirs as "PBL buckets"
    let pbl_dirs: Vec<PathBuf> = fs::read_dir(src_dir)
        .ok()
        .into_iter()
        .flatten()
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();

    if pbl_dirs.is_empty() { return report; }

    // Build name -> pbl_name index
    let mut obj_to_pbl: HashMap<String, String> = HashMap::new();
    for pbl_dir in &pbl_dirs {
        let pbl_name = pbl_dir.file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        if let Ok(rd) = fs::read_dir(pbl_dir) {
            for entry in rd.flatten() {
                if let Some(stem) = entry.path().file_stem() {
                    obj_to_pbl.insert(stem.to_string_lossy().to_lowercase(), pbl_name.clone());
                }
            }
        }
    }

    // Scan each PBL's source for references to objects in other PBLs
    for pbl_dir in &pbl_dirs {
        let pbl_name = pbl_dir.file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        let mut deps: std::collections::HashSet<String> = std::collections::HashSet::new();

        if let Ok(rd) = fs::read_dir(pbl_dir) {
            for entry in rd.flatten() {
                let path = entry.path();
                let ext = path.extension()
                    .and_then(|e| e.to_str())
                    .unwrap_or("")
                    .to_lowercase();
                if !matches!(ext.as_str(), "srw"|"srf"|"sru"|"srm") { continue; }

                if let Ok(content) = fs::read_to_string(&path) {
                    // Look for "of <object>" or "from <object>" patterns
                    let lower = content.to_lowercase();
                    for kw in &[" of ", "from "] {
                        let mut pos = 0;
                        while let Some(p) = lower[pos..].find(kw) {
                            let start = pos + p + kw.len();
                            let rest = &lower[start..];
                            let end = rest.find(|c: char| !c.is_alphanumeric() && c != '_')
                                .unwrap_or(rest.len().min(40));
                            let obj = rest[..end].trim().to_string();
                            if let Some(other_pbl) = obj_to_pbl.get(&obj) {
                                if other_pbl != &pbl_name {
                                    deps.insert(other_pbl.clone());
                                }
                            }
                            pos = start + end + 1;
                            if pos >= lower.len() { break; }
                        }
                    }
                }
            }
        }

        if !deps.is_empty() {
            let mut dep_list: Vec<String> = deps.into_iter().collect();
            dep_list.sort();
            report.pbl_deps.insert(pbl_name, dep_list);
        }
    }

    report
}

// ─────────────────────────────────────────────────────────────────────────────
// Improvement suggestions
// ─────────────────────────────────────────────────────────────────────────────

fn generate_suggestions(proj: &ProjectInfo, quality: &QualityReport,
    dw: &DwReport, _deps: &DepReport) -> Vec<String> {
    let mut sug = Vec::new();

    // Large PBL
    for (pbl, counts) in &proj.pbl_object_counts {
        let total: usize = counts.values().sum();
        if total > 100 {
            sug.push(format!("PBL `{}` has {} objects – consider splitting into sub-modules.", pbl, total));
        }
    }

    // Quality
    if quality.by_rule.get("GOTO_USAGE").copied().unwrap_or(0) > 5 {
        sug.push("Multiple GOTO statements found – refactor to structured loops/conditions.".to_string());
    }
    if quality.by_rule.get("GLOBAL_VAR").copied().unwrap_or(0) > 10 {
        sug.push("Many global variables – encapsulate in an application-level singleton object.".to_string());
    }
    if quality.by_rule.get("EMPTY_CATCH").copied().unwrap_or(0) > 0 {
        sug.push("Empty CATCH blocks detected – add logging to avoid silent failures.".to_string());
    }
    if quality.by_rule.get("HARDCODED_SQL").copied().unwrap_or(0) > 0 {
        sug.push("Hardcoded SQL found – move to DataWindow objects or stored procedures.".to_string());
    }
    if quality.by_rule.get("HARDCODED_CONN").copied().unwrap_or(0) > 0 {
        sug.push("Hardcoded connection strings – centralise in application open event config.".to_string());
    }

    // DW
    if dw.total > 0 {
        let no_table: usize = dw.datawindows.iter()
            .filter(|d| d.tables.is_empty())
            .count();
        if no_table > 0 {
            sug.push(format!("{} DataWindow(s) with no detected table – may use stored procs or dynamic SQL; add comments.", no_table));
        }
    }

    if proj.pbl_files.is_empty() && (!proj.exe_files.is_empty() || !proj.pbd_files.is_empty()) {
        sug.push("Only compiled files (EXE/PBD) found – run `pb autoexport` to extract source objects.".to_string());
    }

    if sug.is_empty() {
        sug.push("✅ Project structure is clean; no major issues detected.".to_string());
    }

    sug
}

// ─────────────────────────────────────────────────────────────────────────────
// Markdown renderer
// ─────────────────────────────────────────────────────────────────────────────

fn render_markdown(proj: &ProjectInfo, quality: &QualityReport,
    dw: &DwReport, deps: &DepReport, suggestions: &[String]) -> String {
    let ts = now_iso();
    let mut out = String::new();

    out.push_str("# PowerBuilder 项目审查报告\n\n");
    out.push_str(&format!("> 生成时间: {}  \n", &ts));
    out.push_str(&format!("> 项目路径: `{}`\n\n", proj.root));
    out.push_str("---\n\n");

    // ── Section 1: Structure ──
    out.push_str("## 一、项目结构\n\n");
    if !proj.pbl_files.is_empty() {
        out.push_str(&format!("- **PBL**: {}\n", proj.pbl_files.join(", ")));
    }
    if !proj.exe_files.is_empty() {
        out.push_str(&format!("- **EXE**: {}\n", proj.exe_files.join(", ")));
    }
    if !proj.pbd_files.is_empty() {
        out.push_str(&format!("- **PBD**: {}\n", proj.pbd_files.join(", ")));
    }
    if let Some(ref sd) = proj.src_dir {
        out.push_str(&format!("- **源码目录**: `{}`\n", sd));
    }
    out.push('\n');

    if !proj.object_counts.is_empty() {
        out.push_str("### 对象统计\n\n| 类型 | 数量 |\n|------|------|\n");
        let mut types: Vec<(&String, &usize)> = proj.object_counts.iter().collect();
        types.sort_by_key(|(t, _)| t.as_str());
        for (t, c) in &types {
            out.push_str(&format!("| {} | {} |\n", t, c));
        }
        out.push_str(&format!("| **合计** | **{}** |\n\n", proj.total_objects));
        out.push_str(&format!("总行数: **{}**\n\n", proj.total_lines));
    }

    // Per-PBL breakdown
    if !proj.pbl_object_counts.is_empty() {
        out.push_str("### 各 PBL 对象分布\n\n");
        let all_types: Vec<String> = {
            let mut s: std::collections::HashSet<String> = std::collections::HashSet::new();
            for m in proj.pbl_object_counts.values() { for k in m.keys() { s.insert(k.clone()); } }
            let mut v: Vec<String> = s.into_iter().collect(); v.sort(); v
        };
        out.push_str(&format!("| PBL | {} | 合计 |\n", all_types.join(" | ")));
        out.push_str(&format!("|-----|{}|------|\n", "---|".repeat(all_types.len())));
        let mut pbls: Vec<(&String, &HashMap<String, usize>)> = proj.pbl_object_counts.iter().collect();
        pbls.sort_by_key(|(n, _)| n.as_str());
        for (pbl, counts) in pbls {
            let total: usize = counts.values().sum();
            let cells: Vec<String> = all_types.iter()
                .map(|t| counts.get(t).copied().unwrap_or(0).to_string())
                .collect();
            out.push_str(&format!("| `{}` | {} | {} |\n", pbl, cells.join(" | "), total));
        }
        out.push('\n');
    }

    // ── Section 2: Quality ──
    out.push_str("---\n\n## 二、代码质量\n\n");
    if quality.total_findings == 0 {
        out.push_str("> ✅ 未发现代码质量问题。\n\n");
    } else {
        out.push_str(&format!("- 警告 (warning): **{}**\n", quality.by_severity.get("warning").copied().unwrap_or(0)));
        out.push_str(&format!("- 信息 (info): **{}**\n\n", quality.by_severity.get("info").copied().unwrap_or(0)));
        out.push_str("### 规则分布\n\n| 规则 | 数量 |\n|------|------|\n");
        let mut rules: Vec<(&String, &usize)> = quality.by_rule.iter().collect();
        rules.sort_by(|a, b| b.1.cmp(a.1));
        for (rule, cnt) in &rules {
            out.push_str(&format!("| `{}` | {} |\n", rule, cnt));
        }
        out.push('\n');

        let show = quality.findings.iter().take(30);
        out.push_str("### 发现明细 (Top 30)\n\n| 级别 | 文件 | 行 | 描述 |\n|------|------|-----|------|\n");
        for f in show {
            let icon = match f.severity.as_str() {
                "error" => "🔴", "warning" => "🟡", _ => "🔵",
            };
            out.push_str(&format!("| {} | `{}` | {} | {} |\n",
                icon, f.file, f.line, f.message.replace('|', "\\|")));
        }
        if quality.findings.len() > 30 {
            out.push_str(&format!("\n> ... 还有 {} 条明细\n", quality.findings.len() - 30));
        }
        out.push('\n');
    }

    // ── Section 3: DataWindows ──
    out.push_str("---\n\n## 三、DataWindow 清单\n\n");
    if dw.total == 0 {
        out.push_str("> 未发现 DataWindow 对象。\n\n");
    } else {
        out.push_str(&format!("共 **{}** 个 DataWindow，引用 **{}** 个数据库表。\n\n",
            dw.total, dw.tables_usage.len()));

        out.push_str("### 数据库表使用频率\n\n| 表名 | 引用 DW 数 |\n|------|----------|\n");
        let mut tbl_list: Vec<(&String, &Vec<String>)> = dw.tables_usage.iter().collect();
        tbl_list.sort_by(|a, b| b.1.len().cmp(&a.1.len()));
        for (tbl, dws) in tbl_list.iter().take(30) {
            out.push_str(&format!("| `{}` | {} |\n", tbl, dws.len()));
        }
        out.push('\n');

        out.push_str("### DataWindow 详情\n\n| 名称 | 样式 | 表 | 列数 | SQL |\n|------|------|----|------|-----|\n");
        for d in &dw.datawindows {
            let tbls = d.tables.iter().map(|t| format!("`{}`", t)).collect::<Vec<_>>().join(", ");
            let has_sql = if d.has_sql { "✅" } else { "—" };
            out.push_str(&format!("| `{}` | {} | {} | {} | {} |\n",
                d.name, d.style, tbls, d.column_count, has_sql));
        }
        out.push('\n');
    }

    // ── Section 4: Dependencies ──
    out.push_str("---\n\n## 四、PBL 依赖关系\n\n");
    if deps.pbl_deps.is_empty() {
        out.push_str("> 未检测到跨 PBL 依赖关系。\n\n");
    } else {
        out.push_str("| PBL | 依赖 |\n|-----|------|\n");
        let mut dep_list: Vec<(&String, &Vec<String>)> = deps.pbl_deps.iter().collect();
        dep_list.sort_by_key(|(n, _)| n.as_str());
        for (pbl, dep_pbls) in dep_list {
            out.push_str(&format!("| `{}` | {} |\n", pbl,
                dep_pbls.iter().map(|d| format!("`{}`", d)).collect::<Vec<_>>().join(", ")));
        }
        out.push('\n');
    }

    // ── Section 5: Suggestions ──
    out.push_str("---\n\n## 五、改进建议\n\n");
    for (i, s) in suggestions.iter().enumerate() {
        out.push_str(&format!("{}. {}\n", i + 1, s));
    }
    out.push('\n');
    out.push_str("---\n\n");
    out.push_str("*Generated by [pb-devkit](https://github.com/sugitter/pb-devkit) — `pb review`*\n");

    out
}

fn now_iso() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Simple ISO-8601 approximation without chrono dependency
    format!("{} UTC", secs)
}
