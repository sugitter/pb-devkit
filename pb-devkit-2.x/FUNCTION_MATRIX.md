# PB DevKit 功能对比矩阵 / Function Matrix

> 对比 1.x (Python CLI) 与 2.x (Rust CLI + Tauri Desktop) 的功能覆盖情况
> Compare 1.x (Python CLI) vs 2.x (Rust CLI + Tauri Desktop) feature coverage
>
> 更新时间 / Updated: 2026-05-11

## 命令功能对比 / Command Comparison

| 命令 / Command | 1.x Python CLI | 2.x Rust CLI | 2.x Desktop (Tauri) | 状态 / Status | 备注 / Notes |
|----------------|---------------|--------------|---------------------|--------------|-------------|
| **PBL 解析 / PBL Parse** |
| parse / list | ✅ `list.py` | ✅ `parse` / `list` | ✅ `parse_pbl` / `list_entries` | ✅ Done | |
| info | ✅ `list.py --info` | ✅ `info` | ✅ `get_pbl_info` | ✅ Done | |
| export | ✅ `export.py` | ✅ `export` | ✅ `export_entry` | ✅ Done | |
| export_pbl (batch) | ✅ `export.py` | ✅ `export-pbl` | ✅ `export_pbl` | ✅ Done | |
| **PE 解析 / PE Analysis** |
| file_type | ✅ `analyze.py` | ✅ `file-type` | ✅ `detect_file_type` | ✅ Done | |
| analyze_pe | ✅ `analyze.py` | ✅ `analyze-pe` | ✅ `analyze_pe` | ✅ Done | |
| extract_pbd | ✅ `analyze.py` | ✅ `extract-pbd` | ✅ `extract_pbd_from_exe` | ✅ Done | |
| **项目管理 / Project Management** |
| doctor | ✅ `doctor.py` | ✅ `doctor` | ✅ `run_doctor` | ✅ Done | |
| init / detect | ✅ `init.py` | ✅ `project` | ✅ `detect_project` | ✅ Done | |
| find_pbl | ✅ `analyze_project.py` | ✅ `find-pbl` | ✅ `find_pbl_files` | ✅ Done | |
| **搜索 / Search** |
| search | ✅ `search.py` | ✅ `search` | ✅ `search_in_files` | ✅ Done | |
| search_by_type | ✅ `search.py --type` | ✅ `search-type` | ✅ `search_by_type` | ✅ Done | |
| **DataWindow** |
| dw analyze | ✅ `dw.py` | ✅ `analyze-dw` | ✅ `analyze_datawindows` | ✅ Done | |
| dw sql | ✅ `dw.py --sql` | ✅ `dw-sql` | ✅ `get_dw_sql` | ✅ Done | |
| **反编译 / Decompile** |
| decompile | ✅ `decompile.py` | ✅ `decompile` | ✅ `decompile_entry` | ✅ Done | |
| decompile_all | ✅ `decompile.py --all` | ✅ `decompile-all` | ✅ `decompile_all` | ✅ Done | |
| list_decompile | ✅ `decompile.py --list` | ✅ `list-decompile` | ✅ `list_decompile_entries` | ✅ Done | |
| **报告 / Report** |
| report | ✅ `report.py` | ✅ `report` | ✅ `generate_report` | ✅ Done | |
| export_report | ✅ `report.py --export` | ✅ `export-report` | ✅ `export_report` | ✅ Done | |
| stats | ✅ `stats.py` | ✅ (in `report`) | ✅ (in `report`) | ✅ Done | |
| **ORCA 引擎 / ORCA Engine** |
| import | ✅ `import_.py` | ⏳ | ⏳ | ⏳ Pending | 需要 PBSpyORCA.dll / Requires PBSpyORCA.dll |
| build | ✅ `build.py` | ⏳ | ⏳ | ⏳ Pending | 需要 PBSpyORCA.dll / Requires PBSpyORCA.dll |
| compile | ✅ `compile.py` | ⏳ | ⏳ | ⏳ Pending | 需要 PBSpyORCA.dll / Requires PBSpyORCA.dll |
| **高级功能 / Advanced** |
| refactor | ✅ `refactor.py` | ⏳ | ⏳ | ⏳ Pending | 复杂，使用频率低 / Complex, low usage |
| review | ✅ `review.py` | ⏳ | ⏳ | ⏳ Pending | 复杂，使用频率低 / Complex, low usage |
| snapshot | ✅ `snapshot.py` | ⏳ | ⏳ | ⏳ Pending | 有用但非核心 / Useful but non-core |
| workflow | ✅ `workflow.py` | ⏳ | ⏳ | ⏳ Pending | 高级自动化 / Advanced automation |
| diff | ✅ `diff.py` | ⏳ | ⏳ | ⏳ Pending | 代码对比 / Code diff |

## 前端功能对比 / Frontend Comparison

