"""pb list command - List objects in PBL (pure Python, no DLL required)."""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("list", help="List objects in PBL")
    p.add_argument("target", nargs="+", help="PBL file or directory")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """List objects in PBL using pure Python parser."""
    from pb_devkit.pbl_parser import PBLParser

    targets = args.target
    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix.lower() == ".pbl":
            print(f"\n{p} ({p.stat().st_size:,} bytes)")
            with PBLParser(p) as parser:
                entries = parser.list_entries()
                if args.json:
                    print(json.dumps(entries, indent=2, ensure_ascii=False))
                else:
                    print(f"  {'Type':<15} {'Name':<30} {'Size':>8}")
                    print(f"  {'-'*15} {'-'*30} {'-'*8}")
                    for e in entries:
                        print(f"  {e['type']:<15} {e['name']:<30} {e['size']:>8,}")
                    print(f"  Total: {len(entries)} objects")
        elif p.is_dir():
            for pbl in sorted(p.glob("**/*.pbl")):
                print(f"\n{pbl} ({pbl.stat().st_size:,} bytes)")
                with PBLParser(pbl) as parser:
                    entries = parser.list_entries()
                    print(f"  {len(entries)} objects")
                    if not args.json:
                        for e in entries[:10]:
                            print(f"    {e['type']:<12} {e['name']}")
                        if len(entries) > 10:
                            print(f"    ... and {len(entries) - 10} more")
        else:
            print(f"Error: not a PBL file or directory: {target}", file=sys.stderr)
            sys.exit(1)
