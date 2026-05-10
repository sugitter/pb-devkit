# PB DevKit — PowerBuilder Legacy System Toolkit

PB DevKit is a toolkit for analyzing, parsing, and decompiling PowerBuilder legacy systems — **without launching the PB IDE**.

**Supported versions**: PB 5 ~ PB 12.6 (ANSI + Unicode)

---

PB DevKit 是一套无需打开 PowerBuilder IDE，即可完成 PBL/PBD/EXE 解析、源码导出、代码搜索、DataWindow 分析、反编译全流程的工具包。

**适用版本**：PB 5 ~ PB 12.6（ANSI + Unicode 均支持）

---

## ✨ Features / 功能特性

| Feature / 功能 | Description / 说明 |
|----------------|-------------------|
| 📁 PBL/PBD Parser | Parse library files, list objects, export source code |
| 📁 PBL/PBD 解析 | 解析库文件，列出对象，导出源码 |
| 🔍 Full-text Search | Search PowerScript code across exported sources |
| 🔍 全文搜索 | 在导出的源码中搜索 PowerScript 代码 |
| 📊 DataWindow Analysis | Extract SQL, tables, and columns from DW objects |
| 📊 DataWindow 分析 | 提取 DW 对象的 SQL、引用表和列 |
| 📦 Decompiler | Extract source from EXE/PBD using ORCA |
| 📦 反编译 | 从 EXE/PBD 提取源码（需 ORCA DLL） |
| 🖥️ Desktop GUI | Tauri + Angular cross-platform desktop app |
| 🖥️ 桌面图形界面 | Tauri + Angular 跨平台桌面应用 |
| 🔧 Doctor | Diagnose Python/Rust/ORCA DLL environment |
| 🔧 环境诊断 | 检查 Python/Rust/ORCA DLL 状态 |

---

## 🏗️ Architecture (v2.x) / 架构（v2.x）

```
pb-devkit/
├── pb-devkit-2.x/
│   ├── pb-devkit-core/        ← Rust core library (PBL/PBD/PE/DW parser)
│   │                            Rust 核心库（PBL/PBD/PE/DW 解析）
│   ├── pb-devkit-cli/         ← CLI tool (20 commands, interactive REPL)
│   │                            CLI 命令行工具（20 个命令，支持交互式 REPL）
│   └── pb-devkit-desktop/    ← Tauri + Angular desktop GUI
│                                 Tauri + Angular 桌面图形界面
└── docs/                      ← Documentation / 使用文档
```

| Component / 组件 | Tech Stack / 技术栈 | Description / 说明 |
|-------------------|---------------------|---------------------|
| `pb-devkit-core` | Rust | Zero-dependency parse engine, shared by CLI & Desktop |
| `pb-devkit-cli` | Rust + Clap | 20 commands with interactive REPL |
| `pb-devkit-desktop` | Tauri v2 + Angular 17+ | Cross-platform desktop GUI |

> **v1.x (Python)** is in the repo root and still works, but is no longer actively maintained.
> **1.x（Python）版本**位于仓库根目录，仍可使用但不再积极维护。

---

## 🚀 Quick Start / 快速开始

### Option 1: Desktop GUI (Recommended) / 方式一：桌面 GUI（推荐）

```bash
cd pb-devkit-2.x/pb-devkit-desktop
cargo tauri build
# Outputs / 生成安装包：
#   - PB DevKit_2.0.0_x64-setup.exe (NSIS)
#   - PB DevKit_2.0.0_x64_en-US.msi (MSI)
```

**GUI Panels / 界面面板：**

| Icon | Panel / 面板 | Description / 说明 |
|------|--------------|---------------------|
| 📁 | Explorer / 资源管理器 | Select PBL/PBD/EXE → browse objects |
| 🔍 | Search / 全文搜索 | Search keywords in exported source code |
| 📊 | DataWindow / 数据窗口 | Analyze DW object SQL, tables, columns |
| 🔧 | Doctor / 环境诊断 | Check Python/Rust/ORCA DLL status |
| 📦 | Decompile / 反编译 | Extract source from EXE/PBD |

### Option 2: CLI / 方式二：命令行

```bash
cd pb-devkit-2.x/pb-devkit-cli
cargo build --release
./target/release/pbdevkit --help

# Interactive mode (recommended) / 交互模式（推荐）
./target/release/pbdevkit interactive
```

---

## 📋 CLI Commands / CLI 命令一览

### PBL Operations / PBL 操作

| Command | Description |
|---------|-------------|
| `parse <pbl>` | Parse PBL file / 解析 PBL 文件 |
| `info <pbl>` | Show PBL metadata / 获取 PBL 元信息 |
| `list <pbl>` | List all objects / 列出所有对象 |
| `export <pbl> <name>` | Export single object source / 导出单个对象源码 |
| `export-pbl <pbl> <dir> [--by-type]` | Batch export / 批量导出 |

### PE Analysis (EXE/DLL) / PE 分析（EXE/DLL）

