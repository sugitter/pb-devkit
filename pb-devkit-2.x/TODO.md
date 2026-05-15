# PB DevKit 2.x 开发进度

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
| **Desktop** | **22 panels** | **✅ 79%** |
| orca | import, build, compile | ⏳ (需 DLL) |
| advanced | refactor, review, snapshot, workflow, diff | ⏳ |

## ⏳ 待完成

### Rust 后端
- [ ] ORCA 引擎封装 (需要 PBSpyORCA.dll)
- [ ] 版本快照
- [ ] 重构引擎

### 优化方向 (v2.2)

#### 1. Desktop 进度 Modal
- [ ] 添加进度 Modal 组件
- [ ] 支持取消按钮
- [ ] 导出失败文件自动重试机制

#### 2. 搜索结果缓存
- [ ] 实现搜索结果缓存机制
- [ ] 缓存失效策略

#### 3. ORCA 引擎 (待定)
- [ ] ORCA 引擎封装（需要 PBSpyORCA.dll）
- [ ] 版本快照
- [ ] 重构引擎

### 文档
- [x] 完善 README.md (中英双语)
- [x] 添加命令行使用示例 (CLI_EXAMPLES.md)
- [x] 更新 FUNCTION_MATRIX.md (CLI 100% 完成)