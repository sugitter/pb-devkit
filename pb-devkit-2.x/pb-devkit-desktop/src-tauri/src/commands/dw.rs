// DataWindow analysis commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::DwAnalysisResult;

/// Analyze DataWindow objects
#[tauri::command]
pub fn analyze_datawindows(root_path: String) -> Result<DwAnalysisResult, String> {
    core::dw::analyze_datawindows(&root_path)
}

/// Get DataWindow SQL details
#[tauri::command]
pub fn get_dw_sql(dw_path: String) -> Result<String, String> {
    core::dw::get_dw_sql(&dw_path)
}
