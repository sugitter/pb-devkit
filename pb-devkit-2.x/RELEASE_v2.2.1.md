# PB DevKit v2.2.1 Release Notes

> PowerBuilder Legacy System Toolkit — Rust + Tauri + Angular Desktop Application

---

## What's New in v2.2.1

### 🧭 Migrate Panel — PB → Web Migration Wizard

A dedicated guided wizard for migrating PowerBuilder projects to Angular + TypeScript:

- **Step 1 — Configure**: Set source directory, output path, and migration options (export DW/events/menus)
- **Step 2 — Analyze**: Scan and display project statistics (Windows, DataWindows, Functions, Menus)
- **Step 3 — Generate**: Real-time progress display for Angular scaffold generation
- **Step 4 — Complete**: Summary cards showing generated components/services/models with "Next Steps" guide

### 🔨 Build Panel — PBGen.exe Compiler GUI

A full-featured GUI for PowerBuilder compilation without the IDE:

- **Auto-detect PBGen.exe**: Scans PATH and common PB installation directories automatically
- **Three build modes**: `exe` / `exe + pbd` / `exe + dll` output options
- **Live build log**: Real-time scrolling output with timestamps and status indicators
- **Graceful degradation**: When PBGen is not found, surfaces a "Go to Migrate Wizard" shortcut

### 🔧 Bug Fixes

- **`MigrateResult.components` fix**: Added `components` / `services` / `models` alias fields to `MigrateResult` struct — previously the frontend received `undefined` when reading `result?.components`
- **Tauri command registration**: Registered `check_pbgen` and `build_pb_application` in `lib.rs`; added `build` module to `commands/mod.rs`

### 📊 Complete Coverage — Desktop Now 100%

| Layer | Commands/Panels | Status |
|-------|----------------|--------|
| 1.x Python CLI | 22 commands | 100% ✅ |
| 2.x Rust CLI | 30 commands | 100% ✅ |
| Desktop (Angular) | **22 panels** | **100% ✅** ← upgraded from 79% |

---

## All Desktop Panels

| Panel | Description |
|-------|-------------|
| `project-selector` | Project directory picker with recent history |
| `pbl-list` | PBL file explorer with entry listing |
| `explorer-panel` | PBL/EXE project tree explorer |
| `source-viewer` | PowerScript source code viewer with syntax highlight |
| `dw-analyzer` | DataWindow SQL structure analyzer |
| `search-panel` | Cross-file full-text code search |
| `search-regex-panel` | Regex-based advanced search |
| `decompile-panel` | PBD/EXE decompile with batch export |
| `doctor-panel` | Environment diagnostics (Python/Rust/PBSpyORCA) |
| `pe-view` | PE/binary structure viewer |
| `report-view` | Project analysis report viewer |
| `diff-panel` | File diff viewer with side-by-side comparison |
| `object-browser` | Project object type browser |
| `project-stats` | Code statistics dashboard |
| `workflow-panel` | Workflow automation and CI integration |
| `refactor-panel` | Code refactoring assistant |
| `snapshot-panel` | Project snapshot management |
| `review-panel` | Code review assistant |
| `autoexport-panel` | One-click smart source export with progress/history |
| `migrate-panel` | **NEW in v2.2.1** PB → Angular migration wizard |
| `build-panel` | **NEW in v2.2.1** PBGen.exe compiler GUI |
| `settings-panel` | Application settings |
| `progress-modal` | Reusable progress indicator with cancel support |

---

## Installation

### Windows (NSIS / MSI)

```powershell
# Download from GitHub Releases
https://github.com/sugitter/pb-devkit/releases/tag/v2.2.1

# NSIS installer
PB DevKit_2.2.1_x64-setup.exe

# MSI installer
PB DevKit_2.2.1_x64_en-US.msi
```

### Build from Source

```bash
cd pb-devkit-2.x/pb-devkit-desktop/src-tauri
set CARGO_TARGET_DIR=D:\cargo_target\pb-devkit-desktop
cargo tauri build
```

---

## Requirements

- **Windows 10/11 x64**
- **Python 3.8+** (for 1.x pack engine; optional, manifest fallback available)
- **PowerBuilder 5–12** projects (PBL/EXE/PBD format)
- **PBGen.exe** (optional, required for Build Panel compilation)

---

## Upgrade from v2.2.0

No breaking changes. Replace the installer — all existing project paths and settings are preserved.

---

## Full Changelog

### Desktop (Angular)
- **feat**: `migrate-panel` — 4-step PB→Web migration wizard with statistics cards
- **feat**: `build-panel` — PBGen.exe GUI with mode selection and live log output
- **feat**: Sidebar icons `transform` (migrate) and `construction` (build)
- **fix**: `app.component.ts` Tab type extended with `migrate` and `build`

### Tauri Backend (Rust)
- **feat**: `commands/build.rs` — `check_pbgen()` + `build_pb_application()`
- **fix**: `commands/mod.rs` — registered `build` module
- **fix**: `lib.rs` — registered `check_pbgen` and `build_pb_application` Tauri commands

### Core (Rust)
- **fix**: `MigrateResult` — added `components`, `services`, `models` alias fields
  - `components = window_count`
  - `services = function_count`
  - `models = dw_count`

### Docs
- **update**: `FUNCTION_MATRIX.md` — Desktop coverage 20/20 → 22/22 (100%)
- **update**: `README.md` — bilingual coverage stats synchronized
- **add**: `RELEASE_v2.2.1.md` — this file

---

## Contributors

- 大虾 (sugitter) — Project Lead & Architect

---

## Links

- **GitHub**: https://github.com/sugitter/pb-devkit
- **Issues**: https://github.com/sugitter/pb-devkit/issues
- **1.x Python CLI**: `pb-devkit-1.x/`
- **2.x Rust + Tauri**: `pb-devkit-2.x/`
