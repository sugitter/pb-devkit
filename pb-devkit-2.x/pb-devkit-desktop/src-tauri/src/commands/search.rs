// Search commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::SearchResults;

/// Search for text in source files
#[tauri::command]
pub fn search_in_files(
    root_path: String,
    query: String,
    case_sensitive: bool,
    file_types: Vec<String>,
) -> Result<SearchResults, String> {
    core::search::search_in_files(&root_path, &query, case_sensitive, &file_types)
}

/// Search by object type
#[tauri::command]
pub fn search_by_type(root_path: String, object_type: String) -> Result<Vec<String>, String> {
    core::search::search_by_type(&root_path, &object_type)
}
