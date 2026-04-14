# PowerScript VS Code Extension

> PowerScript 语言支持插件 — 为 PowerBuilder .sr* 源码文件提供现代 IDE 体验。

## 功能

### ✅ 语法高亮
- **关键字**: if/then/else, for/next, do/loop, choose case, try/catch/finally, create/destroy...
- **类型**: integer, long, string, date, datetime, datawindow, userobject, transaction...
- **访问修饰符**: public, private, protected, shared, instance, global, constant, readonly
- **PB 枚举常量**: HourGlass!, Arrow!, TRUE, FALSE, OK!, CANCEL!...
- **嵌入式 SQL**: SELECT/INSERT/UPDATE/DELETE 关键字特殊高亮
- **DataWindow 表达式**: dw_1.Retrieve, dw_1.SetItem, dw_1.Object.Data[1,1]...
- **注释**: 单行 `//` 和块 `/* */`
- **字符串**: 双引号 `"` 和单引号 `'`，含 PB 转义 `~n ~r ~t ~"`
- **数字**: 整数、浮点数、十六进制

### ✅ 实时诊断 (Lint)
在编辑时自动检测代码质量问题：

| 级别 | 规则 | 说明 |
|------|------|------|
| 🔴 Error | empty_catch | 空 CATCH 块 — 错误被静默吞掉 |
| 🟡 Warning | routine_too_long | 函数超过 200 行 |
| 🟡 Warning | deep_nesting | 嵌套深度超过 4 层 |
| 🟡 Warning | select_star | DataWindow 使用 SELECT * |
| 🟡 Warning | hardcoded_sql | 硬编码 SQL |
| 🟡 Warning | deprecated_function | 使用废弃 PB 函数 |
| 🟡 Warning | high_complexity | 圈复杂度超过 20 |
| 🔵 Info | global_variable | 全局变量 |
| 🔵 Info | no_error_handling | 函数缺少 try-catch |
| 🔵 Info | magic_numbers | 使用未命名常量 |

所有阈值可在 VS Code 设置中自定义。

### ✅ 自动补全
- 关键字补全（if, for, choose case, try 等）
- 类型补全（integer, string, datawindow 等）
- PB 内置函数补全（Retrieve, SetItem, MessageBox 等）
- 对象方法补全（Hide, Show, TriggerEvent 等）
- 访问修饰符补全（public, private, protected 等）

### ✅ 悬停提示
鼠标悬停在关键字/函数上显示文档说明：
- 数据类型说明（integer, long, string, date...）
- SQLCA 对象属性说明
- 常用函数语法和返回值说明
- DataWindow 函数用法

### ✅ 智能编辑
- **自动缩进**: if/for/do/try/choose 自动增加缩进
- **括号匹配**: `()`, `[]`, `""`, `''` 自动配对
- **代码折叠**: 函数/事件自动折叠
- **$PBExportHeader$ 识别**: 首行自动识别 PB 源文件

## 支持的文件类型

| 扩展名 | PB 对象类型 |
|--------|------------|
| .srw | Window 窗口 |
| .sru | User Object 用户对象 |
| .srd | DataWindow 数据窗口 |
| .srf | Function 全局函数 |
| .srm | Menu 菜单 |
| .sra | Application 应用程序 |
| .srs | Structure 结构体 |
| .srq | Query 查询 |
| .srp | Pipeline 数据管道 |
| .srj | Project 工程 |
| .srx | Proxy 代理 |
| .sre | Embedded SQL 嵌入式 SQL |
| .src | Component 组件 |

## 安装

### 方式 1: 从源码安装

```bash
cd vscode-extension
npm install -g @vscode/vsce
vsce package
# 生成 powerscript-1.0.0.vsix，双击安装或:
code --install-extension powerscript-1.0.0.vsix
```

### 方式 2: 开发模式

```bash
cd vscode-extension
code --extensionDevelopmentPath .
```

## 配置

在 VS Code 设置中搜索 "PowerScript"：

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| powerscript.enableLinting | true | 启用实时语法检查 |
| powerscript.maxRoutineLines | 200 | 函数最大行数 |
| powerscript.maxComplexity | 20 | 圈复杂度阈值 |
| powerscript.maxNesting | 4 | 最大嵌套深度 |
| powerscript.enableEmptyCatchCheck | true | 检查空 CATCH 块 |
| powerscript.enableSelectStarCheck | true | 检查 SELECT * |
| powerscript.enableGlobalVariableCheck | true | 报告全局变量 |
| powerscript.enableDeprecatedCheck | true | 检查废弃函数 |
| powerscript.enableHardcodedSqlCheck | true | 检查硬编码 SQL |

## 命令

- **PowerScript: Run Lint on Current File** — 对当前文件执行检查
- **PowerScript: Run Lint on Directory** — 对整个工作区执行检查

## 零依赖

本插件 **零外部运行时依赖**：
- 语法高亮: VS Code 内置 TextMate 引擎
- 诊断: 纯 JavaScript 实现
- 补全/悬停: VS Code Extension API

与 [pb-devkit](../README.md) CLI 工具互补：
- **VS Code 插件**: 实时编辑体验（高亮+lint+补全）
- **pb-devkit CLI**: 批量分析/重构/导入/编译

## License

MIT
