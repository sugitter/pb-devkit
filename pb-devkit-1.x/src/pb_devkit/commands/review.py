"""pb review command - Project analysis, restructure suggestions, and code review.

Given a project directory (PBL sources or binary), performs a comprehensive
analysis and generates a structured report:

  1. Project structure overview (PBL layout, object counts by type)
  2. Code quality analysis (issues, complexity hotspots)
  3. Dependency graph summary (cross-PBL dependencies)
  4. DataWindow inventory (SQL, tables referenced)
  5. Refactoring suggestions (naming, structure, patterns)
  6. Compilation readiness (missing ORCA? library list?)

Usage:
    python pb.py review <project_dir>
    python pb.py review <project_dir> --html          # HTML report
    python pb.py review <project_dir> --src ./src     # Specify source dir
    python pb.py review <project_dir> --no-dw         # Skip DW analysis
    python pb.py review <project_dir> -o report.md    # Custom output path
"""
import argparse
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "review",
        help="Comprehensive project review: structure, quality, DW, refactoring suggestions",
        description=(
            "Analyze a PowerBuilder project directory and generate a full "
            "review report covering structure, code quality, DataWindow inventory, "
            "dependencies, and actionable improvement suggestions."
        ),
    )
    p.add_argument(
        "target",
        help="Project directory (containing .pbl, .exe, .pbd files) or source dir (containing .sr* files)",
    )
    p.add_argument(
        "--src",
        default=None,
        metavar="DIR",
        help="Explicitly specify the exported source directory (if different from target)",
    )
    p.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML report instead of Markdown",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Output file path (default: <target>/REVIEW.md or REVIEW.html)",
    )
    p.add_argument(
        "--no-dw",
        action="store_true",
        help="Skip DataWindow SQL analysis (faster)",
    )
    p.add_argument(
        "--no-quality",
        action="store_true",
        help="Skip code quality analysis",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Also output raw JSON data alongside the report",
    )
    p.add_argument(
        "--top",
        type=int,
        default=20,
        metavar="N",
        help="Show top N hotspots / issues (default: 20)",
    )
    return p


def run(args):
    """Run project review."""
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"[error] Path not found: {target}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*62}")
    print(f"  pb review — PowerBuilder Project Review")
    print(f"{'='*62}")
    print(f"  Target: {target}")
    print()

    # ---------------------------------------------------------------
    # Phase 1: Detect project type and locate source files
    # ---------------------------------------------------------------
    print("[1/5] Scanning project structure ...")
    src_dir = _find_source_dir(target, args.src)
    project_info = _scan_project(target, src_dir)
    _print_structure_summary(project_info)

    # ---------------------------------------------------------------
    # Phase 2: Code quality
    # ---------------------------------------------------------------
    quality_data = {}
    if not args.no_quality and src_dir:
        print(f"\n[2/5] Analyzing code quality in {src_dir} ...")
        quality_data = _analyze_quality(src_dir)
        _print_quality_summary(quality_data, args.top)
    else:
        print(f"\n[2/5] Code quality analysis skipped.")

    # ---------------------------------------------------------------
    # Phase 3: DataWindow inventory
    # ---------------------------------------------------------------
    dw_data = {}
    if not args.no_dw and src_dir:
        print(f"\n[3/5] Scanning DataWindow objects ...")
        dw_data = _analyze_datawindows(src_dir)
        _print_dw_summary(dw_data)
    else:
        print(f"\n[3/5] DataWindow analysis skipped.")

    # ---------------------------------------------------------------
    # Phase 4: Dependency mapping
    # ---------------------------------------------------------------
    dep_data = {}
    if src_dir:
        print(f"\n[4/5] Mapping dependencies ...")
        dep_data = _analyze_dependencies(src_dir)
        _print_dep_summary(dep_data)
    else:
        print(f"\n[4/5] Dependency analysis skipped (no source dir).")

    # ---------------------------------------------------------------
    # Phase 5: Generate report
    # ---------------------------------------------------------------
    print(f"\n[5/5] Generating report ...")

    report_data = {
        "project": project_info,
        "quality": quality_data,
        "datawindows": dw_data,
        "dependencies": dep_data,
        "generated_at": datetime.now().isoformat(),
    }

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        ext = ".html" if args.html else ".md"
        out_path = target / f"REVIEW{ext}"

    if args.html:
        content = _render_html(report_data, args.top)
        out_path.write_text(content, encoding="utf-8")
    else:
        content = _render_markdown(report_data, args.top)
        out_path.write_text(content, encoding="utf-8")

    print(f"  Report written: {out_path}")

    if args.json:
        json_path = out_path.with_suffix(".json")
        json_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8"
        )
        print(f"  JSON data:     {json_path}")

    print(f"\n{'='*62}")
    print(f"  Review complete!")
    print(f"  {_count_summary(report_data)}")
    print(f"{'='*62}")
    return out_path


