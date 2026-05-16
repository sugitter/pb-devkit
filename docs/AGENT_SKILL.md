# PB DevKit - Universal Agent Skill

> **PowerBuilder 旧系统现代化工具包 — 适配所有 AI Agent 平台**
> **最新状态**：CLI 20/20 命令 100% 完成 | Desktop 23/28 功能 82% 完成
>
> 适用于：WorkBuddy / OpenClaw / Claude Desktop / Cursor / GitHub Copilot Agent 等

---

## ⚠️ 版本选择

| 版本 | 技术栈 | 安装方式 |
|------|--------|----------|
| **pb-devkit-2.x** (推荐) | Rust + Tauri + Angular | `cargo build` |
| pb-devkit-1.x | Python | `pip install pb-devkit` |

---

## 安装 (2.x 推荐)

### 从源码编译

```bash
# 克隆仓库
git clone https://github.com/sugitter/pb-devkit.git
cd pb-devkit/pb-devkit-2.x

# 构建 CLI
cd pb-devkit-cli
cargo build --release
# 输出: target/release/pbdevkit.exe

# 构建 Desktop GUI (需要 Node.js)
cd ../pb-devkit-desktop
npm install
npm run tauri build
```

### 直接使用预编译

下载 Release 包: https://github.com/sugitter/pb-devkit/releases

---

## 安装 (1.x 遗留)

### pip install

```bash
pip install pb-devkit
pb --version
```

### 从源码运行

```bash
git clone <repo-url> pb-devkit
cd pb-devkit
python pb.py <command> [options]
```

**环境要求 (1.x)**: Python 3.9+，零外部依赖。

## 何时触发

当用户提到以下场景时，加载此 Skill：

- PowerBuilder / PB / PBL 相关开发、维护、迁移、分析
- 导出/查看 PB 源码（.sr* 文件）
- 代码质量分析、依赖关系、复杂度评估
- 重构或优化 PB 旧系统
- PB 项目结构梳理、文档生成
- Bug 定位、问题排查
- 版本追踪、快照管理
- SQL 质量检查

## 命令速查 (2.x - 推荐)

```bash
# ===== PBL 操作 =====
pbdevkit parse <pbl>              # 解析 PBL 文件
pbdevkit info <pbl>               # 获取 PBL 元信息
pbdevkit list <pbl>               # 列出所有对象
pbdevkit export <pbl> <name>      # 导出单个对象源码
pbdevkit export-pbl <pbl> <dir>   # 批量导出 [--by-type]

# ===== PE 分析 =====
pbdevkit file-type <file>         # 检测文件类型
pbdevkit analyze-pe <file>        # 分析 PE 结构
pbdevkit extract-pbd <exe> <dir>  # 从 EXE 提取 PBD

# ===== 项目管理 =====
pbdevkit project <path>           # 检测 PB 项目
pbdevkit find-pbl <path>          # 递归查找 PBL
pbdevkit doctor                   # 环境诊断

# ===== 搜索 =====
pbdevkit search <path> <query>    # 全文搜索
pbdevkit search-type <path> <type> # 按类型搜索

# ===== DataWindow =====
pbdevkit analyze-dw <path>        # 分析 DW SQL
pbdevkit dw-sql <path>            # 获取 DW SQL

# ===== 反编译 =====
pbdevkit list-decompile <file>    # 列出 PBD 条目
pbdevkit decompile <file> <name>  # 反编译单个条目
pbdevkit decompile-all <file> <dir> # 批量反编译

# ===== 报告 =====
pbdevkit report <path>            # 生成项目报告
pbdevkit export-report <path> <output.json> # 导出 JSON

# ===== 交互模式 =====
pbdevkit interactive              # 启动 REPL
```

### 交互模式示例

```bash
pbdevkit interactive
# pbdevkit> parse myapp.pbl
# pbdevkit> list myapp.pbl
# pbdevkit> help
# pbdevkit> exit
```

---

## 遗留命令 (1.x - 不推荐)

```bash
# 1.x 版本命令 (Python)
pb doctor [project_dir]
pb init <project_dir> [--json]
pb list <pbl_or_dir> [--json]
pb export <pbl_or_dir> [output_dir]
pb analyze <dir> [--json]
pb search <pattern> <dir>
pb report <dir> [-o output.md]
pb refactor <dir> [--apply]
pb snapshot <pbl_or_dir> [output_dir]
```

