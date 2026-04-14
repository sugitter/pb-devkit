"""pb build command - Rebuild application."""
import argparse
import time


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("build", help="Rebuild application")
    p.add_argument("pbl", help="Application PBL")
    p.add_argument("app_name", help="Application object name")
    p.add_argument("--exe", help="Also create executable")
    p.add_argument("--icon", help="Icon file for executable")
    p.add_argument("--machine-code", action="store_true")
    return p


def run(args):
    """Rebuild application."""
    from pb_devkit.pborca_engine import PBORCAEngine

    engine = PBORCAEngine(pb_version=args.pb_version)
    engine.session_open()
    try:
        print(f"Rebuilding: {args.pbl} / {args.app_name}")
        t0 = time.time()
        engine.rebuild_application(args.pbl, args.app_name)
        elapsed = time.time() - t0
        print(f"Build success ({elapsed:.1f}s)")

        if args.exe:
            print(f"Creating executable: {args.exe}")
            engine.build_executable(
                args.exe, args.icon or "",
                machine_code=args.machine_code)
            print("Executable created.")
    finally:
        engine.session_close()
