# PB DevKit - PowerBuilder Legacy System Toolkit

> **面向 AI Agent 的 PowerBuilder 旧系统维护工具包**
> 无需安装 PowerBuilder IDE，在命令行即可完成 EXE/PBD **反编译**、PBL 源码导出、分析、重构、导入、编译全流程。
> 适用于 PB4 ~ PB2025 全系列版本。

## 何时触发

当用户提到以下任何场景时，应立即加载此 Skill：

- PowerBuilder / PB / PBL / PBD 相关的开发、维护、迁移、分析
- 查看或导出 PB 源码（.sr* 文件）
- **从 EXE/PBD 反编译恢复 PowerScript 源码**（无原始 PBL 时）
- 分析 PB 代码质量、依赖关系、复杂度
- 重构或优化 PB 旧系统代码
- PB 项目结构梳理、文档生成
- PB 系统的 Bug 定位、问题排查
- SQL 质量检查（SELECT *、硬编码 SQL、SQL 注入风险）
- 批量导出/导入 PB 项目
- **一键自动检测项目类型并全量导出源码**

## 背景：为什么这个工具有意义

PowerBuilder 在 1990s~2010s 是企业级数据库管理系统的主流开发工具。大量金融、医疗、酒店、零售等行业的旧系统仍在 PB 上运行。这些系统面临：

1. **维护人员流失** - 年轻开发者不熟悉 PB，老开发者退休
2. **文档缺失** - 旧系统几乎没有文档，代码是唯一的信息载体
3. **技术债务积累** - 多年修改后代码质量恶化
4. **迁移前评估** - 在迁移到 Web 之前需要全面了解现有系统

此工具让 AI Agent 能够像一位经验丰富的 PB 开发者一样，高效地理解和维护这些旧系统。

## 工具位置

```
{workspace}/pb-devkit/
├── pb.py                      # CLI 入口（19 个命令）
├── pyproject.toml             # 包元数据
├── src/pb_devkit/
│   ├── __init__.py
│   ├── cli.py                 # pip install 后的 pb 命令入口
│   ├── commands/              # CLI 命令处理（每命令一文件）
│   │   └── autoexport.py      # ★ 新：智能检测 + 全量导出
│   ├── pbl_parser.py          # PBL 二进制格式解析器（PB4-PB12+）
│   ├── chunk_engine.py        # ChunkEngine 通用解析引擎
│   ├── pbl_grouper.py         # PBL 分组推断 + 结构化导出（--pbl-tree）
│   ├── project_detector.py    # ★ 新：项目类型检测（PBL/BINARY/MIXED）
│   ├── sr_parser.py           # .sr* 源码解析 + 质量分析 + 依赖分析 + 复杂度分析
│   ├── pborca_engine.py       # PBORCA DLL 封装（导入/编译/构建 EXE）
│   ├── pe_extractor.py        # PE EXE/DLL → 提取内嵌 PBD 数据
│   ├── decompiler.py          # PBD/PBL/EXE 反编译 → PowerScript
│   ├── resoures/              # 反编译器资源文件（PB 类型定义 .bin）
│   ├── refactoring.py         # 自动重构引擎（5 条规则）
│   └── config.py              # 项目级配置（.pbdevkit.json）
├── orca/                      # PBSpyORCA.dll（需手动下载）
└── tests/
    └── test_pb_devkit.py      # 68 个单元测试
```

## Python 环境

```bash
# 使用 Python 3.13
C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe

# 运行命令前先进入工具目录
cd {workspace}/pb-devkit
python pb.py <command> [options]
```

## 命令速查

