"""pb decompile command - Decompile PBD/PBL/EXE compiled binary to PowerScript."""
import argparse
import os
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "decompile",
        help="Decompile PBD/PBL/EXE compiled binary back to PowerScript",
        description=(
            "Decompile a PowerBuilder PBD, PBL, or EXE (with embedded PBD) "
            "back to readable PowerScript source code."
        )
    )
    p.add_argument("target", help="PBD / PBL / EXE file to decompile")
    p.add_argument(
        "--entry", "-e",
        metavar="NAME",
        help="Decompile a specific entry (e.g. w_main, f_calc). Default: all"
    )
    p.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available entries without decompiling"
    )
    p.add_argument(
        "--tree", "-t",
        action="store_true",
        help="Show PBD internal structure tree"
    )
    p.add_argument(
        "--output", "-o",
        metavar="DIR",
        help="Output directory for decompiled .ps files (default: print to stdout)"
    )
    p.add_argument(
        "--suffix",
        default=".ps",
        help="File suffix for saved decompiled files (default: .ps)"
    )
    p.add_argument(
        "--resources", "-r",
        metavar="DIR",
        help="Extract binary resources (images/icons) to this directory"
    )
    return p


def run(args):
    """Run the decompile command."""
    from pb_devkit.decompiler import (
        decompile_file, list_entries, get_tree_str,
        DecompileResult, extract_resources, list_resource_entries
    )

    target = Path(args.target)
    if not target.exists():
        print(f"[error] File not found: {target}", file=sys.stderr)
        sys.exit(1)

    target_path = str(target)
    suffix = target.suffix.lower()

    # PbdCli's PbProject supports .exe, .pbl, and .pbd directly
    # For .exe: it finds the embedded PBD automatically via the EXE entry
    # No need to manually extract PBD bytes first

    # ---- List mode ----
    if args.list:
        entries = list_entries(target_path)
        if not entries:
            print("[warn] No entries found (or parse error).", file=sys.stderr)
            return
        for name in entries:
            print(name)
        return

    # ---- Tree mode ----
    if args.tree:
        print(get_tree_str(target_path))
        return

    # ---- Decompile ----
    entry_name = args.entry  # None = all
    output_dir = args.output

    print(f"[info] Loading {target_path}...", file=sys.stderr)
    results = decompile_file(target_path, entry_name=entry_name, decompile_all=True)

    if not results:
        print("[warn] No entries found.", file=sys.stderr)
        return

    ok = 0
    fail = 0
    skipped = 0

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        for r in results:
            if not r.success:
                fail += 1
                print(f"[warn] {r.entry_name}: {r.error}", file=sys.stderr)
                continue
            # Skip empty source (binary/image entries like bmp\s1.gif)
            if not r.source or not r.source.strip():
                skipped += 1
                continue
            # Skip path-like entry names (e.g. bmp\logo.gif) - these are resources
            if '\\' in r.entry_name or ('/' in r.entry_name and not r.entry_name.startswith('/')):
                skipped += 1
                continue
            # Derive filename: w_main.win -> w_main.ps (or user-specified suffix)
            base = r.entry_name.rsplit('.', 1)[0] if '.' in r.entry_name else r.entry_name
            out_file = out_path / (base + args.suffix)
            out_file.write_text(r.source, encoding="utf-8")
            print(f"  {r.entry_name} -> {out_file.name}")
            ok += 1
        skip_note = f", {skipped} skipped" if skipped else ""
        print(f"\n[done] {ok} saved to {output_dir}, {fail} failed{skip_note}.", file=sys.stderr)
    else:
        # Print to stdout
        for r in results:
            if not r.success:
                fail += 1
                print(f"\n[error] {r.entry_name}: {r.error}", file=sys.stderr)
            elif not r.source or not r.source.strip():
                skipped += 1
            else:
                ok += 1
                print(r.source)
        summary = f"[done] {ok} ok"
        if fail:
            summary += f", {fail} failed"
        if skipped:
            summary += f", {skipped} skipped"
        print(f"\n{summary}.", file=sys.stderr)

    # ---- Resource extraction ----
    if args.resources:
        res_dir = args.resources
        print(f"\n[info] Extracting resources to {res_dir}...", file=sys.stderr)
        res_results = extract_resources(target_path, res_dir)
        res_ok = sum(1 for r in res_results if r.success)
        res_fail = sum(1 for r in res_results if not r.success)
        if res_ok:
            # Group by subdirectory for nice output
            dirs = set()
            for r in res_results:
                if r.success:
                    parts = r.entry_name.replace('\\', '/').split('/')
                    if len(parts) > 1:
                        dirs.add(parts[0])
            if dirs:
                print(f"  Resource directories: {', '.join(sorted(dirs))}")
            total_size = sum(r.size for r in res_results if r.success)
            print(f"  {res_ok} files extracted ({total_size:,} bytes)")
        if res_fail:
            print(f"  {res_fail} failed", file=sys.stderr)
        print(f"[done] Resources saved to {res_dir}.", file=sys.stderr)
