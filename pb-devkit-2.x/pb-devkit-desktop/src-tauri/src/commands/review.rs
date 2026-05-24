// Review command - comprehensive project review: structure, quality, DW, refactoring suggestions

use std::fs;
use std::path::Path;
use std::collections::HashMap;

#[derive(serde::Serialize)]
pub struct ReviewSection {
    pub title: String,
    pub status: String,   // "ok" | "warn" | "error"
    pub items: Vec<String>,
}

#[derive(serde::Serialize)]
pub struct ReviewResult {
    pub success: bool,
    pub project_name: String,
    pub total_score: u8,        // 0-100
    pub sections: Vec<ReviewSection>,
    pub report_path: String,
    pub message: String,
}

/// Run comprehensive project review
#[tauri::command]
pub fn run_review(project_dir: String, output_dir: String) -> Result<ReviewResult, String> {
    let proj_path = Path::new(&project_dir);
    if !proj_path.exists() {
        return Err(format!("Project directory not found: {}", project_dir));
    }

    fs::create_dir_all(&output_dir).map_err(|e| e.to_string())?;

    let project_name = proj_path.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let mut sections: Vec<ReviewSection> = Vec::new();
    let mut score: u8 = 100u8;

    // ── 1. Project structure ──────────────────────────────────────────────────
    let (struct_section, struct_deduct) = review_structure(proj_path);
    score = score.saturating_sub(struct_deduct);
    sections.push(struct_section);

    // ── 2. File statistics ────────────────────────────────────────────────────
    let (stats_section, stats_deduct, file_stats) = review_stats(proj_path);
    score = score.saturating_sub(stats_deduct);
    sections.push(stats_section);

    // ── 3. Code quality ───────────────────────────────────────────────────────
    let (quality_section, quality_deduct) = review_quality(proj_path, &file_stats);
    score = score.saturating_sub(quality_deduct);
    sections.push(quality_section);

    // ── 4. DataWindow analysis ────────────────────────────────────────────────
    let (dw_section, dw_deduct) = review_datawindows(proj_path, &file_stats);
    score = score.saturating_sub(dw_deduct);
    sections.push(dw_section);

    // ── 5. Migration readiness ────────────────────────────────────────────────
    let (migr_section, migr_deduct) = review_migration_readiness(proj_path, &file_stats);
    score = score.saturating_sub(migr_deduct);
    sections.push(migr_section);

    // ── Generate report ───────────────────────────────────────────────────────
    let report_path = format!("{}/REVIEW_REPORT.md", output_dir);
    let report = build_review_report(&project_name, score, &sections);
    fs::write(&report_path, &report).map_err(|e| e.to_string())?;

    let msg = format!(
        "项目评审完成：综合评分 {}/100，{}",
        score,
        score_label(score)
    );

    Ok(ReviewResult {
        success: true,
        project_name,
        total_score: score,
        sections,
        report_path,
        message: msg,
    })
}

// ── helpers ──────────────────────────────────────────────────────────────────

struct FileStats {
    pub pb_source_count: usize,
    pub pbl_count: usize,
    pub exe_count: usize,
    pub total_lines: usize,
    pub by_ext: HashMap<String, usize>,
    pub dw_files: Vec<String>,
}

