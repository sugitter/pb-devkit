# PB DevKit - PowerBuilder Legacy System Toolkit

> 不用打开 PowerBuilder IDE，在命令行完成 PBL 源码导出、代码梳理、分析、重构、搜索、报告、DataWindow解析、导入、编译全流程。
> 适用于 **PB5 ~ PB12.6** 全系列版本（ANSI + Unicode 均支持）。
>
> **Python API**：纯标准库实现，零外部依赖，`pip install` 非必需。
> **68 个单元测试全部通过**（49 核心 + 19 PEExtractor）。

## 为什么需要这个工具

PowerBuilder 在 1990s~2010s 是企业级数据库管理系统的主流开发工具。大量金融、医疗、酒店、零售等行业旧系统仍在运行。这些系统面临维护人员流失、文档缺失、技术债务积累等挑战。

PB DevKit 让 AI Agent 和开发者能够高效地理解、维护和优化这些旧系统——无需安装庞大的 PB IDE。

## 快速开始

```bash
cd pb-devkit
python pb.py --help
```

### 环境诊断

```bash
# 检查 Python 环境、模块加载、ORCA DLL 是否就绪
python pb.py doctor

# 指定项目路径，额外检查项目文件
python pb.py doctor F:\path\to\project
```

### 项目初始化

```bash
# 自动识别 PB 项目结构（PBL 文件、.pbt/.pbw 等）
python pb.py init F:\path\to\project --json
```

### 常用命令

```bash
# 1. 列出项目中所有 PBL 的对象
python pb.py list F:\path\to\project

# 2a. 智能全量导出（自动检测 PBL/EXE/PBD，推荐入手点）
python pb.py autoexport F:\path\to\project
python pb.py autoexport F:\path\to\project --detect   # 仅检测类型，不导出

# 2b. 手动导出 PBL 源码（--by-type 按类型分目录）
python pb.py export F:\path\to\project ./src --by-type

# 2c. 从 EXE 导出并按推断的 PBL 组织（用于无 PBL 的场景）
python pb.py export app.exe -o ./src --pbl-tree
python pb.py export app.exe -o ./src --pbl-tree --project-name myapp

# 3. 从 EXE/PBD 梳理导出 PowerScript 源码
python pb.py decompile app.exe --list           # 列出所有可导出的对象
python pb.py decompile app.exe --output ./src   # 全量导出，写入 .ps 文件
python pb.py decompile app.exe --entry w_login  # 导出单个对象
python pb.py decompile app.exe --output ./src --resources ./resources  # 导出源码 + 资源

# 4. 项目全面审查报告（结构 + 质量 + DW + 建议）
python pb.py review ./src
python pb.py review ./src --html -o review.html

# 5. DataWindow 专项解析（SQL / 表 / 列 / 引用关系）
python pb.py dw ./src                           # 终端概览
python pb.py dw ./src --sql                     # 输出所有 DW SQL
python pb.py dw ./src --tables                  # 反推数据库表结构
python pb.py dw ./src --html -o dw_report.html  # 交互式 HTML 报告
python pb.py dw ./src --json                    # JSON 输出
python pb.py dw ./src --filter "d_order*"       # 过滤指定 DW

# 6. 完整项目分析（依赖关系 + 复杂度 + 质量报告）
python pb.py analyze-project ./src --json

# 7. 全文搜索
python pb.py search "employee" ./src --mode sql
python pb.py search "uf_login" ./src --mode function -t WIN

# 8. 自动重构（预览 → 应用）
python pb.py refactor ./src/module -v
python pb.py refactor ./src/module --apply -v

# 9. 生成 Markdown 分析报告
python pb.py report ./src -o ./CODE_REVIEW.md

# 10. 一键全流程（导出 → 分析 → 重构）
python pb.py workflow F:\path\to\project\module.pbl --apply

# 11. 导入修改后的源码 + 编译（需要 PBSpyORCA.dll）
python pb.py import module.pbl ./src
python pb.py build module.pbl appname --mode exe           # 单 EXE
python pb.py build module.pbl appname --mode exe+pbd       # EXE + PBD 分离
python pb.py build module.pbl appname --mode exe+dll       # EXE + DLL 分离
```

### 项目配置

在 PB 项目根目录放置 `.pbdevkit.json`，工具会自动检测：

