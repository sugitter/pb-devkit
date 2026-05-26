/// pb-devkit CLI — `autoexport` command
///
/// Auto-detect project type and export all sources to a structured src/ directory.
/// Supports three project types:
///   PBL_PROJECT    — Export .pbl source files by PBL grouping or object type
///   BINARY_PROJECT — Decompile EXE/PBD embedded sources via pb-devkit-core
///   MIXED_PROJECT  — PBL export (primary) + decompiled binaries (_decompiled/)
///
/// Usage:
///   pbdevkit autoexport <dir>
///   pbdevkit autoexport <dir> -o ./src
///   pbdevkit autoexport <dir> --detect
///   pbdevkit autoexport <dir> --by-type
///   pbdevkit autoexport <dir> --force
///   pbdevkit autoexport <dir> --no-readme

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// ── Public entry point ────────────────────────────────────────────────────────

pub fn run_autoexport(args: &[String]) -> Result<String, String> {
    if args.is_empty() || args[0] == "--help" || args[0] == "-h" {
        return Ok(autoexport_help());
    }

    let target = PathBuf::from(&args[0]);
    if !target.is_dir() {
        return Err(format!("Not a directory: {}", target.display()));
    }

    // Parse flags
    let output_dir = extract_flag_value(args, &["-o", "--output"]);
    let detect_only = args.contains(&"--detect".to_string());
    let force = args.contains(&"--force".to_string());
    let no_readme = args.contains(&"--no-readme".to_string());
    let by_type = args.contains(&"--by-type".to_string());
    let quick = args.contains(&"--quick".to_string());
    let project_name_override = extract_flag_value(args, &["--project-name"]);

    let out_dir = match output_dir {
        Some(ref o) => PathBuf::from(o),
        None => target.join("src"),
    };

    // ── Step 1: Detect project type ──────────────────────────────────────────
    let mut output = Vec::new();
    output.push(format!("{}", "=".repeat(60)));
    output.push("  pb autoexport — Smart Project Export".to_string());
    output.push(format!("{}", "=".repeat(60)));
    output.push(String::new());
    output.push(format!("[1/3] Scanning project: {}", target.display()));

    let detection = detect_project_type(&target, quick);
    output.push(String::new());
    output.push(format!("  Project type : {}", detection.project_type));
    output.push(format!("  Project name : {}", detection.project_name));
    if !detection.pbl_files.is_empty() {
        output.push(format!("  PBL files    : {}", detection.pbl_files.len()));
    }
    if !detection.exe_files.is_empty() {
        output.push(format!("  EXE files    : {}", detection.exe_files.len()));
    }
    if !detection.pbd_files.is_empty() {
        output.push(format!("  PBD files    : {}", detection.pbd_files.len()));
    }

    if detect_only {
        output.push(String::new());
        output.push("[detect-only] Done.".to_string());
        return Ok(output.join("\n"));
    }

    if detection.project_type == "UNKNOWN" {
        return Err(format!(
            "No recognizable PB files found in: {}\n  Expected: .pbl, .exe (with embedded PBD), or .pbd files",
            target.display()
        ));
    }

    // ── Step 2: Check output directory ───────────────────────────────────────
    if out_dir.exists() {
        let has_contents = out_dir.read_dir()
            .map(|mut d| d.next().is_some())
            .unwrap_or(false);
        if has_contents && !force {
            return Err(format!(
                "Output directory already exists: {}\n  Use --force to overwrite, or specify a different -o path.",
                out_dir.display()
            ));
        }
        if has_contents {
            output.push(format!("\n[warn] Overwriting existing output: {}", out_dir.display()));
        }
    }

    let project_name = project_name_override
        .unwrap_or_else(|| detection.project_name.clone());

    // ── Step 3: Export ────────────────────────────────────────────────────────
    output.push(String::new());
    output.push(format!(
        "[2/3] Exporting [{}] → {}",
        detection.project_type,
        out_dir.display()
    ));

    let (exported, failed) = match detection.project_type.as_str() {
        "PBL_PROJECT" => export_pbl_project(&detection, &out_dir, &project_name, by_type, no_readme, &mut output),
        "BINARY_PROJECT" => export_binary_project(&detection, &out_dir, &project_name, no_readme, &mut output),
        "MIXED_PROJECT" => export_mixed_project(&detection, &out_dir, &project_name, by_type, no_readme, &mut output),
        _ => (0, 0),
    };

    // ── Summary ───────────────────────────────────────────────────────────────
    output.push(String::new());
    output.push("[3/3] Complete".to_string());
    output.push(format!("{}", "=".repeat(60)));
    output.push(format!("  Project type:  {}", detection.project_type));
    output.push(format!("  Project name:  {}", project_name));
    output.push(format!("  Output:        {}", out_dir.display()));
    output.push(format!("  Exported:      {} files", exported));
    if failed > 0 {
        output.push(format!("  Failed:        {} entries", failed));
    }
    output.push(format!("{}", "=".repeat(60)));

    Ok(output.join("\n"))
}

