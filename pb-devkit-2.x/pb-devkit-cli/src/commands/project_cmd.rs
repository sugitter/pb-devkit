// Project commands for CLI - delegates to pb-devkit-core

use pb_devkit_core::project;
use pb_devkit_core::types::{ProjectInfo, PblFileInfo};

pub fn detect_project(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit project <path>".to_string());
    }
    let info: ProjectInfo = project::detect_project(&args[0])?;

    let status = if info.is_valid {
        "✓ Valid PowerBuilder Project"
    } else {
        "⚠ No PBL/PBT/EXE files found"
    };

    Ok(format!(
        "Project: {}\nPath: {}\n{}\n\nFiles:\n  PBL: {}\n  PBT: {}\n  PBW: {}\n  EXE/PBD: {}",
        info.name,
        info.path,
        status,
        info.pbl_files.len(),
        info.pbt_files.len(),
        info.pbw_files.len(),
        info.exe_files.len()
    ))
}

pub fn find_pbl_files(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit find-pbl <path>".to_string());
    }
    let files: Vec<PblFileInfo> = project::find_pbl_files(&args[0])?;

    if files.is_empty() {
        return Ok(format!("No PBL files found in {}", &args[0]));
    }

    let mut output = format!("PBL files in {}:\n", &args[0]);
    output.push_str(&format!("{:<50} {:>10}\n", "Name", "Size (KB)"));
    output.push_str(&"-".repeat(65));
    output.push('\n');

    for f in files.iter().take(50) {
        output.push_str(&format!(
            "{:<50} {:>10}\n",
            f.name[..f.name.len().min(48)].to_string(),
            f.size / 1024
        ));
    }

    if files.len() > 50 {
        output.push_str(&format!("\n... and {} more files", files.len() - 50));
    }

    Ok(output)
}

pub fn run_doctor() -> Result<String, String> {
    let result = project::run_doctor();

    let mut output = "Environment Diagnostics:\n".to_string();
    output.push_str(&format!("  Python: {}\n", result.python_version.as_deref().unwrap_or("not found")));
    output.push_str(&format!("  Rust: {}\n", if result.rust_available { "found" } else { "not found" }));
    output.push_str(&format!("  ORCA DLL: {}\n", if result.orca_dll_found { "found" } else { "not found" }));

    if !result.warnings.is_empty() {
        output.push_str("\nWarnings:\n");
        for w in &result.warnings {
            output.push_str(&format!("  ⚠ {}\n", w));
        }
    }

    Ok(output)
}
