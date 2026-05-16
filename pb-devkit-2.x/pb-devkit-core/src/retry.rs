// Retry - Export retry mechanism with exponential backoff
// v2.1+: Support automatic retry for failed exports

use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};

/// Configuration for retry behavior
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryConfig {
    pub max_retries: u32,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        RetryConfig {
            max_retries: 3,
            initial_delay_ms: 100,
            max_delay_ms: 5000,
            backoff_multiplier: 2.0,
        }
    }
}

/// Result of a retry operation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryResult<T> {
    pub success: bool,
    pub value: Option<T>,
    pub error: Option<String>,
    pub attempts: u32,
    pub total_time_ms: u64,
}

/// Retry utility with exponential backoff
pub struct Retry<T> {
    config: RetryConfig,
    _phantom: std::marker::PhantomData<T>,
}

impl<T> Retry<T> {
    pub fn new(config: RetryConfig) -> Self {
        Retry {
            config,
            _phantom: std::marker::PhantomData,
        }
    }

    /// Execute an operation with retry logic
    pub fn execute<F>(&self, mut operation: F) -> RetryResult<T>
    where
        F: FnMut() -> Result<T, String>,
    {
        let start = Instant::now();
        let mut attempts = 0;
        let mut delay = self.config.initial_delay_ms;

        loop {
            attempts += 1;

            match operation() {
                Ok(value) => {
                    let elapsed = start.elapsed().as_millis() as u64;
                    return RetryResult {
                        success: true,
                        value: Some(value),
                        error: None,
                        attempts,
                        total_time_ms: elapsed,
                    };
                }
                Err(e) => {
                    // Check if we should retry
                    if attempts >= self.config.max_retries {
                        let elapsed = start.elapsed().as_millis() as u64;
                        return RetryResult {
                            success: false,
                            value: None,
                            error: Some(format!("{} (attempts: {})", e, attempts)),
                            attempts,
                            total_time_ms: elapsed,
                        };
                    }

                    // Wait before retry with exponential backoff
                    std::thread::sleep(Duration::from_millis(delay));

                    // Calculate next delay
                    delay = ((delay as f64) * self.config.backoff_multiplier) as u64;
                    delay = delay.min(self.config.max_delay_ms);
                }
            }
        }
    }

    /// Execute with custom retry condition
    pub fn execute_with_condition<F, C>(&self, mut operation: F, mut should_retry: C) -> RetryResult<T>
    where
        F: FnMut() -> Result<T, String>,
        C: FnMut(&str) -> bool,
    {
        let start = Instant::now();
        let mut attempts = 0;
        let mut delay = self.config.initial_delay_ms;

        loop {
            attempts += 1;

            match operation() {
                Ok(value) => {
                    let elapsed = start.elapsed().as_millis() as u64;
                    return RetryResult {
                        success: true,
                        value: Some(value),
                        error: None,
                        attempts,
                        total_time_ms: elapsed,
                    };
                }
                Err(e) => {
                    // Check custom retry condition
                    if !should_retry(&e) || attempts >= self.config.max_retries {
                        let elapsed = start.elapsed().as_millis() as u64;
                        return RetryResult {
                            success: false,
                            value: None,
                            error: Some(format!("{} (attempts: {})", e, attempts)),
                            attempts,
                            total_time_ms: elapsed,
                        };
                    }

                    // Wait before retry
                    std::thread::sleep(Duration::from_millis(delay));

                    // Calculate next delay
                    delay = ((delay as f64) * self.config.backoff_multiplier) as u64;
                    delay = delay.min(self.config.max_delay_ms);
                }
            }
        }
    }
}

/// Batch export result with retry information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchExportResult {
    pub total: usize,
    pub successful: usize,
    pub failed: usize,
    pub failed_items: Vec<FailedExport>,
    pub total_time_ms: u64,
    pub retry_summary: String,
}

/// Information about a failed export
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FailedExport {
    pub name: String,
    pub error: String,
    pub attempts: u32,
}

/// Export with retry capability
pub fn export_with_retry<F>(
    items: &[String],
    mut export_fn: F,
    config: RetryConfig,
) -> BatchExportResult
where
    F: FnMut(&str) -> Result<String, String>,
{
    let start = Instant::now();
    let mut successful = 0;
    let mut failed = 0;
    let mut failed_items = Vec::new();

    for item in items {
        let retry = Retry::<String>::new(config.clone());
        let result = retry.execute(|| export_fn(item));

        if result.success {
            successful += 1;
        } else {
            failed += 1;
            failed_items.push(FailedExport {
                name: item.clone(),
                error: result.error.unwrap_or_else(|| "Unknown error".to_string()),
                attempts: result.attempts,
            });
        }
    }

    let elapsed = start.elapsed().as_millis() as u64;

    let retry_summary = format!(
        "Total: {}, Success: {}, Failed: {} (retries used: {} total attempts)",
        items.len(),
        successful,
        failed,
        failed_items.iter().map(|f| f.attempts).sum::<u32>()
    );

    BatchExportResult {
        total: items.len(),
        successful,
        failed,
        failed_items,
        total_time_ms: elapsed,
        retry_summary,
    }
}

/// Default retry config for file exports
pub fn default_export_retry_config() -> RetryConfig {
    RetryConfig {
        max_retries: 3,
        initial_delay_ms: 200,
        max_delay_ms: 3000,
        backoff_multiplier: 2.0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retry_success() {
        let retry = Retry::<i32>::new(RetryConfig::default());
        let result = retry.execute(|| Ok(42));
        
        assert!(result.success);
        assert_eq!(result.value, Some(42));
        assert_eq!(result.attempts, 1);
    }

    #[test]
    fn test_retry_failure() {
        let retry = Retry::<i32>::new(RetryConfig {
            max_retries: 2,
            initial_delay_ms: 10,
            max_delay_ms: 50,
            backoff_multiplier: 1.5,
        });
        
        let call_count = std::sync::Arc::new(std::sync::atomic::AtomicU32::new(0));
        let call_count_clone = call_count.clone();
        
        let result = retry.execute(move || {
            call_count_clone.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            Err("Test error".to_string())
        });
        
        assert!(!result.success);
        assert_eq!(result.attempts, 2);
    }
}