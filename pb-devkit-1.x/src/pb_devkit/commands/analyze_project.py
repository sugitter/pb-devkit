"""pb analyze-project command - Full project analysis with PBL tree support.

Supports analyzing source code organized in PBL directory structure:
  src/
    app.pbl/
    framework.pbl/
    common.pbl/
    ...
"""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("analyze-project",
                       help="Full project analysis (deps + complexity)")
    p.add_argument("target", help="Source directory (flat or PBL tree)")
    p.add_argument("--json", action="store_true",
                   help="Output results as JSON")
    p.add_argument("--pbl-tree", action="store_true",
                   help="Analyze as PBL tree structure (auto-detected if not set)")
    p.add_argument("--html", metavar="FILE",
                   help="Generate HTML analysis report to file")
    return p


def run(args):
    """Full project analysis with dependency graph and complexity metrics."""
    from pb_devkit.sr_parser import PBSourceAnalyzer

    source_dir = Path(args.target)
    if not source_dir.is_dir():
        print(f"Error: not a directory: {source_dir}", file=sys.stderr)
        sys.exit(1)

    analyzer = PBSourceAnalyzer()

    # Auto-detect PBL tree structure
    is_pbl_tree = args.pbl_tree
    if not is_pbl_tree:
        is_pbl_tree = _detect_pbl_tree(source_dir)

    if is_pbl_tree:
        report = _analyze_pbl_tree(source_dir, analyzer)
    else:
        report = analyzer.analyze_project(source_dir)

    # Print summary
    summary = report["summary"]
    print(f"\n{'='*60}")
    title = f"  Project Analysis: {source_dir.name}"
    if is_pbl_tree:
        title += " (PBL Tree)"
    print(title)
    print(f"{'='*60}")
    print(f"  Files: {summary['files']}")
    print(f"  Objects: {summary['objects']}")
    print(f"  Total Issues: {summary['total_issues']}")
    print(f"  By Severity: {json.dumps(summary['by_severity'])}")

    # PBL breakdown
    pbl_breakdown = report.get("pbl_breakdown", {})
    if pbl_breakdown:
        print(f"\n  {'PBL Breakdown':^40}")
        print(f"  {'-'*40}")
        for pbl, info in sorted(pbl_breakdown.items()):
            issues = info.get("issues", 0)
            objs = info.get("objects", 0)
            loc = info.get("loc", 0)
            print(f"    {pbl}: {objs} objects, {loc} LOC, {issues} issues")

    # Print complexity summary
    complexity = report.get("complexity", {})
    if complexity:
        print(f"\n  {'Complexity':^40}")
        print(f"  {'-'*40}")
        high_cc = []
        for obj_name, routines in complexity.items():
            for r in routines:
                if r["complexity"] > 10:
                    high_cc.append(f"    {obj_name}.{r['name']}: "
                                   f"CC={r['complexity']} ({r['rating']}) "
                                   f"[{r['code_lines']} lines]")
        if high_cc:
            for h in high_cc[:20]:
                print(h)
            if len(high_cc) > 20:
                print(f"    ... and {len(high_cc) - 20} more")
        else:
            print("    All routines within acceptable complexity (CC <= 10)")

    # Print dependency graph
    deps = report.get("dependencies", {})
    if deps:
        print(f"\n  {'Dependencies':^40}")
        print(f"  {'-'*40}")
        for name, dep_list in deps.get("dependencies", {}).items():
            if dep_list:
                print(f"    {name} -> {', '.join(dep_list[:5])}")
                if len(dep_list) > 5:
                    print(f"      ... +{len(dep_list) - 5} more")
        inheritance = deps.get("inheritance", {})
        if inheritance:
            print(f"\n  {'Inheritance':^40}")
            print(f"  {'-'*40}")
            for child, parent in inheritance.items():
                print(f"    {child} extends {parent}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    # HTML report
    if args.html:
        _generate_html_report(report, args.html, source_dir.name, is_pbl_tree)
        print(f"\n[*] HTML report: {args.html}")


def _detect_pbl_tree(source_dir: Path) -> bool:
    """Auto-detect if directory is a PBL tree structure.

    A PBL tree has subdirectories ending in .pbl containing source files.
    """
    has_pbl_dirs = False
    for child in source_dir.iterdir():
        if child.is_dir() and child.name.endswith(".pbl"):
            has_pbl_dirs = True
            break
    return has_pbl_dirs


def _analyze_pbl_tree(source_dir: Path, analyzer) -> dict:
    """Analyze a PBL tree directory structure.

    Scans each *.pbl subdirectory, runs analysis per-PBL, and assembles
    a combined report with PBL breakdown.
    """
    pbl_dirs = sorted(
        [d for d in source_dir.iterdir()
         if d.is_dir() and d.name.endswith(".pbl")]
    )

    if not pbl_dirs:
        # No .pbl dirs found, fall back to flat analysis
        return analyzer.analyze_project(source_dir)

    # Collect all analysis results
    all_results = {}
    pbl_breakdown = {}
    total_files = 0
    total_objects = 0
    total_issues = 0
    severity_counts = {"error": 0, "warning": 0, "info": 0}
    all_complexity = {}
    all_deps = {"dependencies": {}, "inheritance": {}}

    for pbl_dir in pbl_dirs:
        pbl_name = pbl_dir.stem  # e.g. "logistic" from "logistic.pbl"
        try:
            pbl_report = analyzer.analyze_project(pbl_dir)
        except Exception as e:
            print(f"  [warn] Failed to analyze {pbl_dir.name}: {e}",
                  file=sys.stderr)
            continue

        pbl_summary = pbl_report.get("summary", {})
        files = pbl_summary.get("files", 0)
        objects = pbl_summary.get("objects", 0)
        issues = pbl_summary.get("total_issues", 0)

        # Count LOC
        loc = 0
        for f in pbl_dir.rglob("*"):
            if f.is_file() and f.suffix in (".ps", ".srw", ".srd", ".srm",
                                             ".srf", ".srs", ".sru"):
                try:
                    loc += len(f.read_text(encoding="utf-8").splitlines())
                except Exception:
                    loc += 0

        total_files += files
        total_objects += objects
        total_issues += issues

        by_sev = pbl_summary.get("by_severity", {})
        for sev in severity_counts:
            severity_counts[sev] += by_sev.get(sev, 0)

        pbl_breakdown[pbl_name] = {
            "objects": objects,
            "issues": issues,
            "loc": loc,
        }

        # Merge complexity
        for obj_name, routines in pbl_report.get("complexity", {}).items():
            all_complexity[f"{pbl_name}/{obj_name}"] = routines

        # Merge dependencies
        pbl_deps = pbl_report.get("dependencies", {})
        for name, dep_list in pbl_deps.get("dependencies", {}).items():
            all_deps["dependencies"][f"{pbl_name}/{name}"] = dep_list
        for child, parent in pbl_deps.get("inheritance", {}).items():
            all_deps["inheritance"][f"{pbl_name}/{child}"] = parent

        all_results[pbl_name] = pbl_report

    return {
        "summary": {
            "files": total_files,
            "objects": total_objects,
            "total_issues": total_issues,
            "by_severity": severity_counts,
        },
        "pbl_breakdown": pbl_breakdown,
        "complexity": all_complexity,
        "dependencies": all_deps,
        "pbl_reports": all_results,
    }


def _generate_html_report(report: dict, output_path: str,
                          project_name: str, is_pbl_tree: bool):
    """Generate an HTML analysis report."""
    summary = report["summary"]
    pbl_breakdown = report.get("pbl_breakdown", {})
    complexity = report.get("complexity", {})
    deps = report.get("dependencies", {})

    # Severity icons
    sev_icons = {"error": "🔴", "warning": "🟡", "info": "🔵"}

    lines = [
        "<!DOCTYPE html>",
        "<html lang='zh-CN'>",
        "<head>",
        "<meta charset='UTF-8'>",
        f"<title>{project_name} - Project Analysis</title>",
        "<style>",
        "body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 960px; "
        "margin: 0 auto; padding: 20px; background: #f8f9fa; color: #212529; }",
        "h1 { border-bottom: 3px solid #0d6efd; padding-bottom: 10px; }",
        "h2 { color: #495057; margin-top: 30px; border-bottom: 1px solid #dee2e6; "
        "padding-bottom: 5px; }",
        ".card { background: white; border-radius: 8px; padding: 20px; "
        "margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        ".stat { display: inline-block; text-align: center; padding: 15px 25px; "
        "margin: 5px; background: #e9ecef; border-radius: 6px; min-width: 120px; }",
        ".stat .num { font-size: 28px; font-weight: bold; color: #0d6efd; }",
        ".stat .label { font-size: 12px; color: #6c757d; text-transform: uppercase; }",
        "table { width: 100%; border-collapse: collapse; margin: 10px 0; }",
        "th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #dee2e6; }",
        "th { background: #0d6efd; color: white; font-weight: 600; }",
        "tr:hover { background: #f8f9fa; }",
        ".severity-error { color: #dc3545; }",
        ".severity-warning { color: #fd7e14; }",
        ".severity-info { color: #0d6efd; }",
        ".cc-high { color: #dc3545; font-weight: bold; }",
        ".cc-medium { color: #fd7e14; }",
        ".cc-low { color: #198754; }",
        ".footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #dee2e6; "
        "color: #6c757d; font-size: 12px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{project_name}</h1>",
        f"<p>Project Analysis Report "
        f"{'(PBL Tree Structure)' if is_pbl_tree else ''}</p>",
        "",
        "<div class='card'>",
        "<div class='stat'><div class='num'>{}</div><div class='label'>Files</div></div>".format(summary["files"]),
        "<div class='stat'><div class='num'>{}</div><div class='label'>Objects</div></div>".format(summary["objects"]),
        "<div class='stat'><div class='num'>{}</div><div class='label'>Issues</div></div>".format(summary["total_issues"]),
        "<div class='stat'><div class='num' style='color:#dc3545'>{}</div>"
        "<div class='label'>Errors</div></div>".format(summary["by_severity"].get("error", 0)),
        "<div class='stat'><div class='num' style='color:#fd7e14'>{}</div>"
        "<div class='label'>Warnings</div></div>".format(summary["by_severity"].get("warning", 0)),
        "</div>",
    ]

    # PBL Breakdown table
    if pbl_breakdown:
        lines.extend([
            "<h2>PBL Breakdown</h2>",
            "<div class='card'>",
            "<table>",
            "<tr><th>PBL</th><th>Objects</th><th>LOC</th><th>Issues</th></tr>",
        ])
        for pbl, info in sorted(pbl_breakdown.items()):
            lines.append(
                f"<tr><td><b>{pbl}</b></td>"
                f"<td>{info['objects']}</td>"
                f"<td>{info['loc']:,}</td>"
                f"<td>{info['issues']}</td></tr>"
            )
        lines.extend(["</table>", "</div>"])

    # High complexity routines
    high_cc = []
    for obj_name, routines in complexity.items():
        for r in routines:
            if r["complexity"] > 10:
                cc = r["complexity"]
                cls = "cc-high" if cc > 20 else "cc-medium"
                high_cc.append(
                    f"<tr><td>{obj_name}</td><td>{r['name']}</td>"
                    f"<td class='{cls}'>{cc}</td>"
                    f"<td>{r['rating']}</td>"
                    f"<td>{r['code_lines']}</td></tr>"
                )
    if high_cc:
        lines.extend([
            "<h2>High Complexity Routines (CC > 10)</h2>",
            "<div class='card'>",
            "<table>",
            "<tr><th>Object</th><th>Routine</th><th>CC</th>"
            "<th>Rating</th><th>Lines</th></tr>",
        ])
        lines.extend(high_cc[:30])
        if len(high_cc) > 30:
            lines.append(f"<tr><td colspan='5'>... and {len(high_cc) - 30} more</td></tr>")
        lines.extend(["</table>", "</div>"])

    # Dependencies
    dep_items = list(deps.get("dependencies", {}).items())
    if dep_items:
        lines.extend([
            "<h2>Dependencies</h2>",
            "<div class='card'>",
            "<table>",
            "<tr><th>Object</th><th>Depends On</th></tr>",
        ])
        for name, dep_list in dep_items[:50]:
            deps_str = ", ".join(dep_list[:8])
            if len(dep_list) > 8:
                deps_str += f" ... +{len(dep_list) - 8} more"
            lines.append(f"<tr><td>{name}</td><td>{deps_str}</td></tr>")
        if len(dep_items) > 50:
            lines.append(f"<tr><td colspan='2'>... and {len(dep_items) - 50} more</td></tr>")
        lines.extend(["</table>", "</div>"])

    # Inheritance
    inheritance = deps.get("inheritance", {})
    if inheritance:
        lines.extend([
            "<h2>Inheritance</h2>",
            "<div class='card'>",
            "<table>",
            "<tr><th>Child</th><th>Parent</th></tr>",
        ])
        for child, parent in sorted(inheritance.items()):
            lines.append(f"<tr><td>{child}</td><td>{parent}</td></tr>")
        lines.extend(["</table>", "</div>"])

    lines.extend([
        "",
        "<div class='footer'>",
        f"Generated by pb-devkit | {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "</div>",
        "</body>",
        "</html>",
    ])

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
