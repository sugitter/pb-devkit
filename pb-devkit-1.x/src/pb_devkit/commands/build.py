"""pb build command - Rebuild application with three output modes.

Three compilation modes:
  --mode exe        Single EXE (all code embedded, no external PBDs)
  --mode exe+pbd    EXE + separate PBDs (faster startup, updatable components)
  --mode exe+dll    EXE + DLLs (PowerBuilder DLL libraries)

NOTE: This command requires an installed PowerBuilder IDE to compile.
      The pb-devkit toolkit handles EXE→source→web migration without PB IDE.
      To compile a PB application, use PowerBuilder's IDE or PBGen CLI tool.

Usage:
    pb build <pbl> <app_name>
    pb build <pbl> <app_name> --mode exe --exe app.exe
    pb build <pbl> <app_name> --mode exe+pbd --exe app.exe --pbd-libs lib1.pbl,lib2.pbl
"""
import argparse
import sys
from pathlib import Path
from typing import Optional


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "build",
        help="Rebuild a PB application (requires PowerBuilder IDE installed)",
        description=(
            "Rebuild a PowerBuilder application.\n\n"
            "Three output modes:\n"
            "  exe      — Single standalone EXE (all code baked in)\n"
            "  exe+pbd  — EXE + separate PBD files (runtime-loadable components)\n"
            "  exe+dll  — EXE + DLL files (PowerBuilder dynamic libraries)\n\n"
            "NOTE: Compilation requires PowerBuilder IDE. This command invokes\n"
            "      the PBGen CLI that ships with PowerBuilder.\n"
        ),
    )
    p.add_argument("pbl", help="Application PBL file path")
    p.add_argument("app_name", help="Application object name (e.g. myapp)")

    # Output mode
    p.add_argument(
        "--mode",
        choices=["exe", "exe+pbd", "exe+dll"],
        default="exe",
        help="Compilation output mode (default: exe)",
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
        help="Output directory for EXE + PBD/DLL files",
    )

    # Library list
    p.add_argument(
        "--lib-list",
        default=None,
        metavar="PBL1;PBL2;...",
        help="Semicolon-separated library list (all PBLs in the project).",
    )

    # PBD/DLL library selection
    p.add_argument(
        "--pbd-libs",
        default=None,
        metavar="PBL1,PBL2,...",
        help="Comma-separated PBL names that should become separate PBD files.",
    )
    p.add_argument(
        "--dll-libs",
        default=None,
        metavar="PBL1,PBL2,...",
        help="Comma-separated PBL names that should become DLL files.",
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
    p.add_argument(
        "--pbgen",
        default=None,
        metavar="PATH",
        help="Path to PBGen.exe (PowerBuilder CLI compiler). Auto-detected if not set.",
    )

    return p


def run(args):
    """Build application using PowerBuilder's PBGen CLI compiler."""
    import subprocess
    import shutil

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

    # Locate PBGen.exe
    pbgen = _find_pbgen(args.pbgen)

    print(f"\n{'='*60}")
    print(f"  pb build — PowerBuilder Compiler")
    print(f"{'='*60}")
    print(f"  PBL:      {pbl_path}")
    print(f"  App:      {args.app_name}")
    print(f"  Mode:     {args.mode}")
    print(f"  Output:   {out_dir}")
    if exe_path:
        print(f"  EXE:      {exe_path.name}")

    if not pbgen:
        print(
            f"\n[error] PowerBuilder PBGen.exe not found.\n"
            f"  Install PowerBuilder, then either:\n"
            f"  1. Add PBGen.exe to your PATH, or\n"
            f"  2. Use --pbgen <path_to_PBGen.exe>\n\n"
            f"  Typical locations:\n"
            f"    C:\\Program Files\\Appeon\\PowerBuilder xx.x\\PBGen.exe\n"
            f"\n"
            f"  For EXE analysis (no IDE needed), use:\n"
            f"    pb export <your.exe> --pbl-tree\n"
            f"    pb migrate <your.exe> -o ./web-output\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse library list
    lib_list = _parse_lib_list(args.lib_list, pbl_path)
    lib_list_str = ";".join(str(p) for p in lib_list)

    # Build PBD flags
    pbd_flags = _compute_pbd_flags(args.mode, lib_list, args)

    # Build PBGen command
    # PBGen syntax: PBGen.exe -l <liblist> -a <appname> -e <exepath> -p <pbdflags>
    cmd = [
        str(pbgen),
        "-l", lib_list_str,
        "-a", args.app_name,
    ]
    if exe_path and not args.rebuild_only:
        cmd += ["-e", str(exe_path)]
    if args.icon:
        cmd += ["-i", args.icon]
    if args.pbr:
        cmd += ["-r", args.pbr]
    if args.machine_code:
        cmd += ["-m"]
    if pbd_flags and args.mode != "exe":
        cmd += ["-p", pbd_flags]

    print(f"\n  Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode != 0:
            print(f"\n[error] PBGen exited with code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)
    except FileNotFoundError:
        print(f"[error] Cannot execute: {pbgen}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"[error] Build timed out after 300s", file=sys.stderr)
        sys.exit(1)

    if exe_path and exe_path.exists():
        size = exe_path.stat().st_size // 1024
        print(f"\n  ✅ EXE created: {exe_path} ({size} KB)")

    print(f"\n{'='*60}")
    print(f"  Build complete — mode: {args.mode}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_pbgen(explicit_path: Optional[str]) -> Optional[Path]:
    """Locate PBGen.exe from explicit path, PATH, or common install dirs."""
    import shutil

    if explicit_path:
        p = Path(explicit_path)
        return p if p.exists() else None

    # Check PATH
    found = shutil.which("PBGen.exe") or shutil.which("PBGen")
    if found:
        return Path(found)

    # Common install locations
    candidates = []
    for base in [
        r"C:\Program Files\Appeon",
        r"C:\Program Files (x86)\Appeon",
        r"C:\Program Files\Sybase",
        r"C:\Program Files (x86)\Sybase",
    ]:
        base_p = Path(base)
        if base_p.exists():
            for sub in base_p.iterdir():
                g = sub / "PBGen.exe"
                if g.exists():
                    candidates.append(g)

    return candidates[0] if candidates else None


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
    Compute PBD flags string for PBGen -p option.

    Flag meaning per library slot:
      'n' = no PBD (compile into EXE)
      'y' = create PBD file
      'd' = create DLL file
    """
    if mode == "exe":
        return "n" * len(lib_list)

    if mode == "exe+pbd":
        pbd_lib_names = set()
        if args.pbd_libs:
            for name in args.pbd_libs.split(","):
                pbd_lib_names.add(name.strip().lower().removesuffix(".pbl"))
        flags = []
        for i, lib in enumerate(lib_list):
            lib_stem = lib.stem.lower()
            if i == 0:
                flags.append("n")
            elif pbd_lib_names and lib_stem in pbd_lib_names:
                flags.append("y")
            elif not pbd_lib_names:
                flags.append("y")
            else:
                flags.append("n")
        return "".join(flags)

    if mode == "exe+dll":
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
