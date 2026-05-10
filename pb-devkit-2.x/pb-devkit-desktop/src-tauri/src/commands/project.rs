// Project detection commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::{ProjectInfo, PblFileInfo, DoctorResult};

/// Detect PowerBuilder project structure
#[tauri::command]
pub fn detect_project(path: String) -> Result<ProjectInfo, String> {
    core::project::detect_project(&path)
}

/// Run environment diagnostics
#[tauri::command]
pub fn run_doctor() -> DoctorResult {
    core::project::run_doctor()
}

/// List all PBL files in a directory recursively
#[tauri::command]
pub fn find_pbl_files(root_path: String) -> Result<Vec<PblFileInfo>, String> {
    core::project::find_pbl_files(&root_path)
}
