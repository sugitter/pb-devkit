# PB DevKit 2.2.1

> PowerBuilder Legacy System Toolkit / PowerBuilder 遗留系统工具包

[English](#english) | [中文](#中文)

---

## English

### Overview

PB DevKit 2.2 is a modern toolkit for analyzing, maintaining, and migrating PowerBuilder legacy systems. Built with Rust for core parsing and Tauri + Angular for the desktop application.

### Features

| Category | Features |
|----------|----------|
| **PBL Parsing** | Parse, list, export PBL files (PB5-PB12.6, ANSI/Unicode) |
| **PE Analysis** | Detect file type, analyze PE headers, extract PBD from EXE |
| **Decompile** | Restore PowerScript source from PBD/EXE |
| **Search** | Full-text search, search by object type |
| **DataWindow** | Analyze SQL, table structure, column relationships |
| **Project** | Detect projects, find PBL files, environment diagnostics |

### Architecture

```
pb-devkit-2.x/
├── pb-devkit-core/      # Rust core library (zero-dependency parsing)
├── pb-devkit-cli/       # Command-line interface (30 commands)
├── pb-devkit-desktop/   # Tauri + Angular desktop application
```

### Quick Start

#### CLI Usage

```bash
# Parse a PBL file
pbdevkit parse myapp.pbl

# List all entries
pbdevkit list myapp.pbl

# Analyze PE file
pbdevkit analyze-pe myapp.exe

# Detect project
pbdevkit project C:/projects/myapp

# Run environment diagnostics
pbdevkit doctor

# Interactive mode
pbdevkit interactive
```

#### Desktop Application

```bash
cd pb-devkit-desktop
npm install
npm run tauri dev
```

### Command Coverage

| Category | CLI | Desktop |
|----------|-----|---------|
| PBL parse/info/list/export | ✅ | ✅ |
| PE analyze/extract/file-type | ✅ | ✅ |
| Search / Search by type / Regex | ✅ | ✅ |
| DataWindow analyze/SQL/enhanced | ✅ | ✅ |
| Decompile / list / batch | ✅ | ✅ |
| Report / export / stats | ✅ | ✅ |
| Project detect/find-PBL/doctor | ✅ | ✅ |
| Code Engineering: diff/workflow/refactor/snapshot/review | ✅ | ✅ |
| Migration: migrate (PB→Angular scaffold) | ✅ | ✅ |
| Build: build (PBGen.exe compiler) | ✅ | ✅ |

**Current coverage**: 30/30 CLI commands (100%), 22/22 Desktop panels (100%)

### Tech Stack

- **Core**: Rust (no external dependencies for PBL/PBD/PE parsing)
- **CLI**: Rust + rustyline (interactive REPL)
- **Desktop**: Tauri 2.x + Angular 17+ (standalone components, control flow syntax)
- **Frontend**: Angular Signals, CSS variables, Material Icons

### Roadmap

- [x] **v2.2.0** — PE info view UI ✅
- [x] **v2.2.0** — Project statistics panel ✅
- [x] **v2.2.1** — autoexport/migrate/build 移植（CLI + Desktop 100%）✅
- [x] **v2.2.1** — refactor/snapshot/review（CLI 三命令 + Desktop 三面板 100%）✅
- [ ] **v2.2.2 (Planning)** DataWindow SQL 解析完善（嵌套查询、子查询、UNION、参数绑定）
- [ ] **v2.2.2 (Planning)** 批量导出进度显示（CLI 进度条 + Desktop 进度 Modal）
- [ ] **v2.2.2 (Planning)** PBL 版本检测增强（自动检测版本、区分 ANSI/Unicode、PB 12.5+）
- [ ] **v2.2.2 (Planning)** 搜索性能优化（并行搜索、索引文件、增量搜索）
- [ ] ORCA engine integration (requires PBSpyORCA.dll)

---

## 中文

### 概述

PB DevKit 2.2 是用于分析、维护和迁移 PowerBuilder 遗留系统的现代化工具包。采用 Rust 构建核心解析引擎，Tauri + Angular 构建桌面应用。

### 功能特性

| 类别 | 功能 |
|------|------|
| **PBL 解析** | 解析、列出、导出 PBL 文件（支持 PB5-PB12.6，ANSI/Unicode） |
| **PE 分析** | 检测文件类型、分析 PE 头、从 EXE 提取 PBD |
| **反编译** | 从 PBD/EXE 还原 PowerScript 源码 |
| **搜索** | 全文搜索、按对象类型搜索 |
| **DataWindow** | 分析 SQL、表结构、列引用关系 |
| **项目管理** | 检测项目、查找 PBL 文件、环境诊断 |

### 项目架构

```
pb-devkit-2.x/
├── pb-devkit-core/      # Rust 核心库（零依赖 PBL/PBD/PE 解析）
├── pb-devkit-cli/       # 命令行工具（30 条命令）
├── pb-devkit-desktop/   # Tauri + Angular 桌面应用
```

### 快速开始

#### CLI 使用

```bash
# 解析 PBL 文件
pbdevkit parse myapp.pbl

# 列出所有条目
pbdevkit list myapp.pbl

# 分析 PE 文件
pbdevkit analyze-pe myapp.exe

# 检测项目
pbdevkit project C:/projects/myapp

# 环境诊断
pbdevkit doctor

# 交互模式
pbdevkit interactive
```

#### 桌面应用

```bash
cd pb-devkit-desktop
npm install
npm run tauri dev
```

### 命令覆盖

| 类别 | CLI | Desktop |
|------|-----|---------|
| PBL 解析/列表/导出 | ✅ | ✅ |
| PE 分析/提取/文件类型 | ✅ | ✅ |
| 搜索 / 按类型搜索 / 正则 | ✅ | ✅ |
| DataWindow 分析/SQL/增强 | ✅ | ✅ |
| 反编译 / 列表 / 批量 | ✅ | ✅ |
| 报告 / 导出 / 统计 | ✅ | ✅ |
| 项目检测/查找 PBL/环境诊断 | ✅ | ✅ |
| 代码工程: diff/workflow/refactor/snapshot/review | ✅ | ✅ |
| 迁移向导: migrate (PB→Angular 脚手架) | ✅ | ✅ |
| 构建面板: build (PBGen.exe 编译器) | ✅ | ✅ |

**当前覆盖率**：30/30 CLI 命令（100%），22/22 Desktop 面板（100%）

### 技术栈

- **核心引擎**：Rust（零外部依赖的 PBL/PBD/PE 解析）
- **命令行**：Rust + rustyline（交互式 REPL）
- **桌面应用**：Tauri 2.x + Angular 17+（独立组件，控制流语法）
- **前端**：Angular Signals、CSS 变量、Material Icons

### 开发计划

- [x] **v2.2.0** — PE 信息视图 UI ✅
- [x] **v2.2.0** — 项目统计面板 ✅
- [x] **v2.2.1** — autoexport/migrate/build 移植（CLI + Desktop 100%）✅
- [x] **v2.2.1** — refactor/snapshot/review（CLI 三命令 + Desktop 三面板 100%）✅
- [ ] **v2.2.2 (规划中)** DataWindow SQL 解析完善（嵌套查询、子查询、UNION、参数绑定）
- [ ] **v2.2.2 (规划中)** 批量导出进度显示（CLI 进度条 + Desktop 进度 Modal）
- [ ] **v2.2.2 (规划中)** PBL 版本检测增强（自动检测版本、区分 ANSI/Unicode、PB 12.5+）
- [ ] **v2.2.2 (规划中)** 搜索性能优化（并行搜索、索引文件、增量搜索）
- [ ] ORCA 引擎集成（需要 PBSpyORCA.dll）

### License / 许可证

MIT License