# ---------------------------------------------------------------------------
# Phase 1 helpers
# ---------------------------------------------------------------------------

def _find_source_dir(target: Path, explicit_src: Optional[str]) -> Optional[Path]:
    """Locate the exported source directory."""
    if explicit_src:
        p = Path(explicit_src).resolve()
        return p if p.is_dir() else None

    # If target itself has .sr* or .ps files -> it's already a source dir
    sr_files = list(target.rglob("*.srw")) + list(target.rglob("*.srd")) + list(target.rglob("*.sru"))
    ps_files = list(target.rglob("*.ps"))
    if sr_files or ps_files:
        return target

    # Otherwise look for src/ subdirectory
    src_candidate = target / "src"
    if src_candidate.is_dir():
        return src_candidate

    return None


def _scan_project(target: Path, src_dir: Optional[Path]) -> dict:
    """Scan project structure and collect file inventory."""
    info = {
        "root": str(target),
        "src_dir": str(src_dir) if src_dir else None,
        "pbl_files": [],
        "exe_files": [],
        "pbd_files": [],
        "dll_files": [],
        "object_counts": defaultdict(int),
        "pbl_object_counts": {},
        "total_objects": 0,
        "total_lines": 0,
        "source_files": [],
    }

    # Binary project files
    for ext, key in [(".pbl", "pbl_files"), (".exe", "exe_files"),
                     (".pbd", "pbd_files"), (".dll", "dll_files")]:
        for f in sorted(target.glob(f"*{ext}")):
            info[key].append(f.name)

    # Source files
    if src_dir and src_dir.is_dir():
        ext_map = {
            ".srw": "Window", ".srd": "DataWindow", ".srm": "Menu",
            ".srf": "Function", ".srs": "Structure", ".sru": "UserObject",
            ".sra": "Application", ".srq": "Query", ".ps": "Binary(ps)",
        }
        pbl_counts = defaultdict(lambda: defaultdict(int))

        for sr_file in sorted(src_dir.rglob("*")):
            if not sr_file.is_file():
                continue
            ext = sr_file.suffix.lower()
            obj_type = ext_map.get(ext)
            if not obj_type:
                continue

            info["object_counts"][obj_type] += 1
            info["total_objects"] += 1
            info["source_files"].append(str(sr_file.relative_to(src_dir)))

            # Count lines
            try:
                text = sr_file.read_text(encoding="utf-8-sig", errors="replace")
                info["total_lines"] += text.count("\n")
            except Exception:
                pass

            # Per-PBL counts
            parts = sr_file.relative_to(src_dir).parts
            pbl_name = parts[0] if len(parts) > 1 else "(root)"
            pbl_counts[pbl_name][obj_type] += 1

        info["object_counts"] = dict(info["object_counts"])
        info["pbl_object_counts"] = {
            k: dict(v) for k, v in sorted(pbl_counts.items())
        }

    return info


def _print_structure_summary(info: dict):
    """Print structure summary to console."""
    print(f"  Root:    {info['root']}")
    if info["pbl_files"]:
        print(f"  PBL:     {', '.join(info['pbl_files'])}")
    if info["exe_files"]:
        print(f"  EXE:     {', '.join(info['exe_files'])}")
    if info["pbd_files"]:
        print(f"  PBD:     {', '.join(info['pbd_files'])}")
    if info["dll_files"]:
        print(f"  DLL:     {', '.join(info['dll_files'])}")
    if info["total_objects"]:
        counts_str = ", ".join(
            f"{v} {k}" for k, v in sorted(info["object_counts"].items())
        )
        print(f"  Objects: {info['total_objects']} ({counts_str})")
        print(f"  Lines:   {info['total_lines']:,}")


# ---------------------------------------------------------------------------
# Phase 2: Code quality
# ---------------------------------------------------------------------------

