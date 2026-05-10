# PB DevKit — PowerBuilder Legacy System Toolkit

不用打开 PowerBuilder IDE，在命令行完成 PBL/PBD/EXE 解析、源码导出、代码搜索、DataWindow SQL 提取、反编译全流程。

**适用版本**：PB 5 ~ PB 12.6（ANSI + Unicode 均支持）

---

## 架构（v2.x）

```
pb-devkit/
├── pb-devkit-2.x/
│   ├── pb-devkit-core/        ← Rust 核心库（PBL/PBD/PE/DW 解析）
│   ├── pb-devkit-cli/         ← 命令行工具（20 个命令）
│   └── pb-devkit-desktop/    ← Tauri + Angular 桌面 GUI
└── docs/                      ← 使用文档
```

| 组件 | 技术栈 | 说明 |
|------|--------|------|
| `pb-devkit-core` | Rust | 零依赖解析引擎，被 CLI 和 Desktop 共享调用 |
| `pb-devkit-cli` | Rust + Clap | 20 个命令，支持交互式 REPL |
| `pb-devkit-desktop` | Tauri v2 + Angular 17+ | 跨平台桌面 GUI |

> **1.x（Python）版本**位于仓库根目录，仍可使用但不再积极维护。

---

## 快速开始

### 方式一：桌面 GUI（推荐）

```bash
cd pb-devkit-2.x/pb-devkit-desktop
cargo tauri build
# 生成安装包：
#   - PB DevKit_2.0.0_x64-setup.exe (NSIS)
#   - PB DevKit_2.0.0_x64_en-US.msi (MSI)
```

运行后界面：
- 📁 资源管理器：选择 PBL/PBD/EXE → 浏览对象
- 🔍 全文搜索：在导出的源码中搜索关键字
- 📊 DataWindow：分析 DW 对象的 SQL、表、列
- 🔧 环境诊断：检查 Python/Rust/ORCA DLL 状态
- 📦 反编译：从 EXE/PBD 提取源码

### 方式二：命令行

```bash
cd pb-devkit-2.x/pb-devkit-cli
cargo build --release
./target/release/pbdevkit --help

# 交互模式（推荐）
./target/release/pbdevkit interactive
```

---

## CLI 命令一览

### PBL 操作
| 命令 | 说明 |
|------|------|
| `parse <pbl>` | 解析 PBL 文件 |
| `info <pbl>` | 获取 PBL 元信息 |
| `list <pbl>` | 列出所有对象 |
| `export <pbl> <name>` | 导出单个对象源码 |
| `export-pbl <pbl> <dir> [--by-type]` | 批量导出 |

### PE 分析（EXE/DLL）
| 命令 | 说明 |
|------|------|
| `file-type <file>` | 检测文件类型 |
| `analyze-pe <file>` | 分析 PE 结构 |
| `extract-pbd <exe> <dir>` | 从 EXE 提取嵌入的 PBD |

### 项目 / 搜索 / DataWindow / 反编译 / 报告
```bash
pbdevkit project  <path>        # 检测 PB 项目
pbdevkit find-pbl <path>        # 递归查找 PBL
pbdevkit search   <path> <q>    # 全文搜索
pbdevkit analyze-dw <path>      # DW SQL 分析
pbdevkit decompile-all <file> <dir>  # 批量反编译
pbdevkit report <path>          # 生成项目报告
pbdevkit doctor                  # 环境诊断
```

---

## 为什么需要这个工具

PowerBuilder 在 1990s~2010s 是企业级系统的主流开发工具。大量金融、医疗、酒店、零售等行业旧系统仍在运行，但面临：

- 维护人员流失，知识断层
- 文档缺失，系统行为难以理解
- PB IDE 体积庞大，环境搭建困难

PB DevKit 让开发者和 AI Agent 无需安装 PB IDE 即可：
- 解析 PBL/PBD 库文件，提取对象列表和源码
- 从 EXE/DLL 提取嵌入的 PBD 资源和反编译源码
- 分析 DataWindow 对象的 SQL 语句、引用表和列
- 全文搜索 PowerScript 代码
- 生成项目结构报告，辅助迁移评估

---

## 构建要求

| 组件 | 要求 |
|------|------|
| `pb-devkit-core` | Rust 1.75+ |
| `pb-devkit-cli` | Rust 1.75+ |
| `pb-devkit-desktop` | Rust 1.75+ + Node.js 18+ + Angular CLI |
| ORCA 功能（可选） | PBSpyORCA.dll |

---

## 开源协议

[MIT License](LICENSE)

---

## 作者

[sugitter](https://github.com/sugitter)

> 如果本工具对您的遗留系统维护有帮助，欢迎 ⭐ Star 支持！
