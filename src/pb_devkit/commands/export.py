"""pb export command - Export PBL source to .sr* files."""
import argparse
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("export", help="Export PBL to .sr* files")
    p.add_argument("target", nargs="+", help="PBL file or directory")
    p.add_argument("output", nargs="?", help="Output directory")
    p.add_argument("--orca", action="store_true",
                   help="Use PBORCA DLL for export")
    p.add_argument("--no-headers", action="store_true",
                   help="Strip export header lines")
    return p


def run(args):
    """Export PBL source files."""
    from pb_devkit.pbl_parser import PBLParser, PBLBatchExporter

    targets = args.target
    output = args.output or "./exported"
    use_orca = args.orca

    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix.lower() == ".pbl":
            print(f"Exporting: {p}")
            if use_orca:
                _export_with_orca(p, output, args)
            else:
                with PBLParser(p) as parser:
                    exported = parser.export_to_directory(output)
                    for f in exported:
                        print(f"  -> {f}")
                    print(f"  Total: {len(exported)} objects")
        elif p.is_dir():
            print(f"Batch exporting: {p}/*")
            exporter = PBLBatchExporter(p, output)
            results = exporter.export_all()
            total = sum(len(v) for v in results.values())
            print(f"  Total: {total} objects from {len(results)} PBLs")
        else:
            print(f"Error: not a PBL file or directory: {target}",
                  file=sys.stderr)
            sys.exit(1)

    print(f"\nExported to: {Path(output).resolve()}")


def _export_with_orca(pbl_path: Path, output_dir: str, args):
    """Export using PBORCA DLL for accurate results."""
    from pb_devkit.pborca_engine import PBORCAEngine

    engine = PBORCAEngine(pb_version=args.pb_version)
    engine.session_open()
    try:
        exported = engine.export_all(str(pbl_path), output_dir,
                                     headers=not args.no_headers)
        for f in exported:
            print(f"  -> {f}")
        print(f"  Total: {len(exported)} objects (via ORCA)")
    finally:
        engine.session_close()
