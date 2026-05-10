"""pb build command - Rebuild application with three output modes.

Three compilation modes:
  --mode exe        Single EXE (all code embedded, no external PBDs)
  --mode exe+pbd    EXE + separate PBDs (faster startup, updatable components)
  --mode exe+dll    EXE + DLLs (PowerBuilder DLL libraries)

PBD flags control which PBLs are compiled into EXE vs separate PBDs:
  n = include in EXE (no separate PBD)
  y = create separate PBD
  d = create as DLL

Usage:
    python pb.py build <pbl> <app_name>
    python pb.py build <pbl> <app_name> --mode exe --exe app.exe
    python pb.py build <pbl> <app_name> --mode exe+pbd --exe app.exe --pbd-libs lib1.pbl,lib2.pbl
    python pb.py build <pbl> <app_name> --mode exe+dll --exe app.exe --dll-libs lib1.pbl
    python pb.py build <pbl> <app_name> --exe app.exe --lib-list a.pbl;b.pbl;c.pbl
"""
import argparse
import sys
import time
from pathlib import Path
from typing import Optional


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "build",
        help="Rebuild application (single EXE / EXE+PBD / EXE+DLL)",
        description=(
            "Rebuild a PowerBuilder application.\n\n"
            "Three output modes:\n"
            "  exe      — Single standalone EXE (all code baked in)\n"
            "  exe+pbd  — EXE + separate PBD files (runtime-loadable components)\n"
            "  exe+dll  — EXE + DLL files (PowerBuilder dynamic libraries)\n"
        ),
    )
    p.add_argument("pbl", help="Application PBL file path")
    p.add_argument("app_name", help="Application object name (e.g. myapp)")

    # Output mode
    p.add_argument(
        "--mode",
        choices=["exe", "exe+pbd", "exe+dll"],
        default="exe",
        help=(
            "Compilation output mode:\n"
            "  exe       — Single EXE (default)\n"
            "  exe+pbd   — EXE + separate PBD files\n"
            "  exe+dll   — EXE + DLL files"
        ),
    )

    # Output paths
    p.add_argument(
        "--exe",
        default=None,
        help="Output EXE path (default: <app_name>.exe in PBL directory)",
    )
    p.add_argument(
        "--output-dir", "-d",
        default=None,
        metavar="DIR",
        help="Output directory for EXE + PBD/DLL files (default: PBL directory)",
    )

    # Library list (semicolon-separated, for multi-PBL projects)
    p.add_argument(
        "--lib-list",
        default=None,
        metavar="PBL1;PBL2;...",
        help=(
            "Semicolon-separated library list (all PBLs in the project). "
            "If not specified, only the main PBL is used."
        ),
    )

    # PBD/DLL library selection
    p.add_argument(
        "--pbd-libs",
        default=None,
        metavar="PBL1,PBL2,...",
        help=(
            "Comma-separated PBL names that should become separate PBD files "
            "(for --mode exe+pbd). Others are baked into the EXE."
        ),
    )
    p.add_argument(
        "--dll-libs",
        default=None,
        metavar="PBL1,PBL2,...",
        help=(
            "Comma-separated PBL names that should become DLL files "
            "(for --mode exe+dll). Others are baked into the EXE."
        ),
    )

    # Build options
    p.add_argument(
        "--icon",
        default=None,
        help="Icon file (.ico) for the EXE",
    )
    p.add_argument(
        "--pbr",
        default=None,
        metavar="FILE",
        help="PBR resource file path",
    )
    p.add_argument(
        "--machine-code",
        action="store_true",
        help="Compile to native machine code (Pcode is default)",
    )
    p.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Rebuild PBL only (don't create EXE)",
    )

    return p


