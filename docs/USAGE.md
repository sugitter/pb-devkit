# PB DevKit 完整使用指南

> **版本**: v1.2.0 | **协议**: MIT | **零外部依赖**（纯 Python 标准库）

PB DevKit 是一套完整的 PowerBuilder 旧系统现代化工具链，包含 **CLI 命令行工具** + **VS Code 插件** + **JetBrains IDEA 插件**，让你不打开 PB IDE 也能高效维护 PB 项目。

---

## 目录

1. [安装](#1-安装)
2. [CLI 命令行工具](#2-cli-命令行工具)
3. [版本快照工作流](#3-版本快照工作流)
4. [现代 IDE 开发](#4-现代-ide-开发)
   - 4.1 [VS Code 插件](#41-vs-code-插件)
   - 4.2 [JetBrains IDEA 插件](#42-jetbrains-idea-插件)
5. [完整工作流程](#5-完整工作流程)
6. [项目配置](#6-项目配置)
7. [代码分析规则](#7-代码分析规则)
8. [常见问题](#8-常见问题)

---

## 1. 安装

### 1.1 CLI 工具（必需）

```bash
# 克隆项目
git clone https://github.com/yourname/pb-devkit.git
cd pb-devkit

# 安装为可执行命令（推荐）
pip install -e .

# 之后直接用 pb 命令
pb --version
# 输出: PB DevKit 1.2.0

# 或者直接运行
python pb.py --help
```

**环境要求**: Python 3.9+，无任何外部依赖。

### 1.2 PBORCA DLL（可选，用于导入/编译）

```bash
# 下载 PBSpyORCA（MIT 协议，支持 PB5-PB2025）
# https://github.com/Hucxy/PBSpyORCA/releases
# 下载后放入 orca/ 目录：
copy PBSpy.dll orca\PBSpy.dll

# 验证
pb doctor
```

> 不安装 DLL 也能使用 export/analyze/search/refactor/report/stats/snapshot/diff 等核心功能。只有 import/build/compile 需要 DLL。

### 1.3 VS Code 插件

```bash
cd vscode-extension
npm install -g @vscode/vsce
vsce package
# 生成 powerscript-1.0.0.vsix

# 安装：VS Code → Extensions → ⋯ → Install from VSIX → 选择 .vsix
# 或命令行：code --install-extension powerscript-1.0.0.vsix
```

### 1.4 JetBrains IDEA 插件

```bash
cd idea-plugin

# 构建（需要 JDK 17+）
gradlew buildPlugin
# 生成 build/distributions/powerscript-1.0.0.zip

# 安装：IDEA → Settings → Plugins → ⚙️ → Install from disk → 选择 .zip

# 或者直接在沙箱 IDE 中测试
gradlew runIde
```

**兼容 IDE**: IntelliJ IDEA / WebStorm / PyCharm / DataGrip / PhpStorm 2023.2+

---

## 2. CLI 命令行工具

### 2.1 命令总览

```
pb <command> [arguments] [options]
```

| 命令 | 说明 | 需要 ORCA |
|------|------|:---:|
| `pb doctor [dir]` | 环境诊断（Python/DLL/模块） | 否 |
| `pb init <dir>` | 初始化项目（识别 PB 项目结构） | 否 |
| `pb list <pbl_or_dir>` | 列出 PBL 中的对象 | 可选 |
| `pb export <pbl_or_dir> [out]` | 导出 PBL 源码为 .sr* 文件 | 可选 |
| `pb analyze <dir>` | 代码质量分析 | 否 |
| `pb analyze-project <dir>` | 完整项目分析（依赖图+复杂度） | 否 |
| `pb search <pattern> <dir>` | 全文搜索（文本/SQL/函数） | 否 |
| `pb stats <dir>` | 项目统计仪表盘 | 否 |
| `pb report <dir>` | 生成 Markdown 分析报告 | 否 |
| `pb refactor <dir>` | 自动重构（支持 dry-run） | 否 |
| `pb diff <dir1> <dir2>` | 比较两份源码 | 否 |
| `pb snapshot <pbl> [out]` | 版本快照（导出+对比+git） | 可选 |
| `pb workflow <pbl> [dir]` | 全流程：导出→分析→重构 | 否 |
| `pb import <pbl> <dir>` | 导入 .sr* 文件到 PBL | 是 |
| `pb build <pbl> <app>` | 全量重建应用 | 是 |
| `pb compile <pbl> <dir>` | 导入+重建一步完成 | 是 |

所有命令支持 `--json` 输出 JSON，`--verbose` / `-v` 显示详情。

### 2.2 环境诊断

```bash
# 检查 Python 环境、模块加载、ORCA DLL
pb doctor

# 检查指定项目
pb doctor F:\workspace\X6\3.5
```

输出示例：
```
✓ Python 3.12.0
✓ pb_devkit 模块加载正常
✗ PBORCA DLL 未找到 (orca/PBSpy.dll)
  → import/build/compile 命令不可用
  → 下载: https://github.com/Hucxy/PBSpyORCA/releases

项目检查: F:\workspace\X6\3.5
  ✓ 找到 12 个 PBL 文件
  ✓ 找到 dgsauna.pbt
```

### 2.3 项目初始化

```bash
# 自动识别 PB 项目结构
pb init F:\path\to\project

# JSON 格式输出
pb init F:\path\to\project --json
```

### 2.4 导出 PBL

```bash
# 导出单个 PBL
pb export dgsauna.pbl ./src

# 导出整个目录下的所有 PBL（递归）
pb export F:\workspace\X6\3.5 ./src

# 使用 ORCA 导出（更精确，支持 PB12+）
pb export dgsauna.pbl ./src --orca

# 去掉 $PBExportHeader$ 行
pb export dgsauna.pbl ./src --no-headers
```

### 2.5 列出对象

```bash
# 列出 PBL 中所有对象
pb list dgsauna.pbl

# 列出目录下所有 PBL 的对象
pb list F:\workspace\X6\3.5

# JSON 输出
pb list dgsauna.pbl --json
```

### 2.6 代码分析

```bash
# 分析指定目录下的 .sr* 文件
pb analyze ./src

# 只分析 Window 类型
pb analyze ./src -t WIN

# JSON 输出
pb analyze ./src --json

# 完整项目分析（含依赖图和复杂度评级）
pb analyze-project ./src --json
```

### 2.7 全文搜索

```bash
# 文本搜索（默认）
pb search "uf_login" ./src

# SQL 模式搜索
pb search "employee" ./src --mode sql

# 函数搜索
pb search "uf_calculate" ./src --mode function

# 按对象类型过滤
pb search "open" ./src -t WIN

# 大小写敏感
pb search "SQLCA" ./src --case-sensitive
```

### 2.8 项目统计

```bash
pb stats ./src

# JSON 输出
pb stats ./src --json
```

输出示例：
```
═══════════════════════════════════════
  PB DevKit — Project Statistics
═══════════════════════════════════════

  Files:         156
  Total Lines:   45,230
  Routines:      1,842

  Type Distribution:
    Window       42 files (26.9%)
    UserObject   38 files (24.4%)
    DataWindow   31 files (19.9%)
    Function     28 files (17.9%)
    Menu         12 files (7.7%)
    Other         5 files (3.2%)

  Complexity Distribution:
    A (1-5)      1,102 (59.8%)
    B (6-10)       389 (21.1%)
    C (11-15)      198 (10.7%)
    D (16-20)       98 (5.3%)
    E (21-30)       42 (2.3%)
    F (31+)         13 (0.7%)
```

### 2.9 代码重构

```bash
# 预览模式（只看不改）
pb refactor ./src

# 详细显示每个文件的建议
pb refactor ./src -v

# 应用重构
pb refactor ./src --apply

# 只应用特定规则
pb refactor ./src --apply --rules fix_empty_catch,fix_deprecated
```

### 2.10 差异对比

```bash
# 对比两个导出目录
pb diff ./src-v1 ./src-v2

# 详细显示变更
pb diff ./src-v1 ./src-v2 -v

# JSON 输出
pb diff ./src-v1 ./src-v2 --json
```

### 2.11 生成报告

```bash
# 生成 Markdown 分析报告
pb report ./src

# 输出到指定文件
pb report ./src -o ./CODE_REVIEW.md

# JSON 输出
pb report ./src --json
```

### 2.12 一键全流程

```bash
# 导出 → 分析 → 重构（预览）
pb workflow dgsauna.pbl

# 导出 → 分析 → 重构（应用）
pb workflow dgsauna.pbl --apply
```

### 2.13 导入和编译（需要 ORCA DLL）

```bash
# 导入 .sr* 文件到 PBL
pb import dgsauna.pbl ./src

# 全量构建 EXE
pb build dgsauna.pbl dgsauna --exe dgsauna.exe

# 一步完成导入+编译
pb compile dgsauna.pbl ./src
```

---

## 3. 版本快照工作流

`pb snapshot` 是版本追踪的核心命令，一条命令完成 **导出 → 差异对比 → Git 提交**。

### 3.1 基本用法

```bash
# 快照单个 PBL
pb snapshot dgsauna.pbl ./src

# 快照整个项目（目录下所有 PBL）
pb snapshot F:\workspace\X6\3.5 ./src
```

**执行流程：**
1. 导出 PBL 到 `./src/` 目录（.sr* 文本文件）
2. 与上一次快照对比（added/removed/modified）
3. 在 `.pb-snapshots/` 目录保存快照元数据
4. 自动 `git add` + `git commit`（commit message 包含变更摘要）

### 3.2 选项

```bash
# 自定义 commit message
pb snapshot dgsauna.pbl ./src -m "修复登录窗口 bug"

# 不执行 git 操作（只导出+对比）
pb snapshot dgsauna.pbl ./src --no-git

# 不对比差异（只导出+git）
pb snapshot dgsauna.pbl ./src --no-diff

# 详细显示所有变更文件
pb snapshot dgsauna.pbl ./src -v

# JSON 格式输出差异报告
pb snapshot dgsauna.pbl ./src --json

# 使用 ORCA 导出
pb snapshot dgsauna.pbl ./src --orca

# 自定义快照元数据目录
pb snapshot dgsauna.pbl ./src --snapshot-dir .pb-history
```

### 3.3 快照元数据

快照信息保存在 `.pb-snapshots/` 目录：

```
.pb-snapshots/
├── latest.json       # 最新快照信息
└── history.jsonl     # 历史记录（每行一个 JSON）
```

`latest.json` 示例：
```json
{
  "timestamp": "2026-04-14T13:00:00",
  "targets": ["dgsauna.pbl"],
  "output_dir": "./src",
  "files_count": 156,
  "diff": {
    "added": ["n_cst_log.sru", "f_encrypt.srf"],
    "removed": [],
    "modified": ["w_main.srw", "n_cst_app.sru"],
    "unchanged": 152
  }
}
```

### 3.4 推荐的 .gitignore

```gitignore
# PB 二进制文件（由文本重新生成）
*.pbl
*.pbd
*.exe
*.dll

# 快照元数据（自动维护）
.pb-snapshots/

# 导出临时目录（如果用 snapshot 则不需要忽略 src/）
# exported/
```

---

## 4. 现代 IDE 开发

### 4.1 VS Code 插件

**安装后自动支持的功能：**

| 功能 | 说明 |
|------|------|
| 🔤 语法高亮 | 关键字/类型/字符串/注释/嵌入式 SQL/DW 表达式/PB 枚举常量/SQLCA |
| 🔍 实时 Lint | 10 条规则，编辑时自动检测（与 CLI 完全一致） |
| ✨ 自动补全 | 80+ 项（关键字+类型+PB 函数+对象方法），输入即触发 |
| 💡 悬停提示 | 悬停关键字/函数查看类型说明和语法 |
| 🎯 智能编辑 | 自动缩进、括号匹配、`//`/`'` 注释切换、代码折叠 |
| 📦 13 种文件 | .srw .sru .srd .srf .srm .sra .srs .srq .srp .srj .srx .sre .src |

**自定义设置：**

打开 VS Code 设置（`Ctrl+,`），搜索 `pb-devkit`：

```json
{
  "pb-devkit.maxRoutineLines": 200,
  "pb-devkit.maxComplexity": 20,
  "pb-devkit.maxNesting": 4
}
```

**配合 AI 工具使用：**

安装插件后，Copilot / Continue / Cursor 等 AI 工具能自动识别 PowerScript 语法，提供更精准的代码补全和建议。

### 4.2 JetBrains IDEA 插件

**安装后自动支持的功能：**

| 功能 | 说明 |
|------|------|
| 🔤 语法高亮 | 手写词法分析器，关键字/类型/字符串/注释/嵌入式 SQL/SQLCA |
| 🔍 Lint 诊断 | 10 条规则，在 Problems 面板实时显示 |
| ✨ 自动补全 | 130+ 项（关键字+类型+PB 函数+对象方法），`Ctrl+Space` 触发 |
| 💡 悬停文档 | `Ctrl+Q` 查看类型说明、SQLCA 属性、函数语法 |
| 🎯 智能编辑 | 注释切换（`Ctrl+/`）、括号匹配、自动缩进、代码折叠 |
| 🛠 Tools Menu | `Tools → Run PowerScript Lint` 手动触发分析 |
| 📦 13 种文件 | 同 VS Code |

**快捷键：**

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Space` | 代码补全 |
| `Ctrl+Q` | 悬停文档 |
| `Ctrl+/` | 注释切换 |
| `Ctrl+F` | 全局搜索 |
| `Ctrl+Shift+F` | 项目范围搜索 |
| `Ctrl+Alt+L` | 格式化（如有语言支持） |

---

## 5. 完整工作流程

### 5.1 从零开始（老项目上现代化）

```bash
# 第一步：初始化
pb init F:\workspace\X6\3.5

# 第二步：首次快照（导出 + git）
pb snapshot F:\workspace\X6\3.5 ./src

# 第三步：用现代 IDE 打开 ./src/
# VS Code: code ./src
# IDEA:    idea ./src

# 第四步：编辑代码...
# 现在可以享受语法高亮、Lint、补全、Git 版本管理

# 第五步：再次快照（对比 + 提交）
pb snapshot F:\workspace\X6\3.5 ./src

# 第六步：最终编译（需要 ORCA DLL）
pb compile dgsauna.pbl ./src
```

### 5.2 日常开发循环

```
  ① pb snapshot       导出 PBL → 对比差异 → git commit
  ② VS Code / IDEA    编辑代码（语法高亮 + Lint + 补全）
  ③ pb analyze        检查代码质量
  ④ pb refactor       自动修复问题
  ⑤ pb snapshot       再次快照 → 对比 → commit
  ⑥ pb compile        编译最终可执行文件
```

### 5.3 纯文本工作流（不依赖 PB IDE）

```
PBL (二进制)                    现代开发环境
    │                              │
    ├─ pb export ──→ .sr* 文本 ──→ VS Code / IDEA
    │                              │
    │                    git diff / blame / merge
    │                    AI Copilot / Continue
    │                    全局搜索 / 批量替换
    │                              │
    └─ pb import ←── .sr* 文本 ←──┘
         │
         └─ pb build → .exe
```

**核心理念：PBL 只是编译产物，.sr* 文本才是源码真相。**

推荐的项目结构：

```
my-pb-project/
├── src/                ← git 管理这里（.sr* 文本文件）
│   ├── w_main.srw
│   ├── n_cst_util.sru
│   ├── d_employee.srd
│   └── ...
├── pbl/                ← .gitignore（编译产物）
│   └── dgsauna.pbl
├── output/             ← .gitignore
│   └── dgsauna.exe
├── .pb-snapshots/      ← 快照元数据
├── .pbdevkit.json      ← 项目配置
├── .gitignore
└── CODE_REVIEW.md      ← pb report 生成
```

---

## 6. 项目配置

在项目根目录放置 `.pbdevkit.json`，所有命令自动检测加载：

```json
{
    "pb_version": 125,
    "max_routine_lines": 150,
    "max_complexity": 15,
    "max_nesting": 3,
    "encoding": "gb2312",
    "rules": {
        "enabled": ["fix_empty_catch", "fix_deprecated"],
        "disabled": ["fix_magic_numbers"]
    },
    "naming": {
        "datawindow": "^d_",
        "window": "^w_",
        "menu": "^m_",
        "function": "^(f_|gf_)",
        "userobject": "^(n_|u_)",
        "structure": "^s_"
    }
}
```

CLI 和 VS Code 插件共用同一份配置。

---

## 7. 代码分析规则

### 7.1 质量检查（10 条）

| 级别 | 规则 | 说明 | CLI + IDE |
|------|------|------|:---------:|
| 🔴 E | empty_catch | 空 CATCH 块（无日志记录） | ✅ |
| 🟡 W | routine_too_long | 函数/子程序超过 200 行 | ✅ |
| 🟡 W | deep_nesting | 嵌套深度超过 4 层 | ✅ |
| 🟡 W | high_complexity | 圈复杂度超过 20 | ✅ |
| 🟡 W | deprecated_function | 使用废弃 PB 函数（SetProfileString 等） | ✅ |
| 🟡 W | hardcoded_sql | 脚本中硬编码 SQL | ✅ |
| 🟡 W | select_star | 使用 `SELECT *` | ✅ |
| 🔵 I | global_variable | 使用全局变量（耦合风险） | ✅ |
| 🔵 I | no_error_handling | 函数缺少 try-catch | ✅ |
| 🔵 I | magic_numbers | 使用未命名数字常量 | ✅ |

### 7.2 自动重构规则（5 条）

| 规则 | 安全级别 | 说明 |
|------|---------|------|
| fix_empty_catch | ✅ SAFE | 自动添加错误日志到空 CATCH |
| fix_select_star | ⚠️ MANUAL | 建议列出显式列名 |
| fix_magic_numbers | ⚠️ LIKELY | 建议提取为命名常量 |
| fix_deprecated | ⚠️ LIKELY | 建议替换为推荐 API |
| fix_long_routine | ⚠️ MANUAL | 建议拆分长函数 |

---

## 8. 常见问题

### Q: pb export 导出的文件编码不对？

在 `.pbdevkit.json` 中设置 `"encoding": "gb2312"` 或 `"gbk"`。

### Q: PB12+ 的 PBL 解析失败？

PB11+ 使用 1024 字节头（vs 旧版 512 字节），pb-devkit 已自动适配。如果仍失败，尝试 `--orca` 参数使用 ORCA DLL 导出。

### Q: git diff 中文乱码？

```bash
git config --global core.quotepath false
git config --global gui.encoding utf-8
```

### Q: VS Code 插件没有生效？

确认文件扩展名是 `.srw` / `.sru` / `.srd` 等，不是 `.txt`。右下角状态栏应显示 "PowerScript"。

### Q: IDEA 插件安装后没反应？

确认 build version ≥ 232（2023.2+）。在 Settings → Plugins 中确认插件已启用。

### Q: 如何多人协作？

每人从 git clone 源码（.sr* 文本），在 VS Code / IDEA 中编辑，通过 git merge 解决文本冲突。最后 `pb import` 回各自的 PBL，由一人统一 `pb build` 编译。

### Q: 能处理 PB2025 吗？

纯 Python 解析器支持 PB4-PB12+。PB2025 如需完整支持，建议使用 ORCA DLL（PBSpyORCA 支持 PB5-PB2025）。

---

## 项目结构

```
pb-devkit/
├── pb.py                          # CLI 入口（16 个命令）
├── pyproject.toml                 # 包元数据
├── README.md                      # 项目介绍
├── USAGE.md                       # ← 本文件
├── SKILL.md                       # AI Agent Skill 描述
├── LICENSE                        # MIT License
├── src/pb_devkit/
│   ├── cli.py                     # pip install 后的入口
│   ├── commands/                  # 16 个命令模块
│   │   ├── snapshot.py            # ← 版本快照
│   │   ├── export.py              # ← 导出
│   │   ├── diff.py                # ← 差异对比
│   │   ├── ...                    # ← 其他命令
│   │   └── __init__.py
│   ├── pbl_parser.py              # PBL 二进制解析器
│   ├── sr_parser.py               # .sr* 源码解析 + 分析
│   ├── pborca_engine.py           # PBORCA DLL 封装
│   ├── refactoring.py             # 自动重构引擎
│   ├── config.py                  # 项目配置
│   └── __init__.py
├── vscode-extension/              # VS Code 插件
│   ├── package.json
│   ├── syntaxes/powerscript.tmLanguage.json
│   ├── language-configuration.json
│   ├── src/extension.js
│   └── README.md
├── idea-plugin/                   # JetBrains IDEA 插件
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── src/main/
│   │   ├── resources/META-INF/plugin.xml
│   │   └── java/com/pbdevkit/powerscript/
│   │       ├── PSLexer.java       # 词法分析器
│   │       ├── PSSyntaxHighlighter.java
│   │       ├── completion/        # 130+ 补全
│   │       ├── hover/             # 悬停文档
│   │       ├── inspections/       # 10 条 Lint
│   │       └── actions/           # Tools Menu
│   └── README.md
├── orca/                          # PBSpyORCA.dll（需手动下载）
├── tests/
│   └── test_pb_devkit.py          # 44 个单元测试
└── .gitignore
```

---

## License

MIT