def _analyze_quality(src_dir: Path) -> dict:
    """Run quality analysis on source files."""
    try:
        from pb_devkit.sr_parser import PBSourceAnalyzer
        analyzer = PBSourceAnalyzer()
        issues_by_file = analyzer.analyze_directory(src_dir)

        # Flatten
        all_issues = []
        for fname, issues in issues_by_file.items():
            if isinstance(issues, list):
                for iss in issues:
                    all_issues.append({**iss, "file": fname})

        severity_counts = defaultdict(int)
        rule_counts = defaultdict(int)
        for iss in all_issues:
            severity_counts[iss.get("severity", "info")] += 1
            rule_counts[iss.get("rule", "unknown")] += 1

        return {
            "total_issues": len(all_issues),
            "by_severity": dict(severity_counts),
            "by_rule": dict(sorted(rule_counts.items(), key=lambda x: -x[1])),
            "issues": all_issues,
        }
    except Exception as e:
        return {"error": str(e), "total_issues": 0, "issues": []}


def _print_quality_summary(data: dict, top: int):
    if data.get("error"):
        print(f"  [warn] Quality analysis failed: {data['error']}")
        return
    total = data.get("total_issues", 0)
    by_sev = data.get("by_severity", {})
    print(f"  Issues: {total} total — "
          f"{by_sev.get('error', 0)} errors, "
          f"{by_sev.get('warning', 0)} warnings, "
          f"{by_sev.get('info', 0)} info")
    by_rule = data.get("by_rule", {})
    if by_rule:
        print(f"  Top rules:")
        for rule, count in list(by_rule.items())[:5]:
            print(f"    {count:4d}  {rule}")


# ---------------------------------------------------------------------------
# Phase 3: DataWindow analysis
# ---------------------------------------------------------------------------

DW_SQL_RE = re.compile(
    r'retrieve\s*=\s*"([^"]*)"', re.IGNORECASE | re.DOTALL
)
DW_TABLE_RE = re.compile(
    r'\btable\s+name=(["\w]+)', re.IGNORECASE
)
DW_TABLE_FROM_SQL_RE = re.compile(
    r'\bfrom\s+([\w,\s]+?)(?:\s+where|\s+order|\s+group|\s+having|$)',
    re.IGNORECASE
)
DW_COLUMN_RE = re.compile(
    r'\bcolumn\s+type=\w+\s+.*?name=(["\w]+)', re.IGNORECASE
)
DW_RETRIEVE_ARGS_RE = re.compile(
    r'arguments\s*=\s*\(([^)]*)\)', re.IGNORECASE
)


def _analyze_datawindows(src_dir: Path) -> dict:
    """Analyze DataWindow .srd and .ps files to extract SQL and column info."""
    dws = {}
    tables_usage = defaultdict(list)

    for srd_file in sorted(src_dir.rglob("*.srd")):
        try:
            text = srd_file.read_text(encoding="utf-8-sig", errors="replace")
            dw_info = _parse_dw_source(srd_file.stem, text)
            dws[srd_file.stem] = dw_info
            for tbl in dw_info.get("tables", []):
                tables_usage[tbl].append(srd_file.stem)
        except Exception as e:
            dws[srd_file.stem] = {"error": str(e)}

    # Also scan .ps files for dataobject assignments
    dw_refs = defaultdict(list)  # dw_name -> [window/UO that references it]
    for ps_file in sorted(src_dir.rglob("*.ps")):
        try:
            text = ps_file.read_text(encoding="utf-8-sig", errors="replace")
            for m in re.finditer(r'\.dataobject\s*=\s*["\'](\w+)["\']', text, re.IGNORECASE):
                dw_refs[m.group(1).lower()].append(ps_file.stem)
        except Exception:
            pass

    return {
        "total": len(dws),
        "datawindows": dws,
        "tables_usage": {k: v for k, v in sorted(tables_usage.items())},
        "dw_references": dict(dw_refs),
    }


