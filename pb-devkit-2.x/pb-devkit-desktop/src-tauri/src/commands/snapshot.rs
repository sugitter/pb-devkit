// Snapshot command - export PBL to source + compare with previous + optional git commit

use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(serde::Serialize)]
pub struct SnapshotDiffEntry {
    pub file: String,
    pub status: String,   // "added" | "modified" | "removed" | "unchanged"
    pub lines_added: usize,
    pub lines_removed: usize,
}

#[derive(serde::Serialize)]
pub struct SnapshotResult {
    pub success: bool,
    pub snapshot_id: String,
    pub snapshot_dir: String,
    pub exported_files: usize,
    pub diff: Vec<SnapshotDiffEntry>,
    pub total_added: usize,
    pub total_modified: usize,
    pub total_removed: usize,
    pub manifest_path: String,
    pub message: String,
}

/// Take a snapshot: export PBL source → compare with previous snapshot → save manifest
#[tauri::command]
pub fn take_snapshot(
    source_dir: String,
    snapshot_base: String,
    label: String,
) -> Result<SnapshotResult, String> {
    let src_path = Path::new(&source_dir);
    if !src_path.exists() {
        return Err(format!("Source not found: {}", source_dir));
    }

    // Build snapshot ID from timestamp
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let snapshot_id = format!("snap_{}", ts);
    let snapshot_dir = format!("{}/{}", snapshot_base.trim_end_matches(['/', '\\']), snapshot_id);

    fs::create_dir_all(&snapshot_dir).map_err(|e| e.to_string())?;

    // Collect current source files
    let mut current_files: std::collections::HashMap<String, String> = std::collections::HashMap::new();
    let walker = walkdir::WalkDir::new(src_path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !matches!(ext, "srw" | "srd" | "srm" | "srf" | "sru" | "srq" | "srs" | "srj" | "ps") {
            continue;
        }

        let rel = path.strip_prefix(src_path).unwrap_or(path)
            .to_string_lossy().replace('\\', "/");
        let content = read_pb_file(path);

        // Copy file to snapshot dir
        let dest = format!("{}/{}", snapshot_dir, rel);
        if let Some(parent) = Path::new(&dest).parent() {
            let _ = fs::create_dir_all(parent);
        }
        let _ = fs::write(&dest, &content);
        current_files.insert(rel, content);
    }

    // Find previous snapshot (latest by name sort)
    let prev_files = find_prev_snapshot(&snapshot_base, &snapshot_id);

    // Diff
    let mut diff: Vec<SnapshotDiffEntry> = Vec::new();
    let mut total_added = 0usize;
    let mut total_modified = 0usize;
    let mut total_removed = 0usize;

    // Files in current
    for (rel, content) in &current_files {
        match prev_files.get(rel) {
            None => {
                total_added += 1;
                diff.push(SnapshotDiffEntry {
                    file: rel.clone(),
                    status: "added".to_string(),
                    lines_added: content.lines().count(),
                    lines_removed: 0,
                });
            }
            Some(prev_content) if prev_content != content => {
                total_modified += 1;
                let (la, lr) = count_diff_lines(prev_content, content);
                diff.push(SnapshotDiffEntry {
                    file: rel.clone(),
                    status: "modified".to_string(),
                    lines_added: la,
                    lines_removed: lr,
                });
            }
            _ => {} // unchanged, skip
        }
    }

    // Files in previous but not current = removed
    for rel in prev_files.keys() {
        if !current_files.contains_key(rel) {
            total_removed += 1;
            let lines = prev_files[rel].lines().count();
            diff.push(SnapshotDiffEntry {
                file: rel.clone(),
                status: "removed".to_string(),
                lines_added: 0,
                lines_removed: lines,
            });
        }
    }

    // Sort diff by status priority
    diff.sort_by(|a, b| a.file.cmp(&b.file));

    // Write manifest
    let manifest_path = format!("{}/SNAPSHOT.md", snapshot_dir);
    let manifest = build_manifest(
        &snapshot_id, &label, &source_dir,
        current_files.len(), total_added, total_modified, total_removed, &diff,
    );
    fs::write(&manifest_path, &manifest).map_err(|e| e.to_string())?;

    let msg = format!(
        "快照 {} 创建完成：{} 个文件，+{} 新增 ~{} 修改 -{} 删除",
        snapshot_id, current_files.len(), total_added, total_modified, total_removed
    );

    Ok(SnapshotResult {
        success: true,
        snapshot_id,
        snapshot_dir,
        exported_files: current_files.len(),
        diff,
        total_added,
        total_modified,
        total_removed,
        manifest_path,
        message: msg,
    })
}

