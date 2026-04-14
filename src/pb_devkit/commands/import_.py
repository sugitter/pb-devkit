"""pb import command - Import .sr* files into PBL."""
import argparse


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("import", help="Import .sr* files into PBL")
    p.add_argument("pbl", help="Target PBL file")
    p.add_argument("source_dir", help="Source directory with .sr* files")
    return p


def run(args):
    """Import source files into PBL."""
    from pb_devkit.pborca_engine import PBORCAEngine

    engine = PBORCAEngine(pb_version=args.pb_version)
    engine.session_open()
    try:
        imported = engine.import_from_directory(args.pbl, args.source_dir)
        print(f"Imported {len(imported)} objects into {args.pbl}")
        for name in imported:
            print(f"  + {name}")
    finally:
        engine.session_close()
