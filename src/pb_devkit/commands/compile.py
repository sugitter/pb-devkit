"""pb compile command - Import + rebuild in one step."""
import argparse
import time


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("compile", help="Import + rebuild in one step")
    p.add_argument("pbl", help="Target PBL")
    p.add_argument("source_dir", help="Source directory")
    p.add_argument("--app-name", help="App name for rebuild")
    return p


def run(args):
    """Import source + rebuild in one step."""
    from pb_devkit.pborca_engine import PBORCAEngine

    engine = PBORCAEngine(pb_version=args.pb_version)
    engine.session_open()
    try:
        imported = engine.import_from_directory(args.pbl, args.source_dir)
        print(f"Imported {len(imported)} objects")

        if args.app_name:
            print(f"Rebuilding application...")
            t0 = time.time()
            engine.rebuild_application(args.pbl, args.app_name)
            print(f"Build success ({time.time() - t0:.1f}s)")
    finally:
        engine.session_close()