| 功能 / Feature | 1.x (无前端) | 2.x Desktop (Angular) | 状态 / Status |
|----------------|--------------|----------------------|--------------|
| 项目选择器 / Project selector | ❌ | ✅ `project-selector` | ✅ Done |
| PBL 列表视图 / PBL list view | ❌ | ✅ `pbl-list` | ✅ Done |
| 源码编辑器 / Source viewer | ❌ | ✅ `source-viewer` | ✅ Done |
| DataWindow 可视化 / DW analyzer | ❌ | ✅ `dw-analyzer` | ✅ Done |
| 搜索面板 / Search panel | ❌ | ✅ `search-panel` | ✅ Done |
| 反编译面板 / Decompile panel | ❌ | ✅ `decompile-panel` | ✅ Done |
| 环境诊断面板 / Doctor panel | ❌ | ✅ `doctor-panel` | ✅ Done |
| 报告查看器 / Report viewer | ❌ | ✅ `report-view` | ✅ Done |
| PE 信息视图 / PE info view | ❌ | ✅ `pe-view` | ✅ Done |
| 项目管理界面 / Project management UI | ❌ | ⏳ (基础功能 / basic) | ⏳ Pending |

## 覆盖率统计 / Coverage Statistics

| 类别 / Category | 1.x 功能数 / 1.x Count | 2.x CLI 覆盖 | 2.x Desktop 覆盖 | CLI 覆盖率 / CLI % | Desktop 覆盖率 / Desktop % |
|-----------------|--------------------------|--------------|------------------|-------------------|------------------------|
| 核心 PBL 操作 / Core PBL | 4 | 4/4 (100%) | 4/4 (100%) | ✅ | ✅ |
| PE 解析 / PE Analysis | 3 | 3/3 (100%) | 3/3 (100%) | ✅ | ✅ |
| 项目管理 / Project Mgmt | 3 | 3/3 (100%) | 3/3 (100%) | ✅ | ✅ |
| 搜索 / Search | 2 | 2/2 (100%) | 2/2 (100%) | ✅ | ✅ |
| DataWindow | 2 | 2/2 (100%) | 2/2 (100%) | ✅ | ✅ |
| 反编译 / Decompile | 3 | 3/3 (100%) | 3/3 (100%) | ✅ | ✅ |
| 报告 / Report | 3 | 3/3 (100%) | 3/3 (100%) | ✅ | ✅ |
| ORCA 功能 / ORCA | 3 | 0/3 (0%) | 0/3 (0%) | ⏳ | ⏳ |
| 高级功能 / Advanced | 5 | 0/5 (0%) | 0/5 (0%) | ⏳ | ⏳ |
| **总计 / Total** | **28** | **20/28 (71%)** | **22/28 (79%)** | ⏳ | ✅ |

> 注：ORCA 和高级功能依赖外部 DLL 或复杂度较高，列为 v2.1+ 规划。
> Note: ORCA and advanced features depend on external DLLs or high complexity; planned for v2.1+.

## 优先级建议 / Priority Recommendations

### 🔴 高优先级（v2.1）— High Priority (v2.1)

| 功能 / Feature | 原因 / Reason |
|---------------|----------------|
| ORCA 功能 / ORCA features | 需要 DLL，完成后可替代 PB IDE 编译/构建 / Requires DLL, enables PB IDE replacement |
| PE 信息视图 UI / PE info view UI | 后端已完成，前端界面缺失 / Backend done, frontend UI missing |

### 🟡 中优先级（v2.2）— Medium Priority (v2.2)

| 功能 / Feature | 原因 / Reason |
|---------------|----------------|
| 项目管理界面完善 / Project management UI | 当前只有基础功能 / Currently basic only |
| diff 功能 / Diff | 代码对比是常见需求 / Common need for code comparison |

### 🟢 低优先级（v2.3+）— Low Priority (v2.3+)

| 功能 / Feature | 原因 / Reason |
|---------------|----------------|
| refactor | 复杂，使用频率低 / Complex, low usage |
| review | 复杂，使用频率低 / Complex, low usage |
| snapshot | 有用但非核心 / Useful but non-core |
| workflow | 高级自动化，使用频率低 / Advanced automation, low usage |

## 结论 / Conclusion

1. **Desktop (Tauri + Angular) 功能基本完备**（20/28，71% 覆盖），核心功能已可用
   **Desktop (Tauri + Angular) is largely complete** (20/28, 71% coverage), core features ready
2. **CLI 功能已全部实现**（20/20 核心命令 ✅），覆盖所有核心场景
   **CLI is fully implemented** (20/20 core commands ✅), covering all core scenarios
3. **ORCA 功能**需要 PBSpyORCA.dll 才能实施，列为下阶段目标
   **ORCA features** require PBSpyORCA.dll, planned for next phase
4. **建议下一步**：完善 Desktop 前端剩余 UI（PE 视图、项目管理），规划 ORCA 集成
   **Next steps**: Complete remaining Desktop UI (PE view, project management), plan ORCA integration