```json
{
    "pb_version": 125,
    "max_routine_lines": 150,
    "max_complexity": 15,
    "rules": {
        "enabled": ["fix_empty_catch", "fix_deprecated"],
        "disabled": ["fix_magic_numbers"]
    },
    "encoding": "gb2312"
}
```

## 安装

### 纯 Python（无需 PB DLL）

```bash
# doctor, init, list, export, analyze, analyze-project, search, report, refactor, diff, workflow 可直接使用
python pb.py doctor
```

### PBORCA 编译（导入/编译/构建 EXE）

```bash
# 1. 下载 PBSpyORCA（MIT 协议，支持 PB5-PB2025）
#    https://github.com/Hucxy/PBSpyORCA/releases
# 2. 复制 PBSpy.dll 到 orca/ 目录
copy PBSpy.dll orca\PBSpy.dll

# 3. 现在可以使用 import, build, compile 命令
python pb.py import module.pbl ./src
python pb.py build module.pbl appname --exe module.exe
```

## 命令参考

| 命令 | 说明 | 需要 ORCA |
|------|------|:---:|
| `pb doctor [dir]` | 环境诊断（Python/DLL/模块） | 否 |
| `pb init <dir>` | 初始化项目（识别 PB 项目结构） | 否 |
| `pb list <pbl_or_dir>` | 列出 PBL 中的对象 | 可选 |
| `pb export <pbl_or_dir> [out]` | 导出 PBL 源码为 .sr* 文件 | 可选 |
| `pb export ... --by-type` | 按对象类型分子目录导出（推荐） | 可选 |
| `pb export <exe> -o <dir> --pbl-tree` | EXE/PBD 代码梳理并按 PBL 组织导出 | 否 |
| `pb autoexport <dir>` | **智能全量导出**：自动检测 PBL/EXE/PBD 类型 + 导出到 src/ | 否 |
| `pb decompile <exe/pbd/pbl>` | **代码梳理**编译产物 → PowerScript | 否 |
| `pb decompile ... --resources <dir>` | 导出源码 + 提取图片/图标等资源文件 | 否 |
| `pb analyze <dir>` | 代码质量分析 | 否 |
| `pb analyze-project <dir>` | 完整项目分析（依赖图+复杂度，自动检测 PBL tree） | 否 |
| `pb search <pattern> <dir>` | 全文搜索（文本/SQL/函数） | 否 |
| `pb stats <dir>` | 项目统计仪表盘 | 否 |
| `pb report <dir>` | 生成 Markdown 分析报告 | 否 |
| `pb review <dir>` | **综合审查报告**（结构/质量/DW清单/改进建议），支持 --html | 否 |
| `pb dw <dir>` | **DataWindow 专项**：SQL提取/表结构反推/引用关系，支持 --html | 否 |
| `pb refactor <dir>` | 自动重构（支持 dry-run） | 否 |
| `pb diff <dir1> <dir2>` | 比较两份源码 | 否 |
| `pb workflow <pbl> [dir]` | 全流程：导出→分析→重构 | 否 |
| `pb snapshot <dir>` | 快照对比（保存/比较源码快照） | 否 |
| `pb import <pbl> <dir>` | 导入 .sr* 文件到 PBL | 是 |
| `pb build <pbl> <app> --mode <mode>` | 全量重建应用（三种编译模式） | 是 |
| `pb compile <pbl> <dir>` | 导入+重建一步完成 | 是 |

**所有命令支持 `--json` 输出结构化 JSON。**

---

## pb build — 三种编译模式

| 模式 | 命令 | 说明 |
|------|------|------|
| `exe`（默认） | `--mode exe` | 全部 PBD 内嵌 EXE，单文件发布 |
| `exe+pbd` | `--mode exe+pbd` | EXE + 分离 PBD 运行时文件 |
| `exe+dll` | `--mode exe+dll` | EXE + PowerBuilder DLL 组件库 |

```bash
# 单 EXE（最简发布，适合小项目）
python pb.py build app.pbl myapp --mode exe --exe myapp.exe

# EXE + PBD（主程序 + 运行时分离，适合多模块项目）
python pb.py build app.pbl myapp --mode exe+pbd \
  --lib-list "app.pbl;lib1.pbl;lib2.pbl" --pbd-libs "lib1,lib2"

# EXE + DLL（组件化，适合插件式架构）
python pb.py build app.pbl myapp --mode exe+dll \
  --lib-list "app.pbl;lib1.pbl" --dll-libs "lib1"

# 附加选项
python pb.py build ... --machine-code   # 机器码编译（更快运行速度）
python pb.py build ... --icon app.ico   # 指定 EXE 图标
python pb.py build ... --rebuild-only   # 只重建不生成 EXE
```

