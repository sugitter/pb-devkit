// Scan and Migrate commands for Tauri

use pb_devkit_core::project::{self, ScanResult, MigrateResult};
use pb_devkit_core::types::{ProjectInfo, PblFileInfo};

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