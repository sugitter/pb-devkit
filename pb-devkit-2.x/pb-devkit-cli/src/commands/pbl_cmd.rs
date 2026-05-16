// PBL Commands for CLI - delegates to pb-devkit-core

use pb_devkit_core::pbl::PblParser;
use pb_devkit_core::types::PblEntryInfo;
use indicatif::{ProgressBar, ProgressStyle};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

pub fn parse_pbl(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit parse <pbl_path>".to_string());
    }
    let path = &args[0];
    let parser = PblParser::new(path).map_err(|e| e.to_string())?;

    let entries: Vec<PblEntryInfo> = parser.entries().iter().map(|e| e.to_info()).collect();
    let total = entries.len();
    let source = entries.iter().filter(|e| e.is_source).count();
    let compiled = total - source;
    let unicode = if parser.is_unicode() { "Unicode" } else { "ANSI" };

    Ok(format!(
        "PBL: {}\nVersion: {}\nEntries: {} (Source: {}, Compiled: {})",
        path, unicode, total, source, compiled
    ))
}

pub fn get_pbl_info(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit info <pbl_path>".to_string());
    }
    let path = &args[0];
    let parser = PblParser::new(path).map_err(|e| e.to_string())?;
    let info = parser.get_info().map_err(|e| e.to_string())?;

    Ok(format!(
        "File: {}\nSize: {} KB\nEncoding: {}\nEntries: {} (Source: {}, Compiled: {})",
        info.path,
        info.file_size / 1024,
        info.pb_version,
        info.total_entries,
        info.source_entries,
        info.compiled_entries,
    ))
}

pub fn list_entries(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit list <pbl_path>".to_string());
    }
    let path = &args[0];
    let parser = PblParser::new(path).map_err(|e| e.to_string())?;
    let entries: Vec<PblEntryInfo> = parser.entries().iter().map(|e| e.to_info()).collect();

    let mut output = format!("Entries in {}:\n", path);
    output.push_str(&format!("{:<40} {:>10} {:>10}\n", "Name", "Type", "Size"));
    output.push_str(&"-".repeat(65));
    output.push('\n');

    for entry in entries.iter().take(50) {
        let type_marker = if entry.is_source { "[S]" } else { "[C]" };
        output.push_str(&format!(
            "{:<40} {:>6} {:>8} {}\n",
            &entry.name[..entry.name.len().min(38)],
            entry.entry_type_name,
            entry.size,
            type_marker
        ));
    }

    if entries.len() > 50 {
        output.push_str(&format!("\n... and {} more entries", entries.len() - 50));
    }

    Ok(output)
}

pub fn export_entry(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit export <pbl_path> <entry_name>".to_string());
    }
    let pbl_path = &args[0];
    let entry_name = &args[1];

    let parser = PblParser::new(pbl_path).map_err(|e| e.to_string())?;
    match parser.export_entry(entry_name) {
        Ok(source) => Ok(format!(
            "Exported: {} ({} bytes)",
            entry_name,
            source.len()
        )),
        Err(e) => Err(format!("Entry '{}' not found: {}", entry_name, e)),
    }
}

pub fn export_pbl(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit export-pbl <pbl_path> <output_dir> [--by-type]".to_string());
    }
    let pbl_path = &args[0];
    let output_dir = args.get(1).ok_or("Missing output_dir")?;
    let by_type = args.len() > 2 && args[2] == "--by-type";

    let parser = PblParser::new(pbl_path).map_err(|e| e.to_string())?;

    // Get source entries count for progress bar
    let source_entries: Vec<_> = parser.entries().iter()
        .filter(|e| e.is_source)
        .collect();
    let total = source_entries.len();

    if total == 0 {
        return Ok("No source entries to export".to_string());
    }

    // Create progress bar
    let pb = ProgressBar::new(total as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40.cyan/blue}] {pos}/{len} ({eta}) {msg}")?
            .progress_chars("#>-")?
    );
    pb.set_message("Exporting...");

    // Track exported count with Arc for sharing
    let exported = Arc::new(AtomicUsize::new(0));
    let output_path = std::path::Path::new(output_dir);
    std::fs::create_dir_all(output_path).map_err(|e| e.to_string())?;

    // Export with progress
    for entry in source_entries {
        if let Ok(source) = parser.export_entry(&entry.name) {
            let file_path = if by_type {
                let type_dir = output_path.join(&entry.entry_type_name);
                std::fs::create_dir_all(&type_dir).ok();
                type_dir.join(&entry.name)
            } else {
                output_path.join(&entry.name)
            };

            if std::fs::write(&file_path, &source).is_ok() {
                let count = exported.fetch_add(1, Ordering::SeqCst) + 1;
                pb.set_message(format!("Exporting: {}", &entry.name[..entry.name.len().min(30)]));
                pb.set_position(count as u64);
            }
        }
    }

    pb.finish_with_message(format!("Done! Exported {} entries to {}", total, output_dir));

    Ok(format!("Exported {} entries to {}", total, output_dir))
}
