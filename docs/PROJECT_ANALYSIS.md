# PB DevKit 项目架构分析报告

> 版本: 1.5.0 | 更新日期: 2026-05-07

## 1. 项目概览

| 属性 | 值 |
|------|-----|
| **项目名称** | PB DevKit (PowerBuilder Legacy System Toolkit) |
| **定位** | PowerBuilder 旧系统代码分析与处理 CLI 工具 |
| **技术栈** | Python 3.8+ (纯标准库，零外部依赖) |
| **版本** | v1.5.0 |
| **支持版本** | PB5 ~ PB12.6 (ANSI + Unicode) |
| **测试覆盖** | 68 个单元测试 (49 核心 + 19 PEExtractor) |

## 2. 目录结构

```
pb-devkit/
├── src/pb_devkit/           # 核心 Python 包
│   ├── commands/            # 20 个 CLI 命令实现
│   ├── parsers/             # 解析器模块 (预留，当前为空)
│   ├── resoures/            # 资源文件
│   ├── chunk_engine.py      # 分块引擎 (541 行)
│   ├── pbl_parser.py        # PBL 解析器 (410 行)
│   ├── decompiler.py        # 反编译引擎 (2382 行，核心)
│   ├── pborca_engine.py     # ORCA 引擎 (347 行)
│   ├── pe_extractor.py      # PE/EXE 提取器 (610 行)
│   ├── sr_parser.py         # 源码解析器 (510 行)
│   ├── project_detector.py  # 项目检测器 (317 行)
│   ├── pbl_grouper.py       # PBL 分组器 (450 行)
│   ├── refactoring.py       # 重构引擎 (349 行)
│   └── config.py            # 配置管理 (159 行)
├── tests/                   # 单元测试 (68 个测试用例)
├── vscode-extension/        # VS Code 插件
├── idea-plugin/             # IDEA 插件
├── orca/                    # PBORCA DLL (PBSpy.dll + PB 12.0 DLLs)
├── docs/                    # 项目文档
├── pb.py                    # CLI 入口
└── README.md / SKILL.md / AGENT_SKILL.md / UNIVERSAL_PARSER_DESIGN.md
```

## 3. 核心模块解析

### 3.1 反编译引擎 (`decompiler.py` - 2382行)
- **核心功能**：从 EXE/PBD 中还原 PowerScript 源码
- **支持格式**：
  - 源码：.srw/.srd/.srm/.srf/.srs/.sru
  - 编译：.win/.dwo/.prp
- **PB12 特性**：DAT* 源码为 UTF-16LE，ENT* name 含扩展名

### 3.2 PBL 解析器 (`pbl_parser.py` - 410行)
- **二进制格式**：
  - HDR*: 512b (ANSI) / 1024b (Unicode)
  - DAT*: 512b 链式数据块
- **零外部依赖**：纯 Python 实现 PB5-PB12+

### 3.3 PE 提取器 (`pe_extractor.py` - 610行)
- 从 EXE/DLL 中提取嵌入的 PBL 资源
- 支持多 PBD 资源提取

### 3.4 源码解析器 (`sr_parser.py` - 510行)
- PowerScript 语法解析
- 支持 DataWindow、SQL、函数等分析

### 3.5 ORCA 引擎 (`pborca_engine.py` - 347行)
- PBSpyORCA.dll 包装器
- 支持 import/build/compile 操作
- 支持优雅降级 (DLL 不可用时)

## 4. CLI 命令 (20个)

| 命令 | 功能 | 依赖 |
|------|------|------|
| `doctor` | 环境诊断 | 无 |
| `init` | 项目初始化/检测 | 无 |
| `list` | 列出 PBL 对象 | 无 |
| `export` | 导出 PBL/EXE 源码 | 无 |
| `import` | 导入 .sr* 到 PBL | ORCA DLL |
| `build` | 重新构建应用 | ORCA DLL |
| `compile` | 导入+编译一步到位 | ORCA DLL |
| `analyze` | 代码质量分析 | 无 |
| `analyze-project` | 完整项目分析 | 无 |
| `search` | 全文搜索 | 无 |
| `report` | Markdown 报告 | 无 |
| `refactor` | 自动重构 | 无 |
| `diff` | 源码对比 | 无 |
| `workflow` | 全流程自动化 | 无 |
| `stats` | 项目统计 | 无 |
| `snapshot` | 版本快照 | 无 |
| `decompile` | 反编译 PBD/EXE | 无 |
| `autoexport` | 智能自动导出 | 无 |
| `review` | 全面项目审查 | 无 |
| `dw` | DataWindow 专项分析 | 无 |

## 5. 插件生态

### 5.1 VS Code 插件
- 位置：`vscode-extension/`
- 包含：
  - `syntaxes/powerscript.json` - 语法高亮
  - `src/extension.js` - 插件主程序
  - `language-configuration.json` - 语言配置

### 5.2 IDEA 插件
- 位置：`idea-plugin/`
- 构建系统：Gradle (Kotlin DSL)
- 语言：Java/Kotlin

## 6. 测试覆盖

```
tests/
├── test_pb_devkit.py     # 49 个核心测试
│   ├── TestPBLParser
│   ├── TestPBLEntryType
│   ├── TestSourceExport
│   ├── TestRefactoring
│   └── ...
└── test_pe_extractor.py  # 19 个 PE 测试
    ├── TestPEExtractorBasic
    ├── TestPEExtractorResourceNaming
    └── TestChunkEngineMemoryMode
```

**运行测试**:
```bash
python -m pytest tests/ -v
# 结果: 68 passed in 1.38s
```

## 7. 设计亮点

1. **纯 Python 实现**：零外部依赖，跨平台
2. **PB 全版本支持**：PB5 ~ PB12.6，ANSI/Unicode 通吃
3. **离线可用**：无需安装庞大的 PB IDE
4. **可扩展架构**：chunk_engine + parsers 模块化设计
5. **双插件生态**：VS Code + IDEA 完整支持

## 8. v2.0 愿景

> PB → Rust 后端 + Angular 前端 + Tauri 桌面

**市场机会**：
- Mobilize.Net WebMAP (闭源贵)
- Appeon PowerServer (非真正迁移)
- Ispirer SQLWays (纯服务)

## 9. 已知缺口 (TODO)

- [ ] `parsers/` 目录空置 - 需要实现专用解析器
- [ ] 增加更多集成测试用例
- [ ] 完善 CI/CD 流水线

---

*本文档由 AI 自动生成*