def run(args):
    """Build application with specified output mode."""
    from pb_devkit.pborca_engine import PBORCAEngine

    pbl_path = Path(args.pbl).resolve()
    if not pbl_path.exists():
        print(f"[error] PBL not found: {pbl_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    out_dir = Path(args.output_dir).resolve() if args.output_dir else pbl_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine EXE path
    exe_path = None
    if not args.rebuild_only:
        if args.exe:
            exe_path = Path(args.exe).resolve()
        else:
            exe_path = out_dir / f"{args.app_name}.exe"

    # Parse library list
    lib_list = _parse_lib_list(args.lib_list, pbl_path)

    # Build PBD flags based on mode
    pbd_flags = _compute_pbd_flags(args.mode, lib_list, args)

    print(f"\n{'='*60}")
    print(f"  pb build — PowerBuilder Compiler")
    print(f"{'='*60}")
    print(f"  PBL:      {pbl_path}")
    print(f"  App:      {args.app_name}")
    print(f"  Mode:     {args.mode}")
    print(f"  Output:   {out_dir}")
    if exe_path:
        print(f"  EXE:      {exe_path.name}")
    if args.machine_code:
        print(f"  Compile:  Machine Code")
    print()

    engine = PBORCAEngine(pb_version=getattr(args, "pb_version", None) or 125)
    engine.session_open()

    try:
        # Step 1: Set library list
        if len(lib_list) > 1:
            lib_list_str = ";".join(str(p) for p in lib_list)
            print(f"[1/3] Setting library list ({len(lib_list)} PBLs)...")
            engine._dll.PBORCA_SessionSetLibraryList(
                engine._session, lib_list_str.encode("ascii"))
        else:
            lib_list_str = str(pbl_path)

        # Step 2: Set current application
        print(f"[1/3] Setting current application: {args.app_name}")
        engine._setup()
        engine._dll.PBORCA_SessionSetLibraryList(
            engine._session, lib_list_str.encode("ascii"))
        engine._dll.PBORCA_SessionSetCurrentAppl(
            engine._session,
            str(pbl_path).encode("ascii"),
            args.app_name.encode("ascii"))

        # Step 3: Rebuild
        print(f"[2/3] Rebuilding application...")
        t0 = time.time()
        engine._check(
            engine._dll.PBORCA_ApplicationRebuild(engine._session),
            "ApplicationRebuild"
        )
        elapsed = time.time() - t0
        print(f"  ✅ Rebuild complete ({elapsed:.1f}s)")

        # Step 4: Create executable (if requested)
        if exe_path and not args.rebuild_only:
            print(f"\n[3/3] Creating executable ({args.mode})...")
            print(f"  PBD flags: '{pbd_flags}' ({len(pbd_flags)} PBLs)")

            t0 = time.time()
            engine._check(
                engine._dll.PBORCA_ExecutableCreate(
                    engine._session,
                    str(exe_path).encode("ascii"),
                    (args.icon or "").encode("ascii"),
                    (args.pbr or "").encode("ascii"),
                    pbd_flags.encode("ascii"),
                    1 if args.machine_code else 0,
                ),
                "ExecutableCreate"
            )
            elapsed = time.time() - t0
            exe_size = exe_path.stat().st_size // 1024 if exe_path.exists() else 0
            print(f"  ✅ EXE created: {exe_path} ({exe_size} KB, {elapsed:.1f}s)")

            # Report PBD/DLL files created alongside
            if args.mode in ("exe+pbd", "exe+dll"):
                ext = ".pbd" if args.mode == "exe+pbd" else ".dll"
                created = list(out_dir.glob(f"*{ext}"))
                if created:
                    print(f"\n  Side files ({ext}):")
                    for f in sorted(created):
                        size = f.stat().st_size // 1024
                        print(f"    {f.name} ({size} KB)")

    finally:
        engine.session_close()

    print(f"\n{'='*60}")
    print(f"  Build complete — mode: {args.mode}")
    if exe_path and exe_path.exists():
        print(f"  Output: {exe_path}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_lib_list(lib_list_str: Optional[str], main_pbl: Path):
    """Parse semicolon-separated library list into Path objects."""
    if not lib_list_str:
        return [main_pbl]
    libs = []
    for part in lib_list_str.split(";"):
        part = part.strip()
        if part:
            p = Path(part)
            if not p.is_absolute():
                p = main_pbl.parent / p
            libs.append(p.resolve())
    return libs or [main_pbl]


def _compute_pbd_flags(mode: str, lib_list: list, args) -> str:
    """
    Compute PBD flags string for PBORCA_ExecutableCreate.

    Flag meaning per library slot:
      'n' = no PBD (compile into EXE)
      'y' = create PBD file (separate runtime file)
      'd' = create DLL file

    The flags string length = number of libraries in the library list.
    The first library (app PBL) is always 'n' (baked into EXE).
    """
    if mode == "exe":
        # All libraries baked into EXE
        return "n" * len(lib_list)

    if mode == "exe+pbd":
        # Determine which PBLs become separate PBDs
        pbd_lib_names = set()
        if args.pbd_libs:
            for name in args.pbd_libs.split(","):
                pbd_lib_names.add(name.strip().lower().removesuffix(".pbl"))

        flags = []
        for i, lib in enumerate(lib_list):
            lib_stem = lib.stem.lower()
            if i == 0:
                # App PBL is always in EXE
                flags.append("n")
            elif pbd_lib_names and lib_stem in pbd_lib_names:
                flags.append("y")
            elif not pbd_lib_names:
                # If no explicit list: make all non-app PBLs into PBDs
                flags.append("y")
            else:
                flags.append("n")
        return "".join(flags)

    if mode == "exe+dll":
        # Determine which PBLs become DLLs
        dll_lib_names = set()
        if args.dll_libs:
            for name in args.dll_libs.split(","):
                dll_lib_names.add(name.strip().lower().removesuffix(".pbl"))

        flags = []
        for i, lib in enumerate(lib_list):
            lib_stem = lib.stem.lower()
            if i == 0:
                flags.append("n")
            elif dll_lib_names and lib_stem in dll_lib_names:
                flags.append("d")
            elif not dll_lib_names:
                flags.append("d")
            else:
                flags.append("n")
        return "".join(flags)

    return "n" * len(lib_list)
