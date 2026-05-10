// PB DevKit 2.0 - Desktop Application (Tauri)
// Thin command layer delegating to pb-devkit-core

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp_millis()
        .init();

    log::info!("Starting PB DevKit 2.0...");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|_app| {
            log::info!("Application setup complete");
            std::panic::set_hook(Box::new(|panic_info| {
                log::error!("Application panic: {}", panic_info);
            }));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // PBL commands
            commands::pbl::parse_pbl,
            commands::pbl::get_pbl_info,
            commands::pbl::list_entries,
            commands::pbl::export_entry,
            commands::pbl::export_pbl,
            // PE commands
            commands::pe::detect_file_type,
            commands::pe::analyze_pe,
            commands::pe::extract_pbd_from_exe,
            // Project commands
            commands::project::detect_project,
            commands::project::find_pbl_files,
            commands::project::run_doctor,
            // Search commands
            commands::search::search_in_files,
            commands::search::search_by_type,
            // DataWindow commands
            commands::dw::analyze_datawindows,
            commands::dw::get_dw_sql,
            // Decompile commands
            commands::decompile::list_decompile_entries,
            commands::decompile::decompile_entry,
            commands::decompile::decompile_all,
            // Report commands
            commands::report::generate_report,
            commands::report::export_report,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

mod commands;