| Command | Description |
|---------|-------------|
| `file-type <file>` | Detect file type / 检测文件类型 |
| `analyze-pe <file>` | Analyze PE structure / 分析 PE 结构 |
| `extract-pbd <exe> <dir>` | Extract embedded PBD from EXE / 从 EXE 提取嵌入的 PBD |

### Project / Search / DataWindow / Decompile / Report

```bash
pbdevkit project       <path>        # Detect PB project / 检测 PB 项目
pbdevkit find-pbl      <path>        # Recursively find PBLs / 递归查找 PBL
pbdevkit search        <path> <q>    # Full-text search / 全文搜索
pbdevkit analyze-dw    <path>        # DW SQL analysis / DW SQL 分析
pbdevkit decompile-all <file> <dir>  # Batch decompile / 批量反编译
pbdevkit report        <path>        # Generate project report / 生成项目报告
pbdevkit doctor                       # Environment diagnostics / 环境诊断
```

---

## 🔧 Decompiler / ORCA Requirement / 反编译器 / ORCA 要求

Decompiling PBD/EXE requires **PBSpyORCA.dll** (PowerBuilder ORCA API).

反编译 PBD/EXE 需要 **PBSpyORCA.dll**（PowerBuilder ORCA API）。

- PB 9/10.5/11.x → place DLLs in `pb-devkit-core/orca/`
- PB 12.x → place DLLs in `pb-devkit-core/orca/`
- The Doctor panel will auto-detect ORCA availability.
- Doctor 面板会自动检测 ORCA 是否可用。

---

## 🤔 Why This Tool? / 为什么需要这个工具？

PowerBuilder was the dominant enterprise development tool from the 1990s to 2010s. Countless systems in finance, healthcare, hospitality, and retail are still running — but face serious challenges:

PowerBuilder 在 1990s~2010s 是企业级系统的主流开发工具。大量金融、医疗、酒店、零售等行业旧系统仍在运行，但面临：

- **Knowledge loss** — Maintenance staff left, documentation is missing
- **知识断层** — 维护人员流失，文档缺失
- **IDE barriers** — PB IDE is heavy, hard to set up, version-conflicted
- **IDE 障碍** — PB IDE 体积庞大，环境搭建困难，版本冲突
- **Modernization needs** — AI-assisted migration requires source access
- **现代化需求** — AI 辅助迁移需要源码访问

PB DevKit lets developers and AI Agents work with PB systems **without installing the PB IDE**:

PB DevKit 让开发者和 AI Agent 无需安装 PB IDE 即可：

- Parse PBL/PBD library files, extract object lists and source code
- 解析 PBL/PBD 库文件，提取对象列表和源码
- Extract embedded PBD resources and decompile source from EXE/DLL
- 从 EXE/DLL 提取嵌入的 PBD 资源和反编译源码
- Analyze SQL statements, referenced tables and columns in DataWindow objects
- 分析 DataWindow 对象的 SQL 语句、引用表和列
- Full-text search PowerScript code
- 全文搜索 PowerScript 代码
- Generate project structure reports to assist migration assessment
- 生成项目结构报告，辅助迁移评估

---

## 🛠️ Build Requirements / 构建要求

| Component / 组件 | Requirement / 要求 |
|-------------------|-------------------|
| `pb-devkit-core` | Rust 1.75+ |
| `pb-dev-kit-cli` | Rust 1.75+ |
| `pb-devkit-desktop` | Rust 1.75+ + Node.js 18+ + Angular CLI |
| ORCA features (optional) | PBSpyORCA.dll |

---

## 📦 Installation / 安装

### From Release / 从 Release 安装

Download pre-built installers from the [Releases](https://github.com/sugitter/pb-devkit/releases) page.

从 [Releases](https://github.com/sugitter/pb-devkit/releases) 页面下载预构建安装包。

### Build from Source / 从源码构建

```bash
# Clone the repository / 克隆仓库
git clone https://github.com/sugitter/pb-devkit.git
cd pb-devkit/pb-devkit-2.x

# Build CLI / 构建命令行工具
cd pb-devkit-cli && cargo build --release

# Build Desktop GUI / 构建桌面图形界面
cd ../pb-devkit-desktop
cargo tauri build
```

---

## 🤝 Contributing / 贡献

Contributions are welcome! Feel free to submit PRs or open issues.

欢迎贡献！欢迎提交 PR 或开 Issue。

1. Fork the repository / Fork 仓库
2. Create a feature branch / 创建功能分支
3. Submit a pull request / 提交 Pull Request

---

## 📄 License / 开源协议

[MIT License](LICENSE)

---

## 👤 Author / 作者

[sugitter](https://github.com/sugitter)

> If this tool helps with your legacy system maintenance, please ⭐ Star to support!
> 如果本工具对您的遗留系统维护有帮助，欢迎 ⭐ Star 支持！

---

## ⚠️ Disclaimer / 免责声明

This tool is for **legal analysis and maintenance of systems you own or have permission to analyze**. Decompiling third-party PB applications without permission may violate copyright.

本工具仅用于**合法分析和维护您拥有或已获得分析许可的系统**。未经许可反编译第三方 PB 应用程序可能侵犯版权。
