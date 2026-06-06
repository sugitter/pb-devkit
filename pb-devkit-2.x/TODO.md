# PB DevKit 2.x 开发进度

## ✅ 已完成 (v2.2.1) - 2026-06-06 更新

### 本次更新 (2026-06-06)
- [x] 修复 F: 盘 git HEAD（refs/heads/main 指向无效对象）
- [x] 同步本地工作区与远程最新 commit（`1b97b90`）
- [x] 删除脚手架残留文件：`app.component.html` 和 `app.component.css`（已通过 git 提交移除）
- [x] 推送到 Gitea (origin) 和 GitHub，两端均同步至 `1b97b90`
- [x] 修复 `pb-devkit-core/Cargo.toml` 版本号不一致（2.1.0 → 2.2.1）
- [x] 同步 `Cargo.lock`（core + cli）版本号至 2.2.1
- [x] 创建 `CHANGELOG.md`（中英双语，遵循 Keep a Changelog 格式）
- [x] 新增 CLI `#[cfg(test)] mod tests` — main.rs 含 2 个占位测试
- [x] 199/199 测试全部通过，clippy 0 warnings
- [x] 更新 `README.md` — 版本号 v2.2→v2.2.1，清理 Roadmap 完成项
- [x] 提交文档更新，推送到 Gitea + GitHub（`df79f65`，三方均同步）
- [x] **CLI 集成测试补充** — 提取 lib.rs + 37 测试全部通过（unit 16 + integration 21）
- [x] **GitHub 同步** — 全部 commit 和 v2.2.1 tag 已同步至 GitHub
- [x] **PblWriter/PblParser 兼容性修复** — `parse_entries` 在 NOD* 块内扫描 ENT* 条目（修复偏移量 bug），236 测试全部通过
- [x] 提交文档更新，推送到 Gitea + GitHub（`70e4d3f`）

### 三大核心流程 (架构图验证)
- [x] **流程① — 一键 PB 源码解析与导出**
  - Parse PBL → List entries → Export SR* → 可在 IDE 中逐对象阅读和维护
  - CLI: `pbdevkit parse/list/export` 全部 ✅
  - Desktop: PBL List + Source Viewer 面板 ✅
- [x] **流程② — DW SQL 解析 + Angular 现代化 Web 迁移**
  - Parse DW SQL → Extract tables/columns → Scaffold Angular project
  - CLI: `pbdevkit migrate` ✅ | Desktop: migrate-panel ✅
  - 支持 DW→Tabs/Grid/Layout 三种转换模式
- [x] **流程③ — 反向打包：按需修改旧对象 + 编译回写 PBL**
  - Export SR* → Modify code → Repack to PBL → Compile via PBGen
  - CLI: `pbdevkit build` ✅ | Desktop: build-panel ✅
  - Pure Rust PBL Writer (`pbl_writer.rs`, 769 行) 无 Python 依赖 ✅

---

## ✅ 已完成 (v2.2.1) - 2026-06-04 更新

### 本次更新 (2026-06-04)
- [x] 新增 `migrate-panel` Angular 组件 — PB→Web 迁移向导
- [x] 新增 `build-panel` Angular 组件 — PBGen.exe 编译 GUI
- [x] Tauri 后端新增 `commands/build.rs`
- [x] `FUNCTION_MATRIX.md` Desktop 覆盖率 20/20 → 22/22（100%）
- [x] PE 解析器增强（三层扫描策略，解决 logistic.exe 单一 EXE 识别）
- [x] 测试体系补强（111 新测试）— 项目测试从 3→114
- [x] CI/CD 增强（clippy/fmt/audit + Windows builder + Node 22）
- [x] `Cargo.toml` 清理 — `tempfile` 移至 `[dev-dependencies]`

---

## ✅ 已完成 (v2.1.0)

### Rust 后端
- [x] PBL 解析器 (PB5-PB12.6 ANSI/Unicode)
- [x] PE 提取器 (从 EXE 提取 PBD)
- [x] DataWindow SQL 解析增强 (WHERE/ORDER BY/GROUP BY/UNION/子查询/计算列)
- [x] 版本快照功能 (Snapshot + Diff + Manager)
- [x] 导出重试机制 (指数退避 + BatchExportResult)
- [x] 搜索优化 (并行搜索 + 索引 + 缓存 + 正则)

### Angular 前端
- [x] 全部 22 个面板组件 (100%)
- [x] Settings 面板
- [x] 进度 Modal 组件

---

## 命令实现 (2.x)  — 最终状态

| 模块 | CLI 命令 | Desktop 面板 | 状态 |
|------|----------|-------------|------|
| pbl | parse, info, list, export, export-pbl | PBL List, Source Viewer | ✅ |
| pe | file-type, analyze-pe, extract-pbd | PE Info | ✅ |
| project | project, find-pbl, doctor | Project, Doctor | ✅ |
| search | search, search-type, search-regex | Search, Diff | ✅ |
| dw | analyze-dw, dw-sql | DW Analyzer | ✅ |
| decompile | decompile, decompile-all, list-decompile | Decompile | ✅ |
| report | report, export-report | Report, Stats | ✅ |
| code-eng | diff, workflow, refactor, snapshot, review | Diff, Workflow, Refactor, Snapshot, Review | ✅ |
| migration | migrate | Migrate | ✅ |
| build | build | Build | ✅ |
| **CLI 总计** | **30 commands** | **22 panels** | **✅ 100%** |
| orca | import, build, compile | — | ⏳ 需 DLL |

---

## ⏳ 遗留待办

| 项目 | 状态 | 说明 |
|------|------|------|
| ORCA 引擎封装 | ⏳ 需外部 DLL | 需要 PBSpyORCA.dll |
| git 二元管理脆弱 | 🟡 路径 | bare repo + F: 盘工作区，refs 不一致需手动同步（已通过 alternates 改善）
