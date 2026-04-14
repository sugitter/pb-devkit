"""pb diff command - Compare two source directories."""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("diff", help="Compare two source directories")
    p.add_argument("dir1", help="First source directory")
    p.add_argument("dir2", help="Second source directory")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Compare two source directories."""
    from pb_devkit.sr_parser import SRFileParser

    dir1 = Path(args.dir1)
    dir2 = Path(args.dir2)

    if not dir1.is_dir() or not dir2.is_dir():
        print("Error: both arguments must be directories", file=sys.stderr)
        sys.exit(1)

    # Collect files
    files1 = {f.name: f for f in dir1.glob("*.sr*")}
    files2 = {f.name: f for f in dir2.glob("*.sr*")}

    all_names = sorted(set(files1.keys()) | set(files2.keys()))

    added = []
    removed = []
    modified = []
    unchanged = 0

    for name in all_names:
        if name not in files1:
            added.append(name)
        elif name not in files2:
            removed.append(name)
        else:
            t1 = files1[name].read_text(encoding="utf-8-sig", errors="replace")
            t2 = files2[name].read_text(encoding="utf-8-sig", errors="replace")
            if t1 == t2:
                unchanged += 1
            else:
                # Parse and compare structure
                obj1 = SRFileParser().parse_text(t1, name,
                    SRFileParser().parse_file(files1[name]).object_type)
                obj2 = SRFileParser().parse_text(t2, name,
                    SRFileParser().parse_file(files2[name]).object_type)
                changes = _compare_objects(obj1, obj2)
                modified.append({"name": name, "changes": changes})

    # Print report
    print(f"\n{'='*60}")
    print(f"  Diff: {dir1} vs {dir2}")
    print(f"{'='*60}")
    print(f"  Added:     {len(added)}")
    print(f"  Removed:   {len(removed)}")
    print(f"  Modified:  {len(modified)}")
    print(f"  Unchanged: {unchanged}")

    if args.verbose:
        if added:
            print(f"\n  Added files:")
            for f in added:
                print(f"    + {f}")
        if removed:
            print(f"\n  Removed files:")
            for f in removed:
                print(f"    - {f}")
        if modified:
            print(f"\n  Modified files:")
            for m in modified:
                print(f"    ~ {m['name']}")
                for c in m["changes"]:
                    print(f"      {c}")

    if args.json:
        report_data = {
            "added": added, "removed": removed,
            "modified": [{"name": m["name"], "changes": m["changes"]}
                         for m in modified],
            "unchanged": unchanged,
        }
        print(json.dumps(report_data, indent=2, ensure_ascii=False))


def _compare_objects(obj1, obj2) -> list:
    """Compare two parsed PB objects and return list of changes."""
    changes = []
    names1 = {r.name for r in obj1.routines}
    names2 = {r.name for r in obj2.routines}
    for name in names2 - names1:
        changes.append(f"Added routine: {name}")
    for name in names1 - names2:
        changes.append(f"Removed routine: {name}")
    for name in names1 & names2:
        r1 = next(r for r in obj1.routines if r.name == name)
        r2 = next(r for r in obj2.routines if r.name == name)
        if r1.script != r2.script:
            changes.append(f"Modified routine: {name}")
    vars1 = {v.name for v in obj1.variables}
    vars2 = {v.name for v in obj2.variables}
    for v in vars2 - vars1:
        changes.append(f"Added variable: {v}")
    for v in vars1 - vars2:
        changes.append(f"Removed variable: {v}")
    return changes
