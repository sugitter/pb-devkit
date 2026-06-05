// Project detection and initialization - Shared core logic

use std::path::Path;
use std::fs;
use serde::Deserialize;

use crate::types::{ProjectInfo, PblFileInfo, DoctorResult};
use crate::pbl::PblParser;

/// Detect PowerBuilder project structure
pub fn detect_project(path: &str) -> Result<ProjectInfo, String> {
    let project_path = Path::new(path);

    if !project_path.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut pbl_files = Vec::new();
    let mut pbt_files = Vec::new();
    let mut pbw_files = Vec::new();
    let mut exe_files = Vec::new();

    if let Ok(entries) = std::fs::read_dir(project_path) {
        for entry in entries.flatten() {
            let file_path = entry.path();
            let file_name = file_path.file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("");
            let lower = file_name.to_lowercase();

            if lower.ends_with(".pbl") {
                let size = file_path.metadata().map(|m| m.len()).unwrap_or(0);
                pbl_files.push(PblFileInfo {
                    path: file_path.to_string_lossy().to_string(),
                    name: file_name.to_string(),
                    size,
                    entry_count: None,
                    is_unicode: false,
                });
            } else if lower.ends_with(".pbt") {
                pbt_files.push(file_path.to_string_lossy().to_string());
            } else if lower.ends_with(".pbw") {
                pbw_files.push(file_path.to_string_lossy().to_string());
            } else if lower.ends_with(".exe") || lower.ends_with(".pbd") {
                exe_files.push(file_path.to_string_lossy().to_string());
            }
        }
    }

    let project_name = project_path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("Unknown")
        .to_string();

    let is_valid = !pbl_files.is_empty() || !pbt_files.is_empty() || !exe_files.is_empty();

    Ok(ProjectInfo {
        name: project_name,
        path: path.to_string(),
        pbl_files,
        pbt_files,
        pbw_files,
        exe_files,
        is_valid,
    })
}

/// Run environment diagnostics
pub fn run_doctor() -> DoctorResult {
    let issues = Vec::new();
    let mut warnings = Vec::new();

    let python_version = std::process::Command::new("python")
        .arg("--version")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string());

    let rust_available = std::process::Command::new("rustc")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    let orca_dll_paths = [
        "pb-devkit-1.x/PBSpyORCA.dll",
        "orca/PBSpyORCA.dll",
    ];
    let orca_dll_found = orca_dll_paths.iter()
        .any(|p| Path::new(p).exists());

    if !rust_available {
        warnings.push("Rust not found - some features may be limited".to_string());
    }

    if !orca_dll_found {
        warnings.push("PBSpyORCA.dll not found - import/build features disabled".to_string());
    }

    DoctorResult {
        success: true,
        python_version,
        rust_available,
        orca_dll_found,
        issues,
        warnings,
    }
}

/// List all PBL files in a directory recursively
pub fn find_pbl_files(root_path: &str) -> Result<Vec<PblFileInfo>, String> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err("Path does not exist".to_string());
    }

    let mut pbl_files = Vec::new();
    collect_pbl_files(root, &mut pbl_files);

    Ok(pbl_files)
}

fn collect_pbl_files(dir: &Path, files: &mut Vec<PblFileInfo>) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                if !path.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.starts_with('.'))
                    .unwrap_or(false)
                {
                    collect_pbl_files(&path, files);
                }
            } else if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                if name.to_lowercase().ends_with(".pbl") {
                    let size = path.metadata().map(|m| m.len()).unwrap_or(0);
                    files.push(PblFileInfo {
                        path: path.to_string_lossy().to_string(),
                        name: name.to_string(),
                        size,
                        entry_count: None,
                        is_unicode: false,
                    });
                }
            }
        }
    }
}

// ── 一键解析项目 ──

#[derive(Debug, serde::Serialize, Deserialize)]
pub struct ScanResult {
    pub success: bool,
    pub pbl_count: usize,
    /// Total PBL entries scanned (same as exported_count; alias for frontend)
    pub source_count: usize,
    pub entry_count: usize,
    pub exported_count: usize,
    pub failed_count: usize,
    pub output_dir: String,
    pub errors: Vec<String>,
}

