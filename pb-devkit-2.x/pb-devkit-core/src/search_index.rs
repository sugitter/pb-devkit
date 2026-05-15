// Search Index - Index file mechanism for faster repeated searches
// v2.1+: Supports incremental search, cache, .idx file generation

use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};

/// Search index entry for a single file
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct IndexEntry {
    pub path: String,
    pub modified: u64,        // File modification timestamp
    pub size: u64,            // File size
    pub line_count: usize,   // Number of lines
    pub checksum: u64,       // Simple content checksum
}

/// Search index for a directory tree
#[derive(Debug, Serialize, Deserialize)]
pub struct SearchIndex {
    pub root_path: String,
    pub created_at: u64,
    pub updated_at: u64,
    pub version: String,
    pub entries: Vec<IndexEntry>,
}

impl SearchIndex {
    /// Create a new index for a directory
    pub fn new(root_path: &str) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        SearchIndex {
            root_path: root_path.to_string(),
            created_at: now,
            updated_at: now,
            version: "1.0".to_string(),
            entries: Vec::new(),
        }
    }

    /// Build index from directory (collects all source files)
    pub fn build(&mut self, root_path: &str, file_types: &[&str]) -> usize {
        let root = Path::new(root_path);
        self.entries.clear();
        
        let mut count = 0;
        self.collect_files(root, file_types, &mut count);
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        self.updated_at = now;
        
        count
    }

    fn collect_files(&mut self, dir: &Path, file_types: &[&str], count: &mut usize) {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();

                if path.is_dir() {
                    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                        if !name.starts_with('.') && name != "node_modules" && name != "target" {
                            self.collect_files(&path, file_types, count);
                        }
                    }
                } else if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                    let ext_with_dot = format!(".{}", ext.to_lowercase());
                    if file_types.iter().any(|t| t.to_lowercase() == ext_with_dot) {
                        if let Ok(metadata) = fs::metadata(&path) {
                            let modified = metadata.modified()
                                .ok()
                                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                                .map(|d| d.as_secs())
                                .unwrap_or(0);

                            let size = metadata.len();
                            let (line_count, checksum) = self.compute_file_info(&path);

                            self.entries.push(IndexEntry {
                                path: path.to_string_lossy().to_string(),
                                modified,
                                size,
                                line_count,
                                checksum,
                            });
                            *count += 1;
                        }
                    }
                }
            }
        }
    }

    /// Compute line count and simple checksum for a file
    fn compute_file_info(&self, path: &Path) -> (usize, u64) {
        if let Ok(mut file) = File::open(path) {
            let mut content = String::new();
            if file.read_to_string(&mut content).is_ok() {
                let line_count = content.lines().count();
                // Simple FNV-like checksum
                let mut checksum: u64 = 2166136261;
                for byte in content.bytes() {
                    checksum = checksum.wrapping_mul(16777619);
                    checksum ^= byte as u64;
                }
                return (line_count, checksum);
            }
        }
        (0, 0)
    }

    /// Find files that have changed since last index
    pub fn find_changed_files(&self, current_index: &SearchIndex) -> Vec<String> {
        let mut changed = Vec::new();
        
        // Create a map of current entries by path
        let current_map: HashMap<&str, &IndexEntry> = current_index.entries
            .iter()
            .map(|e| (e.path.as_str(), e))
            .collect();

        for old_entry in &self.entries {
            if let Some(current_entry) = current_map.get(old_entry.path.as_str()) {
                // Check if file changed
                if current_entry.modified != old_entry.modified 
                    || current_entry.size != old_entry.size
                    || current_entry.checksum != old_entry.checksum {
                    changed.push(old_entry.path.clone());
                }
            } else {
                // File was removed
                changed.push(old_entry.path.clone());
            }
        }

        // Check for new files
        let old_paths: std::collections::HashSet<_> = self.entries
            .iter()
            .map(|e| e.path.as_str())
            .collect();
        
        for new_entry in &current_index.entries {
            if !old_paths.contains(new_entry.path.as_str()) {
                changed.push(new_entry.path.clone());
            }
        }

        changed
    }

    /// Save index to .idx file
    pub fn save(&self, path: &str) -> Result<(), String> {
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| e.to_string())?;
        
        fs::write(path, json)
            .map_err(|e| e.to_string())
    }

    /// Load index from .idx file
    pub fn load(path: &str) -> Result<Self, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| e.to_string())?;
        
        serde_json::from_str(&content)
            .map_err(|e| e.to_string())
    }

    /// Get the .idx file path for a directory
    pub fn idx_file_path(root_path: &str) -> String {
        format!("{}/.pbdevkit.idx", root_path)
    }

    /// Check if index exists and is valid for a directory
    pub fn is_valid_for(root_path: &str) -> bool {
        let idx_path = Self::idx_file_path(root_path);
        if !Path::new(&idx_path).exists() {
            return false;
        }

        if let Ok(index) = Self::load(&idx_path) {
            // Check if index is for the same path
            index.root_path == root_path
        } else {
            false
        }
    }
}

/// Load or create index for a directory
pub fn get_or_create_index(root_path: &str, file_types: &[&str]) -> SearchIndex {
    let idx_path = SearchIndex::idx_file_path(root_path);
    
    if let Ok(index) = SearchIndex::load(&idx_path) {
        // Try to do incremental update
        let mut current_index = SearchIndex::new(root_path);
        current_index.build(root_path, file_types);
        
        let changed = index.find_changed_files(&current_index);
        
        if changed.is_empty() {
            // No changes, return cached index
            return index;
        }
        
        // Some files changed, rebuild
        let mut new_index = SearchIndex::new(root_path);
        new_index.build(root_path, file_types);
        
        // Save updated index
        let _ = new_index.save(&idx_path);
        
        new_index
    } else {
        // No index exists, create new one
        let mut index = SearchIndex::new(root_path);
        index.build(root_path, file_types);
        
        // Save index
        let _ = index.save(&idx_path);
        
        index
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_index_creation() {
        let index = SearchIndex::new("/test/path");
        assert_eq!(index.root_path, "/test/path");
        assert_eq!(index.entries.len(), 0);
    }
}