"""pb analyze-project command - Full project analysis."""
import argparse
import json
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("analyze-project",
                       help="Full project analysis (deps + complexity)")
    p.add_argument("target", help="Source directory")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Full project analysis with dependency graph and complexity metrics."""
    from pb_devkit.sr_parser import PBSourceAnalyzer

    source_dir = Path(args.target)
    analyzer = PBSourceAnalyzer()
    report = analyzer.analyze_project(source_dir)

    # Print summary
    summary = report["summary"]
    print(f"\n{'='*60}")
    print(f"  Project Analysis: {source_dir}")
    print(f"{'='*60}")
    print(f"  Files: {summary['files']}")
    print(f"  Objects: {summary['objects']}")
    print(f"  Total Issues: {summary['total_issues']}")
    print(f"  By Severity: {json.dumps(summary['by_severity'])}")

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
        else:
            print("    All routines within acceptable complexity")

    # Print dependency graph
    deps = report.get("dependencies", {})
    if deps:
        print(f"\n  {'Dependencies':^40}")
        print(f"  {'-'*40}")
        for name, dep_list in deps.get("dependencies", {}).items():
            if dep_list:
                print(f"    {name} -> {', '.join(dep_list[:5])}")
        inheritance = deps.get("inheritance", {})
        if inheritance:
            print(f"\n  {'Inheritance':^40}")
            print(f"  {'-'*40}")
            for child, parent in inheritance.items():
                print(f"    {child} extends {parent}")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
