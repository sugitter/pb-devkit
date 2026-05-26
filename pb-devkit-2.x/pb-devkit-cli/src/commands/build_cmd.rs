/// pb-devkit CLI — `build` command
///
/// Rebuild a PowerBuilder application via the PBGen CLI tool.
///
/// Three compilation modes:
///   exe       — Single EXE (all code embedded, no external PBDs)
///   exe+pbd   — EXE + separate PBD files (runtime-loadable components)
///   exe+dll   — EXE + DLL files (PowerBuilder DLL libraries)
///
/// NOTE: Requires PowerBuilder IDE installed (PBGen.exe).
///
/// Usage:
///   pbdevkit build <pbl> <app_name>
///   pbdevkit build <pbl> <app_name> --mode exe+pbd
///   pbdevkit build <pbl> <app_name> --mode exe+dll --dll-libs lib1.pbl,lib2.pbl

use std::path::{Path, PathBuf};
use std::process::Command;

// ── Public entry point ────────────────────────────────────────────────────────

pub fn run_build(args: &[String]) -> Result<String, String> {
    if args.is_empty() || args[0] == "--help" || args[0] == "-h" {
        return Ok(build_help());
    }

    if args.len() < 2 {
        return Err("Usage: pbdevkit build <pbl> <app_name> [--mode exe|exe+pbd|exe+dll] [OPTIONS]\nRun 'pbdevkit build --help' for details.".to_string());
    }

    let pbl_path = PathBuf::from(&args[0]).canonicalize()
        .map_err(|_| format!("PBL not found: {}", args[0]))?;
    let app_name = &args[1];

    // Parse flags
    let mode = extract_flag_value(args, &["--mode"]).unwrap_or_else(|| "exe".to_string());
    let output_dir = extract_flag_value(args, &["-d", "--output-dir"])
        .map(PathBuf::from)
        .unwrap_or_else(|| pbl_path.parent().unwrap_or(Path::new(".")).to_path_buf());
    let exe_out = extract_flag_value(args, &["--exe"])
        .map(PathBuf::from)
        .unwrap_or_else(|| output_dir.join(format!("{}.exe", app_name)));
    let lib_list = extract_flag_value(args, &["--lib-list"]);
    let pbd_libs = extract_flag_value(args, &["--pbd-libs"]);
    let dll_libs = extract_flag_value(args, &["--dll-libs"]);
    let icon = extract_flag_value(args, &["--icon"]);
    let pbr = extract_flag_value(args, &["--pbr"]);
    let machine_code = args.contains(&"--machine-code".to_string());
    let rebuild_only = args.contains(&"--rebuild-only".to_string());
    let explicit_pbgen = extract_flag_value(args, &["--pbgen"]);

    // Locate PBGen.exe
    let pbgen = find_pbgen(explicit_pbgen.as_deref())
        .ok_or_else(|| format!(
            "PowerBuilder PBGen.exe not found.\n\
            Install PowerBuilder, then either:\n\
            1. Add PBGen.exe to your PATH, or\n\
            2. Use --pbgen <path_to_PBGen.exe>\n\n\
            Typical location:\n  C:\\Program Files\\Appeon\\PowerBuilder xx.x\\PBGen.exe\n\n\
            For EXE analysis (no IDE needed), use:\n\
              pbdevkit export-pbl <your.pbl> ./src\n\
              pbdevkit migrate <your.pbl> -o ./web-output"
        ))?;

    // Build library list
    let lib_paths = parse_lib_list(lib_list.as_deref(), &pbl_path);
    let lib_list_str = lib_paths.iter()
        .map(|p| p.to_string_lossy().to_string())
        .collect::<Vec<_>>()
        .join(";");

    // Build PBD flags
    let pbd_flags = compute_pbd_flags(&mode, &lib_paths, pbd_libs.as_deref(), dll_libs.as_deref());

    // Assemble PBGen command
    let mut cmd_args = vec![
        "-l".to_string(), lib_list_str,
        "-a".to_string(), app_name.to_string(),
    ];
    if !rebuild_only {
        cmd_args.push("-e".to_string());
        cmd_args.push(exe_out.to_string_lossy().to_string());
    }
    if let Some(icon_path) = &icon {
        cmd_args.push("-i".to_string());
        cmd_args.push(icon_path.clone());
    }
    if let Some(pbr_path) = &pbr {
        cmd_args.push("-r".to_string());
        cmd_args.push(pbr_path.clone());
    }
    if machine_code {
        cmd_args.push("-m".to_string());
    }
    if !pbd_flags.is_empty() && mode != "exe" {
        cmd_args.push("-p".to_string());
        cmd_args.push(pbd_flags);
    }

    let mut output = Vec::new();
    output.push(format!("{}", "=".repeat(60)));
    output.push("  pb build — PowerBuilder Compiler".to_string());
    output.push(format!("{}", "=".repeat(60)));
    output.push(format!("  PBL:      {}", pbl_path.display()));
    output.push(format!("  App:      {}", app_name));
    output.push(format!("  Mode:     {}", mode));
    output.push(format!("  Output:   {}", output_dir.display()));
    if !rebuild_only {
        output.push(format!("  EXE:      {}", exe_out.file_name().unwrap_or_default().to_string_lossy()));
    }
    output.push(format!("  PBGen:    {}", pbgen.display()));
    output.push(String::new());
    output.push(format!("  Command: {} {}", pbgen.display(), cmd_args.join(" ")));
    output.push(String::new());

    // Execute PBGen
    let result = Command::new(&pbgen)
        .args(&cmd_args)
        .output()
        .map_err(|e| format!("Cannot execute PBGen: {}", e))?;

    let stdout = String::from_utf8_lossy(&result.stdout).to_string();
    let stderr = String::from_utf8_lossy(&result.stderr).to_string();

    if !stdout.is_empty() { output.push(stdout); }
    if !stderr.is_empty() { output.push(stderr); }

    if !result.status.success() {
        let code = result.status.code().unwrap_or(-1);
        return Err(format!(
            "{}\n[error] PBGen exited with code {}",
            output.join("\n"), code
        ));
    }

    if !rebuild_only && exe_out.exists() {
        let size = exe_out.metadata().map(|m| m.len() / 1024).unwrap_or(0);
        output.push(format!("  ✓ EXE created: {} ({} KB)", exe_out.display(), size));
    }

    output.push(String::new());
    output.push(format!("{}", "=".repeat(60)));
    output.push(format!("  Build complete — mode: {}", mode));
    output.push(format!("{}", "=".repeat(60)));

    Ok(output.join("\n"))
}