## 技术架构

### 整体结构

```
pb-devkit/
├── pb.py                          # CLI 入口（20 个命令）
├── pyproject.toml                 # 包元数据
├── src/pb_devkit/
│   ├── cli.py                     # pip install 后的 pb 命令入口
│   ├── commands/                  # CLI 命令处理（每命令一文件）
│   │   ├── doctor.py / init.py / list.py / export.py
│   │   ├── analyze.py / analyze_project.py / search.py / stats.py
│   │   ├── report.py / review.py / dw.py   ← 报告 & 审查
│   │   ├── refactor.py / diff.py / workflow.py / snapshot.py
│   │   ├── import_.py / build.py / compile.py   ← 编译链
│   │   ├── decompile.py / autoexport.py
│   │   └── __init__.py
│   ├── pbl_parser.py              # PBL 二进制格式解析器（PB5-PB12.6）
│   ├── chunk_engine.py            # ChunkEngine 通用 PBL 解析引擎
│   ├── pbl_grouper.py             # PBL 分组推断 + 结构化导出（--pbl-tree）
│   ├── project_detector.py        # 项目类型自动检测（PBL/EXE/PBD/混合）
│   ├── sr_parser.py               # .sr* 源码解析 + 分析（质量/依赖/复杂度）
│   ├── pborca_engine.py           # PBORCA DLL 封装（含优雅降级）
│   ├── pe_extractor.py            # PE EXE/DLL → 提取内嵌 PBD
│   ├── decompiler.py              # PBD/PBL/EXE 代码梳理 → PowerScript
│   ├── refactoring.py             # 自动重构引擎（5 条规则）
│   ├── config.py                  # 项目级配置（.pbdevkit.json）
│   └── __init__.py                # 公共 API 导出
├── orca/                          # PBSpyORCA.dll（需手动下载，可选）
├── tests/
│   └── test_pb_devkit.py          # 68 个单元测试
├── SKILL.md                       # WorkBuddy Skill 描述
├── LICENSE                        # MIT License
└── .gitignore
```

### 版本支持矩阵

| PB 版本 | 格式 | HDR* 大小 | 编码 | 支持状态 |
|---------|------|----------|------|---------|
| PB 5.0 ~ 9.x | ANSI | 512 bytes | 系统默认/GB2312 | ✅ 完全支持 |
| PB 10.0 ~ 12.6 | Unicode | 1024 bytes | UTF-16LE | ✅ 完全支持 |
| EXE/PBD（内嵌） | PE 格式 | — | — | ✅ PEExtractor 支持 |

### 核心引擎

```
纯 Python 零依赖
├── ChunkEngine      ── HDR*/NOD*/ENT*/DAT* 完整二进制解析
├── PEExtractor      ── PE EXE/DLL → 内嵌 PBD 资源提取
├── SRFileParser     ── .sr*/.ps 源码结构化解析
├── PBSourceAnalyzer ── 代码质量 10 条规则，可配置
├── DependencyAnalyzer── 跨 PBL 对象引用图
├── ComplexityAnalyzer── 圈复杂度计算
├── DWParser         ── DataWindow SQL/表/列/检索参数解析
├── RefactoringEngine── 自动重构（5 条规则，dry-run 支持）
└── PBORCAEngine     ── ORCA DLL 调用，优雅降级（无 DLL 时只读）
```

## 工作流程

### 完整维护流程

```
PBL (二进制库)               EXE / PBD (编译产物)
  │                                │
  │                          [PEExtractor]
  │                          [Decompiler]
  │                                │
  ├─[Python 解析器]──→ .sr*        ↓
  │                   文本文件  .ps 文件 (PowerScript)
  │                      │        │
  │                      └────────┤
  │                               │
  │                     ┌─────────┴──────────┐
  │                     │                    │
  │                  review                  dw
  │             (综合审查报告)        (DataWindow专项)
  │              HTML / MD            SQL/表/引用/HTML
  │                     │                    │
  │                     └─────────┬──────────┘
  │                               │
  │                    ┌──────────┤
  │                    │          │
  │              analyze      refactor
  │           (质量分析)     (自动修复)
  │                    │          │
  │                    └──────────┤
  │                               │
  └─[PBORCA DLL]──────────────────┘
       │
       ├─ import → 写入 PBL
       ├─ build --mode exe → 单 EXE
       ├─ build --mode exe+pbd → EXE + PBD
       └─ build --mode exe+dll → EXE + DLL
```