所有命令支持 `--json` 输出 JSON，`-v` / `--verbose` 显示详情。

## 6 个标准场景工作流

### 场景 1：首次接触 PB 旧系统

```bash
pb doctor /path/to/project
pb init /path/to/project --json
pb list /path/to/project --json
pb export /path/to/project ./src
pb analyze-project ./src --json
```

→ 向用户报告：项目结构、对象统计、质量问题评级、依赖关系、复杂度热点、修复建议。

### 场景 2：代码质量审查

```bash
pb analyze ./src --json
pb report ./src -o CODE_REVIEW.md
```

**10 条质量规则**：

| 级别 | 规则 | 说明 |
|------|------|------|
| 🔴 E | empty_catch | 空 CATCH 块，错误被静默吞掉 |
| 🟡 W | routine_too_long | 函数超过 200 行 |
| 🟡 W | deep_nesting | 嵌套深度超过 4 层 |
| 🟡 W | high_complexity | 圈复杂度超过 20 |
| 🟡 W | deprecated_function | 使用废弃 PB 函数 |
| 🟡 W | hardcoded_sql | 硬编码 SQL |
| 🟡 W | select_star | 使用 SELECT * |
| 🔵 I | global_variable | 全局变量（耦合风险） |
| 🔵 I | no_error_handling | 函数缺少 try-catch |
| 🔵 I | magic_numbers | 未命名数字常量 |

### 场景 3：自动修复

```bash
# 先预览（dry-run），不要直接改
pb refactor ./src -v --json

# 用户确认后应用
pb refactor ./src --apply -v --json
```

### 场景 4：Bug 定位

```bash
pb export module.pbl ./work
pb analyze-project ./work --json
pb search "keyword" ./work --mode sql
```

### 场景 5：修改代码并回写

```bash
pb export module.pbl ./work
# Agent 直接编辑 .sr* 文件（纯文本）
pb diff ./work-backup ./work -v --json
pb import module.pbl ./work        # 需要 ORCA DLL
```

### 场景 6：版本快照

```bash
pb snapshot project.pbl ./src           # 导出+对比+git commit
pb snapshot project.pbl ./src -v        # 详细变更
pb snapshot project.pbl ./src --no-git  # 只导出+对比
```

## IDE 插件

### VS Code

```bash
cd vscode-extension && npm install -g @vscode/vsce && vsce package
# 安装: code --install-extension powerscript-1.0.0.vsix
```

功能：语法高亮 + 10条Lint + 80+补全 + 悬停提示

### JetBrains IDEA

```bash
cd idea-plugin && gradlew buildPlugin
# 安装: IDEA → Settings → Plugins → Install from disk → 选择 zip
```

功能：语法高亮 + 10条Lint + 130+补全 + 悬停文档 + 代码折叠

兼容：IDEA / WebStorm / PyCharm / DataGrip 2023.2+

## PB 文件类型

| 扩展名 | 类型 |
|--------|------|
| .sra | Application |
| .srd | DataWindow |
| .srw | Window |
| .srm | Menu |
| .srf | Function |
| .srs | Structure |
| .sru | User Object |
| .srq | Query |
| .srp | Pipeline |
| .srj | Project |

## 项目配置

在项目根目录放置 `.pbdevkit.json`：

```json
{
    "pb_version": 125,
    "max_routine_lines": 200,
    "max_complexity": 20,
    "max_nesting": 4,
    "encoding": "utf-8",
    "rules": { "enabled": null, "disabled": [] },
    "naming": {
        "datawindow": "^d_", "window": "^w_", "menu": "^m_",
        "function": "^(f_|gf_)", "userobject": "^(n_|u_)", "structure": "^s_"
    }
}
```

## 关键注意事项

1. **refactor 默认 dry-run**，必须用户确认后才加 `--apply`
2. **ORCA DLL**：export/search/analyze/refactor 不需要，import/build/compile 需要
3. **编码**：默认 UTF-8，旧项目可能需要 `"encoding": "gb2312"`
4. **备份**：refactor --apply 自动创建 .bak 备份

## PB 旧系统典型特征

- C/S 架构，直连数据库（SQL Server / Oracle / Sybase）
- DataWindow 是数据操作核心
- 事件驱动编程（clicked、open、itemchanged）
- 全局变量泛滥
- 错误处理薄弱（靠 SQLCA.SQLCode）
- 嵌入式 SQL 混杂
