"""pb init command - Initialize / detect PB project structure."""
import argparse
import json
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("init", help="Initialize / detect PB project structure")
    p.add_argument("target", help="Project directory")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Initialize a PB project - detect and report structure."""
    from pb_devkit.pbl_parser import PBLParser

    project_dir = Path(args.target).resolve()
    if not project_dir.exists():
        print(f"Error: path not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PB Project Structure: {project_dir.name}")
    print(f"{'='*60}")

    # Find all PBL files
    pbls = sorted(project_dir.glob("**/*.pbl"))
    if not pbls:
        print("\n  No PBL files found. Is this a PB project?")
        sys.exit(1)

    # Analyze each PBL
    modules = {}
    total_objects = 0
    type_counts = {}

    for pbl in pbls:
        try:
            with PBLParser(pbl) as parser:
                entries = parser.list_entries()
                size_mb = pbl.stat().st_size / 1024 / 1024
                rel = pbl.relative_to(project_dir)

                module_info = {
                    "path": str(rel),
                    "absolute_path": str(pbl),
                    "size_mb": round(size_mb, 2),
                    "object_count": len(entries),
                    "objects": entries[:20],
                }
                modules[str(rel)] = module_info
                total_objects += len(entries)

                for e in entries:
                    t = e.get("type", "unknown")[:10]
                    type_counts[t] = type_counts.get(t, 0) + 1

                print(f"\n  {rel} ({size_mb:.1f} MB, {len(entries)} objects)")
                if not args.json:
                    local_types = {}
                    for e in entries:
                        t = e.get("type", "unknown")[:10]
                        local_types[t] = local_types.get(t, 0) + 1
                    for t, c in sorted(local_types.items(), key=lambda x: -x[1])[:5]:
                        print(f"    {t:<12} {c:>4}")

        except Exception as e:
            size_mb = pbl.stat().st_size / 1024 / 1024
            rel = pbl.relative_to(project_dir)
            print(f"\n  {rel} ({size_mb:.1f} MB) [parse skipped: {e}]")
            modules[str(rel)] = {
                "path": str(rel),
                "absolute_path": str(pbl),
                "size_mb": round(size_mb, 2),
                "object_count": 0,
                "parse_error": str(e),
                "note": "PB12+ format may need PBSpyORCA.dll for parsing",
            }

    # Check for application file (.pbt / .pbw)
    app_files = list(project_dir.glob("*.pbt"))
    workspace_files = list(project_dir.glob("*.pbw"))

    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    print(f"  PBL files:       {len(pbls)}")
    print(f"  Total objects:   {total_objects}")
    print(f"  Project file:    {app_files[0].name if app_files else 'not found'}")
    print(f"  Workspace file:  {workspace_files[0].name if workspace_files else 'not found'}")

    if type_counts:
        print(f"\n  Object types:")
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {t:<20} {c:>5}")

    total_size = sum(p.stat().st_size for p in pbls)
    print(f"\n  Total PBL size:   {total_size / 1024 / 1024:.1f} MB")
    if total_objects == 0 and len(pbls) > 0:
        print(f"  Note: Objects could not be counted (PB12+ format).")
        print(f"        Download PBSpyORCA.dll for full support:")
        print(f"        https://github.com/Hucxy/PBSpyORCA/releases")

    print(f"\n  Next steps:")
    print(f"    1. Export all sources:  python pb.py export {project_dir} ./exported")
    print(f"    2. Analyze quality:     python pb.py analyze-project ./exported --json")
    if total_objects == 0:
        print(f"\n  Or with ORCA DLL:")
        print(f"    1. python pb.py --orca export {project_dir} ./exported")
        print(f"    2. python pb.py analyze-project ./exported --json")

    if args.json:
        result = {
            "project_dir": str(project_dir),
            "pbl_count": len(pbls),
            "total_objects": total_objects,
            "type_distribution": type_counts,
            "project_file": str(app_files[0]) if app_files else None,
            "workspace_file": str(workspace_files[0]) if workspace_files else None,
            "modules": modules,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