// ── Helpers ────────────────────────────────────────────────────────────────────

fn find_pbgen(explicit: Option<&str>) -> Option<PathBuf> {
    if let Some(path) = explicit {
        let p = PathBuf::from(path);
        if p.exists() { return Some(p); }
        return None;
    }

    // Check PATH
    if let Ok(output) = Command::new("where").arg("PBGen.exe").output() {
        if output.status.success() {
            let line = String::from_utf8_lossy(&output.stdout);
            let first = line.lines().next().unwrap_or("").trim();
            if !first.is_empty() {
                return Some(PathBuf::from(first));
            }
        }
    }
    // Also try 'which' on Unix-like (cross-platform safety)
    if let Ok(output) = Command::new("which").arg("PBGen").output() {
        if output.status.success() {
            let line = String::from_utf8_lossy(&output.stdout);
            let first = line.lines().next().unwrap_or("").trim();
            if !first.is_empty() { return Some(PathBuf::from(first)); }
        }
    }

    // Common install locations (Windows)
    for base in &[
        r"C:\Program Files\Appeon",
        r"C:\Program Files (x86)\Appeon",
        r"C:\Program Files\Sybase",
        r"C:\Program Files (x86)\Sybase",
    ] {
        let base_p = PathBuf::from(base);
        if base_p.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&base_p) {
                for entry in entries.flatten() {
                    let candidate = entry.path().join("PBGen.exe");
                    if candidate.exists() { return Some(candidate); }
                }
            }
        }
    }

    None
}

fn parse_lib_list(lib_list: Option<&str>, main_pbl: &Path) -> Vec<PathBuf> {
    match lib_list {
        None => vec![main_pbl.to_path_buf()],
        Some(s) => {
            let mut libs = Vec::new();
            for part in s.split(';') {
                let part = part.trim();
                if part.is_empty() { continue; }
                let p = PathBuf::from(part);
                let resolved = if p.is_absolute() { p } else {
                    main_pbl.parent().unwrap_or(Path::new(".")).join(p)
                };
                if let Ok(c) = resolved.canonicalize() {
                    libs.push(c);
                } else {
                    libs.push(resolved);
                }
            }
            if libs.is_empty() { vec![main_pbl.to_path_buf()] } else { libs }
        }
    }
}

