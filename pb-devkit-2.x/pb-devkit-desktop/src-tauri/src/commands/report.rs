// Report generation commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::ProjectReport;

/// Generate comprehensive project report
#[tauri::command]
pub fn generate_report(project_path: String) -> Result<ProjectReport, String> {
    core::report::generate_report(&project_path)
}

/// Export report to JSON file
#[tauri::command]
pub fn export_report(project_path: String, output_path: String) -> Result<String, String> {
    core::report::export_report(&project_path, &output_path)
}
