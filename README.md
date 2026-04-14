# PB DevKit - PowerBuilder Legacy System Toolkit

> 不用打开 PowerBuilder IDE，在命令行完成 PBL 源码导出、分析、重构、搜索、报告、导入、编译全流程。
> 适用于 PB4 ~ PB2025 全系列版本。
>
> **Python API**：`pip install` 无需，纯标准库实现（零外部依赖）。
> **44 个单元测试全部通过**。

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

# 2. 导出所有 PBL 源码
python pb.py export F:\path\to\project ./src

# 3. 完整项目分析（依赖关系 + 复杂度 + 质量报告）
python pb.py analyze-project ./src --json

# 4. 全文搜索
python pb.py search "employee" ./src --mode sql
python pb.py search "uf_login" ./src --mode function -t WIN

# 5. 自动重构（预览 → 应用）
python pb.py refactor ./src/module -v
python pb.py refactor ./src/module --apply -v

# 6. 生成 Markdown 分析报告
python pb.py report ./src -o ./CODE_REVIEW.md

# 7. 一键全流程
python pb.py workflow F:\path\to\project\module.pbl --apply

# 8. 导入修改后的源码（需要 PBSpyORCA.dll）
python pb.py import module.pbl ./src
python pb.py build module.pbl appname
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
| `pb analyze <dir>` | 代码质量分析 | 否 |
| `pb analyze-project <dir>` | 完整项目分析（依赖图+复杂度） | 否 |
| `pb search <pattern> <dir>` | 全文搜索（文本/SQL/函数） | 否 |
| `pb stats <dir>` | 项目统计仪表盘 | 否 |
| `pb report <dir>` | 生成 Markdown 分析报告 | 否 |
| `pb refactor <dir>` | 自动重构（支持 dry-run） | 否 |
| `pb diff <dir1> <dir2>` | 比较两份源码 | 否 |
| `pb workflow <pbl> [dir]` | 全流程：导出→分析→重构 | 否 |
| `pb import <pbl> <dir>` | 导入 .sr* 文件到 PBL | 是 |
| `pb build <pbl> <app>` | 全量重建应用 | 是 |
| `pb compile <pbl> <dir>` | 导入+重建一步完成 | 是 |

**所有命令支持 `--json` 输出结构化 JSON。**

## 技术架构

```
pb-devkit/
├── pb.py                          # CLI 入口（15 个命令）
├── pyproject.toml                 # 包元数据
├── src/pb_devkit/
│   ├── cli.py                     # pip install 后的 pb 命令入口
│   ├── commands/                  # CLI 命令处理（每命令一文件）
│   ├── pbl_parser.py              # PBL 二进制格式解析器（PB4-PB12+）
│   ├── sr_parser.py               # .sr* 源码解析 + 分析
│   ├── pborca_engine.py           # PBORCA DLL 封装（含优雅降级）
│   ├── refactoring.py             # 自动重构引擎（5 条规则）
│   ├── config.py                  # 项目级配置（.pbdevkit.json）
│   └── __init__.py                # 公共 API 导出
├── orca/                          # PBSpyORCA.dll（需手动下载）
├── tests/
│   └── test_pb_devkit.py          # 44 个单元测试
├── SKILL.md                       # WorkBuddy Skill 描述
├── LICENSE                        # MIT License
└── .gitignore
```

## 工作流程

```
PBL (二进制库)
  │
  ├─[Python 解析器]──→ .sr* 文本文件 ──→ 编辑/搜索/重构/审查
  │                                         │
  │                    ┌────────────────────┤
  │                    │                    │
  │              analyze              refactor
  │           (质量分析)           (自动修复)
  │                    │                    │
  │                    └────────────────────┤
  │                                         │
  └─[PBORCA DLL]────────────────────────────┘
       │                              │
       ├─ import → 写入 PBL           │
       ├─ build → 全量编译             │
       └─ build --exe → 生成 EXE      │
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

# 分析代码质量
analyzer = PBSourceAnalyzer()
issues = analyzer.analyze_directory("./exported")

# 重构（dry run）
engine = RefactoringEngine()
results = engine.run("./exported", dry_run=True)

# 加载项目配置
config = PBConfig.load()
```

## AI Agent 集成

本项目附带 `SKILL.md`，可安装为 WorkBuddy Skill，让任何 AI Agent 都能直接维护 PB 旧系统。

## License

MIT
