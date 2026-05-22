"""pb refactor command - Auto-refactor source files."""
import argparse
import json
import time
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("refactor", help="Auto-refactor source files")
    p.add_argument("target", help="Source file or directory")
    p.add_argument("--apply", action="store_true",
                   help="Apply changes (default: dry run)")
    p.add_argument("--rules", help="Comma-separated rule IDs to run")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Auto-refactor source files."""
    from pb_devkit.refactoring import RefactoringEngine
    from pb_devkit.config import PBConfig

    source_path = Path(args.target)

    # Load config for rule filtering
    config = PBConfig.load(args.config if hasattr(args, "config") and args.config else None)
    engine = RefactoringEngine(config=config)

    # Filter rules if specified
    rule_filter = args.rules.split(",") if args.rules else None

    print(f"Refactoring: {source_path} ({'dry run' if args.dry_run else 'apply'})")
    t0 = time.time()
    result = engine.run(source_path, dry_run=not args.apply,
                        rule_filter=rule_filter)
    elapsed = time.time() - t0

    # Print results
    print(f"\n  Total fixes: {result['total_fixes']}")
    print(f"  By severity: {json.dumps(result['by_severity'])}")

    for fix in result["details"]:
        icon = {"safe": "+", "likely": "?", "manual": "!"}.get(
            fix.severity.value, "?")
        loc = f":{fix.line_start}" if fix.line_start else ""
        print(f"  [{icon}] {fix.file_name}{loc} - {fix.description}")
        if fix.original and args.verbose:
            print(f"       - {fix.original[:80]}")
            if fix.replacement:
                print(f"       + {fix.replacement[:80]}")

    if result["files_modified"]:
        print(f"\n  Modified files: {len(result['files_modified'])}")
        for f in result["files_modified"]:
            print(f"    {f}")

    print(f"\n  Completed in {elapsed:.1f}s")

    if args.json:
        serializable = {
            "total_fixes": result["total_fixes"],
            "by_severity": result["by_severity"],
            "files_modified": result["files_modified"],
            "details": [
                {
                    "rule_id": f.rule_id,
                    "description": f.description,
                    "severity": f.severity.value,
                    "file_name": f.file_name,
                    "line_start": f.line_start,
                    "applied": f.applied,
                }
                for f in result["details"]
            ],
        }
        print(json.dumps(serializable, indent=2, ensure_ascii=False))