| 命令 | 说明 | 需要 ORCA DLL |
|------|------|:---:|
| `pb doctor` | 环境诊断（检测 Python、DLL、项目） | 否 |
| `pb init <dir>` | 初始化项目（识别 PB 项目结构） | 否 |
| `pb list <pbl_or_dir>` | 列出 PBL 中的对象 | 可选 |
| `pb export <pbl_or_dir> [out]` | 导出 PBL 源码为 .sr* 文件 | 可选 |
| `pb export ... --by-type` | 按对象类型分子目录导出（推荐） | 可选 |
| `pb export <exe> -o <dir> --pbl-tree` | EXE/PBD 反编译 + 按 PBL 组织导出 | 否 |
| `pb analyze <dir>` | 代码质量分析（单文件/目录） | 否 |
| `pb analyze-project <dir>` | 完整项目分析（自动检测 PBL tree） | 否 |
| `pb analyze-project <dir> --html f` | 生成 HTML 分析报告 | 否 |
| `pb search <pattern> <dir>` | 全文搜索（文本/SQL/函数） | 否 |
| `pb stats <dir>` | 项目统计仪表盘 | 否 |
| `pb report <dir>` | 生成 Markdown 分析报告 | 否 |
| `pb refactor <dir>` | 自动重构（支持 dry-run） | 否 |
| `pb diff <dir1> <dir2>` | 比较两份源码差异 | 否 |
| `pb workflow <pbl> [dir]` | 全流程：导出→分析→重构 | 否 |
| `pb snapshot <dir>` | 快照对比（保存/比较源码快照） | 否 |
| `pb decompile <exe/pbd/pbl>` | **反编译**编译产物回 PowerScript | 否 |
| `pb autoexport <dir>` | **★ 智能检测项目类型+全量导出**到 src/ | 否 |
| `pb import <pbl> <dir>` | 导入 .sr* 文件到 PBL | 是 |
| `pb build <pbl> <app>` | 全量重建应用 | 是 |
| `pb compile <pbl> <dir>` | 导入+重建一步完成 | 是 |

**所有命令都支持 `--json` 输出结构化 JSON 结果。**

## Agent 工作流程

### 场景 1：首次接触一个 PB 旧系统

用户说："帮我看看这个 PB 项目" / "分析一下这个旧系统"

```bash
# Step 1: 诊断环境
python pb.py doctor F:\path\to\project

# Step 2: 识别项目结构
python pb.py init F:\path\to\project --json

# Step 3: 列出所有 PBL 中的对象
python pb.py list F:\path\to\project --json

# Step 4: 导出所有源码（推荐 --by-type 按类型分目录）
python pb.py export F:\path\to\project ./exported --by-type

# Step 4a: 如果只有 EXE 没有 PBL（全内嵌编译），使用 --pbl-tree
python pb.py export app.exe -o ./src --pbl-tree --project-name myapp

# Step 5: 全面分析
python pb.py analyze-project ./exported --json
```

然后基于分析结果，向用户报告：
- 项目结构概览（多少个 PBL、多少个对象、各类型分布）
- 代码质量评级（多少个 E/W/I 级问题）
- 依赖关系图（哪些对象依赖哪些）
- 复杂度热点（最复杂的函数/事件）
- 建议优先处理的问题

### 场景 2：代码质量审查

用户说："检查代码质量" / "有哪些问题需要修复"

```bash
# 质量分析（带 JSON 方便程序处理）
python pb.py analyze ./exported/module --json

# 项目级分析（含依赖和复杂度）
python pb.py analyze-project ./exported --json
```

分析规则：

| 级别 | 规则 ID | 说明 |
|------|---------|------|
| E (错误) | empty_catch | 空 CATCH 块 - 错误被静默吞掉 |
| W (警告) | routine_too_long | 函数超过 200 行 |
| W | deep_nesting | 嵌套深度超过 4 层 |
| W | select_star | 使用 SELECT * - 性能和可维护性问题 |
| W | hardcoded_sql | 硬编码 SQL - 考虑使用 DataWindow |
| W | deprecated_function | 使用废弃 PB 函数 |
| W | high_complexity | 圈复杂度超过 20 |
| I (信息) | global_variable | 全局变量 - 潜在耦合 |
| I | no_error_handling | 函数缺少 try-catch |
| I | magic_numbers | 使用未命名常量 |

### 场景 3：自动修复代码问题

用户说："修复这些问题" / "自动重构"

```bash
# 第一步：先预览（dry run），不要直接改！
python pb.py refactor ./exported/module -v --json

# 确认安全修复项后，应用：
python pb.py refactor ./exported/module --apply -v --json
```

重构规则：

| 规则 | 级别 | 说明 | 自动/手动 |
|------|------|------|:---:|
| fix_empty_catch | SAFE | 空 CATCH 块添加错误日志 | 自动 |
| fix_select_star | MANUAL | SELECT * 改为显式列 | 手动 |
| fix_magic_numbers | LIKELY | 提取魔法数字为常量 | 手动 |
| fix_deprecated | LIKELY | 替换废弃函数调用 | 手动 |
| fix_long_routine | MANUAL | 过长函数建议拆分 | 手动 |