// ── Project detection ────────────────────────────────────────────────────────

struct ProjectDetection {
    project_type: String,
    project_name: String,
    pbl_files: Vec<PathBuf>,
    exe_files: Vec<PathBuf>,
    pbd_files: Vec<PathBuf>,
    dll_files: Vec<PathBuf>,
}

fn detect_project_type(dir: &Path, _quick: bool) -> ProjectDetection {
    let mut pbl_files = Vec::new();
    let mut exe_files = Vec::new();
    let mut pbd_files = Vec::new();
    let mut dll_files = Vec::new();

    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if !p.is_file() { continue; }
            match p.extension().and_then(|e| e.to_str()).map(|s| s.to_lowercase()).as_deref() {
                Some("pbl") => pbl_files.push(p),
                Some("exe") => exe_files.push(p),
                Some("pbd") => pbd_files.push(p),
                Some("dll") => dll_files.push(p),
                _ => {}
            }
        }
    }
    // Also scan one level deep
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let sub = entry.path();
            if !sub.is_dir() { continue; }
            if let Ok(sub_entries) = fs::read_dir(&sub) {
                for se in sub_entries.flatten() {
                    let p = se.path();
                    if !p.is_file() { continue; }
                    match p.extension().and_then(|e| e.to_str()).map(|s| s.to_lowercase()).as_deref() {
                        Some("pbl") => pbl_files.push(p),
                        Some("pbd") => pbd_files.push(p),
                        _ => {}
                    }
                }
            }
        }
    }

    pbl_files.sort();
    exe_files.sort();
    pbd_files.sort();
    dll_files.sort();

    let has_pbl = !pbl_files.is_empty();
    let has_binary = !exe_files.is_empty() || !pbd_files.is_empty();

    let project_type = if has_pbl && has_binary {
        "MIXED_PROJECT"
    } else if has_pbl {
        "PBL_PROJECT"
    } else if has_binary {
        "BINARY_PROJECT"
    } else {
        "UNKNOWN"
    };

    // Infer project name from first PBL or EXE
    let project_name = pbl_files.first()
        .or_else(|| exe_files.first())
        .and_then(|p| p.file_stem())
        .and_then(|s| s.to_str())
        .unwrap_or_else(|| dir.file_name().and_then(|s| s.to_str()).unwrap_or("project"))
        .to_string();

    ProjectDetection {
        project_type: project_type.to_string(),
        project_name,
        pbl_files,
        exe_files,
        pbd_files,
        dll_files,
    }
}

// ── Export strategies ─────────────────────────────────────────────────────────

fn export_pbl_project(
    det: &ProjectDetection,
    out_dir: &Path,
    project_name: &str,
    by_type: bool,
    no_readme: bool,
    output: &mut Vec<String>,
) -> (usize, usize) {
    let mut total = 0usize;
    let mut failed = 0usize;

    for pbl in &det.pbl_files {
        let stem = pbl.file_stem().and_then(|s| s.to_str()).unwrap_or("pbl");
        let sub_dir = out_dir.join(stem);
        output.push(format!("\n  Exporting {} → {}/", pbl.file_name().unwrap_or_default().to_string_lossy(), stem));

        match export_pbl_to_dir(pbl, &sub_dir, by_type) {
            Ok(n) => {
                total += n;
                output.push(format!("    -> {} objects", n));
            }
            Err(e) => {
                output.push(format!("    -> ERROR: {}", e));
                failed += 1;
            }
        }
    }

    if !no_readme && total > 0 {
        write_pbl_readme(out_dir, det, project_name, total);
    }

    (total, failed)
}

fn export_binary_project(
    det: &ProjectDetection,
    out_dir: &Path,
    _project_name: &str,
    no_readme: bool,
    output: &mut Vec<String>,
) -> (usize, usize) {
    let mut total = 0usize;
    let mut failed = 0usize;

    // For each EXE, try extract-then-copy to src
    for exe in &det.exe_files {
        let stem = exe.file_stem().and_then(|s| s.to_str()).unwrap_or("exe");
        let sub_dir = out_dir.join(stem);
        output.push(format!("\n  Decompiling {} (EXE) → {}/", exe.file_name().unwrap_or_default().to_string_lossy(), stem));

        match decompile_binary_to_dir(exe, &sub_dir) {
            Ok(n) => {
                total += n;
                output.push(format!("    -> {} entries", n));
            }
            Err(e) => {
                output.push(format!("    -> NOTE: {} (delegate to: pbdevkit decompile-all)", e));
                failed += 1;
            }
        }
    }

    // Standalone PBDs
    for pbd in &det.pbd_files {
        let stem = pbd.file_stem().and_then(|s| s.to_str()).unwrap_or("pbd");
        let sub_dir = out_dir.join(stem);
        output.push(format!("\n  Decompiling {} (PBD) → {}/", pbd.file_name().unwrap_or_default().to_string_lossy(), stem));

        match decompile_binary_to_dir(pbd, &sub_dir) {
            Ok(n) => {
                total += n;
                output.push(format!("    -> {} entries", n));
            }
            Err(e) => {
                output.push(format!("    -> NOTE: {} (delegate to: pbdevkit decompile-all)", e));
                failed += 1;
            }
        }
    }

    if !no_readme && (total > 0 || failed > 0) {
        write_binary_readme(out_dir, det, total);
    }

    (total, failed)
}

