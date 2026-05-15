// Shared type definitions for PB DevKit

use serde::{Deserialize, Serialize};

// ─── PBL Types ───

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PblEntryInfo {
    pub name: String,
    pub entry_type: u8,
    pub entry_type_name: String,
    pub size: u64,
    pub modified: Option<String>,
    pub is_source: bool,
    pub is_compiled: bool,
    pub version: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PblInfo {
    pub path: String,
    pub is_unicode: bool,
    pub pb_version: String,
    pub total_entries: usize,
    pub source_entries: usize,
    pub compiled_entries: usize,
    pub file_size: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ExportResult {
    pub success: bool,
    pub name: String,
    pub source: Option<String>,
    pub size: usize,
    pub error: Option<String>,
}

// ─── PE Types ───

#[derive(Debug, Serialize, Deserialize)]
pub struct PeInfoResult {
    pub is_pb_exe: bool,
    pub is_64bit: bool,
    pub machine_type: String,
    pub timestamp: Option<String>,
    pub embedded_pbl_count: usize,
    pub resources: Vec<ResourceInfo>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ResourceInfo {
    pub name: String,
    pub offset: u64,
    pub size: u64,
    pub resource_type: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileTypeResult {
    pub file_type: String,
    pub is_pb_exe: bool,
    pub version: Option<String>,
    pub size: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ExtractResult {
    pub success: bool,
    pub pbd_count: usize,
    pub output_path: Option<String>,
    pub error: Option<String>,
}

// ─── Project Types ───

#[derive(Debug, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub name: String,
    pub path: String,
    pub pbl_files: Vec<PblFileInfo>,
    pub pbt_files: Vec<String>,
    pub pbw_files: Vec<String>,
    pub exe_files: Vec<String>,
    pub is_valid: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PblFileInfo {
    pub path: String,
    pub name: String,
    pub size: u64,
    pub entry_count: Option<usize>,
    pub is_unicode: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DoctorResult {
    pub success: bool,
    pub python_version: Option<String>,
    pub rust_available: bool,
    pub orca_dll_found: bool,
    pub issues: Vec<String>,
    pub warnings: Vec<String>,
}

// ─── Search Types ───

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SearchResult {
    pub file: String,
    pub line_number: usize,
    pub line_content: String,
    pub match_start: usize,
    pub match_length: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchResults {
    pub query: String,
    pub matches: Vec<SearchResult>,
    pub files_count: usize,
    pub total_matches: usize,
}

// ─── DataWindow Types ───

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DwInfo {
    pub name: String,
    pub path: String,
    pub sql: Option<String>,
    pub tables: Vec<String>,
    pub columns: Vec<String>,
    pub style: Option<String>,
    // Enhanced SQL parsing (v2.1+)
    pub where_clause: Option<String>,
    pub order_by_clause: Option<String>,
    pub group_by_clause: Option<String>,
    pub arguments: Vec<DwArgument>,
    pub computed_columns: Vec<ComputedColumn>,
    pub has_union: bool,
    pub union_sql: Option<String>,
    pub subqueries: Vec<SubQuery>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DwArgument {
    pub name: String,
    pub data_type: Option<String>,
    pub initial_value: Option<String>,
    pub description: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ComputedColumn {
    pub name: String,
    pub expression: String,
    pub data_type: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SubQuery {
    pub alias: Option<String>,
    pub sql: String,
    pub query_type: String, // "scalar", "exists", "in", "comparison"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DwAnalysisResult {
    pub datawindows: Vec<DwInfo>,
    pub total_count: usize,
    pub tables_found: Vec<String>,
}

// ─── Decompile Types ───

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DecompileEntry {
    pub name: String,
    pub entry_type: String,
    pub size: u64,
    pub is_source: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DecompileListResult {
    pub success: bool,
    pub entries: Vec<DecompileEntry>,
    pub total_count: usize,
    pub source_count: usize,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DecompileResult {
    pub success: bool,
    pub name: String,
    pub source: Option<String>,
    pub size: usize,
    pub error: Option<String>,
}

// ─── Report Types ───

#[derive(Debug, Serialize, Deserialize)]
pub struct ProjectReport {
    pub project_name: String,
    pub project_path: String,
    pub generated_at: String,
    pub summary: ReportSummary,
    pub pbl_files: Vec<PblFileReport>,
    pub object_stats: ObjectStats,
    pub file_stats: FileStats,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReportSummary {
    pub total_pbl_files: usize,
    pub total_pbd_files: usize,
    pub total_exe_files: usize,
    pub total_objects: usize,
    pub source_objects: usize,
    pub compiled_objects: usize,
    pub unicode_pbls: usize,
    pub ansi_pbls: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PblFileReport {
    pub path: String,
    pub name: String,
    pub size_bytes: u64,
    pub is_unicode: bool,
    pub pb_version: String,
    pub total_entries: usize,
    pub source_entries: usize,
    pub compiled_entries: usize,
    pub object_types: std::collections::HashMap<String, usize>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ObjectStats {
    pub by_type: std::collections::HashMap<String, usize>,
    pub top_types: Vec<(String, usize)>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileStats {
    pub total_size_bytes: u64,
    pub largest_file: Option<(String, u64)>,
    pub smallest_file: Option<(String, u64)>,
    pub average_size_bytes: u64,
}
