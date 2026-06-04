# Changelog

All notable changes to this project will be documented in this file.

---

## [2.2.1] - 2026-06-04

> **Desktop 100%**: migrate-panel + build-panel 补全；MigrateResult 字段修复；PE 解析器三层扫描增强；Desktop 覆盖率从 79% 升至 22/22 (100%)

### Added
- **`migrate-panel`** (Angular): 4步迁移向导 — Configure → Analyze → Generate → Complete；显示 Window/DW/Function/Menu 统计卡片；输出 Angular scaffold 路径与"Next Steps"清单
- **`build-panel`** (Angular): PBGen.exe 编译 GUI — 自动扫描 PBGen 路径、三种编译模式（exe/exe+pbd/exe+dll）、实时构建日志滚动、PBGen 未找到时引导跳转迁移向导
- **`commands/build.rs`** (Tauri): `check_pbgen()` 扫描 PATH + 常用安装目录；`build_pb_application()` 调用 PBGen.exe 并实时返回日志
- **`RELEASE_v2.2.1.md`**: GitHub Release Notes
- **测试体系大幅增强**：从 3 个测试扩展到 100+ 个，覆盖 6 个核心模块
  - PE 解析器 (`pe.rs`): 14 个测试（appended/512-aligned/byte-granular/certificate-aware/.rsrc/full-file 三层策略 + dedup + PE64 + detect_file_type + extract + embedded_pbl_count）
  - PBL 解析器 (`pbl.rs`): 17 个测试（ANSI/Unicode 版本检测 PB5/PB10/PB12/PB125/PB126 + 类型识别 + timestamp + export + info）
  - DW 分析器 (`dw.rs`): 30 个测试（extract_sql/extract_columns/extract_where_clause/extract_order_by/extract_group_by/extract_arguments/extract_computed_columns/detect_union/detect_subqueries/parse_table_name/extract_tables/detect_dw_style）
  - 项目工具 (`project.rs`): 21 个测试（detect_project/find_pbl_files/scan_and_export/migrate_to_web/pack_sources_to_pbl/collect_files_recursive/MigrateResult 别名字段）
  - 搜索引擎 (`search.rs`): 22 个测试（search_in_files/search_with_regex/search_by_type/search_file_parallel/search_file_with_regex/collect_files/find_files_by_ext — 含大小写/文件类型过滤/隐藏目录跳过）
  - 反编译器 (`decompile.rs`): 7 个测试（list_decompile_entries/decompile_entry/decompile_all 无效文件/路径/名称保留）
- **CI/CD** (`.github/workflows/ci.yml`): 增强流水线 — 新增 `cargo clippy` + `cargo fmt --check` + `cargo audit` + Windows CLI 构建 + Node 22

### Fixed
- **`MigrateResult`** struct: 补充 `components` / `services` / `models` 别名字段（`components = window_count`, `services = function_count`, `models = dw_count`）——修复前端读取 `result?.components` 返回 `undefined` 的 bug
- **PE 解析器** (`pe.rs`): 三层扫描策略增强，修复 PB 10.0 单一 EXE（如 logistic.exe）识别失败
  - 新增 Optional Header DataDirectory 解析：获取 Certificate Table 偏移（数字证书前为 PBL 上限）+ .rsrc 段 RVA 定位
  - 扫描窗口 4 KiB → 64 KiB（兼容 PB 10+ 更大的段间对齐间隙）
  - 新增 `.rsrc` 段内扫描策略（PB 10+ 将 PBL 嵌入资源段）
  - 新增全文件兜底扫描（≤256 MiB，0x200 起，捕获非标准嵌入）
- **`commands/mod.rs`**: 注册 `build` 模块
- **`lib.rs`**: 注册 `check_pbgen` 和 `build_pb_application` Tauri 命令

### Changed
- Desktop panel count: 20 → 22（新增 migrate-panel + build-panel）
- `FUNCTION_MATRIX.md`: Desktop 覆盖率 20/20 → 22/22 = 100%
- `README.md`: 中英双语覆盖率数字同步
- `Cargo.toml` (core): `tempfile` 从 `[dependencies]` 移至 `[dev-dependencies]`

---

## [2.2.0] - 2026-05-30

> **Release Ready**: Tauri Desktop 安装包构建成功；CLI 30命令 + Desktop 20面板全部就绪

