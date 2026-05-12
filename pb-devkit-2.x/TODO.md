# PB DevKit 2.x 开发进度

## ✅ 已完成

### Rust 后端
- [x] PBL 解析器 (完善版) - 支持 PB5-PB12.6 ANSI/Unicode
- [x] PE 提取器 - 支持从 EXE 提取 PBD 资源
- [x] PBL 命令 - parse_pbl, get_pbl_info, list_entries, export_entry, export_pbl
- [x] PE 命令 - detect_file_type, analyze_pe, extract_pbd_from_exe
- [x] 项目命令 - detect_project, run_doctor, find_pbl_files
- [x] 搜索命令 - search_in_files, search_by_type
- [x] DataWindow 分析 - analyze_datawindows, get_dw_sql
- [x] 反编译命令 - list_decompile_entries, decompile_entry, decompile_all
- [x] 报告生成器 - generate_report, export_report

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

### 构建问题
- [x] 修复 Angular 编译错误 (@if/@for 转义问题)
- [x] 修复 Rust mut 警告

### 命令实现 (2.x)

| 模块 | 命令 | 状态 |
|------|------|------|
| pbl | parse, info, list, export, export-pbl | ✅ |
| pe | file-type, analyze-pe, extract-pbd | ✅ |
| project | project, find-pbl, doctor | ✅ |
| search | search, search-type | ✅ |
| dw | analyze-dw, dw-sql | ✅ |
| decompile | decompile, decompile-all, list-decompile | ✅ |
| report | report, export-report | ✅ |
| orca | import, build, compile | ⏳ (需 DLL) |
| advanced | refactor, review, snapshot, workflow, diff | ⏳ |

## ⏳ 待完成

### Rust 后端
- [ ] ORCA 引擎封装 (需要 PBSpyORCA.dll)
- [ ] 版本快照
- [ ] 重构引擎

### 优化方向
- [ ] 完善 DataWindow SQL 解析
- [ ] 添加更多 PBL 版本支持检测
- [ ] 优化搜索性能 (大项目) 
- [ ] 添加批量导出进度显示

### 文档
- [x] 完善 README.md (中英双语)
- [ ] 添加命令行使用示例