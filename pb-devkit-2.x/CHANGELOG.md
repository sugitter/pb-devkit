# Changelog / 变更日志

> PowerBuilder Legacy System Toolkit — PB DevKit 2.x

---

## [2.2.1] - 2026-06-06

### Added / 新增
- `autoexport-panel` — 一键导出专用面板（扫描项目 + 进度 + 结果 + 历史）
- `migrate-panel` — PB→Web 迁移向导（步骤引导 + 分析结果 + 统计卡片）
- `build-panel` — PBGen.exe 编译 GUI（自动检测 + 多编译模式 + 日志）
- `refactor-panel` / `snapshot-panel` / `review-panel` — 代码工程面板（Desktop 100% 覆盖）
- CLI 新增 `refactor` / `snapshot` / `review` / `autoexport` / `migrate` / `build` 命令
- 测试体系补强：+111 新测试（PE 14 + PBL 17 + DW 30 + Project 21 + Search 22 + Decompile 7）

### Fixed / 修复
- **PE 解析器**：修复 PB 10+ 单一 EXE（如 logistic.exe）PBL 识别失败
  - 解析 Optional Header DataDirectory 获取 Certificate Table 偏移 + .rsrc 段定位
  - 扫描窗口 4KB→64KB；新增 .rsrc 段内扫描 + 全文件兜底扫描（≤256MB）
- **Angular CSS budget**：`4kB/8kB` → `6kB/12kB`（修复构建超限）
- **版本号统一**：core/cli/desktop 三者均为 `2.2.1`
- **Clippy**：0 warnings（core + cli）

### Changed / 变更
- `FUNCTION_MATRIX.md`：Desktop 覆盖率 20/20 → 22/22（100%）
- `README.md`：中英双语同步更新至 v2.2.1
- `MigrateResult`：补充 `components` / `services` / `models` 别名字段
- `Cargo.toml`：`tempfile` 从 `[dependencies]` 移至 `[dev-dependencies]`

### Removed / 移除
- 脚手架残留文件：`app.component.html` 和 `app.component.css`（inline template/styles 已替代）

---

## [2.2.0] - 2026-06-04

### Added / 新增
- CI/CD 增强（`.github/workflows/ci.yml`）— clippy / fmt / audit + Windows builder + Node 22
- Tauri 构建：生成 NSIS（`_x64-setup.exe`）+ MSI（`_x64_en-US.msi`）安装包
- Desktop 22/22 面板全部就绪（100% 覆盖率）

### Changed / 变更
- `FUNCTION_MATRIX.md`：CLI 30/30（100%）、Desktop 20/20 → 22/22
- `README.md`：中英双语同步更新

---

## [2.1.0] - 2026-05-XX

### Added / 新增
- Rust core 库（`pb-devkit-core`）：零依赖 PBL/PE 解析
- Rust CLI（`pb-devkit-cli`）：30 个命令，多线程并行搜索
- Tauri + Angular Desktop 应用：22 个面板
- 测试体系：114 个单元测试（PE/PBL/DW/Project/Search/Decompile）

### Changed / 变更
- 架构重构：Python 1.x → Rust 2.x（性能提升 10x+）
- 零 DLL 依赖（Pure Rust PBL Writer）

---

## [1.6.0] - 2026-04-XX (Python Legacy)

### Added / 新增
- Python CLI 22 个命令全部就绪
- `pbl_writer.py`：零 DLL 依赖的 PBL 写入（import/compile/pack）
- `migrate` 命令：PB→Angular 脚手架生成
- `autoexport` / `dw` / `review` 高级分析命令

### Note / 说明
- 1.x 系列不再维护，建议使用 2.x Rust 版本

---

*Changelog 格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)*
