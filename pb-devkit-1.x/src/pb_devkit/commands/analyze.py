"""pb analyze command - Analyze code quality."""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("analyze", help="Analyze code quality")
    p.add_argument("target", nargs="+", help="Source directory or .sr* files")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Analyze code quality of exported sources."""
    from pb_devkit.sr_parser import PBSourceAnalyzer

    analyzer = PBSourceAnalyzer()
    targets = args.target

    all_issues = {}
    for target in targets:
        p = Path(target)
        if p.is_dir():
            issues = analyzer.analyze_directory(p)
            all_issues[target] = issues
        elif p.is_file():
            all_issues[str(p)] = {p.name: analyzer.analyze_file(p)}

    # Print report
    total_issues = 0
    for src, file_issues in all_issues.items():
        for fname, issues in file_issues.items():
            if isinstance(issues, list):
                total_issues += len(issues)
                for iss in issues:
                    sev = iss.get("severity", "info")
                    icon = {"error": "E", "warning": "W", "info": "I"}.get(sev, "?")
                    loc = f"{iss.get('routine', '')}" if iss.get('routine') else ""
                    print(f"  [{icon}] {fname}: {loc} - {iss['message']}")

    print(f"\nAnalysis complete: {total_issues} issues found")
    if args.json:
        print(json.dumps(all_issues, indent=2, ensure_ascii=False))
