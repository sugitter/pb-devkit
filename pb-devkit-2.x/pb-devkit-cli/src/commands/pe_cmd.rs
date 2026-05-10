// PE commands for CLI - delegates to pb-devkit-core

use pb_devkit_core::pe::PeParser;
use pb_devkit_core::types::PeInfoResult;

pub fn detect_file_type(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit file-type <file_path>".to_string());
    }
    let result = PeParser::detect_file_type(&args[0]).map_err(|e| e.to_string())?;
    Ok(format!(
        "File: {}\nType: {}\nSize: {} bytes\nPB EXE: {}",
        &args[0], result.file_type, result.size, result.is_pb_exe
    ))
}

pub fn analyze_pe(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit analyze-pe <file_path>".to_string());
    }
    let parser = PeParser::new(&args[0]).map_err(|e| e.to_string())?;
    let info: PeInfoResult = parser.get_info_result();

    let mut output = format!(
        "PE Analysis: {}\n  Machine: {}\n  64-bit: {}\n  PB EXE: {}\n  Embedded PBLs: {}\n",
        &args[0],
        info.machine_type,
        info.is_64bit,
        info.is_pb_exe,
        info.embedded_pbl_count
    );

    if let Some(ref ts) = info.timestamp {
        output.push_str(&format!("  Timestamp: {}\n", ts));
    }

    if !info.resources.is_empty() {
        output.push_str("\n  Embedded Resources:\n");
        for r in &info.resources {
            output.push_str(&format!(
                "    - {}: {} bytes (offset: 0x{:X})\n",
                r.name, r.size, r.offset
            ));
        }
    }

    Ok(output)
}

pub fn extract_pbd(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit extract-pbd <exe_path> <output_dir>".to_string());
    }
    let exe_path = &args[0];
    let output_dir = &args[1];

    let parser = PeParser::new(exe_path).map_err(|e| e.to_string())?;
    let result = parser.extract_resources(output_dir).map_err(|e| e.to_string())?;

    if result.success {
        Ok(format!(
            "Extracted {} PBD resources to {}",
            result.pbd_count, output_dir
        ))
    } else {
        Err(result.error.unwrap_or("Unknown error".to_string()))
    }
}
