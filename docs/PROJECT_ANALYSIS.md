# PB DevKit 项目架构分析报告

> 版本: 2.0.0 | 更新日期: 2026-05-14

## 1. 项目概览

| 属性 | 值 |
|------|-----|
| **项目名称** | PB DevKit (PowerBuilder Legacy System Toolkit) |
| **定位** | PowerBuilder 遗留系统代码分析与处理工具包 |
| **技术栈** | Rust (核心) + Tauri + Angular (桌面) |
| **版本** | v2.0.0 |
| **支持版本** | PB5 ~ PB12.6 (ANSI + Unicode) |
| **CLI 命令数** | 20 个 (100% 完成) |
| **Desktop UI 组件** | 10 个 (79% 功能覆盖) |

## 2. 目录结构

```
pb-devkit/
├── pb-devkit-2.x/              # Rust 版本 (推荐)
│   ├── pb-devkit-core/         # 核心解析库 (零外部依赖)
│   │   ├── src/
│   │   │   ├── pbl.rs          # PBL 解析器
│   │   │   ├── pe.rs           # PE 分析器
│   │   │   ├── dw.rs           # DataWindow 分析器
│   │   │   ├── decompile.rs    # 反编译引擎
│   │   │   ├── search.rs       # 全文搜索
│   │   │   └── project.rs      # 项目检测
│   │   └── Cargo.toml
│   ├── pb-devkit-cli/          # CLI 工具
│   │   ├── src/
│   │   │   ├── main.rs         # 入口
│   │   │   └── commands/       # 20 个命令
│   │   └── Cargo.toml
│   └── pb-devkit-desktop/      # 桌面 GUI
│       ├── src/
│       │   ├── app/
│       │   │   ├── components/ # 10 个 UI 组件
│       │   │   └── services/   # 后端服务
│       │   └── tauri.conf.json
│   ├── README.md
│   ├── FUNCTION_MATRIX.md
│   ├── CLI_EXAMPLES.md
│   └── TODO.md
├── pb-devkit-1.x/              # Python 版本 (遗留)
├── docs/                       # 文档
│   ├── SKILL.md               # Agent Skill
│   ├── AGENT_SKILL.md         # 项目级 Skill
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   └── PROJECT_ANALYSIS.md
├── orca/                       # ORCA DLL 目录
└── README.md                   # 项目总览
```

## 3. 核心模块解析

### 3.1 PBL 解析器 (`pb-devkit-core/src/pbl.rs`)
- **核心功能**：解析 PBL/PBD 库文件，提取对象列表和源码
- **支持格式**：PB5-PB12.6，ANSI/Unicode 自动检测
- **关键结构**：
  - `PblHeader`: 库文件头部信息
  - `PblEntry`: 对象条目（名称、类型、偏移、大小）
  - `PblReader`: 读取器实现

### 3.2 PE 分析器 (`pb-devkit-core/src/pe.rs`)
- **核心功能**：分析 PE (EXE/DLL) 结构，提取嵌入的 PBD 资源
- **关键结构**：
  - `PeHeader`: PE 头信息
  - `ResourceTable`: 资源表
  - `PbdExtractor`: PBD 提取器

### 3.3 DataWindow 分析器 (`pb-devkit-core/src/dw.rs`)
- **核心功能**：提取 DataWindow 对象的 SQL、表、列信息
- **支持**：SQL SELECT、WHERE、ORDER BY、GROUP BY
- **DW 类型**：Grid、Tabular、Freeform、Crosstab

### 3.4 反编译引擎 (`pb-devkit-core/src/decompile.rs`)
- **核心功能**：从 EXE/PBD 还原 PowerScript 源码
- **支持格式**：
  - 源码：.srw/.srd/.srm/.srf/.srs/.sru
  - 编译：.win/.dwo/.prp

### 3.5 搜索模块 (`pb-devkit-core/src/search.rs`)
- **核心功能**：全文搜索、按类型搜索
- **未来优化**：并行搜索 (rayon)、索引文件

## 4. CLI 命令覆盖

| 模块 | 命令数 | 状态 |
|------|--------|------|
| PBL 操作 | 5 | ✅ 100% |
| PE 分析 | 3 | ✅ 100% |
| 项目管理 | 3 | ✅ 100% |
| 搜索 | 2 | ✅ 100% |
| DataWindow | 2 | ✅ 100% |
| 反编译 | 3 | ✅ 100% |
| 报告 | 2 | ✅ 100% |
| **总计** | **20** | **✅ 100%** |

## 5. Desktop UI 组件

| 组件 | 功能 |
|------|------|
| project-selector | 项目选择器 |
| pbl-list | PBL 列表视图 |
| source-viewer | 源码编辑器 |
| dw-analyzer | DataWindow 可视化 |
| search-panel | 搜索面板 |
| decompile-panel | 反编译面板 |
| doctor-panel | 环境诊断 |
| pe-view | PE 信息视图 |
| report-view | 报告查看器 |
| project-stats | 项目统计 |

## 6. v2.1 优化方向

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | DataWindow SQL 解析完善 | 嵌套查询、子查询、UNION、参数绑定 |
| 🔴 高 | 批量导出进度显示 | CLI 进度条 + Desktop 进度 Modal |
| 🟡 中 | PBL 版本检测增强 | 自动检测、ANSI/Unicode、PB 12.5+ |
| 🟡 中 | 搜索性能优化 | 并行搜索、索引文件、增量搜索 |

## 7. 技术亮点

1. **零外部依赖**：核心解析库不依赖任何外部 crate
2. **跨平台**：CLI + Desktop 支持 Windows/macOS/Linux
3. **高性能**：Rust 实现比 Python 快 10-100 倍
4. **现代前端**：Angular 17+ 独立组件 + Signals

---

*报告生成日期: 2026-05-14*