### 推荐入门流程（从零开始）

```bash
# Step 1：诊断环境
python pb.py doctor F:\project

# Step 2：智能全量导出（自动识别项目类型）
python pb.py autoexport F:\project

# Step 3：综合审查，生成 HTML 报告
python pb.py review F:\project\src --html -o review.html

# Step 4：DataWindow 专项分析（反推数据库表结构）
python pb.py dw F:\project\src --tables
python pb.py dw F:\project\src --html -o dw_report.html

# Step 5：全文搜索定位关键逻辑
python pb.py search "关键词" F:\project\src --mode sql

# Step 6：重构（先 dry-run 预览，满意后 --apply）
python pb.py refactor F:\project\src -v
python pb.py refactor F:\project\src --apply -v

# Step 7：编译验证（需要 ORCA DLL）
python pb.py build app.pbl myapp --mode exe+pbd
```

## 代码分析规则

### 质量检查

| 级别 | 规则 | 说明 |
|------|------|------|
| E | empty_catch | 空 CATCH 块 |
| W | routine_too_long | 函数超过 200 行 |
| W | deep_nesting | 嵌套深度超过 4 层 |
| W | select_star | 使用 SELECT * |
| W | hardcoded_sql | 硬编码 SQL |
| W | deprecated_function | 使用废弃 PB 函数 |
| W | high_complexity | 圈复杂度超过 20 |
| I | global_variable | 全局变量 |
| I | no_error_handling | 函数缺少 try-catch |
| I | magic_numbers | 使用未命名常量 |

### 重构规则

| 规则 | 级别 | 说明 |
|------|------|------|
| fix_empty_catch | SAFE | 自动添加错误日志到空 CATCH |
| fix_select_star | MANUAL | 建议列出显式列 |
| fix_magic_numbers | LIKELY | 建议提取为命名常量 |
| fix_deprecated | LIKELY | 建议替换为新 API |
| fix_long_routine | MANUAL | 建议拆分长函数 |

## 导出的文件类型

| 扩展名 | PB 对象类型 |
|--------|------------|
| .sra | Application 应用程序 |
| .srd | DataWindow 数据窗口 |
| .srw | Window 窗口 |
| .srm | Menu 菜单 |
| .srf | Function 函数 |
| .srs | Structure 结构体 |
| .sru | User Object 用户对象 |
| .srq | Query 查询 |
| .srp | Pipeline 管道 |
| .srj | Project 工程 |

## 推荐目录结构（--by-type）

使用 `--by-type` 参数导出时，源码按 **PBL 文件 → 对象类型** 两层组织：

```
<project>/
├── src/                              # 导出根目录
│   ├── dgsauna/                      # ← PBL 文件名
│   │   ├── application/              # ← 对象类型子目录
│   │   │   └── dgsauna.sra
│   │   ├── window/
│   │   │   ├── w_main.srw
│   │   │   ├── w_login.srw
│   │   │   └── w_splash.srw
│   │   ├── datawindow/
│   │   │   ├── d_emp_list.srd
│   │   │   └── d_report.srd
│   │   ├── menu/
│   │   │   └── m_main.srm
│   │   ├── userobject/
│   │   │   └── n_cst_service.sru
│   │   ├── function/
│   │   │   └── uf_print_grid.srf
│   │   ├── structure/
│   │   │   └── rect.srs
│   │   └── project/
│   │       └── dgsauna.srj
│   ├── dgsauna01/                    # 另一个 PBL
│   │   ├── window/
│   │   ├── datawindow/
│   │   └── ...
│   └── libs/                         # 第三方库 PBL
│       └── httpclient/
│           └── ...
└── pbl/                              # 原始 PBL/PBD（可选保留）
```

**设计要点：**

| 决策 | 说明 |
|------|------|
| 第一层按 PBL 分 | 保留原始模块边界，与 PB .pbt 库列表一致 |
| 第二层按类型分 | 每类 10-50 个对象，侧边栏清晰可导航 |
| 文件名 = 对象名.扩展名 | 如 `w_main.srw`，同 PBL 内不会重名 |
| import 自动递归 | `import` 命令默认扫描子目录，无需指定类型 |