**重要：默认 refactor 是 dry-run 模式。必须用户确认后才加 --apply。**

### 场景 4：Bug 定位

用户说："XXX 功能有 bug" / "查一下为什么 YYY 出错"

```bash
# 1. 导出相关模块源码
python pb.py export F:\path\to\project\module\module.pbl ./bug-export

# 2. 查看依赖关系（找到相关对象）
python pb.py analyze-project ./bug-export --json

# 3. 读取具体源码文件进行人工分析
# 源码文件是 .sr* 格式，可以直接读取和分析
```

### 场景 5：修改代码并回写

用户说："帮我改一下 XXX 函数" / "把这段逻辑改掉"

```bash
# 1. 导出源码（按类型分目录）
python pb.py export module.pbl ./work --by-type

# 2. Agent 直接编辑 .sr* 文件（纯文本，可直接修改）

# 3. 比较修改前后差异
python pb.py diff ./work-backup ./work --json -v

# 4. 导入回 PBL（自动递归扫描类型子目录，需要 ORCA DLL）
python pb.py import module.pbl ./work
```

### 场景 6：一键全流程

用户说："全部分析一遍" / "帮我全面检查这个项目"

```bash
# 分析报告（不修改任何文件）
python pb.py workflow F:\path\to\project\module.pbl --json

# 分析 + 自动修复（安全项）
python pb.py workflow F:\path\to\project\module.pbl --apply --json
```

## PB 文件类型参考

| 扩展名 | PB 对象类型 | 说明 |
|--------|------------|------|
| .sra | Application | 应用程序入口 |
| .srd | DataWindow | 数据窗口（最常见，含 SQL 查询） |
| .srw | Window | 窗口 |
| .srm | Menu | 菜单 |
| .srf | Function | 全局函数 |
| .srs | Structure | 结构体 |
| .sru | User Object | 用户对象（可视/非可视） |
| .srq | Query | 查询 |
| .srp | Pipeline | 数据管道 |
| .srj | Project | 工程（编译配置） |

## 推荐目录结构（--by-type）

使用 `--by-type` 导出时，源码按 **PBL 文件 → 对象类型** 两层组织：

```
src/
├── dgsauna/                      # ← PBL 文件名
│   ├── application/              # ← 对象类型子目录
│   │   └── dgsauna.sra
│   ├── window/
│   │   ├── w_main.srw
│   │   └── w_login.srw
│   ├── datawindow/
│   │   ├── d_emp_list.srd
│   │   └── d_report.srd
│   ├── menu/
│   │   └── m_main.srm
│   ├── userobject/
│   │   └── n_cst_service.sru
│   ├── function/
│   │   └── uf_print_grid.srf
│   ├── structure/
│   │   └── rect.srs
│   └── project/
│       └── dgsauna.srj
├── dgsauna01/                    # 另一个 PBL
│   ├── window/
│   ├── datawindow/
│   └── ...
└── libs/                         # 第三方库
    └── httpclient/
        └── ...
```

**类型 → 子目录映射：**

| 子目录 | 对象类型 |
|--------|---------|
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

> **import 自动递归**：导入时 `import_from_directory` 默认扫描子目录，无需逐个类型目录指定。

## .sr* 源码文件格式

导出的 .sr* 文件是纯文本，可以直接用文本编辑器或 Agent 阅读/修改：

```
$PBExportHeader$w_main.srw
forward
global type w_main from window
end type
type cb_ok from commandbutton within w_main
end type
type sle_name from singlelineedit within w_main
end type

global variables
    string gs_username
    integer gi_retry_count = 3
end variables

on w_main.create
    this.title = "主窗口"
    this.width = 2000
    this.height = 1200
end on

on cb_ok.clicked
    string ls_name
    ls_name = sle_name.text
    if ls_name = "" then
        messagebox("提示", "请输入名称")
        return
    end if
    // ... 业务逻辑
end on

public function integer of_validate (string as_name)
    if len(as_name) = 0 then return -1
    if len(as_name) > 50 then return -2
    return 1
end function
```

## 关键注意事项