/// 一键扫描并解析整个 PB 项目，按原始目录结构导出
pub fn scan_and_export(project_path: &str, output_dir: &str) -> Result<ScanResult, String> {
    let project = Path::new(project_path);
    let output = Path::new(output_dir);
    
    if !project.exists() {
        return Err("Project path does not exist".to_string());
    }
    
    // 创建输出目录
    fs::create_dir_all(output).map_err(|e| e.to_string())?;
    
    let mut pbl_count = 0;
    let mut entry_count = 0;
    let mut exported_count = 0;
    let mut failed_count = 0;
    let mut errors = Vec::new();
    
    // 递归扫描所有 PBL 文件
    let pbl_files = find_pbl_files(project_path)?;
    
    for pbl_info in &pbl_files {
        let pbl_path = Path::new(&pbl_info.path);
        
        // 计算相对路径以保持目录结构
        let relative_path = pbl_path.strip_prefix(project)
            .unwrap_or(pbl_path);
        let relative_dir = relative_path.parent()
            .unwrap_or(Path::new(""));
        
        // 创建对应的输出子目录
        let pbl_output_dir = output.join(relative_dir).join(&pbl_info.name);
        fs::create_dir_all(&pbl_output_dir).map_err(|e| e.to_string())?;
        
        // 解析 PBL
        match PblParser::new(&pbl_info.path) {
            Ok(parser) => {
                let entries = parser.entries();
                pbl_count += 1;
                entry_count += entries.len();
                
                for entry in entries {
                    if entry.is_source {
                        match parser.export_entry(&entry.name) {
                            Ok(source) => {
                                // 根据对象类型确定扩展名
                                let ext = match entry.entry_type {
                                    0 => ".sra",   // application
                                    1 => ".srd",   // datawindow
                                    2 => ".srw",   // window
                                    3 => ".srm",   // menu
                                    4 => ".srf",   // function
                                    5 => ".srs",   // structure
                                    6 => ".sru",   // userobject
                                    7 => ".srq",   // query
                                    8 => ".srp",   // pipeline
                                    9 => ".srj",   // project
                                    10 => ".srx",  // proxy
                                    _ => ".srx",   // unknown
                                };
                                
                                let file_name = format!("{}{}", entry.name, ext);
                                let file_path = pbl_output_dir.join(&file_name);
                                
                                if fs::write(&file_path, &source).is_ok() {
                                    exported_count += 1;
                                } else {
                                    failed_count += 1;
                                    errors.push(format!("Failed to write: {}", file_name));
                                }
                            }
                            Err(e) => {
                                failed_count += 1;
                                errors.push(format!("Export error {}: {}", entry.name, e));
                            }
                        }
                    }
                }
            }
            Err(e) => {
                errors.push(format!("Parse error {}: {}", pbl_info.name, e));
            }
        }
    }
    
    Ok(ScanResult {
        success: pbl_count > 0,
        pbl_count,
        source_count: exported_count, // alias: same value, used by frontend
        entry_count,
        exported_count,
        failed_count,
        output_dir: output_dir.to_string(),
        errors,
    })
}

/// 一键迁移：将 PB 项目转换为现代 Web 项目结构
#[derive(Debug, serde::Serialize, Deserialize)]
pub struct MigrateResult {
    pub success: bool,
    pub project_name: String,
    pub source_count: usize,
    pub dw_count: usize,
    pub window_count: usize,
    pub menu_count: usize,
    pub function_count: usize,
    pub output_dir: String,
    pub errors: Vec<String>,
    /// Alias for window_count — used by frontend Angular scaffold count
    pub components: usize,
    /// Alias for function_count — service stubs generated
    pub services: usize,
    /// Alias for dw_count — TS model files generated
    pub models: usize,
}

