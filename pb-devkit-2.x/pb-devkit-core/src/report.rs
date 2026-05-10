// Report generation - Shared core logic

use std::collections::HashMap;
use std::path::Path;

use crate::pbl::PblParser;
use crate::types::{ProjectReport, ReportSummary, PblFileReport, ObjectStats, FileStats};

/// Generate comprehensive project report
pub fn generate_report(project_path: &str) -> Result<ProjectReport, String> {
    let root = Path::new(project_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let project_name = root.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("Unknown")
        .to_string();

    let mut pbl_files: Vec<(String, String)> = Vec::new();
    let mut pbd_files: Vec<String> = Vec::new();
    let mut exe_files: Vec<String> = Vec::new();

    scan_directory(root, &mut pbl_files, &mut pbd_files, &mut exe_files)?;

    let mut pbl_reports = Vec::new();
    let mut total_objects = 0;
    let mut total_source = 0;
    let mut total_compiled = 0;
    let mut unicode_count = 0;
    let mut ansi_count = 0;
    let mut type_counts: HashMap<String, usize> = HashMap::new();
    let mut total_size: u64 = 0;
    let mut largest: Option<(String, u64)> = None;
    let mut smallest: Option<(String, u64)> = None;

    for (pbl_path, pbl_name) in &pbl_files {
        match PblParser::new(pbl_path) {
            Ok(parser) => {
                let entries = parser.entries();
                let source_count = entries.iter().filter(|e| e.is_source).count();
                let compiled_count = entries.len() - source_count;

                let mut type_map: HashMap<String, usize> = HashMap::new();
                for entry in entries {
                    let type_name = entry.entry_type_name.clone();
                    *type_map.entry(type_name.clone()).or_insert(0) += 1;
                    *type_counts.entry(type_name).or_insert(0) += 1;
                }

                let file_size = std::fs::metadata(pbl_path).map(|m| m.len()).unwrap_or(0);
                total_size += file_size;

                match &largest {
                    None => largest = Some((pbl_name.clone(), file_size)),
                    Some((_, size)) if file_size > *size => largest = Some((pbl_name.clone(), file_size)),
                    _ => {}
                }
                match &smallest {
                    None => smallest = Some((pbl_name.clone(), file_size)),
                    Some((_, size)) if file_size < *size => smallest = Some((pbl_name.clone(), file_size)),
                    _ => {}
                }

                if parser.is_unicode() {
                    unicode_count += 1;
                } else {
                    ansi_count += 1;
                }

                let version_str = parser.version().short_str().to_string();

                pbl_reports.push(PblFileReport {
                    path: pbl_path.clone(),
                    name: pbl_name.clone(),
                    size_bytes: file_size,
                    is_unicode: parser.is_unicode(),
                    pb_version: version_str,
                    total_entries: entries.len(),
                    source_entries: source_count,
                    compiled_entries: compiled_count,
                    object_types: type_map,
                });

                total_objects += entries.len();
                total_source += source_count;
                total_compiled += compiled_count;
            }
            Err(_) => {
                let file_size = std::fs::metadata(pbl_path).map(|m| m.len()).unwrap_or(0);
                pbl_reports.push(PblFileReport {
                    path: pbl_path.clone(),
                    name: pbl_name.clone(),
                    size_bytes: file_size,
                    is_unicode: false,
                    pb_version: "Unknown".to_string(),
                    total_entries: 0,
                    source_entries: 0,
                    compiled_entries: 0,
                    object_types: HashMap::new(),
                });
            }
        }
    }

    let mut top_types: Vec<(String, usize)> = type_counts.into_iter().collect();
    top_types.sort_by(|a, b| b.1.cmp(&a.1));
    let top_types: Vec<(String, usize)> = top_types.into_iter().take(10).collect();

    let avg_size = if !pbl_files.is_empty() {
        total_size / pbl_files.len() as u64
    } else {
        0
    };

    let generated_at = format_now_utc();

    Ok(ProjectReport {
        project_name,
        project_path: project_path.to_string(),
        generated_at,
        summary: ReportSummary {
            total_pbl_files: pbl_files.len(),
            total_pbd_files: pbd_files.len(),
            total_exe_files: exe_files.len(),
            total_objects,
            source_objects: total_source,
            compiled_objects: total_compiled,
            unicode_pbls: unicode_count,
            ansi_pbls: ansi_count,
        },
        pbl_files: pbl_reports,
        object_stats: ObjectStats {
            by_type: top_types.iter().cloned().collect(),
            top_types,
        },
        file_stats: FileStats {
            total_size_bytes: total_size,
            largest_file: largest,
            smallest_file: smallest,
            average_size_bytes: avg_size,
        },
    })
}

/// Export report to JSON file
pub fn export_report(project_path: &str, output_path: &str) -> Result<String, String> {
    let report = generate_report(project_path)?;
    let json = serde_json::to_string_pretty(&report)
        .map_err(|e| e.to_string())?;

    std::fs::write(output_path, &json)
        .map_err(|e| e.to_string())?;

    Ok(format!("Report exported to {}", output_path))
}

fn scan_directory(
    dir: &Path,
    pbl_files: &mut Vec<(String, String)>,
    pbd_files: &mut Vec<String>,
    exe_files: &mut Vec<String>,
) -> Result<(), String> {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            let name = path.file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_lowercase();

            if path.is_dir() {
                if !name.starts_with('.') && name != "node_modules" && name != "target" {
                    scan_directory(&path, pbl_files, pbd_files, exe_files)?;
                }
            } else if name.ends_with(".pbl") {
                pbl_files.push((path.to_string_lossy().to_string(), name));
            } else if name.ends_with(".pbd") {
                pbd_files.push(path.to_string_lossy().to_string());
            } else if name.ends_with(".exe") {
                exe_files.push(path.to_string_lossy().to_string());
            }
        }
    }
    Ok(())
}

fn format_now_utc() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    let days = secs / 86400;
    let remaining = secs % 86400;
    let hours = remaining / 3600;
    let minutes = (remaining % 3600) / 60;
    let seconds = remaining % 60;
    let mut year = 1970;
    let mut days_left = days as i64;
    loop {
        let days_in_year = if is_leap_year(year) { 366 } else { 365 };
        if days_left < days_in_year {
            break;
        }
        days_left -= days_in_year;
        year += 1;
    }
    let month_days = if is_leap_year(year) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut month = 1;
    for d in month_days.iter() {
        if days_left < *d as i64 {
            break;
        }
        days_left -= *d as i64;
        month += 1;
    }
    let day = days_left + 1;
    format!("{:04}-{:02}-{:02} {:02}:{:02}:{:02} UTC", year, month, day, hours, minutes, seconds)
}

fn is_leap_year(year: i64) -> bool {
    (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
}
