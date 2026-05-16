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
                removed.push(path.to_string());
            }
        }

        // Find added
        for (path, _pbl) in &other_map {
            if !self_map.contains_key(path) {
                added.push(path.to_string());
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
            "Objects: {} ({}), Changes: {}, Added: {}, Removed: {}",
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
        snapshots.sort_by(|a, b| b.created_at.cmp(&a.created_at));

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