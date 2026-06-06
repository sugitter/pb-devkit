# PB DevKit 2.x 开发进度

## ✅ 已完成 (v2.2.1) - 2026-06-06 更新

### 本次更新 (2026-06-06)
- [x] 修复 F: 盘 git HEAD（refs/heads/main 指向无效对象）
- [x] 同步本地工作区与远程最新 commit（`1b97b90`）
- [x] 删除脚手架残留文件：`app.component.html` 和 `app.component.css`（已通过 git 提交移除）
- [x] 推送到 Gitea (origin) 和 GitHub，两端均同步至 `1b97b90`
- [x] 修复 `pb-devkit-core/Cargo.toml` 版本号不一致（2.1.0 → 2.2.1）
- [x] 同步 `Cargo.lock`（core + cli）版本号至 2.2.1
- [x] 创建 `CHANGELOG.md`（中英双语，遵循 Keep a Changelog 格式）
- [x] 新增 CLI `#[cfg(test)] mod tests` — main.rs 含 2 个占位测试
- [x] 199/199 测试全部通过，clippy 0 warnings

---

## ✅ 已完成 (v2.2.1) - 2026-06-04 更新

### 本次更新 (2026-06-04)
- [x] 新增 `migrate-panel` Angular 组件 — PB→Web 迁移向导（步骤引导 + 分析结果 + 统计卡片）
- [x] 新增 `build-panel` Angular 组件 — PBGen.exe 编译 GUI（自动检测 PBGen + 多编译模式 + 日志）
- [x] Tauri 后端新增 `commands/build.rs`（`check_pbgen` / `build_pb_application`）
- [x] `MigrateResult` 补充 `components` / `services` / `models` 别名字段（修复前端字段不匹配）
- [x] `app.component.ts` 集成两个新面板，侧边栏添加 `transform` / `construction` 图标
- [x] `FUNCTION_MATRIX.md` Desktop 覆盖率 20/20 → 22/22（100%），migrate/build 状态从 — 改为 ✅
- [x] `README.md` 中英双语同步更新
- [x] PE 解析器增强（`pe.rs`）：支持 PB 10+ 单一 EXE 的三层扫描策略
  - 解析 Optional Header DataDirectory 获取 Certificate Table 偏移 + .rsrc 段定位
  - 扫描窗口 4KB→64KB；新增 .rsrc 段内扫描 + 全文件兜底扫描（≤256MB）
  - 解决 logistic.exe（PB 10.0 单一 EXE）识别失败问题
- [x] 测试体系补强（111 新测试：PE 14 + PBL 17 + DW 30 + Project 21 + Search 22 + Decompile 7）— 项目测试从 3→114
- [x] CI/CD 增强（`.github/workflows/ci.yml`）— 新增 clippy/fmt/audit + Windows builder + Node 22
- [x] `Cargo.toml` 清理 — `tempfile` 从 `[dependencies]` 移至 `[dev-dependencies]`
- [x] 清理脚手架残留文件：`app.component.html` 和 `app.component.css` ✅ 已通过 git 删除

---

## ✅ 已完成 (v2.1.0) - 2026-05-18 更新

### 本次更新 (2026-05-18)
- [x] CLI clippy 警告修复 (enumerate, unnecessary_to_owned)
- [x] Tauri 后端添加 diff 命令 (diff_files API)
- [x] 修复 Tauri 后端未使用的 import 警告
- [x] CLI help 输出添加 search-regex 命令说明
- [x] 版本号统一更新为 v2.1.0 (CLI/Cargo.toml/Core)
- [x] 选择项目后自动加载第一个 PBL 的对象列表
- [x] 新增 Settings 面板组件 (settings-panel)
- [x] 侧边栏添加设置按钮

---

## ✅ 已完成 (v2.1)

### Rust 后端
- [x] PBL 解析器 (完善版) - 支持 PB5-PB12.6 ANSI/Unicode
- [x] PE 提取器 - 支持从 EXE 提取 PBD 资源
- [x] PBL 命令 - parse_pbl, get_pbl_info, list_entries, export_entry, export_pbl
- [x] PE 命令 - detect_file_type, analyze_pe, extract_pbd_from_exe
- [x] 项目命令 - detect_project, run_doctor, find_pbl_files
- [x] 搜索命令 - search_in_files, search_by_type, **search-with-regex** ⭐
- [x] DataWindow 分析 - analyze_datawindows, get_dw_sql
- [x] 反编译命令 - list_decompile_entries, decompile_entry, decompile_all
- [x] 报告生成器 - generate_report, export_report