1. **永远先 dry-run**：refactor 命令默认不修改文件，确认安全后再 --apply
2. **备份意识**：refactor --apply 会自动创建 .bak 备份
3. **ORCA DLL**：导出（export）不需要 DLL，但导入（import）/编译（build）需要
4. **编码问题**：.sr* 文件使用 UTF-8-sig 编码读取；反编译输出 UTF-8 编码
5. **项目特定配置**：不同 PB 项目的 PB 版本、数据库类型可能不同，用 --pb-version 调整
6. **批量操作**：大部分命令支持目录作为参数，会自动递归处理
7. **反编译限制**：P-code 反编译支持 PB9/PB10/PB10.5/PB11 版本；DataWindow (.dwo) 为编译格式，反编译为原始二进制结构，可读性有限

## 典型 PB 旧系统特征（帮助 Agent 理解上下文）

- **客户端/服务器架构**：PB 应用直接连接数据库（SQL Server / Oracle / Sybase）
- **DataWindow 是核心**：大部分数据操作通过 DataWindow 完成，而非手写 SQL
- **事件驱动编程**：窗口和控件的逻辑写在事件脚本中（如 clicked、open、itemchanged）
- **全局变量泛滥**：旧 PB 项目中全局变量是常见问题
- **错误处理薄弱**：很多旧代码缺少 try-catch，错误靠 SQLCA.SQLCode 判断
- **嵌入 SQL**：部分逻辑直接在 PowerScript 中写 SQL（嵌入式 SQL）

## Agent 最佳实践

1. **先了解全貌再动手**：先用 list 和 analyze-project 建立项目认知
2. **关注高风险项**：优先处理 E 级（空 CATCH）和 W 级（硬编码 SQL）问题
3. **小步修改**：每次只修改一个模块，用 diff 确认修改内容
4. **尊重现有逻辑**：旧系统的代码可能看起来奇怪，但往往有其历史原因
5. **提供上下文**：向用户解释每项发现的意义和风险等级

### 场景 7：从 EXE/PBD 反编译恢复源码（无原始 PBL 时）

用户说："只有 EXE 没有源码，能恢复吗" / "帮我反编译这个 PB 程序"

> **适用情形**：原始 PBL 丢失、仅有编译产物、需要了解已部署程序的实现逻辑。

```bash
# Step 1: 列出可反编译的对象
python pb.py decompile app.exe --list

# Step 2: 全量反编译，输出 .ps 文件到目录
python pb.py decompile app.exe --output ./decompiled

# Step 3: 反编译单个对象（不含扩展名即可）
python pb.py decompile app.exe --entry w_login

# Step 4: 查看 PBD 内部结构树
python pb.py decompile app.exe --tree
```

**说明：**
- 支持 `.exe`（内嵌 PBD）、`.pbd`、`.pbl`（含编译数据）
- 输出为 `.ps` 格式（PowerScript），含窗口声明、变量、事件脚本
- 中文 GBK 字符串自动正确解码（UTF-8 输出）
- 图片/资源等二进制条目自动跳过

**Python API 直接调用：**

```python
from pb_devkit.decompiler import decompile_file, list_entries

# 列出所有对象
entries = list_entries("app.exe")  # ['w_login.win', 'w_main.win', ...]

# 反编译全部
results = decompile_file("app.exe", decompile_all=True)
for r in results:
    if r.success and r.source:
        print(r.entry_name, "->", len(r.source), "chars")

# 反编译单个对象
[r] = decompile_file("app.exe", entry_name="w_login")
print(r.source)
```

## 高级功能

### 全文搜索（pb search）

用户说："找到所有用到 employee 表的地方" / "查一下 uf_login 函数在哪里"

```bash
# 搜索文本（默认模式）
python pb.py search "employee" ./exported

# 搜索 SQL 表引用（只在 FROM/JOIN/INTO/UPDATE 上下文中匹配）
python pb.py search "employee" ./exported --mode sql

# 搜索函数定义
python pb.py search "uf_login" ./exported --mode function

# 按对象类型过滤（只搜 DataWindow）
python pb.py search "salary" ./exported -t DW

# 不区分大小写（默认）
python pb.py search "Employee" ./exported --case-sensitive
```

### Markdown 报告（pb report）

用户说："生成一份分析报告" / "帮我写个项目文档"

```bash
# 生成默认报告（输出到 ANALYSIS_REPORT.md）
python pb.py report ./exported

# 指定输出路径
python pb.py report ./exported -o ./docs/CODE_REVIEW.md
```

