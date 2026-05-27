// Snapshot command for CLI – version tracking: inventory + diff + metadata
//
// Workflow:
//   1. Scan project source directory, capture file inventory (name, size, hash)
//   2. Compare with previous snapshot (if exists)
//   3. Save snapshot metadata (JSON + history)
//
// Usage: pbdevkit snapshot <project_dir> [--output <dir>] [--json]

use std::collections::HashMap;
use std::fs;
use std::io::Read;
use std::path::Path;
use std::time::UNIX_EPOCH;

/// A single file entry in a snapshot
#[derive(Debug, Clone)]
struct FileEntry {
    path: String,
    size: u64,
    hash: String, // simple CRC32-like hash or content hash
}

/// Snapshot metadata
#[derive(Debug)]
struct Snapshot {
    timestamp: String,
    file_count: usize,
    total_size: u64,
    entries: Vec<FileEntry>,
}

/// Run the snapshot command.
pub fn run_snapshot(args: &[String]) -> Result<String, String> {
    if args.is_empty() {
        return Err("Usage: pbdevkit snapshot <project_dir> [--output <dir>] [--json]".to_string());
    }

    let target = &args[0];
    let target_path = Path::new(target);
    if !target_path.exists() || !target_path.is_dir() {
        return Err(format!("Directory not found: {}", target));
    }

    let output_dir = parse_flag_value(args, "--output", ".pb-snapshots");
    let use_json = args.iter().any(|a| a == "--json");

    let snapshot = capture_snapshot(target_path)?;

    // Compare with previous
    let prev = load_previous_snapshot(&output_dir);
    let diff = if let Some(ref prev_snap) = prev {
        Some(compute_diff(prev_snap, &snapshot))
    } else {
        None
    };

    // Save snapshot
    save_snapshot(&output_dir, &snapshot, diff.as_ref())?;

    if use_json {
        render_json_output(&snapshot, diff.as_ref())
    } else {
        Ok(render_text_output(target, &snapshot, diff.as_ref(), &output_dir))
    }
}

/// Capture a snapshot of all PB source files in a directory tree.
fn capture_snapshot(root: &Path) -> Result<Snapshot, String> {
    let mut entries = Vec::new();
    let mut total_size = 0u64;

    let sr_exts = ["srw", "srd", "srm", "srf", "srs", "sru", "sra", "ps", "srq"];

    let walker = walkdir::WalkDir::new(root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let ext = entry
            .path()
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        if !sr_exts.contains(&ext.as_str()) {
            continue;
        }

        let rel_path = entry
            .path()
            .strip_prefix(root)
            .unwrap_or(entry.path())
            .display()
            .to_string();

        let metadata = entry.metadata().map_err(|e| format!("IO error: {}", e))?;
        let size = metadata.len();
        total_size += size;

        let hash = compute_file_hash(entry.path()).unwrap_or_default();

        entries.push(FileEntry {
            path: rel_path,
            size,
            hash,
        });
    }

    // Sort by path for deterministic output
    entries.sort_by(|a, b| a.path.cmp(&b.path));

    // ISO 8601-like timestamp
    let timestamp = format_iso8601();

    Ok(Snapshot {
        timestamp,
        file_count: entries.len(),
        total_size,
        entries,
    })
}

/// Simple file hash using content bytes (not crypto-grade, just for diff detection).
fn compute_file_hash(path: &Path) -> Option<String> {
    let mut file = fs::File::open(path).ok()?;
    let mut buf = Vec::new();
    file.read_to_end(&mut buf).ok()?;

    // Simple DJB2-like hash for speed
    let mut hash: u64 = 5381;
    for &byte in &buf {
        hash = hash.wrapping_mul(33).wrapping_add(byte as u64);
    }

    // Take first 16KB and end for a better fingerprint on large files
    let sample_size = 16384usize.min(buf.len());
    if buf.len() > sample_size {
        for &byte in buf[..sample_size].iter() {
            hash = hash.wrapping_mul(33).wrapping_add(byte as u64);
        }
        for &byte in buf[buf.len().saturating_sub(sample_size)..].iter() {
            hash = hash.wrapping_mul(33).wrapping_add(byte as u64);
        }
    }

    Some(format!("{:016x}", hash))
}

/// Structure for diff between two snapshots
#[derive(Debug)]
struct SnapshotDiff {
    added: Vec<String>,
    removed: Vec<String>,
    modified: Vec<String>,
}

