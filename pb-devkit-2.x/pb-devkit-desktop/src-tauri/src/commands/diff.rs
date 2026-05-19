// Diff command - compares two files

use std::fs;

/// Compare two files and return diff result
#[tauri::command]
pub fn diff_files(file1: String, file2: String) -> Result<DiffResult, String> {
    let content1 = fs::read_to_string(&file1)
        .map_err(|e| format!("Failed to read {}: {}", file1, e))?;
    let content2 = fs::read_to_string(&file2)
        .map_err(|e| format!("Failed to read {}: {}", file2, e))?;

    let lines1: Vec<&str> = content1.lines().collect();
    let lines2: Vec<&str> = content2.lines().collect();

    let diff = compute_diff(&lines1, &lines2);

    Ok(DiffResult {
        file1,
        file2,
        total_changes: diff.len() as u32,
        changes: diff,
    })
}

#[derive(serde::Serialize)]
pub struct DiffResult {
    pub file1: String,
    pub file2: String,
    pub total_changes: u32,
    pub changes: Vec<DiffChange>,
}

#[derive(serde::Serialize)]
pub struct DiffChange {
    pub line_number: u32,
    pub line1: Option<String>,
    pub line2: Option<String>,
    pub change_type: String, // "modified", "added", "removed"
}

fn compute_diff(lines1: &[&str], lines2: &[&str]) -> Vec<DiffChange> {
    let mut changes = Vec::new();
    let max_lines = lines1.len().max(lines2.len());

    for i in 0..max_lines {
        let line1 = lines1.get(i).copied();
        let line2 = lines2.get(i).copied();

        match (line1, line2) {
            (Some(l1), Some(l2)) if l1 == l2 => {
                // Lines are equal - no change
            }
            (Some(l1), Some(l2)) => {
                changes.push(DiffChange {
                    line_number: (i + 1) as u32,
                    line1: Some(l1.to_string()),
                    line2: Some(l2.to_string()),
                    change_type: "modified".to_string(),
                });
            }
            (Some(l1), None) => {
                changes.push(DiffChange {
                    line_number: (i + 1) as u32,
                    line1: Some(l1.to_string()),
                    line2: None,
                    change_type: "removed".to_string(),
                });
            }
            (None, Some(l2)) => {
                changes.push(DiffChange {
                    line_number: (i + 1) as u32,
                    line1: None,
                    line2: Some(l2.to_string()),
                    change_type: "added".to_string(),
                });
            }
            (None, None) => {}
        }
    }

    changes
}