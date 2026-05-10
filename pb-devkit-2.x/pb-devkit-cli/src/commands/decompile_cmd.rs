// Decompile commands for CLI - delegates to pb-devkit-core

use pb_devkit_core as core;

pub fn list_decompile_entries(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit list-decompile <file_path>".to_string());
    }
    let result = core::decompile::list_decompile_entries(&args[0]);

    if !result.success {
        return Err(result.error.unwrap_or("Unknown error".to_string()));
    }

    let mut output = format!("Entries in {}:\n", &args[0]);
    output.push_str(&format!("{:<40} {:>10}\n", "Name", "Type"));
    output.push_str(&"-".repeat(55));
    output.push('\n');

    for (_i, e) in result.entries.iter().take(50).enumerate() {
        let marker = if e.is_source { "[S]" } else { "[C]" };
        output.push_str(&format!(
            "{:<40} {:>6} {}\n",
            &e.name[..e.name.len().min(38)],
            e.entry_type,
            marker
        ));
    }

    if result.entries.len() > 50 {
        output.push_str(&format!("\n... and {} more entries", result.entries.len() - 50));
    }

    Ok(output)
}

pub fn decompile_entry(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit decompile <file_path> <entry_name>".to_string());
    }
    let file_path = &args[0];
    let entry_name = &args[1];

    let result = core::decompile::decompile_entry(file_path, entry_name);

    if result.success {
        Ok(format!(
            "Decompiled: {} ({} bytes)",
            entry_name, result.size
        ))
    } else {
        Err(format!("Failed to decompile '{}': {}", entry_name, result.error.unwrap_or("Unknown error".to_string())))
    }
}

pub fn decompile_all(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit decompile-all <file_path> <output_dir>".to_string());
    }
    core::decompile::decompile_all(&args[0], &args[1])
}
