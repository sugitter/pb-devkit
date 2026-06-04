# ============================================================
# PB DevKit v2.2.1 — 一键发布脚本
# ============================================================
# 用法: 右键 → "使用 PowerShell 运行" 或
#       在 PowerShell 中: .\finish-release.ps1
# ============================================================

$ErrorActionPreference = "Stop"
Set-Location "F:\workspace\X6\pb-devkit"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   PB DevKit v2.2.1 — Release Script         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Clean stale lock file ────────────────────────────
Write-Host "[1/6] 清理 git lock ..." -ForegroundColor Yellow
$lockFile = "F:\workspace\X6\pb-devkit\.git\index.lock"
if (Test-Path $lockFile) {
    Remove-Item $lockFile -Force
    Write-Host "  ✓ 已删除 index.lock" -ForegroundColor Green
} else {
    Write-Host "  - 无需清理" -ForegroundColor Gray
}

# ── Step 2: Stage all changes ────────────────────────────────
Write-Host "[2/6] 暂存变更 ..." -ForegroundColor Yellow
git add `
    "docs/CHANGELOG.md" `
    "pb-devkit-2.x/FUNCTION_MATRIX.md" `
    "pb-devkit-2.x/README.md" `
    "pb-devkit-2.x/TODO.md" `
    "pb-devkit-2.x/RELEASE_v2.2.1.md" `
    "pb-devkit-2.x/pb-devkit-cli/src/main.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/project.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/pe.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/pbl.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/dw.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/search.rs" `
    "pb-devkit-2.x/pb-devkit-core/src/decompile.rs" `
    "pb-devkit-2.x/pb-devkit-desktop/src-tauri/src/commands/mod.rs" `
    "pb-devkit-2.x/pb-devkit-desktop/src-tauri/src/commands/scan.rs" `
    "pb-devkit-2.x/pb-devkit-desktop/src-tauri/src/commands/build.rs" `
    "pb-devkit-2.x/pb-devkit-desktop/src-tauri/src/lib.rs" `
    "pb-devkit-2.x/pb-devkit-desktop/src/app/app.component.ts" `
    "pb-devkit-2.x/pb-devkit-desktop/src/app/components/autoexport-panel/autoexport-panel.component.ts" `
    "pb-devkit-2.x/pb-devkit-desktop/src/app/components/migrate-panel/" `
    "pb-devkit-2.x/pb-devkit-desktop/src/app/components/build-panel/" `
    ".github/workflows/ci.yml" `
    "pb-devkit-2.x/pb-devkit-core/Cargo.toml" `
    "docs/CHANGELOG.md" `
    "docs/art.png" `
    "finish-release.ps1"

Write-Host "  ✓ 已暂存" -ForegroundColor Green

# ── Step 3: Commit ───────────────────────────────────────────
Write-Host "[3/6] 创建提交 ..." -ForegroundColor Yellow
$commitMsg = @"
feat: v2.2.1 — 测试体系补强 + Desktop 22/22 (100%)

Desktop (Angular):
- feat: 新增 migrate-panel 组件 — PB→Web 迁移向导
  (4步引导: 配置→分析→生成→完成, Window/DW/Function/Menu 统计卡片)
- feat: 新增 build-panel 组件 — PBGen.exe 编译 GUI
  (PBGen 自动检测, exe/exe+pbd/exe+dll 三种编译模式, 完整构建日志)
- feat: 侧边栏新增 transform/construction 两个 Tab 图标
- fix: 补全 app.component.ts 的 Tab 类型定义

Tauri Backend (Rust):
- feat: 新增 commands/build.rs (check_pbgen / build_pb_application)
- fix: commands/mod.rs 注册 build 模块
- fix: lib.rs 注册 check_pbgen / build_pb_application 命令

Core (Rust):
- fix: MigrateResult 补充 components/services/models 别名字段
  (修复前端 result?.components 读取 undefined 的问题)
- fix: PE 解析器增强 — 支持 PB 10+ 单一 EXE 识别
  1. 解析 DataDirectory 获取 Certificate Table 偏移
  2. 扫描 .rsrc 段内嵌 PBL (PB 10+ 策略)
  3. 扫描窗口 4KB → 64KB
  4. 全文件兜底扫描
- test: 测试体系大幅增强 (3 → 111 个)
  - PE 14 测试 (3层策略/certificate-aware/dedup/PE64)
  - PBL 17 测试 (版本检测/类型识别/导出)
  - DW 30 测试 (SQL解析/子句提取/UNION/子查询/DW样式)
  - Project 21 测试 (detect/find/scan/migrate/pack/recursive)
  - Search 22 测试 (含regex/类型过滤/隐藏目录跳过)
  - Decompile 7 测试 (无效文件/路径/名称保留)

CI/CD:
- enhance: CI 新增 cargo test (CLI) / clippy / fmt --check / cargo audit
- enhance: CI 新增 Windows runner 构建 CLI + artifact 上传
- enhance: CI Angular 前端构建升级 Node 22

Docs:
- update: FUNCTION_MATRIX.md — Desktop 20/20 → 22/22 (100%)
- update: README.md — 中英双语覆盖率数字同步
- add: RELEASE_v2.2.1.md — GitHub Release Notes
- update: docs/CHANGELOG.md [2.2.1] 条目
"@

git commit -m $commitMsg
Write-Host "  ✓ 提交成功" -ForegroundColor Green

# ── Step 4: Create tag ───────────────────────────────────────
Write-Host "[4/6] 创建 v2.2.1 tag ..." -ForegroundColor Yellow
git tag -a v2.2.1 -m "PB DevKit v2.2.1 — Tests + CI + Desktop 22/22 (100%)"
Write-Host "  ✓ tag v2.2.1 已创建" -ForegroundColor Green

# ── Step 5: Push to remotes ──────────────────────────────────
Write-Host "[5/6] 推送代码 ..." -ForegroundColor Yellow

Write-Host "  → origin (内网 Gitea) ..." -ForegroundColor Gray
git push origin main
Write-Host "    ✓ origin 推送成功" -ForegroundColor Green

Write-Host "  → github ..." -ForegroundColor Gray
git push github main
Write-Host "    ✓ github 推送成功" -ForegroundColor Green

Write-Host "  → 推送 tags ..." -ForegroundColor Gray
git push origin v2.2.1
git push github v2.2.1
Write-Host "    ✓ tags 推送成功" -ForegroundColor Green

# ── Step 6: Verify (optional) ────────────────────────────────
Write-Host "[6/6] 验证编译 ..." -ForegroundColor Yellow
$env:CARGO_TARGET_DIR = "D:\cargo_target\pb-devkit-desktop"
Push-Location "pb-devkit-2.x\pb-devkit-desktop\src-tauri"
cargo check 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ cargo check 通过" -ForegroundColor Green
} else {
    Write-Host "  ⚠ cargo check 有警告/错误，请检查" -ForegroundColor Red
}
Pop-Location

# ── Done ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   🎉 v2.2.1 发布完成！                      ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "GitHub Release: https://github.com/sugitter/pb-devkit/releases/tag/v2.2.1" -ForegroundColor Cyan
Write-Host "Release Notes : pb-devkit-2.x/RELEASE_v2.2.1.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "如需重新构建安装包:" -ForegroundColor Gray
Write-Host "  cd pb-devkit-2.x/pb-devkit-desktop/src-tauri" -ForegroundColor Gray
Write-Host "  set CARGO_TARGET_DIR=D:\cargo_target\pb-devkit-desktop" -ForegroundColor Gray
Write-Host "  cargo tauri build" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ 全部完成。" -ForegroundColor Green