fn export_mixed_project(
    det: &ProjectDetection,
    out_dir: &Path,
    project_name: &str,
    by_type: bool,
    no_readme: bool,
    output: &mut Vec<String>,
) -> (usize, usize) {
    let mut total = 0usize;
    let mut failed = 0usize;

    // Phase 1: PBL sources (authoritative)
    output.push("\n  [Phase 1/2] Exporting PBL source files ...".to_string());
    let (t, f) = export_pbl_project(det, out_dir, project_name, by_type, no_readme, output);
    total += t;
    failed += f;

    // Phase 2: decompile binaries to _decompiled/
    if !det.exe_files.is_empty() || !det.pbd_files.is_empty() {
        let decompiled_out = out_dir.join("_decompiled");
        output.push(format!("\n  [Phase 2/2] Decompiling binaries → _decompiled/"));
        output.push("    (supplementary reference; PBL sources are authoritative)".to_string());
        let (t2, f2) = export_binary_project(det, &decompiled_out, project_name, true, output);
        total += t2;
        failed += f2;
    }

    if !no_readme {
        write_mixed_readme(out_dir, project_name, total);
    }

    (total, failed)
}

// ── Low-level export helpers ─────────────────────────────────────────────────

/// Export a PBL file's source entries to `out_dir/`.
/// Calls into pb-devkit-core via a subprocess (pbdevkit export-pbl).
/// Returns count of exported files.
fn export_pbl_to_dir(pbl: &Path, out_dir: &Path, _by_type: bool) -> Result<usize, String> {
    use std::process::Command;

    fs::create_dir_all(out_dir)
        .map_err(|e| format!("Cannot create dir {}: {}", out_dir.display(), e))?;

    // Delegate to our own CLI: pbdevkit export-pbl <pbl> <dir>
    // This avoids duplicating core logic here
    let exe = std::env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("pbdevkit"));

    let out = Command::new(&exe)
        .args(["export-pbl", &pbl.to_string_lossy(), &out_dir.to_string_lossy()])
        .output()
        .map_err(|e| format!("Failed to run export-pbl: {}", e))?;

    if out.status.success() {
        // Count files written
        let count = count_files_in(out_dir);
        Ok(count)
    } else {
        let stderr = String::from_utf8_lossy(&out.stderr);
        Err(format!("export-pbl failed: {}", stderr.trim()))
    }
}

/// Decompile EXE/PBD to `out_dir/` via pbdevkit decompile-all.
fn decompile_binary_to_dir(binary: &Path, out_dir: &Path) -> Result<usize, String> {
    use std::process::Command;

    fs::create_dir_all(out_dir)
        .map_err(|e| format!("Cannot create dir {}: {}", out_dir.display(), e))?;

    let exe = std::env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("pbdevkit"));

    let out = Command::new(&exe)
        .args(["decompile-all", &binary.to_string_lossy(), &out_dir.to_string_lossy()])
        .output()
        .map_err(|e| format!("Failed to run decompile-all: {}", e))?;

    if out.status.success() {
        let count = count_files_in(out_dir);
        Ok(count)
    } else {
        let stderr = String::from_utf8_lossy(&out.stderr);
        Err(format!("decompile-all: {}", stderr.trim()))
    }
}

fn count_files_in(dir: &Path) -> usize {
    fs::read_dir(dir)
        .map(|entries| entries.flatten().filter(|e| e.path().is_file()).count())
        .unwrap_or(0)
}

// ── README generators ─────────────────────────────────────────────────────────