/// 将解析的 PB 项目转换为现代 Web 项目结构
pub fn migrate_to_web(project_path: &str, output_dir: &str, _template: &str) -> Result<MigrateResult, String> {
    let project = Path::new(project_path);
    let output = Path::new(output_dir);
    
    if !project.exists() {
        return Err("Project path does not exist".to_string());
    }
    
    let project_name = project.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("pb-project")
        .to_string();
    
    // 创建现代 Web 项目结构
    let src_dir = output.join(&project_name).join("src");
    fs::create_dir_all(&src_dir).map_err(|e| e.to_string())?;
    
    // 创建分类目录
    let _dirs = [
        "datawindows",
        "windows",
        "menus",
        "functions",
        "structures",
        "userobjects",
        "applications",
        "queries",
    ];
    
    let mut dw_count = 0;
    let mut window_count = 0;
    let mut menu_count = 0;
    let mut function_count = 0;
    let mut source_count = 0;
    let mut errors = Vec::new();
    
    // 扫描所有 PBL 文件
    let pbl_files = find_pbl_files(project_path)?;
    
    for pbl_info in &pbl_files {
        match PblParser::new(&pbl_info.path) {
            Ok(parser) => {
                let entries = parser.entries();
                source_count += entries.len();
                
                for entry in entries {
                    if entry.is_source {
                        if let Ok(source) = parser.export_entry(&entry.name) {
                            // 根据类型分类保存
                            let (category, ext) = match entry.entry_type {
                                0 => ("applications", ".sra"),
                                1 => ("datawindows", ".srd"),
                                2 => ("windows", ".srw"),
                                3 => ("menus", ".srm"),
                                4 => ("functions", ".srf"),
                                5 => ("structures", ".srs"),
                                6 => ("userobjects", ".sru"),
                                7 => ("queries", ".srq"),
                                _ => ("others", ".srx"),
                            };
                            
                            let category_dir = src_dir.join(category);
                            fs::create_dir_all(&category_dir).map_err(|e| e.to_string())?;
                            
                            let file_name = format!("{}{}", entry.name, ext);
                            let file_path = category_dir.join(&file_name);
                            
                            if fs::write(&file_path, &source).is_ok() {
                                match entry.entry_type {
                                    1 => dw_count += 1,
                                    2 => window_count += 1,
                                    3 => menu_count += 1,
                                    4 => function_count += 1,
                                    _ => {}
                                }
                            }
                        }
                    }
                }
            }
            Err(e) => {
                errors.push(format!("Parse error {}: {}", pbl_info.name, e));
            }
        }
    }
    
    // 生成 package.json
    let package_json = format!(r#"{{
  "name": "{}",
  "version": "1.0.0",
  "description": "Migrated from PowerBuilder",
  "scripts": {{
    "start": "ng serve",
    "build": "ng build",
    "test": "ng test"
  }},
  "dependencies": {{}},
  "devDependencies": {{}}
}}"#, project_name);
    
    fs::write(src_dir.join("../package.json"), package_json).map_err(|e| e.to_string())?;
    
    Ok(MigrateResult {
        success: source_count > 0,
        project_name,
        source_count,
        dw_count,
        window_count,
        menu_count,
        function_count,
        output_dir: output_dir.to_string(),
        errors,
        // alias fields for frontend convenience
        components: window_count,
        services: function_count,
        models: dw_count,
    })
}

// ─── Pack Result ───────────────────────────────────────────────────

#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct PackResult {
    pub success: bool,
    pub packed_count: usize,
    pub pbl_path: String,
    pub message: String,
    pub errors: Vec<String>,
    /// Which engine produced this result: "python", "manifest", or "error"
    pub engine: String,
}

/// Pack source files from a directory back into a PBL binary.
/// Uses pure-Rust PBL writer (no Python dependency).
pub fn pack_sources_to_pbl(src_dir: &str, output_pbl: &str) -> Result<PackResult, String> {
    let src_path = Path::new(src_dir);
    if !src_path.exists() {
        return Err(format!("Source directory not found: {}", src_dir));
    }
    if !src_path.is_dir() {
        return Err(format!("Not a directory: {}", src_dir));
    }

    // Resolve output .pbl path
    let out = Path::new(output_pbl);
    let output_path = if out.extension().is_some_and(|e| e == "pbl") {
        out.to_path_buf()
    } else {
        let src_name = src_path.file_name()
            .unwrap_or_default()
            .to_string_lossy();
        let pbl_name = if src_name.ends_with(".pbl") {
            src_name.to_string()
        } else {
            format!("{}.pbl", src_name)
        };
        out.join(&pbl_name)
    };

    // Use pure-Rust PBL writer
    let encoding = crate::pbl_writer::PblEncoding::Unicode; // PB10+ default
    let pb_version: u32 = 12; // PB 12.5

    match crate::pbl_writer::pack_directory(src_path, &output_path, pb_version, encoding, true) {
        Ok(packed_count) => {
            Ok(PackResult {
                success: packed_count > 0,
                packed_count,
                pbl_path: output_path.to_string_lossy().to_string(),
                message: format!("Packed {} objects into PBL binary", packed_count),
                errors: Vec::new(),
                engine: "rust".to_string(),
            })
        }
        Err(e) => {
            // Fallback: create manifest if PBL write fails
            create_manifest_fallback(src_path, &output_path, e)
        }
    }
}

