# PB DevKit CLI 使用示例 / CLI Usage Examples

> PowerBuilder Legacy System Toolkit - Command Line Examples

---

## English

### Quick Start

```bash
# Build CLI
cd pb-devkit-cli
cargo build --release
./target/release/pbdevkit.exe --help
```

### PBL Operations

```bash
# Parse PBL file
pbdevkit parse myapp.pbl

# Get PBL info
pbdevkit info myapp.pbl

# List all entries
pbdevkit list myapp.pbl

# Export single entry
pbdevkit export myapp.pbl dw_employee

# Export all entries by type
pbdevkit export-pbl myapp.pbl ./output --by-type
```

### PE Analysis

```bash
# Detect file type
pbdevkit file-type myapp.exe

# Analyze PE headers
pbdevkit analyze-pe myapp.exe

# Extract PBD from EXE
pbdevkit extract-pbd myapp.exe ./extracted
```

### Project Management

```bash
# Detect PowerBuilder project
pbdevkit project C:/projects/myapp

# Find all PBL files
pbdevkit find-pbl C:/projects/myapp

# Run environment diagnostics
pbdevkit doctor
```

### Search

```bash
# Full-text search
pbdevkit search C:/projects/myapp "dw_"

# Search by object type
pbdevkit search-type C:/projects/myapp "DataWindow"
```

### DataWindow Analysis

```bash
# Analyze DataWindows
pbdevkit analyze-dw C:/projects/myapp

# Get DataWindow SQL
pbdevkit dw-sql C:/projects/myapp/dw_employee.srd
```

### Decompile

```bash
# List entries in PBD
pbdevkit list-decompile myapp.pbd

# Decompile single entry
pbdevkit decompile myapp.pbd dw_employee

# Decompile all entries
pbdevkit decompile-all myapp.pbd ./output
```

### Reports

```bash
# Generate project report
pbdevkit report C:/projects/myapp

# Export report to JSON
pbdevkit export-report C:/projects/myapp report.json
```

### Interactive Mode

```bash
# Start REPL
pbdevkit interactive

# In interactive mode:
# pbdevkit> parse myapp.pbl
# pbdevkit> list myapp.pbl
# pbdevkit> help
# pbdevkit> exit
```

---

## 中文

### 快速开始

```bash
# 编译 CLI
cd pb-devkit-cli
cargo build --release
./target/release/pbdevkit.exe --help
```

### PBL 操作

```bash
# 解析 PBL 文件
pbdevkit parse myapp.pbl

# 获取 PBL 信息
pbdevkit info myapp.pbl

# 列出所有条目
pbdevkit list myapp.pbl

# 导出单个条目
pbdevkit export myapp.pbl dw_employee

# 按类型导出所有条目
pbdevkit export-pbl myapp.pbl ./output --by-type
```

### PE 分析

```bash
# 检测文件类型
pbdevkit file-type myapp.exe

# 分析 PE 头
pbdevkit analyze-pe myapp.exe

# 从 EXE 提取 PBD
pbdevkit extract-pbd myapp.exe ./extracted
```

### 项目管理

```bash
# 检测 PowerBuilder 项目
pbdevkit project C:/projects/myapp

# 查找所有 PBL 文件
pbdevkit find-pbl C:/projects/myapp

# 运行环境诊断
pbdevkit doctor
```

### 搜索

```bash
# 全文搜索
pbdevkit search C:/projects/myapp "dw_"

# 按对象类型搜索
pbdevkit search-type C:/projects/myapp "DataWindow"
```

### DataWindow 分析

```bash
# 分析 DataWindow
pbdevkit analyze-dw C:/projects/myapp

# 获取 DataWindow SQL
pbdevkit dw-sql C:/projects/myapp/dw_employee.srd
```

### 反编译

```bash
# 列出 PBD 中的条目
pbdevkit list-decompile myapp.pbd

# 反编译单个条目
pbdevkit decompile myapp.pbd dw_employee

# 反编译所有条目
pbdevkit decompile-all myapp.pbd ./output
```

### 报告

```bash
# 生成项目报告
pbdevkit report C:/projects/myapp

# 导出报告为 JSON
pbdevkit export-report C:/projects/myapp report.json
```

### 交互模式

```bash
# 启动 REPL
pbdevkit interactive

# 在交互模式下：
# pbdevkit> parse myapp.pbl
# pbdevkit> list myapp.pbl
# pbdevkit> help
# pbdevkit> exit
```