def _parse_dw_source(name: str, text: str) -> dict:
    """Parse a .srd DataWindow source file."""
    info = {
        "name": name,
        "tables": [],
        "columns": [],
        "sql": "",
        "retrieve_args": [],
        "style": "",
    }

    # Extract table names
    for m in DW_TABLE_RE.finditer(text):
        tbl = m.group(1).strip('"').strip()
        if tbl and tbl not in info["tables"]:
            info["tables"].append(tbl)

    # Extract SQL from retrieve= attribute
    m = DW_SQL_RE.search(text)
    if m:
        sql = m.group(1).strip()
        # Decode PB escape sequences
        sql = sql.replace("~n", "\n").replace("~r", "").replace("~t", "\t").replace('~"', '"')
        info["sql"] = sql
        # Also extract FROM tables from SQL
        fm = DW_TABLE_FROM_SQL_RE.search(sql)
        if fm:
            for tbl in re.split(r'[,\s]+', fm.group(1)):
                tbl = tbl.strip()
                if tbl and len(tbl) > 1 and tbl not in info["tables"]:
                    info["tables"].append(tbl)

    # Extract column names
    for m in DW_COLUMN_RE.finditer(text):
        col = m.group(1).strip('"').strip()
        if col and col not in info["columns"]:
            info["columns"].append(col)

    # Extract retrieve arguments
    m = DW_RETRIEVE_ARGS_RE.search(text)
    if m:
        args_str = m.group(1)
        for arg in re.findall(r'"(\w+)"\s+(\w+)', args_str):
            info["retrieve_args"].append({"name": arg[0], "type": arg[1]})

    # DataWindow style
    m = re.search(r'\bstyle\s+type=(\w+)', text, re.IGNORECASE)
    if m:
        info["style"] = m.group(1)

    return info


def _print_dw_summary(data: dict):
    total = data.get("total", 0)
    tables = data.get("tables_usage", {})
    print(f"  DataWindows: {total}")
    print(f"  Tables referenced: {len(tables)}")
    if tables:
        top_tables = sorted(tables.items(), key=lambda x: -len(x[1]))[:8]
        for tbl, dws in top_tables:
            print(f"    {tbl:25s}  used by {len(dws)} DW(s)")


# ---------------------------------------------------------------------------
# Phase 4: Dependencies
# ---------------------------------------------------------------------------

def _analyze_dependencies(src_dir: Path) -> dict:
    """Map cross-PBL dependencies via function calls and object references."""
    call_pattern = re.compile(
        r'(?:of|from)\s+(\w+)\.(\w+)\s*\(', re.IGNORECASE
    )
    inherits_pattern = re.compile(
        r'(?:autoinstantiate\s+)?(?:global|shared|local)\s+(?:constant\s+)?'
        r'(\w+)\s+\w+\s*(?:=|\Z)', re.IGNORECASE
    )

    pbl_deps: dict[str, set] = defaultdict(set)
    pbl_files = [d for d in src_dir.iterdir() if d.is_dir()] if src_dir.is_dir() else []

    for pbl_dir in pbl_files:
        pbl_name = pbl_dir.name
        for f in pbl_dir.rglob("*"):
            if f.suffix.lower() not in (".srw", ".srf", ".sru", ".srm", ".ps"):
                continue
            try:
                text = f.read_text(encoding="utf-8-sig", errors="replace")
                # Look for from/of references
                for m in call_pattern.finditer(text):
                    obj_name = m.group(1).lower()
                    # Try to find which PBL this object belongs to
                    for other_pbl in pbl_files:
                        if other_pbl == pbl_dir:
                            continue
                        candidate = other_pbl / f"{obj_name}.srw"
                        if not candidate.exists():
                            candidate = other_pbl / f"{obj_name}.sru"
                        if candidate.exists():
                            if other_pbl.name != pbl_name:
                                pbl_deps[pbl_name].add(other_pbl.name)
                            break
            except Exception:
                pass

    return {
        "pbl_dependencies": {k: sorted(v) for k, v in pbl_deps.items()},
    }


def _print_dep_summary(data: dict):
    deps = data.get("pbl_dependencies", {})
    if deps:
        print(f"  Cross-PBL dependencies:")
        for pbl, deps_list in sorted(deps.items()):
            print(f"    {pbl:20s}  -> {', '.join(deps_list)}")
    else:
        print(f"  No explicit cross-PBL dependencies detected.")


# ---------------------------------------------------------------------------
# Report renderers
# ---------------------------------------------------------------------------

def _count_summary(data: dict) -> str:
    proj = data["project"]
    q = data["quality"]
    dw = data["datawindows"]
    return (
        f"{proj.get('total_objects', 0)} objects | "
        f"{q.get('total_issues', 0)} quality issues | "
        f"{dw.get('total', 0)} DataWindows | "
        f"{len(dw.get('tables_usage', {}))} tables"
    )


