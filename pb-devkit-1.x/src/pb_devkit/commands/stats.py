"""pb stats command - Project statistics dashboard."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("stats", help="Project statistics dashboard")
    p.add_argument("target", help="Source directory")
    p.add_argument("--sort", choices=["size", "complexity", "issues", "name"],
                   default="size",
                   help="Sort files by: size (default), complexity, issues, name")
    p.add_argument("--top", type=int, default=20,
                   help="Show top N items (default: 20)")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Generate project statistics dashboard."""
    from pb_devkit.sr_parser import PBSourceAnalyzer, SRFileParser

    source_dir = Path(args.target)
    if not source_dir.is_dir():
        print(f"Error: not a directory: {source_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(source_dir.rglob("*.sr*"))
    if not files:
        print("No .sr* files found in directory.", file=sys.stderr)
        sys.exit(1)

    analyzer = PBSourceAnalyzer()

    # Collect per-file stats
    file_stats = []
    total_lines = 0
    total_size = 0
    type_counter = Counter()
    complexity_routines = []

    for f in files:
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue

        obj = SRFileParser().parse_file(f)
        lines = text.count("\n") + 1
        total_lines += lines
        size = f.stat().st_size
        total_size += size
        type_counter[obj.object_type.value] += 1

        # Complexity per routine
        for r in obj.routines:
            cc = _compute_complexity(r.script)
            complexity_routines.append({
                "object": f.stem,
                "routine": r.name,
                "complexity": cc,
                "lines": len(r.script.splitlines()),
            })

        # Quality issues
        issues = analyzer.analyze_file(f)
        issue_list = issues.get(f.name, []) if isinstance(issues, dict) else issues
        issue_count = len(issue_list) if isinstance(issue_list, list) else 0

        file_stats.append({
            "file": f.name,
            "type": obj.object_type.value,
            "lines": lines,
            "size_bytes": size,
            "routines": len(obj.routines),
            "variables": len(obj.variables),
            "issues": issue_count,
        })

    # Sort
    sort_key = args.sort
    if sort_key == "size":
        file_stats.sort(key=lambda x: -x["size_bytes"])
    elif sort_key == "complexity":
        complexity_routines.sort(key=lambda x: -x["complexity"])
    elif sort_key == "issues":
        file_stats.sort(key=lambda x: -x["issues"])
    elif sort_key == "name":
        file_stats.sort(key=lambda x: x["file"])

    top = args.top

    # Print dashboard
    print(f"\n{'='*60}")
    print(f"  PB Project Statistics: {source_dir.name}")
    print(f"{'='*60}")

    # Overview
    print(f"\n  Overview")
    print(f"  {'-'*40}")
    print(f"  Files:          {len(file_stats)}")
    print(f"  Total lines:    {total_lines:,}")
    print(f"  Total size:     {_format_size(total_size)}")
    print(f"  Routines:       {sum(s['routines'] for s in file_stats)}")
    print(f"  Variables:      {sum(s['variables'] for s in file_stats)}")
    print(f"  Total issues:   {sum(s['issues'] for s in file_stats)}")

    # Type distribution
    print(f"\n  Object Types")
    print(f"  {'-'*40}")
    for t, c in type_counter.most_common():
        bar = "#" * min(c, 40)
        print(f"  {t:<15} {c:>4}  {bar}")

    # Top files
    print(f"\n  Top {top} Files (by {sort_key})")
    print(f"  {'-'*60}")
    if sort_key == "size":
        print(f"  {'File':<30} {'Lines':>6} {'Size':>10} {'Type':<10}")
        for s in file_stats[:top]:
            print(f"  {s['file']:<30} {s['lines']:>6,} "
                  f"{_format_size(s['size_bytes']):>10} {s['type']:<10}")
    elif sort_key == "issues":
        print(f"  {'File':<30} {'Issues':>6} {'Routines':>8} {'Lines':>6}")
        for s in file_stats[:top]:
            if s["issues"] > 0:
                print(f"  {s['file']:<30} {s['issues']:>6} "
                      f"{s['routines']:>8} {s['lines']:>6,}")
    elif sort_key == "name":
        print(f"  {'File':<30} {'Type':<10} {'Lines':>6}")
        for s in file_stats[:top]:
            print(f"  {s['file']:<30} {s['type']:<10} {s['lines']:>6,}")

    # Complexity distribution
    print(f"\n  Complexity Distribution")
    print(f"  {'-'*40}")
    cc_buckets = {"A (1-5)": 0, "B (6-10)": 0, "C (11-20)": 0,
                  "D (21-50)": 0, "F (50+)": 0}
    for cr in complexity_routines:
        cc = cr["complexity"]
        if cc <= 5:
            cc_buckets["A (1-5)"] += 1
        elif cc <= 10:
            cc_buckets["B (6-10)"] += 1
        elif cc <= 20:
            cc_buckets["C (11-20)"] += 1
        elif cc <= 50:
            cc_buckets["D (21-50)"] += 1
        else:
            cc_buckets["F (50+)"] += 1

    for bucket, count in cc_buckets.items():
        bar = "#" * min(count, 30)
        print(f"  {bucket:<12} {count:>4}  {bar}")

    # Top complex routines
    complexity_routines.sort(key=lambda x: -x["complexity"])
    print(f"\n  Top {min(top, len(complexity_routines))} Most Complex Routines")
    print(f"  {'-'*60}")
    print(f"  {'Object.Routine':<35} {'CC':>4} {'Lines':>6}")
    for cr in complexity_routines[:top]:
        if cr["complexity"] > 1:
            rating = _cc_rating(cr["complexity"])
            print(f"  {cr['object']}.{cr['routine']:<25} {cr['complexity']:>4} "
                  f"{cr['lines']:>6}  [{rating}]")

    # Lines per file histogram
    print(f"\n  File Size Distribution (by lines)")
    print(f"  {'-'*40}")
    size_buckets = {"Tiny (<50)": 0, "Small (50-200)": 0,
                    "Medium (200-500)": 0, "Large (500-1000)": 0,
                    "Huge (1000+)": 0}
    for s in file_stats:
        l = s["lines"]
        if l < 50:
            size_buckets["Tiny (<50)"] += 1
        elif l < 200:
            size_buckets["Small (50-200)"] += 1
        elif l < 500:
            size_buckets["Medium (200-500)"] += 1
        elif l < 1000:
            size_buckets["Large (500-1000)"] += 1
        else:
            size_buckets["Huge (1000+)"] += 1
    for bucket, count in size_buckets.items():
        bar = "#" * min(count, 30)
        print(f"  {bucket:<20} {count:>4}  {bar}")

    # JSON output
    if args.json:
        result = {
            "overview": {
                "files": len(file_stats),
                "total_lines": total_lines,
                "total_size_bytes": total_size,
                "total_routines": sum(s["routines"] for s in file_stats),
                "total_variables": sum(s["variables"] for s in file_stats),
                "total_issues": sum(s["issues"] for s in file_stats),
            },
            "type_distribution": dict(type_counter),
            "complexity_distribution": cc_buckets,
            "file_size_distribution": size_buckets,
            "files": file_stats,
            "complexity_top": complexity_routines[:top],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))


def _compute_complexity(script: str) -> int:
    """Quick cyclomatic complexity estimation from PowerScript."""
    keywords = [
        "if", "else", "elseif", "end if",
        "for", "next", "do", "loop", "while",
        "choose", "case",
        "try", "catch", "finally",
        "continue", "exit", "return",
        "and", "or",
    ]
    cc = 1
    for line in script.splitlines():
        stripped = line.strip().lower()
        # Remove single-line comments
        if stripped.startswith("//"):
            continue
        # Remove inline comments
        if "//" in stripped:
            stripped = stripped[:stripped.index("//")]
        for kw in keywords:
            # Use word boundaries for short keywords
            if len(kw) <= 4:
                import re
                if re.search(rf"\b{re.escape(kw)}\b", stripped):
                    cc += 1
                    break
            elif stripped.startswith(kw):
                cc += 1
                break
    return cc


def _cc_rating(cc: int) -> str:
    """Return complexity rating letter."""
    if cc <= 5:
        return "A"
    elif cc <= 10:
        return "B"
    elif cc <= 20:
        return "C"
    elif cc <= 50:
        return "D"
    return "F"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
