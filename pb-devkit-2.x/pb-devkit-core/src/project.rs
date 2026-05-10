// Project detection and initialization - Shared core logic

use std::path::Path;

use crate::types::{ProjectInfo, PblFileInfo, DoctorResult};

/// Detect PowerBuilder project structure
pub fn detect_project(path: &str) -> Result<ProjectInfo, String> {
    let project_path = Path::new(path);

    if !project_path.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut pbl_files = Vec::new();
    let mut pbt_files = Vec::new();
    let mut pbw_files = Vec::new();
    let mut exe_files = Vec::new();

    if let Ok(entries) = std::fs::read_dir(project_path) {
        for entry in entries.flatten() {
            let file_path = entry.path();
            let file_name = file_path.file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("");
            let lower = file_name.to_lowercase();

            if lower.ends_with(".pbl") {
                let size = file_path.metadata().map(|m| m.len()).unwrap_or(0);
                pbl_files.push(PblFileInfo {
                    path: file_path.to_string_lossy().to_string(),
                    name: file_name.to_string(),
                    size,
                    entry_count: None,
                    is_unicode: false,
                });
            } else if lower.ends_with(".pbt") {
                pbt_files.push(file_path.to_string_lossy().to_string());
            } else if lower.ends_with(".pbw") {
                pbw_files.push(file_path.to_string_lossy().to_string());
            } else if lower.ends_with(".exe") || lower.ends_with(".pbd") {
                exe_files.push(file_path.to_string_lossy().to_string());
            }
        }
    }

    let project_name = project_path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("Unknown")
        .to_string();

    let is_valid = !pbl_files.is_empty() || !pbt_files.is_empty() || !exe_files.is_empty();

    Ok(ProjectInfo {
        name: project_name,
        path: path.to_string(),
        pbl_files,
        pbt_files,
        pbw_files,
        exe_files,
        is_valid,
    })
}

/// Run environment diagnostics
pub fn run_doctor() -> DoctorResult {
    let issues = Vec::new();
    let mut warnings = Vec::new();

    let python_version = std::process::Command::new("python")
        .arg("--version")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());

    let rust_available = std::process::Command::new("rustc")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    let orca_dll_paths = [
        "pb-devkit-1.x/PBSpyORCA.dll",
        "orca/PBSpyORCA.dll",
    ];
    let orca_dll_found = orca_dll_paths.iter()
        .any(|p| Path::new(p).exists());

    if !rust_available {
        warnings.push("Rust not found - some features may be limited".to_string());
    }

    if !orca_dll_found {
        warnings.push("PBSpyORCA.dll not found - import/build features disabled".to_string());
    }

    DoctorResult {
        success: true,
        python_version,
        rust_available,
        orca_dll_found,
        issues,
        warnings,
    }
}

/// List all PBL files in a directory recursively
pub fn find_pbl_files(root_path: &str) -> Result<Vec<PblFileInfo>, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut pbl_files = Vec::new();
    collect_pbl_files(root, &mut pbl_files);

    Ok(pbl_files)
}

fn collect_pbl_files(dir: &Path, files: &mut Vec<PblFileInfo>) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                if !path.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.starts_with('.'))
                    .unwrap_or(false)
                {
                    collect_pbl_files(&path, files);
                }
            } else if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                if name.to_lowercase().ends_with(".pbl") {
                    let size = path.metadata().map(|m| m.len()).unwrap_or(0);
                    files.push(PblFileInfo {
                        path: path.to_string_lossy().to_string(),
                        name: name.to_string(),
                        size,
                        entry_count: None,
                        is_unicode: false,
                    });
                }
            }
        }
    }
}