def _render_markdown(data: dict, top: int) -> str:
    proj = data["project"]
    quality = data["quality"]
    dw = data["datawindows"]
    deps = data["dependencies"]
    ts = data.get("generated_at", "")[:16].replace("T", " ")

    lines = [
        f"# PowerBuilder 项目审查报告",
        f"",
        f"> 生成时间: {ts}  ",
        f"> 项目路径: `{proj['root']}`",
        f"",
        f"---",
        f"",
        f"## 一、项目结构",
        f"",
    ]

    # Binary files
    for key, label in [("pbl_files", "PBL"), ("exe_files", "EXE"),
                        ("pbd_files", "PBD"), ("dll_files", "DLL")]:
        files = proj.get(key, [])
        if files:
            lines.append(f"- **{label}**: {', '.join(f'`{f}`' for f in files)}")

    if proj.get("src_dir"):
        lines.append(f"- **源码目录**: `{proj['src_dir']}`")

    lines.append("")

    # Object counts
    obj_counts = proj.get("object_counts", {})
    if obj_counts:
        lines.extend([
            "### 对象统计",
            "",
            "| 类型 | 数量 |",
            "|------|------|",
        ])
        for t, c in sorted(obj_counts.items()):
            lines.append(f"| {t} | {c} |")
        lines.append(f"| **合计** | **{proj.get('total_objects', 0)}** |")
        lines.append(f"")
        lines.append(f"总行数: **{proj.get('total_lines', 0):,}**")
        lines.append("")

    # Per-PBL breakdown
    pbl_counts = proj.get("pbl_object_counts", {})
    if pbl_counts:
        lines.extend([
            "### 各 PBL 对象分布",
            "",
            "| PBL | " + " | ".join(sorted({t for v in pbl_counts.values() for t in v})) + " | 合计 |",
            "|-----|" + "---|" * (len({t for v in pbl_counts.values() for t in v}) + 1),
        ])
        all_types = sorted({t for v in pbl_counts.values() for t in v})
        for pbl, tcounts in sorted(pbl_counts.items()):
            total = sum(tcounts.values())
            row = f"| `{pbl}` | " + " | ".join(str(tcounts.get(t, 0)) for t in all_types) + f" | {total} |"
            lines.append(row)
        lines.append("")

    # Quality section
    lines.extend([
        "---",
        "",
        "## 二、代码质量",
        "",
    ])
    if quality.get("error"):
        lines.append(f"> ⚠️ 质量分析失败: {quality['error']}")
    elif quality.get("total_issues", 0) == 0:
        lines.append("> ✅ 未发现代码质量问题。")
    else:
        by_sev = quality.get("by_severity", {})
        lines.extend([
            f"- 错误 (error): **{by_sev.get('error', 0)}**",
            f"- 警告 (warning): **{by_sev.get('warning', 0)}**",
            f"- 信息 (info): **{by_sev.get('info', 0)}**",
            "",
            "### 问题分布（按规则）",
            "",
            "| 规则 | 数量 |",
            "|------|------|",
        ])
        for rule, cnt in list(quality.get("by_rule", {}).items())[:top]:
            lines.append(f"| `{rule}` | {cnt} |")
        lines.append("")

        # Top issues list
        issues = quality.get("issues", [])[:top]
        if issues:
            lines.extend([
                f"### Top {min(top, len(issues))} 问题",
                "",
                "| 级别 | 文件 | 位置 | 描述 |",
                "|------|------|------|------|",
            ])
            for iss in issues:
                sev = iss.get("severity", "info")
                icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
                fname = iss.get("file", "")
                routine = iss.get("routine", "")
                msg = iss.get("message", "").replace("|", "\\|")
                lines.append(f"| {icon} {sev} | `{fname}` | `{routine}` | {msg} |")
            lines.append("")

    # DataWindow section
    lines.extend([
        "---",
        "",
        "## 三、DataWindow 清单",
        "",
    ])
    dw_total = dw.get("total", 0)
    tables = dw.get("tables_usage", {})
    if dw_total == 0:
        lines.append("> 未找到 DataWindow 对象（.srd 文件）。")
    else:
        lines.extend([
            f"共 **{dw_total}** 个 DataWindow 对象，引用 **{len(tables)}** 个数据库表。",
            "",
            "### 数据库表使用频率",
            "",
            "| 表名 | 使用 DW 数 | DataWindow 列表 |",
            "|------|-----------|----------------|",
        ])
        for tbl, dw_list in sorted(tables.items(), key=lambda x: -len(x[1])):
            dw_str = ", ".join(f"`{d}`" for d in dw_list[:5])
            if len(dw_list) > 5:
                dw_str += f" ... (+{len(dw_list)-5})"
            lines.append(f"| `{tbl}` | {len(dw_list)} | {dw_str} |")
        lines.append("")

        # DW detail
        dws_detail = dw.get("datawindows", {})
        lines.extend([
            "### DataWindow 详情",
            "",
            "| 名称 | 样式 | 表 | 列数 | 参数 |",
            "|------|------|----|------|------|",
        ])
        for dw_name, info in sorted(dws_detail.items()):
            if info.get("error"):
                lines.append(f"| `{dw_name}` | — | ⚠️ {info['error']} | — | — |")
                continue
            style = info.get("style", "")
            tbls = ", ".join(f"`{t}`" for t in info.get("tables", []))
            cols = len(info.get("columns", []))
            args = len(info.get("retrieve_args", []))
            lines.append(f"| `{dw_name}` | {style} | {tbls} | {cols} | {args} |")
        lines.append("")

        # DW references (which windows use which DW)
        dw_refs = dw.get("dw_references", {})
        if dw_refs:
            lines.extend([
                "### DataWindow 引用关系（窗口/UO → DW）",
                "",
                "| DataWindow | 被引用 by |",
                "|------------|-----------|",
            ])
            for dw_name, refs in sorted(dw_refs.items()):
                refs_str = ", ".join(f"`{r}`" for r in refs[:6])
                lines.append(f"| `{dw_name}` | {refs_str} |")
            lines.append("")

    # Dependencies section
    lines.extend([
        "---",
        "",
        "## 四、PBL 依赖关系",
        "",
    ])
    pbl_deps = deps.get("pbl_dependencies", {})
    if not pbl_deps:
        lines.append("> 未检测到跨 PBL 依赖关系。")
    else:
        lines.extend([
            "| PBL | 依赖 |",
            "|-----|------|",
        ])
        for pbl, dep_list in sorted(pbl_deps.items()):
            lines.append(f"| `{pbl}` | {', '.join(f'`{d}`' for d in dep_list)} |")
    lines.append("")

    # Suggestions
    lines.extend([
        "---",
        "",
        "## 五、改进建议",
        "",
    ])
    suggestions = _generate_suggestions(proj, quality, dw, deps)
    for i, sug in enumerate(suggestions, 1):
        lines.append(f"{i}. {sug}")
    lines.append("")

    lines.extend([
        "---",
        f"*Generated by [pb-devkit](https://github.com/pb-devkit) — pb review*",
    ])

    return "\n".join(lines)


