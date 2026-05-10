// PBL Service - Tauri backend communication
import { Injectable } from '@angular/core';
import { invoke } from '@tauri-apps/api/core';

export interface PblEntry {
  name: string;
  entry_type: number;
  entry_type_name: string;
  size: number;
  modified?: string;
  is_source: boolean;
  is_compiled: boolean;
  version: string;
}

export interface ParseResult {
  success: boolean;
  entries: PblEntry[];
  is_unicode: boolean;
  pb_version: string;
  total_count: number;
  source_count: number;
  compiled_count: number;
  error?: string;
}

export interface PblInfo {
  path: string;
  is_unicode: boolean;
  pb_version: string;
  total_entries: number;
  source_entries: number;
  compiled_entries: number;
  file_size: number;
}

export interface ProjectInfo {
  name: string;
  path: string;
  pbl_files: PblFileInfo[];
  pbt_files: string[];
  pbw_files: string[];
  exe_files: string[];
  is_valid: boolean;
}

export interface PblFileInfo {
  path: string;
  name: string;
  size: number;
  entry_count?: number;
  is_unicode: boolean;
}

export interface SearchResult {
  file: string;
  line_number: number;
  line_content: string;
  match_start: number;
  match_length: number;
}

export interface SearchResults {
  query: string;
  matches: SearchResult[];
  files_count: number;
  total_matches: number;
}

export interface DwInfo {
  name: string;
  path: string;
  sql?: string;
  tables: string[];
  columns: string[];
  style?: string;
}

export interface DwAnalysisResult {
  datawindows: DwInfo[];
  total_count: number;
  tables_found: string[];
}

export interface DecompileEntry {
  name: string;
  entry_type: string;
  size: number;
  is_source: boolean;
}

export interface FileTypeResult {
  file_type: string;
  is_pb_exe: boolean;
  version?: string;
  size: number;
}

export interface PeInfoResult {
  is_pb_exe: boolean;
  is_64bit: boolean;
  machine_type: string;
  timestamp?: string | null;
  embedded_pbl_count: number;
  resources: ResourceInfo[];
}

export interface ResourceInfo {
  name: string;
  offset: number;
  size: number;
  resource_type: string;
}

// ──── Doctor 接口 ────

export interface DoctorResult {
  success: boolean;
  python_version: string | null;
  rust_available: boolean;
  orca_dll_found: boolean;
  issues: string[];
  warnings: string[];
}

// ──── Report 接口 ────

export interface ReportSummary {
  total_pbl_files: number;
  total_pbd_files: number;
  total_exe_files: number;
  total_objects: number;
  source_objects: number;
  compiled_objects: number;
  unicode_pbls: number;
  ansi_pbls: number;
}

export interface PblFileReport {
  path: string;
  name: string;
  size_bytes: number;
  is_unicode: boolean;
  pb_version: string;
  total_entries: number;
  source_entries: number;
  compiled_entries: number;
  object_types: Record<string, number>;
}

export interface FileStats {
  total_size_bytes: number;
  largest_file: [string, number] | null;
  smallest_file: [string, number] | null;
  average_size_bytes: number;
}

export interface ProjectReport {
  project_name: string;
  project_path: string;
  generated_at: string;
  summary: ReportSummary;
  pbl_files: PblFileReport[];
  object_stats: {
    by_type: Record<string, number>;
    top_types: [string, number][];
  };
  file_stats: FileStats;
}

@Injectable({ providedIn: 'root' })
export class PblService {

  // ──── PBL 命令 ────

  parsePbl(path: string): Promise<ParseResult> {
    return invoke<ParseResult>('parse_pbl', { path });
  }

  getPblInfo(path: string): Promise<PblInfo> {
    return invoke<PblInfo>('get_pbl_info', { path });
  }

  listEntries(path: string): Promise<PblEntry[]> {
    return invoke<PblEntry[]>('list_entries', { path });
  }

  async exportEntry(pblPath: string, entryName: string): Promise<string> {
    const r = await invoke<{ success: boolean; source?: string; error?: string }>(
      'export_entry', { pblPath, entryName }
    );
    if (r.success && r.source) return r.source;
    throw new Error(r.error ?? 'Export failed');
  }

  exportPbl(pblPath: string, outputDir: string, byType: boolean): Promise<string> {
    return invoke<string>('export_pbl', { pblPath, outputDir, byType });
  }

  // ──── PE 命令 ────

  detectFileType(path: string): Promise<FileTypeResult> {
    return invoke<FileTypeResult>('detect_file_type', { path });
  }

  extractPbdFromExe(exePath: string, outputDir: string) {
    return invoke<{ success: boolean; pbd_count: number; output_path?: string; error?: string }>(
      'extract_pbd_from_exe', { exePath, outputDir }
    );
  }

  // ──── PE 分析命令 ────
  analyzePe(path: string): Promise<PeInfoResult> {
    return invoke<PeInfoResult>('analyze_pe', { path });
  }

  // ──── 项目命令 ────

  detectProject(path: string): Promise<ProjectInfo> {
    return invoke<ProjectInfo>('detect_project', { path });
  }

  findPblFiles(rootPath: string): Promise<PblFileInfo[]> {
    return invoke<PblFileInfo[]>('find_pbl_files', { rootPath });
  }

  runDoctor(): Promise<DoctorResult> {
    return invoke<DoctorResult>('run_doctor');
  }

  // ──── 搜索命令 ────

  searchInFiles(rootPath: string, query: string, caseSensitive: boolean, fileTypes: string[]): Promise<SearchResults> {
    return invoke<SearchResults>('search_in_files', { rootPath, query, caseSensitive, fileTypes });
  }

  searchByType(rootPath: string, objectType: string): Promise<string[]> {
    return invoke<string[]>('search_by_type', { rootPath, objectType });
  }

  // ──── DataWindow 命令 ────

  analyzeDatawindows(rootPath: string): Promise<DwAnalysisResult> {
    return invoke<DwAnalysisResult>('analyze_datawindows', { rootPath });
  }

  getDwSql(dwPath: string): Promise<string> {
    return invoke<string>('get_dw_sql', { dwPath });
  }

  // ──── 反编译命令 ────

  listDecompileEntries(path: string) {
    return invoke<{ success: boolean; entries: DecompileEntry[]; total_count: number; source_count: number; error?: string }>(
      'list_decompile_entries', { path }
    );
  }

  decompileEntry(pbdPath: string, entryName: string) {
    return invoke<{ success: boolean; name: string; source?: string; size: number; error?: string }>(
      'decompile_entry', { pbdPath, entryName }
    );
  }

  decompileAll(pbdPath: string, outputDir: string): Promise<string> {
    return invoke<string>('decompile_all', { pbdPath, outputDir });
  }

  // ──── 报告命令 ────

  generateReport(projectPath: string): Promise<ProjectReport> {
    return invoke<ProjectReport>('generate_report', { projectPath });
  }

  exportReport(projectPath: string, outputPath: string): Promise<string> {
    return invoke<string>('export_report', { projectPath, outputPath });
  }
}
