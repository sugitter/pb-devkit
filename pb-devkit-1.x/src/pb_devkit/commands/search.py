"""pb search command - Full-text search in PB source code."""
import argparse
import json
import re
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("search",
                       help="Search source code for text/SQL/function patterns")
    p.add_argument("pattern", help="Search pattern (text/regex)")
    p.add_argument("target", help="Source directory or .sr* file")
    p.add_argument("--mode", choices=["text", "sql", "function"],
                   default="text",
                   help="Search mode: text (default), sql (table names), "
                        "function (function definitions)")
    p.add_argument("--type-filter", "-t",
                   help="Filter by object type: DW/WIN/MENU/FUNC/UO/STRUCT/APP")
    p.add_argument("--case-sensitive", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Search source code for text patterns, SQL references, or function definitions."""
    pattern = args.pattern
    source_dir = Path(args.target)
    case_insensitive = not args.case_sensitive
    file_filter = args.type_filter.upper() if args.type_filter else None

    # Build file glob from type filter
    type_to_ext = {
        "DW": "*.srd", "DATAWINDOW": "*.srd",
        "WIN": "*.srw", "WINDOW": "*.srw",
        "MENU": "*.srm",
        "FUNC": "*.srf", "FUNCTION": "*.srf",
        "UO": "*.sru", "USEROBJECT": "*.sru",
        "STRUCT": "*.srs", "STRUCTURE": "*.srs",
        "APP": "*.sra", "APPLICATION": "*.sra",
    }
    glob_pattern = type_to_ext.get(file_filter, "*.sr*") if file_filter else "*.sr*"

    # Search mode
    mode = args.mode

    # Compile search regex
    if mode == "sql":
        search_re = re.compile(re.escape(pattern), re.I if case_insensitive else 0)
    elif mode == "function":
        search_re = re.compile(
            rf"(?:subroutine|function)\s+(?:\w+\s+)?{re.escape(pattern)}\s*\(",
            re.I if case_insensitive else 0)
    else:  # text
        search_re = re.compile(re.escape(pattern), re.I if case_insensitive else 0)

    results = []
    files = sorted(source_dir.rglob(glob_pattern)) if source_dir.is_dir() else [source_dir]
    files = [f for f in files if f.is_file()]

    for f in files:
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(source_dir) if source_dir.is_dir() else f.name

        if mode == "sql":
            # Search for table names in SQL context
            for i, line in enumerate(text.splitlines(), 1):
                if search_re.search(line) and re.search(
                        r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\b", line, re.I):
                    results.append({
                        "file": str(rel), "line": i, "text": line.strip()})
        else:
            for i, line in enumerate(text.splitlines(), 1):
                if search_re.search(line):
                    results.append({
                        "file": str(rel), "line": i, "text": line.strip()})

    # Print results
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\nSearch: '{pattern}' (mode={mode}) in {source_dir}")
        print(f"Found {len(results)} matches\n")
        if not results:
            print("  No matches found.")
        current_file = ""
        for r in results:
            if r["file"] != current_file:
                print(f"\n  {r['file']}:")
                current_file = r["file"]
            print(f"    L{r['line']:>4}: {r['text'][:120]}")