/// Compare two snapshots and produce a diff.
fn compute_diff(prev: &Snapshot, curr: &Snapshot) -> SnapshotDiff {
    let prev_map: HashMap<&str, &FileEntry> = prev.entries.iter()
        .map(|e| (e.path.as_str(), e))
        .collect();
    let curr_map: HashMap<&str, &FileEntry> = curr.entries.iter()
        .map(|e| (e.path.as_str(), e))
        .collect();

    let prev_paths: Vec<&str> = prev_map.keys().copied().collect();
    let curr_paths: Vec<&str> = curr_map.keys().copied().collect();

    let mut added = Vec::new();
    let mut removed = Vec::new();
    let mut modified = Vec::new();

    for &p in &curr_paths {
        if !prev_map.contains_key(p) {
            added.push(p.to_string());
        } else {
            let pe = prev_map[p];
            let ce = curr_map[p];
            if pe.hash != ce.hash || pe.size != ce.size {
                modified.push(p.to_string());
            }
        }
    }

    for &p in &prev_paths {
        if !curr_map.contains_key(p) {
            removed.push(p.to_string());
        }
    }

    SnapshotDiff { added, removed, modified }
}

/// Load previous snapshot metadata from disk.
fn load_previous_snapshot(snapshot_dir: &str) -> Option<Snapshot> {
    let meta_path = Path::new(snapshot_dir).join("latest.json");
    if !meta_path.exists() {
        return None;
    }

    let content = fs::read_to_string(&meta_path).ok()?;
    parse_snapshot_json(&content)
}

/// Parse snapshot JSON into a Snapshot struct.
fn parse_snapshot_json(json: &str) -> Option<Snapshot> {
    // Minimal JSON parsing – we know the exact format we wrote
    let file_count = extract_json_int(json, "file_count")?;
    let total_size = extract_json_int(json, "total_size")?;
    let timestamp = extract_json_str(json, "timestamp")?;

    // Parse entries array
    let entries_start = json.find("\"entries\"")?;
    let mut entries = Vec::new();

    // Find each { path, size, hash } object
    let mut pos = entries_start;
    while let Some(obj_start) = json[pos..].find('{') {
        let obj_start = pos + obj_start;
        if let Some(obj_end) = json[obj_start..].find('}') {
            let obj_end = obj_start + obj_end + 1;
            let obj_str = &json[obj_start..obj_end];

            if let (Some(path), Some(size), Some(hash)) = (
                extract_json_str(obj_str, "path"),
                extract_json_int(obj_str, "size"),
                extract_json_str(obj_str, "hash"),
            ) {
                entries.push(FileEntry { path, size, hash });
            }
            pos = obj_end;
        } else {
            break;
        }
    }

    Some(Snapshot { timestamp, file_count: file_count as usize, total_size, entries })
}

fn extract_json_int(json: &str, key: &str) -> Option<u64> {
    let search = format!("\"{}\":", key);
    let start = json.find(&search)? + search.len();
    let slice = json[start..].trim_start();
    let end = slice.find(|c: char| !c.is_ascii_digit())?;
    slice[..end].parse().ok()
}

fn extract_json_str(json: &str, key: &str) -> Option<String> {
    let search = format!("\"{}\":", key);
    let start = json.find(&search)? + search.len();
    let slice = json[start..].trim_start();
    if !slice.starts_with('"') {
        return None;
    }
    let inner = &slice[1..];
    let mut escaped = false;
    let mut end_idx = 0;
    for (i, c) in inner.char_indices() {
        if escaped {
            escaped = false;
            continue;
        }
        if c == '\\' {
            escaped = true;
            continue;
        }
        if c == '"' {
            end_idx = i;
            break;
        }
    }
    Some(inner[..end_idx].to_string())
}

/// Save snapshot metadata to disk.
fn save_snapshot(snapshot_dir: &str, snap: &Snapshot, diff: Option<&SnapshotDiff>) -> Result<(), String> {
    let dir = Path::new(snapshot_dir);
    fs::create_dir_all(dir).map_err(|e| format!("Failed to create {}: {}", snapshot_dir, e))?;

    // Build JSON
    let mut json = String::new();
    json.push_str("{\n");
    json.push_str(&format!("  \"timestamp\": \"{}\",\n", snap.timestamp));
    json.push_str(&format!("  \"file_count\": {},\n", snap.file_count));
    json.push_str(&format!("  \"total_size\": {},\n", snap.total_size));

    if let Some(d) = diff {
        json.push_str("  \"changes\": {\n");
        json.push_str(&format!("    \"added\": {},\n", d.added.len()));
        json.push_str(&format!("    \"removed\": {},\n", d.removed.len()));
        json.push_str(&format!("    \"modified\": {}\n", d.modified.len()));
        json.push_str("  },\n");
    }

    json.push_str("  \"entries\": [\n");
    for (i, e) in snap.entries.iter().enumerate() {
        let comma = if i + 1 < snap.entries.len() { "," } else { "" };
        json.push_str(&format!(
            "    {{\"path\": \"{}\", \"size\": {}, \"hash\": \"{}\"}}{}\n",
            e.path.replace('\\', "/"), e.size, e.hash, comma
        ));
    }
    json.push_str("  ]\n");
    json.push_str("}\n");

    let meta_path = dir.join("latest.json");
    fs::write(&meta_path, &json).map_err(|e| format!("Write error: {}", e))?;

    // Append to history.jsonl
    let history_path = dir.join("history.jsonl");
    let mut history = fs::read_to_string(&history_path).unwrap_or_default();
    history.push_str(&json.replace('\n', ""));
    history.push('\n');
    fs::write(&history_path, history).map_err(|e| format!("Write error: {}", e))?;

    Ok(())
}

