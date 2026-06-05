// Snapshot - Version snapshot for project state tracking
// v2.1+: Capture and compare project states at different times

use std::collections::HashMap;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};

/// Snapshot entry for a single file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileSnapshot {
    pub path: String,
    pub size: u64,
    pub modified: u64,
    pub checksum: u64,
    pub object_count: Option<usize>,
}

/// Project snapshot at a specific point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectSnapshot {
    pub id: String,
    pub name: String,
    pub root_path: String,
    pub created_at: u64,
    pub description: String,
    pub pbl_files: Vec<PblSnapshot>,
    pub total_objects: usize,
    pub total_files: usize,
}

/// Snapshot info for a single PBL file
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PblSnapshot {
    pub path: String,
    pub name: String,
    pub size: u64,
    pub entry_count: usize,
    pub source_count: usize,
    pub compiled_count: usize,
    pub is_unicode: bool,
    pub pb_version: String,
}

impl ProjectSnapshot {
    /// Create a new snapshot for a project
    pub fn new(root_path: &str, name: &str, description: &str) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let id = format!("{:x}_{}", now, Self::generate_random_suffix());

        ProjectSnapshot {
            id,
            name: name.to_string(),
            root_path: root_path.to_string(),
            created_at: now,
            description: description.to_string(),
            pbl_files: Vec::new(),
            total_objects: 0,
            total_files: 0,
        }
    }

    /// Generate a random suffix for snapshot ID
    fn generate_random_suffix() -> u64 {
        use std::time::SystemTime;
        let duration = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        let nanos = duration.subsec_nanos() as u64;
        duration.as_secs().wrapping_mul(nanos).wrapping_add(nanos)
    }

    /// Add a PBL file to the snapshot
    pub fn add_pbl(&mut self, pbl: PblSnapshot) {
        self.total_objects += pbl.entry_count;
        self.total_files += 1;
        self.pbl_files.push(pbl);
    }

    /// Save snapshot to JSON file
    pub fn save(&self, output_dir: &str) -> Result<String, String> {
        let path = Path::new(output_dir);
        fs::create_dir_all(path).map_err(|e| e.to_string())?;

        let filename = format!("{}.json", self.id);
        let filepath = path.join(&filename);

        let json = serde_json::to_string_pretty(self)
            .map_err(|e| e.to_string())?;

        let mut file = File::create(&filepath)
            .map_err(|e| e.to_string())?;

        file.write_all(json.as_bytes())
            .map_err(|e| e.to_string())?;

        Ok(filepath.to_string_lossy().to_string())
    }

    /// Load snapshot from JSON file
    pub fn load(filepath: &str) -> Result<Self, String> {
        let content = fs::read_to_string(filepath)
            .map_err(|e| e.to_string())?;

        serde_json::from_str(&content)
            .map_err(|e| e.to_string())
    }

    /// Compare this snapshot with another
    pub fn compare(&self, other: &ProjectSnapshot) -> SnapshotDiff {
        let mut changes = Vec::new();
        let mut added = Vec::new();
        let mut removed = Vec::new();

        // Create maps for comparison
        let self_map: HashMap<&str, &PblSnapshot> = self.pbl_files
            .iter()
            .map(|p| (p.path.as_str(), p))
            .collect();

        let other_map: HashMap<&str, &PblSnapshot> = other.pbl_files
            .iter()
            .map(|p| (p.path.as_str(), p))
            .collect();

        // Find changed and removed
        for (path, pbl) in &self_map {
            if let Some(other_pbl) = other_map.get(path) {
                if pbl.entry_count != other_pbl.entry_count 
                    || pbl.is_unicode != other_pbl.is_unicode {
                    changes.push(FileChange {
                        path: path.to_string(),
                        change_type: "modified".to_string(),
                        old_value: Some(other_pbl.entry_count),
                        new_value: Some(pbl.entry_count),
                    });
                }
            } else {
                // Path exists in self (new) but not other (old) → was ADDED
                added.push(path.to_string());
            }
        }

        // Find removed (paths in old but not in new)
        for path in other_map.keys() {
            if !self_map.contains_key(path) {
                removed.push(path.to_string());
            }
        }

        SnapshotDiff {
            snapshot_id: self.id.clone(),
            compared_to: other.id.clone(),
            changes,
            added,
            removed,
            object_count_delta: self.total_objects as i64 - other.total_objects as i64,
        }
    }

    /// Format timestamp to readable string
    pub fn format_time(&self) -> String {
        let dt = chrono::DateTime::from_timestamp(self.created_at as i64, 0);
        dt.map(|d| d.format("%Y-%m-%d %H:%M:%S").to_string())
            .unwrap_or_else(|| "Unknown".to_string())
    }
}

/// Represents a change between two snapshots
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileChange {
    pub path: String,
    pub change_type: String,  // "added", "removed", "modified"
    pub old_value: Option<usize>,
    pub new_value: Option<usize>,
}

/// Comparison result between two snapshots
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SnapshotDiff {
    pub snapshot_id: String,
    pub compared_to: String,
    pub changes: Vec<FileChange>,
    pub added: Vec<String>,
    pub removed: Vec<String>,
    pub object_count_delta: i64,
}