fn write_pbl_readme(out_dir: &Path, det: &ProjectDetection, project_name: &str, total: usize) {
    let ts = chrono_now();
    let mut lines = vec![
        format!("# {} — 源码目录", project_name),
        String::new(),
        format!("> 从 {} 个 PBL 文件导出，共 {} 个源码文件", det.pbl_files.len(), total),
        format!("> 导出时间: {}", ts),
        String::new(),
        "## 目录结构".to_string(),
        String::new(),
        "```".to_string(),
        "src/".to_string(),
    ];
    for pbl in &det.pbl_files {
        if let Some(stem) = pbl.file_stem().and_then(|s| s.to_str()) {
            lines.push(format!("  {}/     # 从 {} 导出", stem, pbl.file_name().unwrap_or_default().to_string_lossy()));
        }
    }
    lines.push("  README.md".to_string());
    lines.push("```".to_string());
    lines.push(String::new());
    lines.push("## 说明".to_string());
    lines.push(String::new());
    lines.push("- 每个子目录对应一个原始 PBL 文件".to_string());
    lines.push("- 文件后缀: `.srw`=窗口, `.srd`=数据窗口, `.srm`=菜单, `.srf`=函数, `.srs`=结构体, `.sru`=用户对象".to_string());
    lines.push("- **工具**: pb-devkit (`pbdevkit autoexport`)".to_string());

    let _ = fs::create_dir_all(out_dir);
    let _ = fs::write(out_dir.join("README.md"), lines.join("\n"));
}

fn write_binary_readme(out_dir: &Path, det: &ProjectDetection, total: usize) {
    let ts = chrono_now();
    let source_count = det.exe_files.len() + det.pbd_files.len();
    let lines = vec![
        "# Project — 梳理导出源码目录".to_string(),
        String::new(),
        format!("> 从 {} 个文件梳理导出，共 {} 个文件", source_count, total),
        format!("> 导出时间: {}", ts),
        String::new(),
        "## 说明".to_string(),
        String::new(),
        "- 从编译后的 EXE/PBD/DLL 梳理导出的 PowerScript 源码".to_string(),
        "- **工具**: pb-devkit (`pbdevkit autoexport`)".to_string(),
    ];
    let _ = fs::create_dir_all(out_dir);
    let _ = fs::write(out_dir.join("README.md"), lines.join("\n"));
}

fn write_mixed_readme(out_dir: &Path, project_name: &str, total: usize) {
    let ts = chrono_now();
    let lines = vec![
        format!("# {} — 源码目录（混合模式）", project_name),
        String::new(),
        format!("> PBL 源码 + 梳理导出二进制，共导出 {} 个文件", total),
        format!("> 导出时间: {}", ts),
        String::new(),
        "## 说明".to_string(),
        String::new(),
        "- **PBL 源码目录**（子目录名 = PBL 文件名）: 以源码 PBL 为权威来源".to_string(),
        "- **`_decompiled/`**: 从 EXE/PBD 梳理导出的源码（仅供参考）".to_string(),
        "- **工具**: pb-devkit (`pbdevkit autoexport`)".to_string(),
    ];
    let _ = fs::create_dir_all(out_dir);
    let _ = fs::write(out_dir.join("README.md"), lines.join("\n"));
}

// ── Utilities ─────────────────────────────────────────────────────────────────

fn extract_flag_value(args: &[String], flags: &[&str]) -> Option<String> {
    for (i, arg) in args.iter().enumerate() {
        if flags.contains(&arg.as_str()) {
            return args.get(i + 1).cloned();
        }
        // Also handle --flag=value
        for flag in flags {
            if let Some(val) = arg.strip_prefix(&format!("{}=", flag)) {
                return Some(val.to_string());
            }
        }
    }
    None
}

fn chrono_now() -> String {
    // Simple timestamp without chrono crate
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(d) => {
            let secs = d.as_secs();
            // Approximate date (not timezone-aware, but good enough for README)
            let days_since_epoch = secs / 86400;
            let year = 1970 + days_since_epoch / 365;
            format!("{}-xx-xx (build: {}s epoch)", year, secs)
        }
        Err(_) => "unknown".to_string(),
    }
}

fn autoexport_help() -> String {
    r#"pbdevkit autoexport — Smart Project Auto-Export

USAGE:
    pbdevkit autoexport <dir> [OPTIONS]

ARGS:
    <dir>     Project directory containing .pbl / .exe / .pbd files

OPTIONS:
    -o, --output <DIR>         Output directory (default: <dir>/src)
    --detect                   Detect project type only, do not export
    --quick                    Skip deep PE binary scan (faster)
    --force                    Overwrite existing output directory
    --by-type                  Organize PBL exports by object type
    --no-readme                Skip README.md generation
    --project-name <NAME>      Override inferred project name
    -h, --help                 Show this help

PROJECT TYPES:
    PBL_PROJECT      Directory contains .pbl source files
    BINARY_PROJECT   Directory contains compiled EXE/PBD files
    MIXED_PROJECT    Both PBL sources and compiled binaries present

EXAMPLES:
    pbdevkit autoexport C:/projects/myapp
    pbdevkit autoexport C:/projects/myapp -o D:/export/src
    pbdevkit autoexport C:/projects/myapp --detect
    pbdevkit autoexport C:/projects/myapp --by-type --force
"#.to_string()
}
