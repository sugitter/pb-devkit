// Diff command for CLI - compares two files or directories

use std::fs;
use std::path::Path;

/// Compare two files and return diff output
pub fn diff_files(file1: &str, file2: &str) -> Result<String, String> {
    let content1 = fs::read_to_string(file1).map_err(|e| format!("Failed to read {}: {}", file1, e))?;
    let content2 = fs::read_to_string(file2).map_err(|e| format!("Failed to read {}: {}", file2, e))?;

    let lines1: Vec<&str> = content1.lines().collect();
    let lines2: Vec<&str> = content2.lines().collect();

    let diff = compute_diff(&lines1, &lines2, file1, file2);

    Ok(diff)
}

/// Compare two directories
pub fn diff_dirs(dir1: &str, dir2: &str) -> Result<String, String> {
    let path1 = Path::new(dir1);
    let path2 = Path::new(dir2);

    if !path1.exists() {
        return Err(format!("Directory not found: {}", dir1));
    }
    if !path2.exists() {
        return Err(format!("Directory not found: {}", dir2));
    }

    let mut output = format!("Diff between {} and {}:\n\n", dir1, dir2);
    let mut diff_count = 0;

    // Simple comparison: list files that differ
    let entries1 = walkdir::WalkDir::new(dir1)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in entries1 {
        let rel_path = entry.path().strip_prefix(dir1).unwrap();
        let file2_path = Path::new(dir2).join(rel_path);

        if file2_path.exists() {
            let content1 = fs::read_to_string(entry.path()).unwrap_or_default();
            let content2 = fs::read_to_string(&file2_path).unwrap_or_default();

            if content1 != content2 {
                diff_count += 1;
                output.push_str(&format!("Changed: {}\n", rel_path.display()));
            }
        } else {
            diff_count += 1;
            output.push_str(&format!("Added in {}: {}\n", dir2, rel_path.display()));
        }
    }

    // Check for deleted files
    let entries2 = walkdir::WalkDir::new(dir2)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in entries2 {
        let rel_path = entry.path().strip_prefix(dir2).unwrap();
        let file1_path = Path::new(dir1).join(rel_path);

        if !file1_path.exists() {
            diff_count += 1;
            output.push_str(&format!("Deleted in {}: {}\n", dir2, rel_path.display()));
        }
    }

    if diff_count == 0 {
        output = "No differences found.".to_string();
    } else {
        output = format!("Total differences: {}\n\n{}", diff_count, output);
    }

    Ok(output)
}

/// Compute line-by-line diff
fn compute_diff(lines1: &[&str], lines2: &[&str], file1: &str, file2: &str) -> String {
    let mut output = format!("Diff: {} vs {}\n\n", file1, file2);

    let max_lines = lines1.len().max(lines2.len());
    let mut changes = 0;

    for i in 0..max_lines {
        let line1 = lines1.get(i).copied();
        let line2 = lines2.get(i).copied();

        match (line1, line2) {
            (Some(l1), Some(l2)) if l1 == l2 => {
                // Lines are equal, show context
                if i < 3 || i >= max_lines.saturating_sub(3) {
                    output.push_str(&format!("  {:4}: {}\n", i + 1, l1));
                } else if i == 3 {
                    output.push_str("  ...\n");
                }
            }
            (Some(l1), Some(l2)) => {
                changes += 1;
                output.push_str(&format!("- {:4}: {}\n", i + 1, l1));
                output.push_str(&format!("+ {:4}: {}\n", i + 1, l2));
            }
            (Some(l1), None) => {
                changes += 1;
                output.push_str(&format!("- {:4}: {}\n", i + 1, l1));
            }
            (None, Some(l2)) => {
                changes += 1;
                output.push_str(&format!("+ {:4}: {}\n", i + 1, l2));
            }
            (None, None) => {}
        }
    }

    if changes == 0 {
        "No differences found.".to_string()
    } else {
        format!("Total changes: {}\n\n{}", changes, output)
    }
}

/// Entry point for diff command
pub fn run_diff(args: &[String]) -> Result<String, String> {
    if args.len() < 2 {
        return Err("Usage: pbdevkit diff <file1|dir1> <file2|dir2>".to_string());
    }

    let path1 = Path::new(&args[0]);
    let path2 = Path::new(&args[1]);

    let is_dir1 = path1.is_dir();
    let is_dir2 = path2.is_dir();

    match (is_dir1, is_dir2) {
        (false, false) => diff_files(&args[0], &args[1]),
        (true, true) => diff_dirs(&args[0], &args[1]),
        _ => Err("Both paths must be files or both must be directories".to_string()),
    }
}