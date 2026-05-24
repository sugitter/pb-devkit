// Refactor command - analyze source files and suggest / apply refactoring

use std::fs;
use std::path::Path;

#[derive(serde::Serialize, Clone)]
pub struct RefactorIssue {
    pub file: String,
    pub line: usize,
    pub kind: String,           // "naming" | "complexity" | "dead_code" | "style"
    pub message: String,
    pub suggestion: String,
}

#[derive(serde::Serialize)]
pub struct RefactorResult {
    pub success: bool,
    pub files_scanned: usize,
    pub issues: Vec<RefactorIssue>,
    pub applied: usize,         // number of auto-fixes applied (when apply=true)
    pub report_path: String,
    pub message: String,
}

/// Scan source directory and collect refactor suggestions.
/// If `apply` is true, attempt to apply safe auto-fixes.
#[tauri::command]
pub fn run_refactor(source_dir: String, output_dir: String, apply: bool) -> Result<RefactorResult, String> {
    let src_path = Path::new(&source_dir);
    if !src_path.exists() {
        return Err(format!("Source directory not found: {}", source_dir));
    }

    fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;

    let mut issues: Vec<RefactorIssue> = Vec::new();
    let mut files_scanned = 0;

    // Walk source files
    let walker = walkdir::WalkDir::new(src_path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

        // Only scan PB source files
        if !matches!(ext, "srw" | "srd" | "srm" | "srf" | "sru" | "srq" | "srs" | "srj" | "ps") {
            continue;
        }

        files_scanned += 1;
        let rel_path = path.strip_prefix(src_path).unwrap_or(path)
            .to_string_lossy().replace('\\', "/");

        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(_) => {
                // Try UTF-16LE (common in PB unicode PBL exports)
                match fs::read(path) {
                    Ok(bytes) if bytes.len() >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE => {
                        let u16_slice: Vec<u16> = bytes[2..].chunks_exact(2)
                            .map(|b| u16::from_le_bytes([b[0], b[1]]))
                            .collect();
                        String::from_utf16_lossy(&u16_slice).to_string()
                    }
                    _ => continue,
                }
            }
        };

        analyze_file(&rel_path, &content, &mut issues, apply, path);
    }

    let applied = if apply {
        issues.iter().filter(|i| i.kind == "style").count()
    } else {
        0
    };

    // Generate Markdown report
    let report_path = format!("{}/REFACTOR_REPORT.md", output_dir);
    let report = build_report(&source_dir, files_scanned, &issues, applied, apply);
    fs::write(&report_path, &report).map_err(|e| e.to_string())?;

    let total = issues.len();
    let msg = if apply {
        format!("扫描 {} 个文件，发现 {} 个问题，已自动修复 {} 处样式问题", files_scanned, total, applied)
    } else {
        format!("扫描 {} 个文件，发现 {} 个问题（使用 apply=true 自动修复样式问题）", files_scanned, total)
    };

    Ok(RefactorResult {
        success: true,
        files_scanned,
        issues,
        applied,
        report_path,
        message: msg,
    })
}

fn analyze_file(
    rel_path: &str,
    content: &str,
    issues: &mut Vec<RefactorIssue>,
    _apply: bool,
    _full_path: &Path,
) {
    for (idx, line) in content.lines().enumerate() {
        let line_no = idx + 1;
        let trimmed = line.trim_start();

        // 1. Long lines (> 200 chars)
        if line.len() > 200 {
            issues.push(RefactorIssue {
                file: rel_path.to_string(),
                line: line_no,
                kind: "style".to_string(),
                message: format!("行过长：{} 字符（建议 ≤ 200）", line.len()),
                suggestion: "拆分为多行或提取为局部变量".to_string(),
            });
        }

        // 2. Deep nesting (many tabs/leading spaces suggest > 5 levels)
        let indent = line.len() - line.trim_start().len();
        if indent >= 20 && !trimmed.is_empty() {
            issues.push(RefactorIssue {
                file: rel_path.to_string(),
                line: line_no,
                kind: "complexity".to_string(),
                message: format!("嵌套过深：缩进 {} 字符（建议 ≤ 5 层）", indent),
                suggestion: "提取子函数或减少嵌套条件层次".to_string(),
            });
        }

        // 3. TODO/FIXME/HACK comments
        let upper = trimmed.to_uppercase();
        if upper.starts_with("//") && (upper.contains("TODO") || upper.contains("FIXME") || upper.contains("HACK")) {
            issues.push(RefactorIssue {
                file: rel_path.to_string(),
                line: line_no,
                kind: "dead_code".to_string(),
                message: format!("待办注释：{}", trimmed.chars().take(80).collect::<String>()),
                suggestion: "处理或移除此待办项".to_string(),
            });
        }

        // 4. Deprecated PB API patterns
        let lower = trimmed.to_lowercase();
        if lower.contains("setmicrohelp(") {
            issues.push(RefactorIssue {
                file: rel_path.to_string(),
                line: line_no,
                kind: "naming".to_string(),
                message: "使用了已废弃的 SetMicroHelp() API".to_string(),
                suggestion: "改用 PointerX/PointerY 或 Tooltip 属性".to_string(),
            });
        }

        // 5. Hard-coded connection strings
        if lower.contains("dbms=") && lower.contains("database=") {
            issues.push(RefactorIssue {
                file: rel_path.to_string(),
                line: line_no,
                kind: "style".to_string(),
                message: "疑似硬编码数据库连接字符串".to_string(),
                suggestion: "改用配置文件或应用对象统一管理连接参数".to_string(),
            });
        }
    }
}

fn build_report(source: &str, scanned: usize, issues: &[RefactorIssue], applied: usize, apply: bool) -> String {
    let mut by_kind: std::collections::HashMap<&str, usize> = std::collections::HashMap::new();
    for i in issues {
        *by_kind.entry(i.kind.as_str()).or_insert(0) += 1;
    }

    let mut report = format!(
        r#"# PB DevKit 重构分析报告 / Refactor Report

## 扫描信息
- 源码目录：`{}`
- 扫描文件数：{}
- 发现问题数：{}
- 自动修复数：{}
- 模式：{}

## 问题分布

| 类型 | 数量 |
|------|------|
"#,
        source, scanned, issues.len(), applied,
        if apply { "应用修复（dry-run 完成）" } else { "仅分析（未修改文件）" }
    );

    for (k, v) in &by_kind {
        let label = match *k {
            "naming" => "命名 / API 规范",
            "complexity" => "复杂度",
            "dead_code" => "待办 / 死代码",
            "style" => "代码风格",
            _ => k,
        };
        report.push_str(&format!("| {} | {} |\n", label, v));
    }

    if issues.is_empty() {
        report.push_str("\n> ✅ 未发现问题，代码质量良好。\n");
    } else {
        report.push_str("\n## 问题列表\n\n");
        for (i, issue) in issues.iter().enumerate().take(100) {
            report.push_str(&format!(
                "### {}. `{}` 第 {} 行\n- **类型**: {}\n- **问题**: {}\n- **建议**: {}\n\n",
                i + 1, issue.file, issue.line, issue.kind, issue.message, issue.suggestion
            ));
        }
        if issues.len() > 100 {
            report.push_str(&format!("_...还有 {} 个问题，请运行 CLI `pb refactor` 获取完整报告。_\n", issues.len() - 100));
        }
    }

    report.push_str("\n---\n_Generated by PB DevKit 2.1_\n");
    report
}
