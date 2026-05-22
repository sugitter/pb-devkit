"""
pb pack — Pack .sr* source files back into PowerBuilder Library (.pbl) files.

This is the reverse of `pb export` — it takes a source directory exported by
pb-devkit and rebuilds valid .pbl files that a PB IDE can open.

No PBORCA DLL required. Pure Python implementation.

Usage examples::

    # Pack a single directory into one PBL
    pb pack ./pb_source/common.pbl/ -o common.pbl

    # Pack entire PBL tree (as exported by `pb migrate`/`pb export --pbl-tree`)
    pb pack ./pb_source/ --all -o ./output_pbl/

    # Specify PB version and encoding
    pb pack ./pb_source/framework.pbl/ -o framework.pbl --pb-version 9 --encoding ansi
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "pack",
        help="Pack source files (.sr*) back into PowerBuilder Library (.pbl) files",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "source",
        help="Source directory containing .sr* files (or PBL tree root with --all)",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output path: .pbl file (single mode) or directory (--all mode). "
             "Default: <source>.pbl or ./pb_output/",
    )
    p.add_argument(
        "--all",
        action="store_true",
        dest="pack_all",
        help="Pack all PBL subdirectories in the source tree (one .pbl per subdir)",
    )
    p.add_argument(
        "--pb-version",
        type=int,
        default=12,
        metavar="VERSION",
        help="Target PowerBuilder version (default: 12). "
             "Use 9 for PB9 or earlier (affects encoding).",
    )
    p.add_argument(
        "--encoding",
        choices=["unicode", "ansi"],
        default=None,
        help="PBL encoding: 'unicode' for PB10+, 'ansi' for PB5-9. "
             "Auto-detected from --pb-version if not specified.",
    )
    p.add_argument(
        "--recursive",
        action="store_true",
        help="Scan source directory recursively for .sr* files (single mode only)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be packed without writing any files",
    )


def run_pack(args: argparse.Namespace) -> None:
    """Execute the pack command."""
    try:
        from pb_devkit.pbl_writer import PblWriter, pack_pbl_tree
    except ImportError as e:
        print(f"Error: Cannot import pbl_writer: {e}", file=sys.stderr)
        sys.exit(1)

    source = Path(os.path.abspath(args.source))
    if not source.exists():
        print(f"Error: Source path does not exist: {source}", file=sys.stderr)
        sys.exit(1)
    if not source.is_dir():
        print(f"Error: Source must be a directory, got: {source}", file=sys.stderr)
        sys.exit(1)

    # Auto-detect encoding from pb_version
    pb_version: int = args.pb_version
    if args.encoding:
        encoding = args.encoding
    else:
        encoding = "unicode" if pb_version >= 10 else "ansi"

    dry_run: bool = getattr(args, "dry_run", False)

    # ── Mode: pack entire PBL tree ────────────────────────────────────────
    if args.pack_all:
        _pack_tree(source, args, pb_version, encoding, dry_run)
    else:
        # ── Mode: pack single directory ───────────────────────────────────
        _pack_single(source, args, pb_version, encoding, dry_run)


def _resolve_output_dir(args: argparse.Namespace, source: Path) -> Path:
    """Resolve output directory for --all mode."""
    if args.output:
        return Path(os.path.abspath(args.output))
    return source.parent / "pb_output"


def _resolve_output_pbl(args: argparse.Namespace, source: Path) -> Path:
    """Resolve output .pbl path for single mode."""
    if args.output:
        out = Path(os.path.abspath(args.output))
        if not out.suffix:
            out = out.with_suffix(".pbl")
        return out
    # Derive from source dir name
    name = source.name
    if name.endswith(".pbl"):
        return source.parent / name
    return source.parent / (name + ".pbl")


def _pack_single(
    source: Path, args: argparse.Namespace,
    pb_version: int, encoding: str, dry_run: bool,
) -> None:
    """Pack a single source directory into one .pbl file."""
    from pb_devkit.pbl_writer import PblWriter

    output_pbl = _resolve_output_pbl(args, source)

    print(f"pb pack  —  Single mode")
    print(f"  Source   : {source}")
    print(f"  Output   : {output_pbl}")
    print(f"  PB ver   : {pb_version} ({encoding})")
    print(f"  Recursive: {getattr(args, 'recursive', False)}")
    print()

    recursive = getattr(args, "recursive", False)

    # Discover source files
    pattern = "**/*" if recursive else "*"
    from pb_devkit.chunk_engine import SOURCE_EXT_MAP
    files = sorted([
        p for p in source.glob(pattern)
        if p.is_file() and p.suffix.lower() in SOURCE_EXT_MAP
    ])

    if not files:
        print("  [warn] No .sr* source files found in source directory.")
        sys.exit(0)

    print(f"  Found {len(files)} source files:")
    for f in files:
        print(f"    {f.name}")
    print()

    if dry_run:
        print("[dry-run] No files written.")
        return

    w = PblWriter(pb_version=pb_version, encoding=encoding)
    for f in files:
        w.add_source_file(f)

    if w.entry_count() == 0:
        print("Error: No entries loaded — check source file formats.", file=sys.stderr)
        sys.exit(1)

    try:
        size = w.write(output_pbl)
        print(f"[OK] Packed {w.entry_count()} entries → {output_pbl} ({size:,} bytes)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _pack_tree(
    source: Path, args: argparse.Namespace,
    pb_version: int, encoding: str, dry_run: bool,
) -> None:
    """Pack entire PBL tree: one subdirectory → one .pbl file."""
    output_dir = _resolve_output_dir(args, source)

    print(f"pb pack  —  Tree mode (--all)")
    print(f"  Source tree : {source}")
    print(f"  Output dir  : {output_dir}")
    print(f"  PB version  : {pb_version} ({encoding})")
    print()

    from pb_devkit.chunk_engine import SOURCE_EXT_MAP

    # Discover PBL subdirectories
    pbl_dirs = sorted([d for d in source.iterdir() if d.is_dir()])
    if not pbl_dirs:
        print("  [warn] No subdirectories found. Expected structure: source/<name>.pbl/")
        sys.exit(0)

    total_entries = 0
    results = []

    for pbl_dir in pbl_dirs:
        pbl_name = pbl_dir.name
        if not pbl_name.endswith(".pbl"):
            pbl_name = pbl_dir.name + ".pbl"

        files = sorted([
            p for p in pbl_dir.glob("*")
            if p.is_file() and p.suffix.lower() in SOURCE_EXT_MAP
        ])

        if not files:
            print(f"  [skip] {pbl_dir.name}/ — no .sr* files")
            continue

        output_pbl = output_dir / pbl_name
        results.append((pbl_dir, pbl_name, files, output_pbl))
        print(f"  {pbl_dir.name}/  →  {pbl_name}  ({len(files)} files)")
        total_entries += len(files)

    print(f"\n  Total: {len(results)} PBL files, {total_entries} entries")

    if dry_run:
        print("\n[dry-run] No files written.")
        return

    if not results:
        print("Nothing to pack.", file=sys.stderr)
        sys.exit(0)

    output_dir.mkdir(parents=True, exist_ok=True)
    packed = 0
    total_size = 0

    print()
    for pbl_dir, pbl_name, files, output_pbl in results:
        from pb_devkit.pbl_writer import PblWriter
        w = PblWriter(pb_version=pb_version, encoding=encoding)
        for f in files:
            w.add_source_file(f)
        try:
            size = w.write(output_pbl)
            packed += w.entry_count()
            total_size += size
            print(f"  [OK] {pbl_name}: {w.entry_count()} entries, {size:,} bytes")
        except Exception as e:
            print(f"  [ERR] {pbl_name}: {e}", file=sys.stderr)

    print(f"\nDone!  {len(results)} PBL files  |  {packed} entries  |  {total_size:,} bytes total")
    print(f"Output: {output_dir}")
