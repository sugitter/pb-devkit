// Search Cache - Search result caching mechanism
// v2.1+: Supports cache invalidation, TTL, LRU eviction

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH, Duration};
use serde::{Deserialize, Serialize};

/// Cache entry for a single search query
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheEntry {
    pub query: String,
    pub root_path: String,
    pub case_sensitive: bool,
    pub file_types: Vec<String>,
    pub result_json: String,
    pub created_at: u64,
    pub expires_at: u64,
    pub hit_count: u32,
}

/// Search result cache with TTL and LRU eviction
#[derive(Debug)]
pub struct SearchCache {
    entries: HashMap<String, CacheEntry>,
    max_entries: usize,
    ttl_seconds: u64,
}

impl SearchCache {
    /// Create a new cache with specified capacity and TTL
    pub fn new(max_entries: usize, ttl_seconds: u64) -> Self {
        SearchCache {
            entries: HashMap::new(),
            max_entries,
            ttl_seconds,
        }
    }
    
    /// Generate cache key from search parameters
    fn make_key(query: &str, root_path: &str, case_sensitive: bool, file_types: &[String]) -> String {
        let mut key = format!("{}|{}|{}", query, root_path, case_sensitive);
        if !file_types.is_empty() {
            key.push_str("|");
            key.push_str(&file_types.join(","));
        }
        // Simple hash for key (not cryptographic, just for mapping)
        let mut hash: u64 = 2166136261;
        for byte in key.bytes() {
            hash = hash.wrapping_mul(16777619);
            hash ^= byte as u64;
        }
        format!("{:x}", hash)
    }
    
    /// Get a cached result if valid
    pub fn get(&mut self, query: &str, root_path: &str, case_sensitive: bool, file_types: &[String]) -> Option<String> {
        let key = Self::make_key(query, root_path, case_sensitive, file_types);
        
        if let Some(entry) = self.entries.get_mut(&key) {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            
            // Check if expired
            if now > entry.expires_at {
                self.entries.remove(&key);
                return None;
            }
            
            // Update hit count
            entry.hit_count += 1;
            
            // Return JSON result
            return Some(entry.result_json.clone());
        }
        
        None
    }
    
    /// Store a search result in cache
    pub fn put(&mut self, query: &str, root_path: &str, case_sensitive: bool, file_types: &[String], result_json: &str) {
        let key = Self::make_key(query, root_path, case_sensitive, file_types);
        
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        // Evict if at capacity (LRU - remove lowest hit count)
        if self.entries.len() >= self.max_entries {
            if let Some((min_key, _)) = self.entries.iter()
                .min_by_key(|(_, e)| e.hit_count)
                .map(|(k, v)| (k.clone(), v.hit_count))
            {
                self.entries.remove(&min_key);
            }
        }
        
        self.entries.insert(key, CacheEntry {
            query: query.to_string(),
            root_path: root_path.to_string(),
            case_sensitive,
            file_types: file_types.to_vec(),
            result_json: result_json.to_string(),
            created_at: now,
            expires_at: now + self.ttl_seconds,
            hit_count: 0,
        });
    }
    
    /// Invalidate cache entries for a specific path
    pub fn invalidate_path(&mut self, root_path: &str) {
        let keys_to_remove: Vec<_> = self.entries.iter()
            .filter(|(_, e)| e.root_path == root_path)
            .map(|(k, _)| k.clone())
            .collect();
        
        for key in keys_to_remove {
            self.entries.remove(&key);
        }
    }
    
    /// Invalidate all cache entries
    pub fn clear(&mut self) {
        self.entries.clear();
    }
    
    /// Get cache statistics
    pub fn stats(&self) -> CacheStats {
        let total_hits: u32 = self.entries.values().map(|e| e.hit_count).sum();
        
        CacheStats {
            entry_count: self.entries.len(),
            max_entries: self.max_entries,
            total_hits,
            hit_rate: if total_hits > 0 { 
                (total_hits as f64 / self.entries.len() as f64).min(1.0) 
            } else { 0.0 },
        }
    }
    
    /// Clean up expired entries
    pub fn cleanup(&mut self) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        
        let keys_to_remove: Vec<_> = self.entries.iter()
            .filter(|(_, e)| now > e.expires_at)
            .map(|(k, _)| k.clone())
            .collect();
        
        for key in keys_to_remove {
            self.entries.remove(&key);
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStats {
    pub entry_count: usize,
    pub max_entries: usize,
    pub total_hits: u32,
    pub hit_rate: f64,
}

/// Global cache instance (lazy initialized)
use std::sync::Mutex;
use once_cell::sync::Lazy;

static SEARCH_CACHE: Lazy<Mutex<SearchCache>> = Lazy::new(|| {
    Mutex::new(SearchCache::new(100, 3600)) // 100 entries, 1 hour TTL
});

/// Get cached search results
pub fn get_cached_search(query: &str, root_path: &str, case_sensitive: bool, file_types: &[String]) -> Option<String> {
    let mut cache = SEARCH_CACHE.lock().ok()?;
    cache.get(query, root_path, case_sensitive, file_types)
}

/// Cache search results
pub fn cache_search(query: &str, root_path: &str, case_sensitive: bool, file_types: &[String], result_json: &str) {
    if let Ok(mut cache) = SEARCH_CACHE.lock() {
        cache.put(query, root_path, case_sensitive, file_types, result_json);
    }
}

/// Invalidate cache for a path
pub fn invalidate_path(root_path: &str) {
    if let Ok(mut cache) = SEARCH_CACHE.lock() {
        cache.invalidate_path(root_path);
    }
}

/// Clear all cache
pub fn clear_cache() {
    if let Ok(mut cache) = SEARCH_CACHE.lock() {
        cache.clear();
    }
}

/// Get cache statistics
pub fn get_cache_stats() -> Option<CacheStats> {
    SEARCH_CACHE.lock().ok().map(|c| c.stats())
}