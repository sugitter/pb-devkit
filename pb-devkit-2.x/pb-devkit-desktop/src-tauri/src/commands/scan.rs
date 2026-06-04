// Scan and Migrate commands for Tauri

use pb_devkit_core::project::{self, ScanResult, MigrateResult, PackResult};
use pb_devkit_core::types::{ProjectInfo, PblFileInfo};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Scan and export entire PB project with directory structure
#[tauri::command]
pub fn scan_project(project_path: String, output_dir: String) -> Result<ScanResult, String> {
    project::scan_and_export(&project_path, &output_dir)
        .map_err(|e| e.to_string())
}

/// Migrate PB project to modern web structure
#[tauri::command]
pub fn migrate_project(project_path: String, output_dir: String, template: String) -> Result<MigrateResult, String> {
    project::migrate_to_web(&project_path, &output_dir, &template)
        .map_err(|e| e.to_string())
}

/// Pack source files back into a real PBL using the 1.x Python engine.
/// Falls back to manifest-only packing if Python/pb-devkit is unavailable.
#[tauri::command]
pub fn pack_to_pbl(src_dir: String, output_dir: String) -> Result<PackResult, String> {
    // ── Step 1: Try 1.x Python engine ────────────────────────────────────
    match try_python_pack(&src_dir, &output_dir) {
        Ok(result) => return Ok(result),
        Err(py_err) => {
            eprintln!("[pack_to_pbl] Python engine unavailable: {}", py_err);
        }
    }

    // ── Step 2: Fall back to Rust manifest generation ────────────────────
    project::pack_sources_to_pbl(&src_dir, &output_dir)
        .map_err(|e| e.to_string())
}

/// Attempt to pack using the 1.x Python pb-devkit engine.
fn try_python_pack(src_dir: &str, output_dir: &str) -> Result<PackResult, String> {
    let pb_py = find_pb_py()?;
    let python = find_python()?;
    let output_pbl = Path::new(output_dir).join("output.pbl");

    // Ensure output directory exists
    if let Some(parent) = output_pbl.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("Cannot create output dir: {}", e))?;
    }

    let output = Command::new(python)
        .current_dir(pb_py.parent().unwrap_or(Path::new(".")))
        .arg(&pb_py)
        .arg("pack")
        .arg(src_dir)
        .arg("-o")
        .arg(output_pbl.to_str().unwrap_or("output.pbl"))
        .output()
        .map_err(|e| format!("Failed to run Python: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        return Err(format!("Python pack failed: {}", stderr));
    }

    // Parse stdout for "Packed N entries"
    let packed_count = parse_packed_count(&stdout);

    Ok(PackResult {
        success: true,
        packed_count,
        pbl_path: output_pbl.to_string_lossy().to_string(),
        message: format!("PBL created via 1.x Python engine: {} ({} entries)",
            output_pbl.display(), packed_count),
        errors: vec![],
        engine: "python".to_string(),
    })
}

/// Parse Python pack output for "Packed N entries"
fn parse_packed_count(stdout: &str) -> usize {
    for line in stdout.lines() {
        if let Some(pos) = line.find("Packed ") {
            let rest = &line[pos + 7..];
            if let Some(end) = rest.find(|c: char| !c.is_ascii_digit()) {
                if let Ok(n) = rest[..end].parse::<usize>() {
                    return n;
                }
            }
        }
    }
    0
}

/// Find the 1.x pb.py entry point.
fn find_pb_py() -> Result<PathBuf, String> {
    let candidates = [
        r"F:\workspace\X6\pb-devkit\pb-devkit-1.x\pb.py",
    ];

    for p in &candidates {
        let path = Path::new(p);
        if path.exists() {
            return Ok(path.to_path_buf());
        }
    }

    Err("pb-devkit 1.x Python engine not found. Install pb-devkit 1.x to enable binary PBL packing.".to_string())
}

/// Find Python 3 executable.
fn find_python() -> Result<PathBuf, String> {
    let candidates: &[&str] = &[
        r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe",
        "python3",
        "python",
    ];

    for p in candidates {
        let path = Path::new(p);
        // For bare command names, we can't check existence — just return them
        if path.is_absolute() && path.exists() {
            return Ok(path.to_path_buf());
        }
        if !path.is_absolute() {
            // Try running 'python --version' to verify
            if Command::new(p).arg("--version").output().is_ok() {
                return Ok(PathBuf::from(p));
            }
        }
    }

    Err("Python 3 not found on this system.".to_string())
}

/// Get project info
#[tauri::command]
pub fn get_project_info(path: String) -> Result<ProjectInfo, String> {
    project::detect_project(&path).map_err(|e| e.to_string())
}

/// Find all PBL files in project
#[tauri::command]
pub fn find_project_pbls(path: String) -> Result<Vec<PblFileInfo>, String> {
    project::find_pbl_files(&path).map_err(|e| e.to_string())
}