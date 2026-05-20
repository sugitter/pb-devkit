---
name: pb-devkit
description: PowerBuilder 遗留系统分析工具包 - AI Agent 专用技能。使用此技能来分析、解析和迁移 PowerBuilder 项目。
agent_created: true
tags:
  - powerbuilder
  - pbl
  - legacy
  - migration
  - tauri
  - rust
---

# PB DevKit Agent Skill

PowerBuilder 遗留系统分析工具包的 AI Agent 专用接口。

## 项目位置

- **2.x 版本 (推荐)**: `F:\workspace\X6\pb-devkit\pb-devkit-2.x`
- **Desktop 应用**: `pb-devkit-2.x\pb-devkit-desktop`
- **核心库**: `pb-devkit-2.x\pb-devkit-core`

## 快速开始

### 1. 解析 PBL 文件

```rust
// 使用 Rust 核心库
use pb_devkit_core::pbl::PblParser;

let parser = PblParser::new("path/to/app.pbl").unwrap();
let entries = parser.entries();

for entry in entries {
    println!("{} - {}", entry.name, entry.entry_type_name);
}
```

### 2. 扫描整个 PB 项目

```rust
use pb_devkit_core::project::scan_and_export;

let result = scan_and_export(
    "F:/workspace/X6/my-pb-project",
    "F:/workspace/output"
).unwrap();

println!("导出: {} / {}", result.exported_count, result.entry_count);
```

### 3. 迁移到现代 Web 项目

```rust
use pb_devkit_core::project::migrate_to_web;

let result = migrate_to_web(
    "F:/workspace/X6/my-pb-project", 
    "F:/workspace/modern-web",
    "angular"  // 支持: angular, react, vue
).unwrap();
```

### 4. DataWindow SQL 解析

```rust
use pb_devkit_core::dw::analyze_datawindows;

let result = analyze_datawindows("F:/workspace/X6/dw-files").unwrap();
for dw in &result.datawindows {
    println!("DW: {} - SQL: {}", dw.name, dw.sql.as_ref().unwrap());
}
```

## Tauri 命令 (Desktop)

| 命令 | 功能 |
|------|------|
| `parse_pbl` | 解析单个 PBL 文件 |
| `scan_project` | 一键扫描整个项目 |
| `migrate_project` | 迁移到现代 Web 项目 |
| `analyze_datawindows` | 分析 DataWindow SQL |
| `search_in_files` | 全文搜索 |
| `decompile_entry` | 反编译单个对象 |

## 使用示例

### 场景 1: 分析未知 PB 项目

1. 先用 `detect_project` 检测项目结构
2. 用 `scan_project` 一键解析所有 PBL
3. 用 `analyze_datawindows` 分析 DataWindow
4. 查看 `FUNCTION_MATRIX.md` 了解功能覆盖

### 场景 2: 迁移到现代技术栈

1. 用 `migrate_project` 转换为 Web 项目结构
2. 产物按类型分类: datawindows/, windows/, menus/
3. 自动生成 package.json

### 场景 3: 代码审查

1. 用 `search_in_files` 搜索特定模式
2. 用 `search_with_regex` 正则搜索
3. 用 `decompile_entry` 查看源码

## 已知限制

- **ORCA 引擎**: 需要 PBSpyORCA.dll 外部依赖
- **编译对象**: .win/.dwo 等编译对象只能导出，无法完全还原 P-code
- **PB 版本**: 支持 PB5-PB12.6，测试覆盖 68 个用例

## 构建命令

```bash
# 编译核心库
cd pb-devkit-2.x/pb-devkit-core
cargo check

# 构建桌面应用
cd pb-devkit-2.x/pb-devkit-desktop
npm run tauri build

# 输出位置
# EXE: src-tauri/target/release/pb-devkit-desktop.exe
# NSIS: src-tauri/target/release/bundle/nsis/*.exe
# MSI: src-tauri/target/release/bundle/msi/*.msi
```

## 文件规范

- **源码文件**: .srw/.srd/.srm/.srf/.srs/.sru
- **编译文件**: .win/.dwo/.prp
- **PBL**: PowerBuilder 库文件
- **PBD**: 编译后的库文件

## 相关文档

- `README.md` - 项目说明 (中英双语)
- `FUNCTION_MATRIX.md` - 功能矩阵
- `CLI_EXAMPLES.md` - 命令行示例
- `TODO.md` - 开发进度

## 环境要求

- Rust 1.70+
- Node.js 18+
- Windows (Tauri 2.x)