// DataWindow commands for CLI - delegates to pb-devkit-core

use pb_devkit_core as core;
use pb_devkit_core::types::DwAnalysisResult;

pub fn analyze_datawindows(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit analyze-dw <project_path>".to_string());
    }
    let result: DwAnalysisResult = core::dw::analyze_datawindows(&args[0])?;

    if result.datawindows.is_empty() {
        return Ok(format!("No DataWindow objects found in {}", &args[0]));
    }

    let mut output = format!(
        "DataWindow Analysis: {}\n  Found: {} DataWindows\n  Tables: {}\n\n",
        &args[0],
        result.total_count,
        result.tables_found.len()
    );

    for (i, dw) in result.datawindows.iter().take(30).enumerate() {
        output.push_str(&format!("{}. {} (tables: {})\n", i + 1, dw.name, dw.tables.len()));
        for t in &dw.tables {
            output.push_str(&format!("    - {}\n", t));
        }
    }

    if result.datawindows.len() > 30 {
        output.push_str(&format!("... and {} more\n", result.datawindows.len() - 30));
    }

    Ok(output)
}

pub fn get_dw_sql(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit dw-sql <dw_file_path>".to_string());
    }
    let sql = core::dw::get_dw_sql(&args[0])?;
    Ok(format!("SQL for {}:\n{}", &args[0], sql))
}
