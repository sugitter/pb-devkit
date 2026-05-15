// Search commands for CLI - delegates to pb-devkit-core
// Enhanced v2.1: Parallel search, regex support

use pb_devkit_core::search;
use pb_devkit_core::types::SearchResults;

pub fn search_in_files(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit search <path> <query> [--case-sensitive] [--types ext1,ext2]".to_string());
    }
    let root_path = &args[0];
    let query = &args[1];

    let case_sensitive = args.len() > 2 && args[2] == "--case-sensitive";

    let file_types: Vec<String> = if args.len() > 2 && args[2].starts_with('.') {
        args[2..].to_vec()
    } else if args.len() > 3 && args[3].starts_with('.') {
        args[3..].to_vec()
    } else {
        vec![]
    };

    let result: SearchResults = search::search_in_files(root_path, query, case_sensitive, &file_types)?;

    if result.matches.is_empty() {
        return Ok(format!(
            "No matches found for '{}' in {} ({} files searched)",
            query, root_path, result.files_count
        ));
    }

    let mut output = format!(
        "Search results for '{}' in {}:\n  Files searched: {}\n  Matches found: {}\n\n",
        query, root_path, result.files_count, result.total_matches
    );

    for (i, m) in result.matches.iter().take(20).enumerate() {
        output.push_str(&format!(
            "{}. {} (line {}): {}\n",
            i + 1,
            m.file,
            m.line_number,
            m.line_content.trim().chars().take(60).collect::<String>()
        ));
    }

    if result.matches.len() > 20 {
        output.push_str(&format!("\n... and {} more matches", result.matches.len() - 20));
    }

    Ok(output)
}

pub fn search_by_type(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit search-type <path> <type>\nTypes: window, datawindow, menu, function, structure, userobject, query, pipeline, project, proxy, application".to_string());
    }
    let root_path = &args[0];
    let obj_type = &args[1];

    let files = search::search_by_type(root_path, obj_type)?;

    if files.is_empty() {
        return Ok(format!("No '{}' objects found in {}", obj_type, root_path));
    }

    let mut output = format!("'{}' objects in {}:\n", obj_type, root_path);
    for (i, f) in files.iter().take(50).enumerate() {
        output.push_str(&format!("{}. {}\n", i + 1, f));
    }
    if files.len() > 50 {
        output.push_str(&format!("... and {} more", files.len() - 50));
    }
    Ok(output)
}

/// Search using regex pattern (v2.1+)
pub fn search_with_regex(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit search-regex <path> <pattern> [--case-sensitive]".to_string());
    }
    let root_path = &args[0];
    let pattern = &args[1];
    let case_sensitive = args.len() > 2 && args[2] == "--case-sensitive";

    let result: SearchResults = search::search_with_regex(root_path, pattern, case_sensitive, &[])?;

    if result.matches.is_empty() {
        return Ok(format!(
            "No matches found for regex '{}' in {} ({} files searched)",
            pattern, root_path, result.files_count
        ));
    }

    let mut output = format!(
        "Regex search results for '{}' in {}:\n  Files searched: {}\n  Matches found: {}\n\n",
        pattern, root_path, result.files_count, result.total_matches
    );

    for (i, m) in result.matches.iter().take(20).enumerate() {
        output.push_str(&format!(
            "{}. {} (line {}): {}\n",
            i + 1,
            m.file,
            m.line_number,
            m.line_content.trim().chars().take(60).collect::<String>()
        ));
    }

    if result.matches.len() > 20 {
        output.push_str(&format!("\n... and {} more matches", result.matches.len() - 20));
    }

    Ok(output)
}
