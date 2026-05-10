// Report commands for CLI - delegates to pb-devkit-core

use pb_devkit_core::report;

pub fn generate_report(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit report <project_path>".to_string());
    }
    let project_path = &args[0];
    let report = report::generate_report(project_path)?;

    let mut output = format!(
        "Project Report: {}\n  Path: {}\n\nSummary:\n  Total PBL files: {}\n  Total PBD files: {}\n  Total EXE files: {}\n  Total objects: {}\n  Source objects: {}\n  Compiled objects: {}\n  Unicode PBLs: {}\n  ANSI PBLs: {}\n  Total size: {} KB\n\nTop Object Types:\n",
        report.project_name,
        report.project_path,
        report.summary.total_pbl_files,
        report.summary.total_pbd_files,
        report.summary.total_exe_files,
        report.summary.total_objects,
        report.summary.source_objects,
        report.summary.compiled_objects,
        report.summary.unicode_pbls,
        report.summary.ansi_pbls,
        report.file_stats.total_size_bytes / 1024
    );

    for (t, c) in &report.object_stats.top_types {
        output.push_str(&format!("  - {}: {}\n", t, c));
    }

    output.push_str("\nPBL Files:\n");
    for pbl in report.pbl_files.iter().take(50) {
        output.push_str(&format!(
            "  - {}: {} entries ({} source, {} compiled)\n",
            pbl.name, pbl.total_entries, pbl.source_entries, pbl.compiled_entries
        ));
    }
    if report.pbl_files.len() > 50 {
        output.push_str(&format!("... and {} more\n", report.pbl_files.len() - 50));
    }

    Ok(output)
}

pub fn export_report(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit export-report <project_path> <output.json>".to_string());
    }
    report::export_report(&args[0], &args[1])
}