**类型子目录映射：**

| 子目录名 | 包含的对象类型 |
|----------|--------------|
| application/ | .sra |
| window/ | .srw |
| datawindow/ | .srd |
| menu/ | .srm |
| function/ | .srf |
| userobject/ | .sru |
| structure/ | .srs |
| query/ | .srq |
| pipeline/ | .srp |
| project/ | .srj |
| proxy/ | .srx |
| extension/ | .sre |

> 不使用 `--by-type` 时，所有源码文件平铺在 PBL 子目录下。

## PBL Tree 模式（--pbl-tree）

当 EXE 编译时选择全内嵌模式（没有外部 PBL），所有对象合并到一个 PBD 中。`--pbl-tree` 模式会根据 PB 命名惯例自动推断原始 PBL 组织：

```bash
# 从 EXE 导出并按 PBL 组织
python pb.py export app.exe -o ./src --pbl-tree --project-name myapp
```

输出结构：

```
src/
├── myapp.pbl/              # 主业务模块（w_myapp_* 窗口）
├── dw_myapp.pbl/           # 数据窗口对象（d_*）
├── framework.pbl/          # 框架层（菜单、登录、启动窗口）
├── common.pbl/             # 公共库（工具对象、用户对象、结构体）
├── common_fun.pbl/         # 全局函数（uf_*, f_*）
├── sys.pbl/                # 系统管理（w_sys_*, w_users）
├── app.pbl/                # 应用入口
└── README.md               # 自动生成的结构说明
```

基于 PBL tree 导出的源码可以直接用 `analyze-project` 分析，命令会自动检测 PBL 目录结构并按 PBL 分组报告：

```bash
python pb.py analyze-project ./src                     # 自动检测 PBL tree
python pb.py analyze-project ./src --html report.html  # 生成 HTML 报告
```

## 运行测试

```bash
python tests/test_pb_devkit.py
```

## Python API

```python
from pb_devkit import PBLParser, PBSourceAnalyzer, RefactoringEngine, PBConfig

# 解析 PBL
with PBLParser("app.pbl") as parser:
    entries = parser.list_entries()
    sources = parser.export_all()

# 导出并按类型分目录（推荐）
with PBLParser("app.pbl") as parser:
    parser.export_to_directory("./src", by_type=True)

# 分析代码质量
analyzer = PBSourceAnalyzer()
issues = analyzer.analyze_directory("./exported")

# 重构（dry run）
engine = RefactoringEngine()
results = engine.run("./exported", dry_run=True)

# 加载项目配置
config = PBConfig.load()

# 从 EXE/PBD/PBL 梳理导出 PowerScript 源码
from pb_devkit.decompiler import decompile_file, list_entries, DecompileResult

# 列出所有可导出对象
entries = list_entries("app.exe")   # ['w_login.win', 'w_main.win', ...]

# 全量导出
results = decompile_file("app.exe", decompile_all=True)
for r in results:
    if r.success:
        print(r.entry_name, "->", len(r.source), "chars")

# 导出单个对象
[r] = decompile_file("app.exe", entry_name="w_login")
print(r.source)

# 提取资源（图片、图标等）
from pb_devkit.decompiler import extract_resources, list_resource_entries
res_entries = list_resource_entries("app.exe")   # ['bmp\\logo.gif', ...]
results = extract_resources("app.exe", "./resources")  # 保存到目录
for r in results:
    print(f"{r.entry_name}: {r.size:,} bytes")

# EXE → PBL Tree 导出（自动推断 PBL 分组）
from pb_devkit.pbl_grouper import export_pbl_tree, infer_pbl_groups

# 全量导出：代码梳理 + 按 PBL 分组
stats = export_pbl_tree("app.exe", "./src", project_name="myapp")
print(f"Saved: {stats.total_saved}, PBLs: {list(stats.pbl_files.keys())}")

# 仅推断分组（不导出）
groups = infer_pbl_groups(["w_login.win", "d_orders.dwo", "uf_calc.fun"])
```

## AI Agent 集成

本项目附带 `SKILL.md`，可安装为 WorkBuddy Skill，让任何 AI Agent 都能直接维护 PB 旧系统。

## License

MIT