报告内容包括：项目概览、对象清单、质量问题列表、复杂度热点、依赖关系、继承树、文件详情。

### 项目配置（.pbdevkit.json）

在 PB 项目根目录放置 `.pbdevkit.json`，工具会自动检测和使用：

```json
{
    "pb_version": 125,
    "max_routine_lines": 150,
    "max_complexity": 15,
    "max_nesting": 3,
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
    },
    "encoding": "gb2312"
}
```

也可以通过 `--config` 指定：`python pb.py --config ./my-config.json analyze ./exported`

### 场景 8：EXE 全内嵌反编译 + PBL 组织导出 + 项目分析

用户说：\"只有一个 EXE 文件，帮我导出源码并分析\" / \"这个 EXE 里面没有 PBL 文件\"

> **适用情形**：EXE 编译时选择了全内嵌模式，所有 PBL 合并到 EXE 中，原始 PBL 文件已丢失。

```bash
# Step 1: 反编译 + 自动推断 PBL 分组导出
python pb.py export app.exe -o ./src --pbl-tree

# Step 2: 自动检测 PBL tree 结构并分析（含 PBL 分组统计）
python pb.py analyze-project ./src

# Step 3: 生成 HTML 分析报告
python pb.py analyze-project ./src --html ./src/ANALYSIS_REPORT.html

# Step 4: 基于 PBL tree 结构进行搜索/重构等操作
python pb.py search "uf_login" ./src
python pb.py refactor ./src --apply
```

**推断规则**（基于 PB 命名惯例）：

| 对象模式 | 推断 PBL | 说明 |
|---------|----------|------|
| `w_<app>_*` | `<app>.pbl` | 项目业务窗口 |
| `d_*` | `dw_<app>.pbl` | 数据窗口对象 |
| `w_sys_*`, `w_users` | `sys.pbl` | 系统管理窗口 |
| `w_login`, `w_splash`, `m_*` | `framework.pbl` | 框架层 |
| `n_*`, `u_*`, `s_*` | `common.pbl` | 公共库 |
| `uf_*`, `f_*` | `common_fun.pbl` | 全局函数 |

> 自定义规则可通过 Python API 的 `custom_rules` 参数传入。

### 场景 9：智能检测项目类型 + 一键全量导出（autoexport）

用户说："帮我把这个项目全部导出" / "我有个目录，不知道是源码项目还是编译后的，帮我导出"

> **适用情形**：用户不确定项目类型，或想要一个命令搞定所有情况。

```bash
# 1. 先检测项目类型（不导出）
python pb.py autoexport F:\workspace\X6\3.5\dgsauna --detect

# 输出示例：
# Type:    MIXED
# PBL:     8 files (dgsauna.pbl, dgsauna01.pbl, ...)
# EXE:     2 files (dgsauna.exe [embedded PBD], 7za.exe)
# PBD:     8 standalone files

# 2. 完整自动导出（输出到 <target>/src）
python pb.py autoexport F:\workspace\X6\3.5\dgsauna

# 3. 指定输出目录
python pb.py autoexport F:\workspace\X6\3.5\dgsauna -o ./exported

# 4. 快速模式（跳过 PE 深扫，只靠文件扩展名）
python pb.py autoexport F:\workspace\X6\3.5\dgsauna --quick

# 5. 覆盖已有目录
python pb.py autoexport F:\workspace\X6\3.5\dgsauna --force

# 6. 获取 JSON 格式检测结果（含全部文件列表）
python pb.py autoexport F:\workspace\X6\3.5\dgsauna --detect --json
```

**三种项目类型及导出策略**：

| 类型 | 判断依据 | 导出策略 |
|------|----------|---------|
| `PBL_PROJECT` | 有 HDR* 有效的 .pbl 文件，无 EXE/PBD | 每个 PBL → `src/<pbl_name>/` 子目录 |
| `BINARY_PROJECT` | 有 EXE(内嵌PBD) 或 .pbd 文件，无 PBL | 反编译 + PBL 分组推断 → `src/<pbl_name>.pbl/` |
| `MIXED_PROJECT` | 同时有 PBL 源码 和 EXE/PBD | PBL 导出到 `src/`，EXE/PBD 反编译到 `src/_decompiled/` |

