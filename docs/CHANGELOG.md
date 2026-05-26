# Changelog

All notable changes to this project will be documented in this file.

---

## [1.6.0] - 2026-05-23

### Added
- **`pb pack`**: New command — write `.sr*` source files back to PBL binary (pure Python, zero DLL)
- **`pbl_writer.py`**: PBL binary writer supporting Unicode (UTF-16LE) and ANSI formats; 512B block alignment; HDR\*/FRE\*/NOD\*/DAT\* layout
- **`pb migrate`**: Enhanced — DataWindow SQL → TypeScript interface + Reactive Form factory; Window events → method stubs; generates `MIGRATION.md` with effort estimates
- **`pb export --manifest`**: Generates `export-manifest.json` with object catalog, PBL grouping, and timestamps
- Round-trip validation: EXE → export → pack → rebuilt PBL verified identical by ChunkEngine
- **`pb autoexport`**: Smart auto-detect project type + full batch export to structured src/ (was written but unregistered)
- **`pb dw`**: DataWindow deep analyzer — SQL/table schema/params/HTML report (was written but unregistered)
- **`pb review`**: Comprehensive project review — structure/quality/DW/deps/suggestions in Markdown or HTML (was written but unregistered)
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

## [2.1.0] - 2026-05-25

> **Feature Complete**: CLI 27/27 + Desktop 19/19 = 100% coverage

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
  - PE view, Report view, Project stats (NEW)
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

## [1.4.0] - 2026-04-XX

### Added
- Auto-export smart detection (`autoexport`)
- Project review command (`review`)
- DataWindow SQL extraction

### Changed
- Refactoring engine improvements
- Better Chinese path support

## [1.3.0] - 2026-03-XX

### Added
- ORCA engine wrapper
- Import/Build/Compile commands
- Snapshot versioning

## [1.2.0] - 2026-02-XX

### Added
- Basic PBL parsing
- Source export functionality
- Search and analyze commands

---

*格式参考: [Keep a Changelog](https://keepachangelog.com/)*