impl SnapshotDiff {
    /// Get summary of changes
    pub fn summary(&self) -> String {
        format!(
            "Objects: {}{}, Changes: {}, Added: {}, Removed: {}",
            if self.object_count_delta >= 0 { "+" } else { "" },
            self.object_count_delta,
            self.changes.len(),
            self.added.len(),
            self.removed.len()
        )
    }

    /// Check if there are any changes
    pub fn has_changes(&self) -> bool {
        !self.changes.is_empty() || !self.added.is_empty() || !self.removed.is_empty()
    }
}

/// Snapshot manager for storing and retrieving snapshots
pub struct SnapshotManager {
    snapshots_dir: String,
}

impl SnapshotManager {
    pub fn new(root_path: &str) -> Self {
        let snapshots_dir = format!("{}/.pbdevkit/snapshots", root_path);
        
        // Ensure directory exists
        let _ = fs::create_dir_all(&snapshots_dir);

        SnapshotManager { snapshots_dir }
    }

    /// List all snapshots
    pub fn list_snapshots(&self) -> Result<Vec<ProjectSnapshot>, String> {
        let mut snapshots = Vec::new();
        let path = Path::new(&self.snapshots_dir);

        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let filepath = entry.path();
                if filepath.extension().map(|e| e == "json").unwrap_or(false) {
                    if let Ok(snapshot) = ProjectSnapshot::load(filepath.to_str().unwrap_or("")) {
                        snapshots.push(snapshot);
                    }
                }
            }
        }

        // Sort by creation time (newest first)
        snapshots.sort_by_key(|b| std::cmp::Reverse(b.created_at));

        Ok(snapshots)
    }

    /// Get snapshot by ID
    pub fn get_snapshot(&self, id: &str) -> Result<ProjectSnapshot, String> {
        let filepath = format!("{}/{}.json", self.snapshots_dir, id);
        ProjectSnapshot::load(&filepath)
    }

    /// Delete a snapshot
    pub fn delete_snapshot(&self, id: &str) -> Result<(), String> {
        let filepath = format!("{}/{}.json", self.snapshots_dir, id);
        fs::remove_file(&filepath).map_err(|e| e.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn make_pbl(path: &str, entries: usize) -> PblSnapshot {
        PblSnapshot {
            path: path.to_string(),
            name: path.to_string(),
            size: 1024,
            entry_count: entries,
            source_count: entries / 2,
            compiled_count: entries - entries / 2,
            is_unicode: true,
            pb_version: "12.5".to_string(),
        }
    }

    // ─── ProjectSnapshot::new ───

    #[test]
    fn new_creates_valid_snapshot() {
        let snap = ProjectSnapshot::new("/proj", "v1", "initial");
        assert!(!snap.id.is_empty());
        assert_eq!(snap.name, "v1");
        assert_eq!(snap.root_path, "/proj");
        assert_eq!(snap.description, "initial");
        assert_eq!(snap.total_objects, 0);
        assert_eq!(snap.total_files, 0);
        assert!(snap.pbl_files.is_empty());
        assert!(snap.created_at > 0);
    }

    #[test]
    fn new_ids_are_unique() {
        let s1 = ProjectSnapshot::new("/a", "n", "d");
        let s2 = ProjectSnapshot::new("/a", "n", "d");
        assert_ne!(s1.id, s2.id);
    }

    // ─── add_pbl ───

    #[test]
    fn add_pbl_updates_counters() {
        let mut snap = ProjectSnapshot::new("/p", "v1", "");
        snap.add_pbl(make_pbl("a.pbl", 10));
        assert_eq!(snap.total_objects, 10);
        assert_eq!(snap.total_files, 1);

        snap.add_pbl(make_pbl("b.pbl", 20));
        assert_eq!(snap.total_objects, 30);
        assert_eq!(snap.total_files, 2);
    }

    // ─── save / load ───

    #[test]
    fn save_and_load_roundtrip() {
        let tmp = TempDir::new().unwrap();
        let mut snap = ProjectSnapshot::new("/p", "v1", "test snapshot");
        snap.add_pbl(make_pbl("a.pbl", 10));

        let path = snap.save(tmp.path().to_str().unwrap()).unwrap();
        let loaded = ProjectSnapshot::load(&path).unwrap();
        assert_eq!(loaded.name, "v1");
        assert_eq!(loaded.total_objects, 10);
        assert_eq!(loaded.total_files, 1);
    }

    #[test]
    fn save_creates_directory_if_missing() {
        let tmp = TempDir::new().unwrap();
        let snap = ProjectSnapshot::new("/p", "v1", "");
        let subdir = tmp.path().join("nested").join("snaps");
        let path = snap.save(subdir.to_str().unwrap()).unwrap();
        assert!(Path::new(&path).exists());
    }

    #[test]
    fn load_nonexistent_returns_err() {
        let result = ProjectSnapshot::load("/nonexistent/path/snap.json");
        assert!(result.is_err());
    }

    // ─── compare ───

    #[test]
    fn compare_detects_added() {
        let mut old = ProjectSnapshot::new("/p", "v1", "");
        old.add_pbl(make_pbl("a.pbl", 5));

        let mut new = ProjectSnapshot::new("/p", "v2", "");
        new.add_pbl(make_pbl("a.pbl", 5));
        new.add_pbl(make_pbl("b.pbl", 3));

        let diff = new.compare(&old);
        assert_eq!(diff.added.len(), 1);
        assert!(diff.added[0].contains("b.pbl"));
        assert_eq!(diff.removed.len(), 0);
    }

    #[test]
    fn compare_detects_removed() {
        let mut old = ProjectSnapshot::new("/p", "v1", "");
        old.add_pbl(make_pbl("a.pbl", 5));
        old.add_pbl(make_pbl("b.pbl", 3));

        let mut new = ProjectSnapshot::new("/p", "v2", "");
        new.add_pbl(make_pbl("a.pbl", 5));

        let diff = new.compare(&old);
        assert_eq!(diff.removed.len(), 1);
        assert!(diff.removed[0].contains("b.pbl"));
    }

    #[test]
    fn compare_detects_modified_entry_count() {
        let mut old = ProjectSnapshot::new("/p", "v1", "");
        old.add_pbl(make_pbl("a.pbl", 5));

        let mut new = ProjectSnapshot::new("/p", "v2", "");
        new.add_pbl(make_pbl("a.pbl", 10));

        let diff = new.compare(&old);
        assert_eq!(diff.changes.len(), 1);
        assert_eq!(diff.changes[0].change_type, "modified");
    }

    #[test]
    fn compare_no_changes() {
        let mut old = ProjectSnapshot::new("/p", "v1", "");
        old.add_pbl(make_pbl("a.pbl", 5));

        let mut new = ProjectSnapshot::new("/p", "v2", "");
        new.add_pbl(make_pbl("a.pbl", 5));

        let diff = new.compare(&old);
        assert!(diff.changes.is_empty());
        assert!(diff.added.is_empty());
        assert!(diff.removed.is_empty());
    }

    #[test]
    fn compare_object_count_delta() {
        let mut old = ProjectSnapshot::new("/p", "v1", "");
        old.add_pbl(make_pbl("a.pbl", 10));

        let mut new = ProjectSnapshot::new("/p", "v2", "");
        new.add_pbl(make_pbl("a.pbl", 15));
        new.add_pbl(make_pbl("b.pbl", 5));

        let diff = new.compare(&old);
        assert_eq!(diff.object_count_delta, 10); // 20 - 10
    }

    // ─── SnapshotDiff ───

    #[test]
    fn diff_summary_format() {
        let diff = SnapshotDiff {
            snapshot_id: "s1".into(),
            compared_to: "s2".into(),
            changes: vec![FileChange {
                path: "a.pbl".into(),
                change_type: "modified".into(),
                old_value: Some(5),
                new_value: Some(10),
            }],
            added: vec!["b.pbl".into()],
            removed: vec![],
            object_count_delta: 5,
        };
        let s = diff.summary();
        assert!(s.contains("+5"));
        assert!(s.contains("Changes: 1"));
        assert!(s.contains("Added: 1"));
        assert!(s.contains("Removed: 0"));
    }

    #[test]
    fn diff_has_changes_true() {
        let diff = SnapshotDiff {
            snapshot_id: "s1".into(),
            compared_to: "s2".into(),
            changes: vec![],
            added: vec!["x".into()],
            removed: vec![],
            object_count_delta: 0,
        };
        assert!(diff.has_changes());
    }

    #[test]
    fn diff_has_changes_false() {
        let diff = SnapshotDiff {
            snapshot_id: "s1".into(),
            compared_to: "s2".into(),
            changes: vec![],
            added: vec![],
            removed: vec![],
            object_count_delta: 0,
        };
        assert!(!diff.has_changes());
    }

    // ─── SnapshotManager ───

    #[test]
    fn manager_list_empty() {
        let tmp = TempDir::new().unwrap();
        let mgr = SnapshotManager::new(tmp.path().to_str().unwrap());
        let snaps = mgr.list_snapshots().unwrap();
        assert!(snaps.is_empty());
    }

    #[test]
    fn manager_save_and_list() {
        let tmp = TempDir::new().unwrap();
        // SnapshotManager looks in {root}/.pbdevkit/snapshots/
        let snap_dir = tmp.path().join(".pbdevkit").join("snapshots");
        let snap = ProjectSnapshot::new("/p", "v1", "desc");
        snap.save(snap_dir.to_str().unwrap()).unwrap();

        let mgr = SnapshotManager::new(tmp.path().to_str().unwrap());
        let snaps = mgr.list_snapshots().unwrap();
        assert!(!snaps.is_empty());
    }

    #[test]
    fn manager_delete_nonexistent_returns_err() {
        let tmp = TempDir::new().unwrap();
        let mgr = SnapshotManager::new(tmp.path().to_str().unwrap());
        let result = mgr.delete_snapshot("nonexistent");
        assert!(result.is_err());
    }
}