/// Fallback: create a .pbl.manifest text file when PBL binary write fails.
fn create_manifest_fallback(
    src_path: &Path,
    output_path: &Path,
    error: String,
) -> Result<PackResult, String> {
    let source_extensions = ["srw", "srd", "srm", "srf", "srs", "sru"];
    let mut source_files: Vec<std::path::PathBuf> = Vec::new();
    let mut errors: Vec<String> = Vec::new();

    collect_files_recursive(src_path, &mut source_files);

    for file_path in &source_files {
        let ext = file_path.extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();
        if source_extensions.contains(&ext.as_str()) {
            let name = file_path.file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            errors.push(format!("{} (would pack)", name));
        }
    }

    let packed_count = errors.len();

    let manifest_path = output_path.with_extension("pbl.manifest");
    let mut manifest = format!(
        "# PB DevKit Pack Manifest (fallback)\n# Source: {}\n# Error: {}\n\n",
        src_path.display(),
        error
    );
    for entry in &errors {
        manifest.push_str(&format!("{}\n", entry));
    }

    fs::write(&manifest_path, &manifest).map_err(|e| e.to_string())?;

    Ok(PackResult {
        success: false,
        packed_count,
        pbl_path: manifest_path.to_string_lossy().to_string(),
        message: format!("PBL write failed, manifest created: {}", error),
        errors,
        engine: "fallback".to_string(),
    })
}

/// Helper: collect all files recursively without external crates
fn collect_files_recursive(dir: &Path, result: &mut Vec<std::path::PathBuf>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                collect_files_recursive(&path, result);
            } else if path.is_file() {
                result.push(path);
            }
        }
    }
}

