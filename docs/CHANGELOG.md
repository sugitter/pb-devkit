# Changelog

All notable changes to this project will be documented in this file.

---

## [2.0.0] - 2026-05-XX

> **Major Release**: Complete rewrite in Rust for better performance

### Added (2.x)
- **Rust Core**: Zero-dependency PBL/PBD/PE parser (PB5-PB12.6)
- **CLI**: 20 commands with interactive REPL (rustyline)
- **Desktop GUI**: Tauri 2.x + Angular 17+ (10 UI components)
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
- Updated FUNCTION_MATRIX.md (CLI 100% complete)
- Added v2.1 roadmap (optimization priorities)

### Known Issues
- ORCA features require PBSpyORCA.dll (not included)
- Advanced features (refactor/review/snapshot/workflow) pending

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