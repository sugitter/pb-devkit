"""pb list command - List objects in PBL."""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("list", help="List objects in PBL")
    p.add_argument("target", nargs="+", help="PBL file or directory")
    p.add_argument("--json", action="store_true")
    p.add_argument("--orca", action="store_true")
    return p


def run(args):
    """List objects in PBL."""
    from pb_devkit.pbl_parser import PBLParser
    use_orca = args.orca

    targets = args.target
    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix.lower() == ".pbl":
            print(f"\n{p} ({p.stat().st_size:,} bytes)")
            if use_orca:
                _list_with_orca(str(p), args.json)
            else:
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


def _list_with_orca(pbl_path: str, as_json: bool):
    """List PBL entries using ORCA DLL."""
    from pb_devkit.pborca_engine import PBORCAEngine, TYPE_TO_EXT
    engine = PBORCAEngine(pb_version=125)
    engine.session_open()
    try:
        entries = engine.library_directory(pbl_path)
        result = []
        for name, tc, comment in entries:
            ext = TYPE_TO_EXT.get(tc, "?")
            result.append({"name": name, "type_code": tc, "ext": ext,
                           "comment": comment})
        if as_json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"  {'Ext':<6} {'Name':<30} {'Comment'}")
            print(f"  {'-'*6} {'-'*30} {'-'*30}")
            for e in result:
                print(f"  {e['ext']:<6} {e['name']:<30} {e['comment'][:30]}")
            print(f"  Total: {len(result)} objects")
    finally:
        engine.session_close()
