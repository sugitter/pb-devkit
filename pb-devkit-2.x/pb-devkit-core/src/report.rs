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

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    // ─── is_leap_year ───

    #[test]
    fn leap_year_divisible_by_4() {
        assert!(is_leap_year(2024));
        assert!(is_leap_year(2020));
        assert!(is_leap_year(2016));
    }

    #[test]
    fn not_leap_year_regular() {
        assert!(!is_leap_year(2023));
        assert!(!is_leap_year(2022));
        assert!(!is_leap_year(2021));
    }

    #[test]
    fn century_not_leap() {
        assert!(!is_leap_year(1900));
        assert!(!is_leap_year(2100));
    }

    #[test]
    fn century_divisible_by_400_is_leap() {
        assert!(is_leap_year(2000));
        assert!(is_leap_year(1600));
    }

    // ─── format_now_utc ───

    #[test]
    fn format_now_utc_produces_valid_format() {
        let s = format_now_utc();
        // Should look like: "2026-06-04 11:30:00 UTC"
        assert!(s.ends_with(" UTC"));
        assert_eq!(s.len(), "2026-06-04 00:00:00 UTC".len());
        assert!(s.contains('-'));
        assert!(s.contains(':'));
        // year should be >= 2026
        let year: i32 = s[0..4].parse().unwrap();
        assert!(year >= 2026);
    }

    // ─── scan_directory ───

    #[test]
    fn scan_directory_finds_pbl_files() {
        let tmp = TempDir::new().unwrap();
        fs::write(tmp.path().join("app.pbl"), b"fake").unwrap();
        fs::write(tmp.path().join("lib.pbl"), b"fake").unwrap();

        let mut pbl = Vec::new();
        let mut pbd = Vec::new();
        let mut exe = Vec::new();
        scan_directory(tmp.path(), &mut pbl, &mut pbd, &mut exe).unwrap();
        assert_eq!(pbl.len(), 2);
        assert_eq!(pbd.len(), 0);
        assert_eq!(exe.len(), 0);
    }

    #[test]
    fn scan_directory_finds_pbd_and_exe() {
        let tmp = TempDir::new().unwrap();
        fs::write(tmp.path().join("app.pbd"), b"fake").unwrap();
        fs::write(tmp.path().join("app.exe"), b"fake").unwrap();

        let mut pbl = Vec::new();
        let mut pbd = Vec::new();
        let mut exe = Vec::new();
        scan_directory(tmp.path(), &mut pbl, &mut pbd, &mut exe).unwrap();
        assert_eq!(pbl.len(), 0);
        assert_eq!(pbd.len(), 1);
        assert_eq!(exe.len(), 1);
    }

    #[test]
    fn scan_directory_skips_dot_and_node_modules() {
        let tmp = TempDir::new().unwrap();
        fs::create_dir_all(tmp.path().join(".git")).unwrap();
        fs::create_dir_all(tmp.path().join("node_modules")).unwrap();
        fs::create_dir_all(tmp.path().join("target")).unwrap();
        fs::write(tmp.path().join(".git").join("conf.pbl"), b"x").unwrap();
        fs::write(tmp.path().join("node_modules").join("x.pbl"), b"x").unwrap();
        fs::write(tmp.path().join("target").join("x.pbl"), b"x").unwrap();

        let mut pbl = Vec::new();
        let mut pbd = Vec::new();
        let mut exe = Vec::new();
        scan_directory(tmp.path(), &mut pbl, &mut pbd, &mut exe).unwrap();
        assert_eq!(pbl.len(), 0);
    }

    #[test]
    fn scan_directory_recursive() {
        let tmp = TempDir::new().unwrap();
        fs::create_dir_all(tmp.path().join("sub")).unwrap();
        fs::write(tmp.path().join("sub").join("b.pbl"), b"x").unwrap();

        let mut pbl = Vec::new();
        let mut pbd = Vec::new();
        let mut exe = Vec::new();
        scan_directory(tmp.path(), &mut pbl, &mut pbd, &mut exe).unwrap();
        assert_eq!(pbl.len(), 1);
    }

    // ─── export_report with nonexistent path ───

    #[test]
    fn export_report_nonexistent_path_returns_err() {
        let result = export_report("/nonexistent/path", "/tmp/out.json");
        assert!(result.is_err());
    }
}
