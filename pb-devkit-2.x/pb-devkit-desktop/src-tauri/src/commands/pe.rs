// PE file parsing commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::{PeInfoResult, FileTypeResult, ExtractResult};

/// Detect file type from magic bytes
#[tauri::command]
pub fn detect_file_type(path: String) -> Result<FileTypeResult, String> {
    core::pe::PeParser::detect_file_type(&path).map_err(|e| e.to_string())
}

/// Analyze PE file
#[tauri::command]
pub fn analyze_pe(path: String) -> Result<PeInfoResult, String> {
    let parser = core::pe::PeParser::new(&path).map_err(|e| e.to_string())?;
    Ok(parser.get_info_result())
}

/// Extract PBD resources from EXE/DLL
#[tauri::command]
pub fn extract_pbd_from_exe(exe_path: String, output_dir: String) -> ExtractResult {
    match core::pe::PeParser::new(&exe_path) {
        Ok(parser) => match parser.extract_resources(&output_dir) {
            Ok(result) => result,
            Err(e) => ExtractResult {
                success: false,
                pbd_count: 0,
                output_path: None,
                error: Some(e.to_string()),
            },
        },
        Err(e) => ExtractResult {
            success: false,
            pbd_count: 0,
            output_path: None,
            error: Some(e.to_string()),
        },
    }
}
