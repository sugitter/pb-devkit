# PB DevKit 2.0

> PowerBuilder Legacy System Toolkit / PowerBuilder 遗留系统工具包

[English](#english) | [中文](#中文)

---

## English

### Overview

PB DevKit 2.0 is a modern toolkit for analyzing, maintaining, and migrating PowerBuilder legacy systems. Built with Rust for core parsing and Tauri + Angular for the desktop application.

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
├── pb-devkit-cli/       # Command-line interface (20 commands)
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

| Command | CLI | Desktop |
|---------|-----|---------|
| PBL parse/info/list/export | ✅ | ✅ |
| PE analyze/extract | ✅ | ✅ |
| Search / Search by type | ✅ | ✅ |
| DataWindow analyze/SQL | ✅ | ✅ |
| Decompile | ✅ | ✅ |
| Report generation | ✅ | ✅ |
| Project detect/find-PBL | ✅ | ✅ |
| Environment doctor | ✅ | ✅ |

**Current coverage**: 20/20 CLI commands (100%), 22/28 Desktop features (79%)

### Tech Stack

- **Core**: Rust (no external dependencies for PBL/PBD/PE parsing)
- **CLI**: Rust + rustyline (interactive REPL)
- **Desktop**: Tauri 2.x + Angular 17+ (standalone components, control flow syntax)
- **Frontend**: Angular Signals, CSS variables, Material Icons

### Roadmap

- [ ] ORCA engine integration (requires PBSpyORCA.dll)
- [ ] PE info view UI
- [ ] Project statistics panel
- [ ] Advanced features: refactor, review, snapshot, workflow

---

## 中文

### 概述

PB DevKit 2.0 是用于分析、维护和迁移 PowerBuilder 遗留系统的现代化工具包。采用 Rust 构建核心解析引擎，Tauri + Angular 构建桌面应用。

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
├── pb-devkit-cli/       # 命令行工具（20 条命令）
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

| 命令 | CLI | Desktop |
|------|-----|---------|
| PBL 解析/列表/导出 | ✅ | ✅ |
| PE 分析/提取 | ✅ | ✅ |
| 搜索 / 按类型搜索 | ✅ | ✅ |
| DataWindow 分析/SQL | ✅ | ✅ |
| 反编译 | ✅ | ✅ |
| 报告生成 | ✅ | ✅ |
| 项目检测/查找 PBL | ✅ | ✅ |
| 环境诊断 | ✅ | ✅ |

**当前覆盖率**：20/20 CLI 命令（100%），22/28 Desktop 功能（79%）

### 技术栈

- **核心引擎**：Rust（零外部依赖的 PBL/PBD/PE 解析）
- **命令行**：Rust + rustyline（交互式 REPL）
- **桌面应用**：Tauri 2.x + Angular 17+（独立组件，控制流语法）
- **前端**：Angular Signals、CSS 变量、Material Icons

### 开发计划

- [ ] ORCA 引擎集成（需要 PBSpyORCA.dll）
- [ ] PE 信息视图 UI
- [ ] 项目统计面板
- [ ] 高级功能：重构、审查、快照、工作流

### License / 许可证

MIT License