def _generate_suggestions(proj: dict, quality: dict, dw: dict, deps: dict) -> list:
    """Generate actionable improvement suggestions."""
    suggestions = []

    total_objs = proj.get("total_objects", 0)
    total_lines = proj.get("total_lines", 0)

    # Structure suggestions
    pbl_counts = proj.get("pbl_object_counts", {})
    for pbl, counts in pbl_counts.items():
        total = sum(counts.values())
        if total > 100:
            suggestions.append(
                f"PBL `{pbl}` 包含 {total} 个对象，建议按功能模块拆分为多个 PBL 以降低耦合。"
            )

    # Quality suggestions
    by_rule = quality.get("by_rule", {})
    if by_rule.get("GOTO_USAGE", 0) > 5:
        suggestions.append(
            f"发现 {by_rule['GOTO_USAGE']} 处 GOTO 语句，建议重构为结构化控制流（循环+条件）。"
        )
    if by_rule.get("GLOBAL_VAR", 0) > 10:
        suggestions.append(
            f"发现 {by_rule['GLOBAL_VAR']} 个全局变量，建议封装到应用级单例对象中集中管理。"
        )
    if by_rule.get("EMPTY_CATCH", 0) > 0:
        suggestions.append(
            f"发现 {by_rule['EMPTY_CATCH']} 处空 catch 块，这会吞掉异常，建议添加日志记录。"
        )
    if by_rule.get("LONG_SCRIPT", 0) > 0:
        suggestions.append(
            f"发现 {by_rule['LONG_SCRIPT']} 个超长函数/事件脚本，建议提取子函数降低圈复杂度。"
        )
    if by_rule.get("HARDCODED_SQL", 0) > 0:
        suggestions.append(
            f"发现 {by_rule['HARDCODED_SQL']} 处硬编码 SQL，建议统一放入 DataWindow 对象或存储过程。"
        )

    # DW suggestions
    dw_total = dw.get("total", 0)
    tables = dw.get("tables_usage", {})
    no_table_dws = [
        name for name, info in dw.get("datawindows", {}).items()
        if isinstance(info, dict) and not info.get("tables") and not info.get("error")
    ]
    if no_table_dws:
        suggestions.append(
            f"{len(no_table_dws)} 个 DataWindow 没有检测到表名（可能使用存储过程或动态 SQL），"
            f"建议添加注释说明数据来源。"
        )

    # Compilation
    if not proj.get("pbl_files") and (proj.get("exe_files") or proj.get("pbd_files")):
        suggestions.append(
            "项目只有编译产物（EXE/PBD），没有 PBL 源码。建议使用 `pb autoexport` 梳理导出后，"
            "再通过 `pb import` + `pb build` 进行二次开发和编译。"
        )

    if not suggestions:
        suggestions.append("✅ 项目结构良好，暂无明显改进建议。")

    return suggestions