### Added
- **Autoexport Panel** (`autoexport-panel`): Dedicated Angular panel for one-click source export with 5-step progress tracking, operation history, per-run stats (src/pbl counts)
- **`pack_to_pbl` Tauri Command**: Dual-engine binary PBL packing — Priority 1: calls 1.x Python engine (`pb pack`); Priority 2: Rust manifest fallback when Python unavailable
- **`PackResult.engine` field**: Reports which engine produced the PBL (`"python"` / `"manifest"`) for frontend transparency
- **`try_python_pack()`**: Auto-detects 1.x pb.py + Python 3 executable (multi-path probe); parses stdout for object count
- **Desktop Quick Actions**: Three one-click buttons in Explorer sidebar — 导出源码 / 转Web项目 / 重打包PBL — each with running/done/error state machine and auto-dismiss result message
- **Tauri Desktop Release Build**: `PB DevKit_2.2.0_x64_en-US.msi` + `PB DevKit_2.2.0_x64-setup.exe` 构建成功（Windows x64）
- **Desktop 版本号同步**: About 弹窗 + Welcome 屏幕统一更新为 v2.2.0
- **`pbdevkit autoexport`**: Smart project auto-export — auto-detects PBL_PROJECT / BINARY_PROJECT / MIXED_PROJECT; exports to `src/` with README.md generation
- **`pbdevkit migrate`**: PB → Angular 18 scaffold migration — generates Angular Components, TypeScript models, Reactive Forms, service stubs, `AppRoutingModule`, `MIGRATION.md` with effort estimates
- **`pbdevkit build`**: Rebuild PB application via PBGen.exe — three modes (`exe`/`exe+pbd`/`exe+dll`); auto-detects PBGen from PATH and common Appeon/Sybase install paths; pure Rust std-lib
- **`docs/art.png`**: Project architecture diagram

### Fixed
- Explorer theme unification — `.object-panel`, `.search-tab-wrapper`, `.other-tab-layout` all use Catppuccin Mocha `#1e1e2e` (was mixing dark + light backgrounds)

### Changed
- CLI command count: 27 → 30 (added autoexport/migrate/build)
- Desktop panel count: 19 → 20 (added autoexport-panel)
- CLI version string: v2.1.0 → v2.2.0
- `FUNCTION_MATRIX.md`: Desktop 覆盖率 19/19 → 20/20 = 100%

### Architecture Notes
- `pack_to_pbl` uses `std::process::Command` to invoke Python engine; no extra Tauri shell plugin needed
- `collect_files_recursive()` — zero-crate recursive file walk (std::fs only)
- All new CLI commands: zero external crate dependencies (pure std-lib)

---

## [2.1.0] - 2026-05-25

> **Feature Complete**: 2.x CLI 27/27 + Desktop 19/19 = 100% coverage

### Added (2.x CLI)
- **`pbdevkit refactor`**: Code pattern scanner — detects GOTO/GLOBAL/EMPTY_CATCH/HARDCODED_SQL/LONG_FUNC anti-patterns; generates `REFACTOR_REPORT.md` with severity ratings and remediation hints
- **`pbdevkit snapshot`**: Project snapshot tool — file manifest with SHA-256 hashes, diff between snapshots, tracks added/removed/modified files
- **`pbdevkit review`**: Comprehensive project review — 4-phase analysis (structure → quality → security → maintainability); produces `REVIEW.md` with weighted scoring; pure std-lib, zero dependencies

### Added (2.x Desktop)
- **Refactor Panel** (`refactor-panel`): Angular UI for pattern scanning with apply/dry-run toggle
- **Snapshot Panel** (`snapshot-panel`): Snapshot creation and diff visualization
- **Review Panel** (`review-panel`): Five-dimension 100-point scoring dashboard with Tauri `run_review` command

### Changed
- CLI command count: 24 → 27 (added refactor/snapshot/review)
- Desktop panel count: 16 → 19 (added refactor/snapshot/review panels)
- `FUNCTION_MATRIX.md`: Updated coverage to CLI 27/27 (100%) + Desktop 19/19 (100%) = 34/34 overall
- `README.md`: Updated command coverage tables to reflect 100% parity

### Architecture Notes
- All new CLI commands use pure Rust std-lib (no external crates beyond walkdir for refactor)
- Tauri commands follow existing `invoke()` pattern in Angular components
- Full function matrix now at 100% — no pending items in Code Engineering category

---

## [2.0.0] - 2026-05-16

> **Major Release**: Complete rewrite in Rust for better performance