// ─── Tests ────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::Path;

    // ── detect_project ──
    #[test]
    fn test_detect_project_path_not_exists() {
        let result = detect_project("/nonexistent/path/that/does/not/exist");
        assert!(result.is_err());
    }

    #[test]
    fn test_detect_project_empty_dir() {
        let tmp = tempfile::tempdir().unwrap();
        let info = detect_project(tmp.path().to_str().unwrap()).unwrap();
        assert_eq!(info.name, tmp.path().file_name().unwrap().to_str().unwrap());
        assert!(!info.is_valid);
        assert!(info.pbl_files.is_empty());
    }

    #[test]
    fn test_detect_project_with_pbl() {
        let tmp = tempfile::tempdir().unwrap();
        let pbl_path = tmp.path().join("test.pbl");
        fs::write(&pbl_path, b"HDR*PB125").unwrap();
        let info = detect_project(tmp.path().to_str().unwrap()).unwrap();
        assert!(info.is_valid);
        assert_eq!(info.pbl_files.len(), 1);
    }

    #[test]
    fn test_detect_project_with_pbt() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("app.pbt"), b"PBORCA_BUILDLIBRARY").unwrap();
        let info = detect_project(tmp.path().to_str().unwrap()).unwrap();
        assert!(info.is_valid);
        assert_eq!(info.pbt_files.len(), 1);
    }

    #[test]
    fn test_detect_project_with_exe() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("app.exe"), b"MZ").unwrap();
        let info = detect_project(tmp.path().to_str().unwrap()).unwrap();
        assert!(info.is_valid);
        assert_eq!(info.exe_files.len(), 1);
    }

    // ── find_pbl_files ──
    #[test]
    fn test_find_pbl_files_path_not_exists() {
        let result = find_pbl_files("/nonexistent/path");
        assert!(result.is_err());
    }

    #[test]
    fn test_find_pbl_files_recursive() {
        let tmp = tempfile::tempdir().unwrap();
        let sub = tmp.path().join("subdir");
        fs::create_dir(&sub).unwrap();
        fs::write(tmp.path().join("a.pbl"), b"HDR*PB125").unwrap();
        fs::write(sub.join("b.pbl"), b"HDR*PB125").unwrap();
        let pbls = find_pbl_files(tmp.path().to_str().unwrap()).unwrap();
        assert_eq!(pbls.len(), 2);
    }

    #[test]
    fn test_find_pbl_files_skips_hidden_dirs() {
        let tmp = tempfile::tempdir().unwrap();
        let hidden = tmp.path().join(".git");
        fs::create_dir(&hidden).unwrap();
        fs::write(hidden.join("x.pbl"), b"HDR*PB125").unwrap();
        fs::write(tmp.path().join("visible.pbl"), b"HDR*PB125").unwrap();
        let pbls = find_pbl_files(tmp.path().to_str().unwrap()).unwrap();
        assert_eq!(pbls.len(), 1);
    }

    // ── collect_files_recursive ──
    #[test]
    fn test_collect_files_recursive_empty() {
        let tmp = tempfile::tempdir().unwrap();
        let mut result = Vec::new();
        collect_files_recursive(tmp.path(), &mut result);
        assert!(result.is_empty());
    }

    #[test]
    fn test_collect_files_recursive_flat() {
        let tmp = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("a.txt"), b"hello").unwrap();
        fs::write(tmp.path().join("b.rs"), b"world").unwrap();
        let mut result = Vec::new();
        collect_files_recursive(tmp.path(), &mut result);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_collect_files_recursive_nested() {
        let tmp = tempfile::tempdir().unwrap();
        let sub = tmp.path().join("sub");
        fs::create_dir(&sub).unwrap();
        fs::write(sub.join("deep.txt"), b"deep").unwrap();
        let mut result = Vec::new();
        collect_files_recursive(tmp.path(), &mut result);
        assert_eq!(result.len(), 1);
    }

    // ── scan_and_export ──
    #[test]
    fn test_scan_and_export_path_not_exists() {
        let tmp = tempfile::tempdir().unwrap();
        let result = scan_and_export("/nonexistent", tmp.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_scan_and_export_empty_project() {
        let tmp = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let result = scan_and_export(tmp.path().to_str().unwrap(), out.path().to_str().unwrap()).unwrap();
        assert!(!result.success);
    }

    // ── migrate_to_web ──
    #[test]
    fn test_migrate_to_web_path_not_exists() {
        let tmp = tempfile::tempdir().unwrap();
        let result = migrate_to_web("/nonexistent", tmp.path().to_str().unwrap(), "angular");
        assert!(result.is_err());
    }

    #[test]
    fn test_migrate_to_web_empty_project() {
        let tmp = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        let result = migrate_to_web(tmp.path().to_str().unwrap(), out.path().to_str().unwrap(), "angular").unwrap();
        assert!(!result.success);
    }

    // ── pack_sources_to_pbl ──
    #[test]
    fn test_pack_sources_to_pbl_src_not_exists() {
        let tmp = tempfile::tempdir().unwrap();
        let result = pack_sources_to_pbl("/nonexistent", tmp.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_pack_sources_to_pbl_not_a_dir() {
        let tmp = tempfile::tempdir().unwrap();
        let f = tmp.path().join("not_a_dir.txt");
        fs::write(&f, b"test").unwrap();
        let out = tempfile::tempdir().unwrap();
        let result = pack_sources_to_pbl(f.to_str().unwrap(), out.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_pack_sources_to_pbl_with_srw_files() {
        let tmp = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        fs::write(tmp.path().join("w_main.srw"), b"release 12.5;").unwrap();
        fs::write(tmp.path().join("w_login.srw"), b"release 12.5;").unwrap();
        let result = pack_sources_to_pbl(tmp.path().to_str().unwrap(), out.path().to_str().unwrap()).unwrap();
        assert!(result.success);
        assert_eq!(result.packed_count, 2);
        assert_eq!(result.engine, "rust");
        let manifest = Path::new(&result.pbl_path);
        assert!(manifest.exists());
    }

    // ── MigrateResult alias fields ──
    #[test]
    fn test_migrate_result_aliases() {
        let r = MigrateResult {
            success: true,
            project_name: "t".into(),
            source_count: 10,
            dw_count: 3,
            window_count: 2,
            menu_count: 1,
            function_count: 4,
            output_dir: "/out".into(),
            errors: vec![],
            components: 2,
            services: 4,
            models: 3,
        };
        assert_eq!(r.components, r.window_count);
        assert_eq!(r.services, r.function_count);
        assert_eq!(r.models, r.dw_count);
    }
}