def _render_html(data: dict, top: int) -> str:
    """Render review as standalone HTML with embedded CSS."""
    md = _render_markdown(data, top)

    # Simple markdown-to-HTML conversion
    lines_out = []
    in_table = False
    in_code = False

    for line in md.splitlines():
        if line.startswith("```"):
            if not in_code:
                lines_out.append("<pre><code>")
                in_code = True
            else:
                lines_out.append("</code></pre>")
                in_code = False
            continue

        if in_code:
            lines_out.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Table rows
        if line.startswith("|"):
            if not in_table:
                lines_out.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.strip("|").split("|")]
            tag = "th" if "---" in line else "td"
            if "---" in line:
                continue
            is_header = all(c.startswith("**") or c == "" for c in cells[:2])
            tag = "th" if is_header else "td"
            row = "".join(f"<{tag}>{_md_inline(c)}</{tag}>" for c in cells)
            lines_out.append(f"<tr>{row}</tr>")
            continue
        else:
            if in_table:
                lines_out.append("</table>")
                in_table = False

        # Headings
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            lines_out.append(f"<h{level}>{_md_inline(m.group(2))}</h{level}>")
            continue

        # List items
        if line.startswith("- ") or line.startswith("* "):
            lines_out.append(f"<li>{_md_inline(line[2:])}</li>")
            continue

        if line.startswith("> "):
            lines_out.append(f"<blockquote>{_md_inline(line[2:])}</blockquote>")
            continue

        if line.startswith("---") or line.startswith("==="):
            lines_out.append("<hr>")
            continue

        if line.strip() == "":
            lines_out.append("<br>")
            continue

        lines_out.append(f"<p>{_md_inline(line)}</p>")

    if in_table:
        lines_out.append("</table>")

    body = "\n".join(lines_out)
    proj = data["project"]
    title = f"PB Review — {Path(proj['root']).name}"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 20px 40px;
         background: #f8f9fa; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #2980b9; margin-top: 40px; border-left: 4px solid #3498db; padding-left: 10px; }}
  h3 {{ color: #555; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; background: white;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 6px; overflow: hidden; }}
  th {{ background: #2980b9; color: white; padding: 10px 14px; text-align: left; }}
  td {{ padding: 8px 14px; border-bottom: 1px solid #ecf0f1; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f1f9ff; }}
  code {{ background: #ecf0f1; border-radius: 3px; padding: 2px 6px; font-family: monospace; font-size: 0.92em; }}
  pre {{ background: #2c3e50; color: #ecf0f1; padding: 16px; border-radius: 6px; overflow-x: auto; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  blockquote {{ border-left: 4px solid #bdc3c7; padding: 8px 16px; color: #666;
               background: #fafafa; margin: 8px 0; border-radius: 0 4px 4px 0; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 30px 0; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #2c3e50; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, code, links) to HTML."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Italic
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text
