// Decompile commands - Thin Tauri wrappers over pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::{DecompileListResult, DecompileResult};

/// List all entries in a PBD/EXE file
#[tauri::command]
pub fn list_decompile_entries(path: String) -> DecompileListResult {
    core::decompile::list_decompile_entries(&path)
}

/// Decompile a single entry
#[tauri::command]
pub fn decompile_entry(pbd_path: String, entry_name: String) -> DecompileResult {
    core::decompile::decompile_entry(&pbd_path, &entry_name)
}

/// Decompile all entries from PBD/EXE
#[tauri::command]
pub fn decompile_all(pbd_path: String, output_dir: String) -> Result<String, String> {
    core::decompile::decompile_all(&pbd_path, &output_dir)
}
