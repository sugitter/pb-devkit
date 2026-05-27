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
    })
}