### Added (2.x)
- **Rust Core**: Zero-dependency PBL/PBD/PE parser (PB5-PB12.6)
- **CLI**: 20 commands with interactive REPL (rustyline)
- **Desktop GUI**: Tauri 2.x + Angular 17+ (11 UI components)
  - Project selector, PBL list, Source viewer
  - DataWindow analyzer, Search panel
  - Decompile panel, Doctor panel
  - PE view, Report view, Project stats
- **PE Analysis**: File type detection, header analysis, PBD extraction
- **DataWindow**: SQL extraction, table/column analysis
- **Function Matrix**: Complete CLI/Desktop feature coverage

### Documentation
- Updated README (EN/CN bilingual)
- Added CLI_EXAMPLES.md
- Updated FUNCTION_MATRIX.md (CLI 100%, Desktop 82%)
- Updated AGENT_SKILL.md (v2.x commands)
- Added v2.1 roadmap (optimization priorities)

### Fixed
- pbl_cmd.rs: Fix progress_chars Result handling (indicatif 0.17 compatibility)

### Known Issues
- ORCA features require PBSpyORCA.dll (not included); replaced by pbl_writer + PBGen.exe in 1.x
- Advanced features (refactor/review/snapshot/workflow) → **resolved in v2.1.0**

---

## [1.6.0] - 2026-05-23

> **Zero-DLL Complete**: All 1.x CLI commands free of ORCA DLL dependency

### Added
- **`pb pack`**: New command — write `.sr*` source files back to PBL binary (pure Python, zero DLL)
- **`pbl_writer.py`**: PBL binary writer supporting Unicode (UTF-16LE) and ANSI formats; 512B block alignment; HDR\*/FRE\*/NOD\*/DAT\* layout
- **`pb migrate`**: Enhanced — DataWindow SQL → TypeScript interface + Reactive Form factory; Window events → method stubs; generates `MIGRATION.md` with effort estimates
- **`pb export --manifest`**: Generates `export-manifest.json` with object catalog, PBL grouping, and timestamps
- Round-trip validation: EXE → export → pack → rebuilt PBL verified identical by ChunkEngine
- **`pb autoexport`**: Smart auto-detect project type + full batch export to structured src/ (registered to all entry points)
- **`pb dw`**: DataWindow deep analyzer — SQL/table schema/params/HTML report (registered to all entry points)
- **`pb review`**: Comprehensive project review — structure/quality/DW/deps/suggestions in Markdown or HTML (registered to all entry points)
- **CLI completion**: All 22 commands now registered in both entry points (`pb.py` + `cli.py`); version bumped to 1.6.0

### Changed
- **Zero-DLL Architecture**: `import`, `compile` rewritten to use `pbl_writer` (no ORCA/DLL)
- **`pb build`**: Rewritten to call `PBGen.exe` (PB IDE CLI tool) via subprocess; auto-detects installation path; supports `--pbgen` override
- **`pb workflow`**: Step 4 now calls `pb pack` instead of ORCA
- **`pb doctor`**: Removed ORCA DLL check; now checks Python + pbl_parser + pbl_writer
- **`pb init`**: Removed PBSpyORCA.dll reference from setup hints
- **`pb list`, `pb snapshot`, `pb export`**: Removed `--orca` options
- **`pborca_engine.py`**: Marked DEPRECATED; no longer called by any core CLI command

### Fixed
- ENT\* `name_buf` format: correctly writes `name_bytes + ver_suffix(2B)` — not as prefix; fixes name corruption in round-trip validation

---

## [1.5.0] - 2026-05-07

### Added
- Project architecture analysis document (`docs/PROJECT_ANALYSIS.md`)
- Complete CLI command suite (20 commands)
- VS Code and IDEA plugin support
- PB12 Unicode support (UTF-16LE)
- DataWindow专项分析命令 (`dw`)

### Fixed
- Version consistency: pyproject.toml aligned with `__init__.py`

### Changed
- Enhanced decompiler error handling
- Improved PBL parsing performance

---

## [1.4.0] - 2026-04-XX

### Added
- Auto-export smart detection (`autoexport`)
- Project review command (`review`)
- DataWindow SQL extraction

### Changed
- Refactoring engine improvements
- Better Chinese path support

---

## [1.3.0] - 2026-03-XX

### Added
- ORCA engine wrapper
- Import/Build/Compile commands
- Snapshot versioning

---

## [1.2.0] - 2026-02-XX

### Added
- Basic PBL parsing
- Source export functionality
- Search and analyze commands

---

*格式参考: [Keep a Changelog](https://keepachangelog.com/)*
