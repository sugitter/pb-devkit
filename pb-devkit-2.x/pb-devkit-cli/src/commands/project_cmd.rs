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

pub fn scan_and_export(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit scan-export <project_path> <output_dir>".to_string());
    }
    let result = project::scan_and_export(&args[0], &args[1])?;
    let status = if result.success { "✓" } else { "✗" };
    let mut output = format!(
        "{} Scan & Export: {} PBLs, {} sources, {} entries, {} exported, {} failed\n",
        status, result.pbl_count, result.source_count,
        result.entry_count, result.exported_count, result.failed_count
    );
    output.push_str(&format!("Output: {}\n", result.output_dir));
    if !result.errors.is_empty() {
        output.push_str("\nErrors:\n");
        for e in &result.errors {
            output.push_str(&format!("  ✗ {}\n", e));
        }
    }
    Ok(output)
}

pub fn pack_sources_to_pbl(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit pack-to-pbl <source_dir> <output_pbl>".to_string());
    }
    let result = project::pack_sources_to_pbl(&args[0], &args[1])?;
    let status = if result.success { "✓" } else { "✗" };
    let mut output = format!(
        "{} Pack to PBL: {} entries packed (engine: {})\n",
        status, result.packed_count, result.engine
    );
    output.push_str(&format!("Output: {}\n", result.pbl_path));
    if !result.errors.is_empty() {
        output.push_str("\nErrors:\n");
        for e in &result.errors {
            output.push_str(&format!("  ✗ {}\n", e));
        }
    }
    Ok(output)
}
