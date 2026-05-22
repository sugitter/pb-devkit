"""pb report command - Generate Markdown analysis report."""
import argparse
from datetime import datetime
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("report", help="Generate Markdown analysis report")
    p.add_argument("target", help="Source directory")
    p.add_argument("--output", "-o", help="Output file path (default: ANALYSIS_REPORT.md)")
    return p


def run(args):
    """Generate Markdown analysis report for a PB project."""
    from pb_devkit.sr_parser import PBSourceAnalyzer, SRFileParser

    source_dir = Path(args.target)
    output_file = Path(args.output) if args.output else source_dir / "ANALYSIS_REPORT.md"

    if not source_dir.is_dir():
        print(f"Error: not a directory: {source_dir}", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    print(f"\nGenerating report: {source_dir} -> {output_file}")

    # Run analysis
    analyzer = PBSourceAnalyzer()
    report = analyzer.analyze_project(source_dir)
    summary = report["summary"]

    # Collect file-level stats
    files = sorted(source_dir.rglob("*.sr*"))
    file_stats = []
    for f in files:
        obj = SRFileParser().parse_file(f)
        file_stats.append({
            "file": f.name,
            "type": obj.object_type.value,
            "routines": len(obj.routines),
            "variables": len(obj.variables),
            "size_bytes": f.stat().st_size,
        })

    # Build Markdown
    lines = []
    lines.append("# PB Project Analysis Report\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Source:** `{source_dir}`\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Source files | {summary['files']} |")
    lines.append(f"| Objects | {summary['objects']} |")
    lines.append(f"| Total issues | {summary['total_issues']} |")
    lines.append(f"| Errors | {summary['by_severity'].get('error', 0)} |")
    lines.append(f"| Warnings | {summary['by_severity'].get('warning', 0)} |")
    lines.append(f"| Info | {summary['by_severity'].get('info', 0)} |\n")

    # Object inventory
    type_counts = {}
    for fs in file_stats:
        t = fs["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    lines.append("## Object Inventory\n")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {c} |\n")

    # Top issues
    if report["issues"]:
        lines.append("## Quality Issues\n")
        for obj_name, issues in sorted(report["issues"].items()):
            for iss in issues:
                sev = iss.get("severity", "info")
                icon = {"error": "E", "warning": "W", "info": "I"}.get(sev, "?")
                routine = iss.get("routine", "")
                loc = f"`{routine}` " if routine else ""
                lines.append(f"- [{icon}] **{obj_name}** {loc}- {iss['message']}")
        lines.append("")

    # Complexity hotspots
    complexity = report.get("complexity", {})
    if complexity:
        lines.append("## Complexity Hotspots\n")
        lines.append("| Object | Routine | CC | Rating | Lines |")
        lines.append("|--------|---------|----|--------|-------|")
        hotspots = []
        for obj_name, routines in complexity.items():
            for r in routines:
                if r["complexity"] > 10:
                    hotspots.append((obj_name, r))
        hotspots.sort(key=lambda x: -x[1]["complexity"])
        for obj_name, r in hotspots[:30]:
            lines.append(
                f"| {obj_name} | {r['name']} | {r['complexity']} "
                f"| {r['rating']} | {r['code_lines']} |")
        if not hotspots:
            lines.append("| - | All routines within acceptable limits | - | A | - |")
        lines.append("")

    # Dependencies
    deps = report.get("dependencies", {})
    if deps:
        dep_map = deps.get("dependencies", {})
        inheritance = deps.get("inheritance", {})

        if inheritance:
            lines.append("## Inheritance Tree\n")
            lines.append("```")
            for child, parent in sorted(inheritance.items()):
                lines.append(f"{child} extends {parent}")
            lines.append("```\n")

        if dep_map:
            lines.append("## Cross-Object Dependencies\n")
            lines.append("| Object | Depends On |")
            lines.append("|--------|-----------|")
            for name, dep_list in sorted(dep_map.items()):
                if dep_list:
                    lines.append(f"| {name} | {', '.join(dep_list[:5])} |")
            lines.append("")

    # File details
    lines.append("## File Details\n")
    lines.append("| File | Type | Routines | Variables | Size |")
    lines.append("|------|------|----------|-----------|------|")
    total_size = 0
    for fs in file_stats:
        sz = fs["size_bytes"]
        total_size += sz
        size_str = f"{sz:,} B" if sz < 1024 else f"{sz/1024:.1f} KB"
        lines.append(
            f"| {fs['file']} | {fs['type']} | {fs['routines']} "
            f"| {fs['variables']} | {size_str} |")
    lines.append(f"\n**Total source size:** {total_size/1024:.1f} KB\n")

    # Write report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report written: {output_file}")
    print(f"  Summary: {summary['files']} files, {summary['total_issues']} issues")
