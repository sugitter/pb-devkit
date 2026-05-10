# PB DevKit 功能对比矩阵

> 对比 1.x (Python CLI) 与 2.x (Rust CLI + Tauri Desktop) 的功能覆盖情况
> 
> 生成时间: 2026-05-10

## 命令功能对比

| 命令 | 1.x Python CLI | 2.x Rust CLI | 2.x Desktop (Tauri) | 状态 | 备注 |
|-------|---------------|--------------|---------------------|------|------|
| **PBL 解析** |
| parse / list | ✅ `list.py` | ✅ `list` | ✅ `list_entries` | ✅ 完成 | |
| info | ✅ `list.py --info` | ✅ `info` | ✅ `get_pbl_info` | ✅ 完成 | |
| export | ✅ `export.py` | ✅ `export` | ✅ `export_entry` | ✅ 完成 | |
| export_pbl (批量) | ✅ `export.py` | ❌ | ✅ `export_pbl` | ⚠️ CLI 缺失 | |
| **PE 解析** |
| file_type | ✅ `analyze.py` | ❌ | ✅ `detect_file_type` | ⚠️ CLI 缺失 | |
| analyze_pe | ✅ `analyze.py` | ❌ | ✅ `analyze_pe` | ⚠️ CLI 缺失 | |
| extract_pbd | ✅ `analyze.py` | ❌ | ✅ `extract_pbd_from_exe` | ⚠️ CLI 缺失 | |
| **项目管理** |
| doctor | ✅ `doctor.py` | ❌ | ✅ `run_doctor` | ⚠️ CLI 缺失 | |
| init / detect | ✅ `init.py` | ✅ `project` | ✅ `detect_project` | ✅ 完成 | |
| find_pbl | ✅ `analyze_project.py` | ❌ | ✅ `find_pbl_files` | ⚠️ CLI 缺失 | |
| **搜索** |
| search | ✅ `search.py` | ✅ `search` | ✅ `search_in_files` | ✅ 完成 | |
| search_by_type | ✅ `search.py --type` | ❌ | ✅ `search_by_type` | ⚠️ CLI 缺失 | |
| **DataWindow** |
| dw analyze | ✅ `dw.py` | ❌ | ✅ `analyze_datawindows` | ⚠️ CLI 缺失 | |
| dw sql | ✅ `dw.py --sql` | ❌ | ✅ `get_dw_sql` | ⚠️ CLI 缺失 | |
| **反编译** |
| decompile | ✅ `decompile.py` | ❌ | ✅ `decompile_entry` | ⚠️ CLI 缺失 | |
| decompile_all | ✅ `decompile.py --all` | ❌ | ✅ `decompile_all` | ⚠️ CLI 缺失 | |
| list_decompile | ✅ `decompile.py --list` | ❌ | ✅ `list_decompile_entries` | ⚠️ CLI 缺失 | |
| **报告** |
| report | ✅ `report.py` | ✅ `report` | ✅ `generate_report` | ✅ 完成 | |
| export_report | ✅ `report.py --export` | ❌ | ✅ `export_report` | ⚠️ CLI 缺失 | |
| stats | ✅ `stats.py` | ❌ | ✅ (含在 report) | ⚠️ CLI 缺失 | |
| **ORCA 引擎** |
| import | ✅ `import_.py` | ❌ | ❌ | ⏳ 需要 DLL | |
| build | ✅ `build.py` | ❌ | ❌ | ⏳ 需要 DLL | |
| compile | ✅ `compile.py` | ❌ | ❌ | ⏳ 需要 DLL | |
| **高级功能** |
| refactor | ✅ `refactor.py` | ❌ | ❌ | ⏳ 待实现 | |
| review | ✅ `review.py` | ❌ | ❌ | ⏳ 待实现 | |
| snapshot | ✅ `snapshot.py` | ❌ | ❌ | ⏳ 待实现 | |
| workflow | ✅ `workflow.py` | ❌ | ❌ | ⏳ 待实现 | |
| diff | ✅ `diff.py` | ❌ | ❌ | ⏳ 待实现 | |

## 前端功能对比

| 功能 | 1.x (无前端) | 2.x Desktop (Angular) | 状态 |
|------|--------------|----------------------|------|
| 项目选择器 | ❌ | ✅ `project-selector` | ✅ 完成 |
| PBL 列表视图 | ❌ | ✅ `pbl-list` | ✅ 完成 |
| 源码编辑器 | ❌ | ✅ `source-viewer` | ✅ 完成 |
| DataWindow 可视化 | ❌ | ✅ `dw-analyzer` | ✅ 完成 |
| 搜索面板 | ❌ | ✅ `search-panel` | ✅ 完成 |
| 反编译面板 | ❌ | ✅ `decompile-panel` | ✅ 完成 |
| 报告查看器 | ❌ | ✅ (主界面集成) | ✅ 完成 |
| PE 信息视图 | ❌ | ⚠️ (接口已定义，UI 待实现) | ⏳ 待实现 |
| 项目管理界面 | ❌ | ⚠️ (基础功能) | ⏳ 待完善 |

## 覆盖率统计

| 类别 | 1.x 功能数 | 2.x CLI 覆盖 | 2.x Desktop 覆盖 | CLI 覆盖率 | Desktop 覆盖率 |
|------|------------|--------------|------------------|-----------|----------------|
| 核心 PBL 操作 | 4 | 3/4 (75%) | 4/4 (100%) | ⚠️ | ✅ |
| PE 解析 | 3 | 0/3 (0%) | 3/3 (100%) | ❌ | ✅ |
| 项目管理 | 3 | 1/3 (33%) | 3/3 (100%) | ❌ | ✅ |
| 搜索 | 2 | 1/2 (50%) | 2/2 (100%) | ⚠️ | ✅ |
| DataWindow | 2 | 0/2 (0%) | 2/2 (100%) | ❌ | ✅ |
| 反编译 | 3 | 0/3 (0%) | 3/3 (100%) | ❌ | ✅ |
| 报告 | 2 | 1/2 (50%) | 2/2 (100%) | ⚠️ | ✅ |
| ORCA 功能 | 3 | 0/3 (0%) | 0/3 (0%) | ⏳ | ⏳ |
| 高级功能 | 5 | 0/5 (0%) | 0/5 (0%) | ⏳ | ⏳ |
| **总计** | **27** | **6/27 (22%)** | **19/27 (70%)** | ❌ | ✅ |

## 优先级建议

### 🔴 高优先级（CLI 功能缺失，影响命令行用户）

| 功能 | 原因 |
|------|------|
| PE 解析命令 | CLI 用户无法分析 EXE 文件 |
| 反编译命令 | CLI 是主要反编译使用场景 |
| DW 分析命令 | 数据分析是常见需求 |

### 🟡 中优先级（Desktop 功能完善）

| 功能 | 原因 |
|------|------|
| PE 信息视图 UI | 后端已完成，前端界面缺失 |
| 项目管理界面 | 当前只有基础功能 |
| diff 功能 | 代码对比是常见需求 |

### 🟢 低优先级（高级功能）

| 功能 | 原因 |
|------|------|
| refactor | 复杂，使用频率低 |
| review | 复杂，使用频率低 |
| snapshot | 有用但非核心 |
| workflow | 高级自动化，使用频率低 |

## 结论

1. **Desktop (Tauri + Angular) 功能基本完备**（70% 覆盖），核心功能已可用
2. **CLI 功能严重缺失**（仅 22% 覆盖），需要补强
3. **ORCA 功能**需要 PBSpyORCA.dll 才能实施
4. **建议下一步**：优先补充 CLI 的核心命令（PE、反编译、DW）