fn format_iso8601() -> String {
    use std::time::SystemTime;
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    // Simple: convert to YYYY-MM-DDTHH:MM:SS
    let days = secs / 86400;
    let time = secs % 86400;
    let hours = time / 3600;
    let minutes = (time % 3600) / 60;
    let seconds = time % 60;

    // Epoch days = 719528 for 1970-01-01; we'll just use a rough format
    // Actually let's just use the chrono-like approach manually
    let (year, month, day) = days_to_date(days as i64 + 719528);

    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}",
        year, month, day, hours, minutes, seconds
    )
}

fn days_to_date(days: i64) -> (i64, u32, u32) {
    let mut d = days;
    // Algorithm from Howard Hinnant
    d += 719468;
    let era = if d >= 0 { d } else { d - 146096 } / 146097;
    let doe = (d - era * 146097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = y + if month <= 2 { 1 } else { 0 };
    (year, month, day)
}

fn parse_flag_value(args: &[String], flag: &str, default: &str) -> String {
    for i in 0..args.len().saturating_sub(1) {
        if args[i] == flag {
            return args[i + 1].clone();
        }
    }
    default.to_string()
}

/// Render text output for snapshot.
fn render_text_output(target: &str, snap: &Snapshot, diff: Option<&SnapshotDiff>, output_dir: &str) -> String {
    let mut out = String::new();
    out.push_str(&format!(
        "pb snapshot — Project Snapshot\n{}\n\n",
        "=".repeat(60)
    ));
    out.push_str(&format!("Target:       {}\n", target));
    out.push_str(&format!("Files:        {}\n", snap.file_count));
    out.push_str(&format!("Total size:   {} bytes\n", snap.total_size));
    out.push_str(&format!("Timestamp:    {}\n", snap.timestamp));

    if let Some(d) = diff {
        out.push_str(&format!("\nChanges from previous snapshot:\n"));
        out.push_str(&format!("  + {} added\n", d.added.len()));
        out.push_str(&format!("  - {} removed\n", d.removed.len()));
        out.push_str(&format!("  ~ {} modified\n", d.modified.len()));

        if !d.added.is_empty() {
            out.push_str("Added:\n");
            for f in &d.added {
                out.push_str(&format!("  + {}\n", f));
            }
        }
        if !d.removed.is_empty() {
            out.push_str("Removed:\n");
            for f in &d.removed {
                out.push_str(&format!("  - {}\n", f));
            }
        }
        if !d.modified.is_empty() {
            out.push_str("Modified:\n");
            for f in &d.modified {
                out.push_str(&format!("  ~ {}\n", f));
            }
        }
    } else {
        out.push_str("\nNo previous snapshot (first snapshot).\n");
    }

    out.push_str(&format!("\nSnapshot saved: {}/latest.json\n", output_dir));
    out.push_str(&format!("{}\n", "=".repeat(60)));

    out
}

/// Render JSON output for snapshot.
fn render_json_output(snap: &Snapshot, diff: Option<&SnapshotDiff>) -> Result<String, String> {
    let mut json = String::new();
    json.push_str("{\n");
    json.push_str(&format!("  \"timestamp\": \"{}\",\n", snap.timestamp));
    json.push_str(&format!("  \"file_count\": {},\n", snap.file_count));
    json.push_str(&format!("  \"total_size\": {},\n", snap.total_size));

    if let Some(d) = diff {
        json.push_str("  \"changes\": {\n");
        json.push_str(&format!("    \"added\": {},\n", d.added.len()));
        json.push_str(&format!("    \"removed\": {},\n", d.removed.len()));
        json.push_str(&format!("    \"modified\": {}\n", d.modified.len()));
        json.push_str("  },\n");

        json.push_str("  \"added_list\": [");
        json.push_str(&d.added.iter().map(|f| format!("\"{}\"", f)).collect::<Vec<_>>().join(", "));
        json.push_str("],\n");

        json.push_str("  \"removed_list\": [");
        json.push_str(&d.removed.iter().map(|f| format!("\"{}\"", f)).collect::<Vec<_>>().join(", "));
        json.push_str("],\n");

        json.push_str("  \"modified_list\": [");
        json.push_str(&d.modified.iter().map(|f| format!("\"{}\"", f)).collect::<Vec<_>>().join(", "));
        json.push_str("]\n");
    } else {
        json.push_str(&format!("  \"changes\": null\n"));
    }

    json.push_str("}\n");
    Ok(json)
}