fn compute_pbd_flags(mode: &str, lib_list: &[PathBuf], pbd_libs: Option<&str>, dll_libs: Option<&str>) -> String {
    match mode {
        "exe" => "n".repeat(lib_list.len()),
        "exe+pbd" => {
            let pbd_names: std::collections::HashSet<String> = pbd_libs
                .map(|s| s.split(',')
                    .map(|p| p.trim().to_lowercase()
                        .trim_end_matches(".pbl").to_string())
                    .collect())
                .unwrap_or_default();

            lib_list.iter().enumerate().map(|(i, lib)| {
                let stem = lib.file_stem().and_then(|s| s.to_str())
                    .unwrap_or("").to_lowercase();
                if i == 0 { 'n' }
                else if !pbd_names.is_empty() && pbd_names.contains(&stem) { 'y' }
                else if pbd_names.is_empty() { 'y' }
                else { 'n' }
            }).collect()
        }
        "exe+dll" => {
            let dll_names: std::collections::HashSet<String> = dll_libs
                .map(|s| s.split(',')
                    .map(|p| p.trim().to_lowercase()
                        .trim_end_matches(".pbl").to_string())
                    .collect())
                .unwrap_or_default();

            lib_list.iter().enumerate().map(|(i, lib)| {
                let stem = lib.file_stem().and_then(|s| s.to_str())
                    .unwrap_or("").to_lowercase();
                if i == 0 { 'n' }
                else if !dll_names.is_empty() && dll_names.contains(&stem) { 'd' }
                else if dll_names.is_empty() { 'd' }
                else { 'n' }
            }).collect()
        }
        _ => "n".repeat(lib_list.len()),
    }
}

fn extract_flag_value(args: &[String], flags: &[&str]) -> Option<String> {
    for (i, arg) in args.iter().enumerate() {
        if flags.contains(&arg.as_str()) {
            return args.get(i + 1).cloned();
        }
        for flag in flags {
            if let Some(val) = arg.strip_prefix(&format!("{}=", flag)) {
                return Some(val.to_string());
            }
        }
    }
    None
}

fn build_help() -> String {
    r#"pbdevkit build — Rebuild a PowerBuilder Application

USAGE:
    pbdevkit build <pbl> <app_name> [OPTIONS]

ARGS:
    <pbl>         Application PBL file path
    <app_name>    Application object name (e.g. myapp)

OPTIONS:
    --mode <MODE>              Compilation mode: exe | exe+pbd | exe+dll (default: exe)
    --exe <PATH>               Output EXE path (default: <app_name>.exe)
    -d, --output-dir <DIR>     Output directory for EXE + PBD/DLL
    --lib-list <PBL1;PBL2>    Semicolon-separated library list (all project PBLs)
    --pbd-libs <PBL1,PBL2>    Comma-separated PBLs to compile as PBD (exe+pbd mode)
    --dll-libs <PBL1,PBL2>    Comma-separated PBLs to compile as DLL (exe+dll mode)
    --icon <FILE>              Icon file (.ico) for the EXE
    --pbr <FILE>               PBR resource file path
    --machine-code             Compile to native machine code (default: Pcode)
    --rebuild-only             Rebuild PBL only, don't create EXE
    --pbgen <PATH>             Path to PBGen.exe (auto-detected if not set)
    -h, --help                 Show this help

NOTES:
    Requires PowerBuilder IDE installed (PBGen.exe).
    For source analysis without IDE, use:
      pbdevkit export-pbl <your.pbl> ./src
      pbdevkit migrate <your.pbl> -o ./web-output

EXAMPLES:
    pbdevkit build myapp.pbl myapp
    pbdevkit build myapp.pbl myapp --mode exe+pbd --pbd-libs lib1,lib2
    pbdevkit build myapp.pbl myapp --machine-code -d C:/dist
    pbdevkit build myapp.pbl myapp --pbgen "C:/Program Files/Appeon/PB22/PBGen.exe"
"#.to_string()
}
