// Search Cache - Search result caching mechanism
// v2.1+: Supports cache invalidation, TTL, LRU eviction

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
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
            if now >= entry.expires_at {
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
            .filter(|(_, e)| now >= e.expires_at)
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

#[cfg(test)]
mod tests {
    use super::*;

    // ─── helper ───

    fn sample_types() -> Vec<String> {
        vec!["sr".to_string(), "srw".to_string()]
    }

    // ─── make_key ───

    #[test]
    fn make_key_deterministic() {
        let k1 = SearchCache::make_key("dw_users", "/proj", false, &[]);
        let k2 = SearchCache::make_key("dw_users", "/proj", false, &[]);
        assert_eq!(k1, k2);
    }

    #[test]
    fn make_key_case_sensitive_differs() {
        let k1 = SearchCache::make_key("dw_users", "/proj", false, &[]);
        let k2 = SearchCache::make_key("dw_users", "/proj", true, &[]);
        assert_ne!(k1, k2);
    }

    #[test]
    fn make_key_file_types_affect() {
        let k1 = SearchCache::make_key("x", "/p", false, &[]);
        let k2 = SearchCache::make_key("x", "/p", false, &sample_types());
        assert_ne!(k1, k2);
    }

    #[test]
    fn make_key_different_queries_differ() {
        let k1 = SearchCache::make_key("a", "/p", false, &[]);
        let k2 = SearchCache::make_key("b", "/p", false, &[]);
        assert_ne!(k1, k2);
    }

    // ─── put / get ───

    #[test]
    fn get_miss_returns_none() {
        let mut cache = SearchCache::new(10, 3600);
        let result = cache.get("q", "/p", false, &[]);
        assert!(result.is_none());
    }

    #[test]
    fn put_and_get_roundtrip() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q", "/p", false, &[], r#"{"hits":3}"#);
        let result = cache.get("q", "/p", false, &[]);
        assert_eq!(result, Some(r#"{"hits":3}"#.to_string()));
    }

    #[test]
    fn get_increments_hit_count() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q", "/p", false, &[], "x");
        cache.get("q", "/p", false, &[]); // hit 1
        cache.get("q", "/p", false, &[]); // hit 2
        let stats = cache.stats();
        assert_eq!(stats.total_hits, 2);
    }

    #[test]
    fn case_sensitive_isolation() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q", "/p", false, &[], "insensitive");
        cache.put("q", "/p", true, &[], "sensitive");
        assert_eq!(cache.get("q", "/p", false, &[]), Some("insensitive".to_string()));
        assert_eq!(cache.get("q", "/p", true, &[]), Some("sensitive".to_string()));
    }

    // ─── TTL expiry ───

    #[test]
    fn get_returns_none_after_ttl_expiry() {
        let mut cache = SearchCache::new(10, 0); // TTL = 0 → expires immediately
        cache.put("q", "/p", false, &[], "x");
        // TTL 0 means expires_at <= now, so get should return None
        let result = cache.get("q", "/p", false, &[]);
        assert!(result.is_none());
    }

    // ─── LRU eviction ───

    #[test]
    fn lru_evicts_lowest_hit_count() {
        let mut cache = SearchCache::new(2, 3600);
        cache.put("a", "/p", false, &[], "a");
        cache.put("b", "/p", false, &[], "b");
        // hit "a" once
        cache.get("a", "/p", false, &[]);
        // put "c" → should evict "b" (hit_count=0 < 1)
        cache.put("c", "/p", false, &[], "c");
        assert_eq!(cache.get("a", "/p", false, &[]), Some("a".to_string()));
        assert_eq!(cache.get("c", "/p", false, &[],), Some("c".to_string()));
        assert!(cache.get("b", "/p", false, &[]).is_none());
    }

    #[test]
    fn lru_evicts_when_at_capacity() {
        let mut cache = SearchCache::new(3, 3600);
        cache.put("a", "/p", false, &[], "a");
        cache.put("b", "/p", false, &[], "b");
        cache.put("c", "/p", false, &[], "c");
        cache.put("d", "/p", false, &[], "d"); // should evict one
        let stats = cache.stats();
        assert!(stats.entry_count <= 3);
    }

    // ─── invalidate_path ───

    #[test]
    fn invalidate_path_removes_matching_entries() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q", "/proj_a", false, &[], "a");
        cache.put("q", "/proj_b", false, &[], "b");
        cache.invalidate_path("/proj_a");
        assert!(cache.get("q", "/proj_a", false, &[]).is_none());
        assert!(cache.get("q", "/proj_b", false, &[]).is_some());
    }

    // ─── clear ───

    #[test]
    fn clear_removes_all_entries() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q1", "/p", false, &[], "x");
        cache.put("q2", "/p", false, &[], "y");
        cache.clear();
        let stats = cache.stats();
        assert_eq!(stats.entry_count, 0);
        assert!(cache.get("q1", "/p", false, &[],).is_none());
    }

    // ─── stats ───

    #[test]
    fn stats_reflects_current_state() {
        let mut cache = SearchCache::new(10, 3600);
        let stats = cache.stats();
        assert_eq!(stats.entry_count, 0);
        assert_eq!(stats.max_entries, 10);

        cache.put("q", "/p", false, &[], "x");
        let stats = cache.stats();
        assert_eq!(stats.entry_count, 1);
    }

    // ─── cleanup ───

    #[test]
    fn cleanup_removes_expired_entries() {
        let mut cache = SearchCache::new(10, 0); // TTL=0
        cache.put("q", "/p", false, &[], "x");
        assert!(cache.stats().entry_count == 1);
        cache.cleanup();
        assert_eq!(cache.stats().entry_count, 0);
    }

    #[test]
    fn cleanup_keeps_valid_entries() {
        let mut cache = SearchCache::new(10, 3600);
        cache.put("q", "/p", false, &[], "x");
        cache.cleanup();
        assert_eq!(cache.stats().entry_count, 1);
    }

    // ─── global static cache ───

    #[test]
    fn global_cache_put_and_get() {
        clear_cache();
        cache_search("test_q", "/tmp", false, &[], r#"{"ok":true}"#);
        let result = get_cached_search("test_q", "/tmp", false, &[]);
        assert_eq!(result, Some(r#"{"ok":true}"#.to_string()));
    }

    #[test]
    fn global_cache_get_stats_works() {
        clear_cache();
        cache_search("stats_q", "/tmp", false, &[], "x");
        let stats = get_cache_stats();
        assert!(stats.is_some());
        assert!(stats.unwrap().entry_count >= 1);
    }

    #[test]
    fn global_invalidate_path_works() {
        clear_cache();
        cache_search("q", "/tmp/a", false, &[], "a");
        cache_search("q", "/tmp/b", false, &[], "b");
        invalidate_path("/tmp/a");
        assert!(get_cached_search("q", "/tmp/a", false, &[]).is_none());
        assert!(get_cached_search("q", "/tmp/b", false, &[]).is_some());
    }

    #[test]
    fn global_clear_cache_works() {
        clear_cache();
        cache_search("q", "/tmp", false, &[], "x");
        clear_cache();
        assert!(get_cached_search("q", "/tmp", false, &[]).is_none());
    }
}

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