/// List existing snapshots in the snapshot base directory
#[tauri::command]
pub fn list_snapshots(snapshot_base: String) -> Result<Vec<String>, String> {
    let base = Path::new(&snapshot_base);
    if !base.exists() {
        return Ok(vec![]);
    }
    let mut snaps: Vec<String> = fs::read_dir(base)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .filter(|e| e.file_name().to_string_lossy().starts_with("snap_"))
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .collect();
    snaps.sort();
    snaps.reverse(); // newest first
    Ok(snaps)
}

// ── helpers ──────────────────────────────────────────────────────────────────

fn read_pb_file(path: &Path) -> String {
    if let Ok(s) = fs::read_to_string(path) {
        return s;
    }
    if let Ok(bytes) = fs::read(path) {
        if bytes.len() >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE {
            let u16s: Vec<u16> = bytes[2..].chunks_exact(2)
                .map(|b| u16::from_le_bytes([b[0], b[1]]))
                .collect();
            return String::from_utf16_lossy(&u16s).to_string();
        }
    }
    String::new()
}

fn find_prev_snapshot(base: &str, current_id: &str) -> std::collections::HashMap<String, String> {
    let base_path = Path::new(base);
    if !base_path.exists() {
        return std::collections::HashMap::new();
    }

    let mut snaps: Vec<String> = match fs::read_dir(base_path) {
        Ok(d) => d
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
            .map(|e| e.file_name().to_string_lossy().into_owned())
            .filter(|n| n.starts_with("snap_") && n.as_str() < current_id)
            .collect(),
        Err(_) => return std::collections::HashMap::new(),
    };
    snaps.sort();

    let prev = match snaps.last() {
        Some(s) => s.clone(),
        None => return std::collections::HashMap::new(),
    };

    let prev_dir = format!("{}/{}", base, prev);
    let mut result = std::collections::HashMap::new();
    let walker = walkdir::WalkDir::new(&prev_dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !matches!(ext, "srw" | "srd" | "srm" | "srf" | "sru" | "srq" | "srs" | "srj" | "ps") {
            continue;
        }
        let rel = path.strip_prefix(&prev_dir).unwrap_or(path)
            .to_string_lossy().replace('\\', "/");
        result.insert(rel, read_pb_file(path));
    }
    result
}

fn count_diff_lines(old: &str, new: &str) -> (usize, usize) {
    let old_lines: std::collections::HashSet<&str> = old.lines().collect();
    let new_lines: std::collections::HashSet<&str> = new.lines().collect();
    let added = new_lines.difference(&old_lines).count();
    let removed = old_lines.difference(&new_lines).count();
    (added, removed)
}

fn build_manifest(
    id: &str, label: &str, source: &str,
    total: usize, added: usize, modified: usize, removed: usize,
    diff: &[SnapshotDiffEntry],
) -> String {
    let mut m = format!(
        r#"# PB DevKit 快照 / Snapshot: {}

- **标签 / Label**: {}
- **源码目录**: `{}`
- **总文件数**: {}
- **变更**: +{} 新增  ~{} 修改  -{} 删除

## 变更文件列表

| 文件 | 状态 | +行 | -行 |
|------|------|-----|-----|
"#,
        id, label, source, total, added, modified, removed
    );

    for e in diff {
        let status_zh = match e.status.as_str() {
            "added" => "✅ 新增",
            "modified" => "📝 修改",
            "removed" => "🗑️ 删除",
            _ => &e.status,
        };
        m.push_str(&format!(
            "| `{}` | {} | +{} | -{} |\n",
            e.file, status_zh, e.lines_added, e.lines_removed
        ));
    }

    if diff.is_empty() {
        m.push_str("| — | 无变更 | — | — |\n");
    }

    m.push_str("\n---\n_Generated by PB DevKit 2.1_\n");
    m
}