fn scan_stats(proj_path: &Path) -> FileStats {
    let mut stats = FileStats {
        pb_source_count: 0,
        pbl_count: 0,
        exe_count: 0,
        total_lines: 0,
        by_ext: HashMap::new(),
        dw_files: Vec::new(),
    };

    let walker = walkdir::WalkDir::new(proj_path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    for entry in walker {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        *stats.by_ext.entry(ext.clone()).or_insert(0) += 1;

        match ext.as_str() {
            "srw" | "srd" | "srm" | "srf" | "sru" | "srq" | "srs" | "srj" | "ps" => {
                stats.pb_source_count += 1;
                if let Ok(content) = fs::read_to_string(path) {
                    stats.total_lines += content.lines().count();
                    if ext == "srd" {
                        stats.dw_files.push(path.to_string_lossy().to_string());
                    }
                }
            }
            "pbl" => stats.pbl_count += 1,
            "exe" => stats.exe_count += 1,
            _ => {}
        }
    }
    stats
}

fn review_structure(proj_path: &Path) -> (ReviewSection, u8) {
    let mut items = Vec::new();
    let mut deduct = 0u8;

    // Check for PBL / EXE files
    let has_pbl = walkdir::WalkDir::new(proj_path).into_iter()
        .filter_map(|e| e.ok())
        .any(|e| e.path().extension().and_then(|x| x.to_str()) == Some("pbl"));
    let has_exe = walkdir::WalkDir::new(proj_path).into_iter()
        .filter_map(|e| e.ok())
        .any(|e| e.path().extension().and_then(|x| x.to_str()) == Some("exe"));
    let has_src = walkdir::WalkDir::new(proj_path).into_iter()
        .filter_map(|e| e.ok())
        .any(|e| {
            matches!(
                e.path().extension().and_then(|x| x.to_str()),
                Some("srw") | Some("srd") | Some("srf") | Some("sru")
            )
        });

    if has_pbl {
        items.push("✅ 发现 PBL 源码库文件".to_string());
    } else {
        items.push("⚠️ 未发现 PBL 文件，可能是已部署目录".to_string());
        deduct = deduct.saturating_add(5);
    }
    if has_exe {
        items.push("✅ 发现 EXE 可执行文件".to_string());
    }
    if has_src {
        items.push("✅ 发现已导出的源码文件（.srw/.srd 等）".to_string());
    } else {
        items.push("ℹ️ 未发现已导出的源码文件，建议先运行 `pb export`".to_string());
    }

    let status = if deduct == 0 { "ok" } else { "warn" }.to_string();
    (ReviewSection { title: "项目结构".to_string(), status, items }, deduct)
}

fn review_stats(proj_path: &Path) -> (ReviewSection, u8, FileStats) {
    let stats = scan_stats(proj_path);
    let mut items = Vec::new();
    let mut deduct = 0u8;

    items.push(format!("📁 PBL 文件：{}", stats.pbl_count));
    items.push(format!("📄 源码文件：{} 个（{} 行代码）", stats.pb_source_count, stats.total_lines));
    items.push(format!("🪟 DataWindow（.srd）：{} 个", stats.dw_files.len()));

    if stats.total_lines > 100_000 {
        items.push(format!("⚠️ 代码量较大（{} 行），迁移工作量可能很高", stats.total_lines));
        deduct = deduct.saturating_add(10);
    } else if stats.total_lines > 50_000 {
        items.push(format!("⚠️ 代码量中等（{} 行），迁移需分阶段进行", stats.total_lines));
        deduct = deduct.saturating_add(5);
    }

    let status = if deduct == 0 { "ok" } else { "warn" }.to_string();
    (ReviewSection { title: "项目规模统计".to_string(), status, items }, deduct, stats)
}

fn review_quality(proj_path: &Path, stats: &FileStats) -> (ReviewSection, u8) {
    let mut items = Vec::new();
    let mut issues = 0usize;

    let walker = walkdir::WalkDir::new(proj_path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file());

    let mut long_line_files = 0usize;
    let mut todo_count = 0usize;
    let mut deep_nesting_files = 0usize;

    for entry in walker {
        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        if !matches!(ext, "srw" | "srd" | "srm" | "srf" | "sru" | "ps") {
            continue;
        }

        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let mut file_long_line = false;
        let mut file_deep_nesting = false;

        for line in content.lines() {
            if line.len() > 200 { file_long_line = true; }
            let indent = line.len() - line.trim_start().len();
            if indent >= 20 { file_deep_nesting = true; }
            let upper = line.trim().to_uppercase();
            if (upper.starts_with("//") || upper.starts_with("'"))
                && (upper.contains("TODO") || upper.contains("FIXME")) {
                todo_count += 1;
            }
        }
        if file_long_line { long_line_files += 1; issues += 1; }
        if file_deep_nesting { deep_nesting_files += 1; issues += 1; }
    }

    if long_line_files == 0 {
        items.push("✅ 无超长行（> 200字符）".to_string());
    } else {
        items.push(format!("⚠️ {} 个文件含超长行（> 200字符）", long_line_files));
    }
    if deep_nesting_files == 0 {
        items.push("✅ 无嵌套过深的代码块".to_string());
    } else {
        items.push(format!("⚠️ {} 个文件存在嵌套过深问题", deep_nesting_files));
    }
    if todo_count > 0 {
        items.push(format!("ℹ️ {} 处 TODO/FIXME 待办注释", todo_count));
    }

    let avg_lines = if stats.pb_source_count > 0 { stats.total_lines / stats.pb_source_count } else { 0 };
    items.push(format!("📊 平均每文件 {} 行", avg_lines));

    let deduct = (issues * 3).min(20) as u8;
    let status = if issues == 0 { "ok" } else { "warn" }.to_string();
    (ReviewSection { title: "代码质量".to_string(), status, items }, deduct)
}

fn review_datawindows(proj_path: &Path, stats: &FileStats) -> (ReviewSection, u8) {
    let mut items = Vec::new();
    let deduct = 0u8;

    items.push(format!("🪟 DataWindow 对象：{} 个", stats.dw_files.len()));

    // Quick scan for SQL complexity
    let mut complex_dw = 0usize;
    let mut join_count = 0usize;

    for dw_path in &stats.dw_files {
        let content = match fs::read_to_string(dw_path) {
            Ok(c) => c,
            Err(_) => continue,
        };
        let lower = content.to_lowercase();
        if lower.contains(" join ") { join_count += 1; }
        let select_count = lower.matches("select ").count();
        if select_count > 2 { complex_dw += 1; }
    }

    if join_count > 0 {
        items.push(format!("🔗 含 JOIN 的 DW：{} 个（迁移时需处理多表关联）", join_count));
    }
    if complex_dw > 0 {
        items.push(format!("⚠️ 复杂 DW（嵌套/UNION）：{} 个，需人工核对 SQL", complex_dw));
    }
    if stats.dw_files.len() > 0 && join_count == 0 {
        items.push("✅ 大部分 DW 为简单单表查询，迁移相对容易".to_string());
    }
    if stats.dw_files.is_empty() {
        items.push("ℹ️ 未发现 .srd 文件，请先运行 `pb export` 导出源码".to_string());
    }

    let status = if deduct == 0 { "ok" } else { "warn" }.to_string();
    (ReviewSection { title: "DataWindow 分析".to_string(), status, items }, deduct)
}

fn review_migration_readiness(_proj_path: &Path, stats: &FileStats) -> (ReviewSection, u8) {
    let mut items = Vec::new();
    let mut deduct = 0u8;

    // Estimate migration effort
    let loc = stats.total_lines;
    let dw_count = stats.dw_files.len();

    let days_estimate = (loc / 1000) + (dw_count * 2);
    let difficulty = if days_estimate < 30 { "🟢 低" } else if days_estimate < 90 { "🟡 中" } else { "🔴 高" };

    items.push(format!("📊 迁移难度：{}", difficulty));
    items.push(format!("⏱️ 预估工作量：约 {} 人天", days_estimate));
    items.push("📋 建议迁移路径：PBL export → Angular scaffold (pb migrate) → 逐模块验证".to_string());

    if dw_count > 50 {
        items.push(format!("⚠️ DataWindow 数量较多（{}），建议优先迁移高频使用的查询窗口", dw_count));
        deduct = deduct.saturating_add(5);
    }
    if loc < 10_000 {
        items.push("✅ 代码量较小，可考虑整体一次性迁移".to_string());
    } else {
        items.push("ℹ️ 建议按模块分阶段迁移，每阶段完成后进行回归测试".to_string());
    }

    let status = if deduct == 0 { "ok" } else { "warn" }.to_string();
    (ReviewSection { title: "迁移评估".to_string(), status, items }, deduct)
}

fn score_label(score: u8) -> &'static str {
    match score {
        90..=100 => "优秀 ✅",
        70..=89  => "良好 🟢",
        50..=69  => "一般 🟡",
        _        => "需改进 🔴",
    }
}

fn build_review_report(project_name: &str, score: u8, sections: &[ReviewSection]) -> String {
    let mut r = format!(
        r#"# PB DevKit 项目评审报告 / Project Review Report

## 项目：{}

**综合评分：{}/100 — {}**

---

"#,
        project_name, score, score_label(score)
    );

    for section in sections {
        let icon = match section.status.as_str() {
            "ok" => "✅",
            "warn" => "⚠️",
            "error" => "❌",
            _ => "ℹ️",
        };
        r.push_str(&format!("## {} {}\n\n", icon, section.title));
        for item in &section.items {
            r.push_str(&format!("- {}\n", item));
        }
        r.push('\n');
    }

    r.push_str("---\n_Generated by PB DevKit 2.1_\n");
    r
}
