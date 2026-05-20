---
name: pb-devkit
description: PowerBuilder 遗留系统分析工具包 - AI Agent 专用技能。通过 CLI 命令分析和解析用户的 PB 项目。
agent_created: true
tags:
  - powerbuilder
  - pbl
  - legacy
  - migration
  - cli
---

# PB DevKit Agent Skill

AI Agent 专用技能：通过 CLI 命令分析和解析用户的 PB 项目。

## 项目位置

- **CLI 工具**: `F:\workspace\X6\pb-devkit\pb-devkit-2.x\pb-devkit-cli`
- **Desktop 应用**: `F:\workspace\X6\pb-devkit\pb-devkit-2.x\pb-devkit-desktop`

## CLI 命令清单

### 1. 项目分析

```bash
# 检测 PB 项目结构
pbdevkit project <项目路径>

# 查找所有 PBL 文件
pbdevkit find-pbl <项目路径>

# 环境诊断
pbdevkit doctor
```

### 2. PBL 解析

```bash
# 解析单个 PBL 文件
pbdevkit parse <pbl路径>

# 获取 PBL 信息
pbdevkit info <pbl路径>

# 列出所有对象
pbdevkit list <pbl路径>
```

### 3. 一键解析项目 (核心功能)

```bash
# 一键扫描整个项目，按目录结构导出源码
pbdevkit scan <项目路径> -o <输出目录>

# 一键迁移到现代 Web 项目结构
pbdevkit migrate <项目路径> -o <输出目录> -t angular
```

### 4. DataWindow 分析

```bash
# 分析 DataWindow SQL
pbdevkit dw analyze <目录路径>

# 获取特定 DW 的 SQL
pbdevkit dw sql <srd文件>
```

### 5. 搜索

```bash
# 全文搜索
pbdevkit search <关键词> <路径>

# 按类型搜索
pbdevkit search-type window <路径>

# 正则搜索
pbdevkit search-regex "SELECT.*FROM" <路径>
```

### 6. 反编译

```bash
# 列出 PBD/EXE 中的对象
pbdevkit list-decompile <pbd路径>

# 反编译单个对象
pbdevkit decompile <pbd路径> <对象名>

# 导出所有源码
pbdevkit decompile-all <pbd路径> -o <输出目录>
```

### 7. 报告生成

```bash
# 生成项目分析报告
pbdevkit report <项目路径> -o <输出文件>
```

## Agent 使用流程

### 场景: 分析用户的 PB 项目

**Step 1: 检测项目结构**
```bash
pbdevkit project "/path/to/user/pb-project"
```

**Step 2: 一键解析导出**
```bash
pbdevkit scan "/path/to/user/pb-project" -o "/path/to/output"
```

**Step 3: 分析 DataWindow**
```bash
pbdevkit dw analyze "/path/to/output/datawindows"
```

**Step 4: 生成报告**
```bash
pbdevkit report "/path/to/user/pb-project" -o "analysis.md"
```

### 场景: 迁移到现代 Web

```bash
# 一键迁移
pbdevkit migrate "/path/to/user/pb-project" \
  -o "/path/to/modern-web" \
  -t angular
```

产物结构:
```
modern-web/src/
├── datawindows/   # DataWindow 对象
├── windows/       # 窗口对象
├── menus/         # 菜单对象
├── functions/     # 函数对象
├── structures/    # 结构对象
└── applications/  # 应用对象
```

### 场景: 代码审查

```bash
# 搜索特定模式
pbdevkit search "MessageBox" "/path/to/project"

# 搜索硬编码 SQL
pbdevkit search-regex "SELECT\s+.*\s+FROM" "/path/to/project"

# 检查 DataWindow
pbdevkit dw analyze "/path/to/project"
```

## 一键命令详解

### `pbdevkit scan` - 一键解析

扫描所有 PBL 文件，按原始目录结构导出源码对象。

```
用法: pbdevkit scan <项目路径> [选项]

选项:
  -o, --output <dir>    输出目录
  -t, --type <type>     导出类型: source|compiled|all (默认: source)
  -v, --verbose         详细输出

示例:
  pbdevkit scan F:/my-pb-app -o F:/output
```

### `pbdevkit migrate` - 一键迁移

将 PB 项目转换为现代 Web 项目结构，自动按对象类型分类。

```
用法: pbdevkit migrate <项目路径> [选项]

选项:
  -o, --output <dir>    输出目录
  -t, --template <tmpl> 模板: angular|react|vue (默认: angular)
  --skip-compiled       跳过编译对象

示例:
  pbdevkit migrate F:/my-pb-app -o F:/modern-web -t angular
```

## 输出结果解读

### scan 命令输出
```
✅ 扫描完成!
  PBL 文件: 5
  对象总数: 1,234
  导出成功: 1,180
  导出失败: 54
  输出目录: F:/output
```

### migrate 命令输出
```
✅ 迁移完成!
  项目名称: my-pb-app
  DataWindow: 320
  窗口: 150
  菜单: 45
  函数: 280
  输出目录: F:/modern-web
```

## 常见错误处理

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `Invalid PBL file` | 文件损坏或非PBL | 检查文件完整性 |
| `Entry not found` | 对象不存在 | 用 `list` 确认对象名 |
| `Permission denied` | 权限不足 | 以管理员运行 |
| `Out of memory` | 文件过大 | 分批处理 |

## 构建命令

```bash
# 构建 CLI
cd pb-devkit-2.x/pb-devkit-cli
cargo build --release

# 构建 Desktop
cd pb-devkit-2.x/pb-devkit-desktop
npm run tauri build

# CLI 位置: target/release/pbdevkit.exe
# EXE 位置: src-tauri/target/release/pb-devkit-desktop.exe
```

## 相关文档

- `README.md` - 项目说明
- `FUNCTION_MATRIX.md` - 功能矩阵
- `CLI_EXAMPLES.md` - 命令行示例