### v2.1 新增功能 ⭐
- [x] **DataWindow SQL 解析增强**
  - [x] WHERE/ORDER BY/GROUP BY 完整表达式提取
  - [x] 参数绑定信息提取 (Retrieve arguments)
  - [x] 支持 UNION 查询
  - [x] 子查询检测 (IN/EXISTS/SCALAR)
  - [x] 计算列/Computed Column 提取
- [x] **批量导出进度显示**
  - [x] CLI 进度条 (indicatif)
  - [x] 显示已导出/总数、当前文件
- [x] **搜索性能优化**
  - [x] 并行搜索 (rayon 多线程)
  - [x] 正则表达式搜索支持
- [x] **PBL 版本检测增强**
  - [x] 自动检测 PBL 版本（magic bytes 分析）
  - [x] 区分 ANSI/Unicode 编码
  - [x] 支持 PB 12.5+ 新增对象类型 (soap_client, soap_server, etc.)
- [x] **搜索索引机制**
  - [x] 索引文件生成 (.pbdevkit.idx)
  - [x] 增量搜索（只搜变更文件）
  - [x] 文件变化检测 (modified, size, checksum)
- [x] **搜索结果缓存**
  - [x] TTL 缓存机制 (默认 1 小时)
  - [x] LRU 淘汰策略
  - [x] 路径失效支持
- [x] **Desktop 进度 Modal**
  - [x] progress-modal 组件
  - [x] 进度条显示
  - [x] 支持取消按钮
- [x] **版本快照功能**
  - [x] ProjectSnapshot 结构体
  - [x] 快照保存/加载
  - [x] 快照对比 (SnapshotDiff)
  - [x] SnapshotManager 工具类
- [x] **导出失败自动重试机制**
  - [x] Retry 工具类 (指数退避)
  - [x] RetryConfig 配置
  - [x] BatchExportResult 批量导出结果

### Angular 前端
- [x] 项目选择器组件 (project-selector)
- [x] PBL 列表视图 (pbl-list)
- [x] 源码编辑器 (source-viewer)
- [x] DataWindow 可视化 (dw-analyzer)
- [x] 搜索结果面板 (search-panel)
- [x] 反编译面板 (decompile-panel)
- [x] 环境诊断面板 (doctor-panel)
- [x] PE 信息视图 (pe-view)
- [x] 报告查看器 (report-view)
- [x] 项目统计面板 (project-stats)

### 构建问题
- [x] 修复 Angular 编译错误 (@if/@for 转义问题)
- [x] 修复 Rust mut 警告

### 命令实现 (2.x)

| 模块 | 命令 | 状态 |
|------|------|------|
| pbl | parse, info, list, export, export-pbl | ✅ 100% |
| pe | file-type, analyze-pe, extract-pbd | ✅ 100% |
| project | project, find-pbl, doctor | ✅ 100% |
| search | search, search-type, **search-regex** | ✅ 100% |
| dw | analyze-dw, dw-sql | ✅ 100% |
| decompile | decompile, decompile-all, list-decompile | ✅ 100% |
| report | report, export-report | ✅ 100% |
| **CLI 总计** | **21 commands** | **✅ 100%** |
| **Desktop** | **22 panels** | **✅ 100%** |
| orca | import, build, compile | ⏳ (需 DLL) |
| advanced | refactor, review, snapshot, workflow, diff | ⏳ |

## ⏳ 待完成 (仅剩 ORCA 引擎)

### 仅剩 ORCA 引擎
- [ ] ORCA 引擎封装 (需要 PBSpyORCA.dll) - 待外部依赖

> 注: v2.1 所有计划功能均已完成 ✅

### 文档
- [x] 完善 README.md (中英双语)
- [x] 添加命令行使用示例 (CLI_EXAMPLES.md)
- [x] 更新 FUNCTION_MATRIX.md (CLI 100% 完成)