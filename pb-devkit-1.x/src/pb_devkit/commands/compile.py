"""pb compile command - Import .sr* sources + rebuild PBL in one step (pure Python).

Previously required PBORCA DLL. Now uses pbl_writer.py for PBL creation.
Note: Application rebuild (compiling PCode) still requires PB IDE.
      This command handles source -> PBL packaging only.
"""
import argparse
import sys
import time


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("compile",
                       help="Import .sr* sources into PBL (pure Python, no DLL)")
    p.add_argument("pbl", help="Target PBL file (created or overwritten)")
    p.add_argument("source_dir", help="Source directory with .sr* files")
    p.add_argument("--pb-version", type=int, default=12,
                   help="PB version for encoding (default: 12)")
    p.add_argument("--encoding", choices=["unicode", "ansi"], default="unicode",
                   help="PBL encoding (default: unicode)")
    return p


def run(args):
    """Import source files into PBL (pure Python)."""
    from pb_devkit.pbl_writer import PblWriter, SOURCE_EXT_TO_TYPE
    import os

    source_dir = args.source_dir
    pbl_path = args.pbl

    if not os.path.isdir(source_dir):
        print(f"Error: source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect .sr* files
    sr_files = []
    for fname in sorted(os.listdir(source_dir)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in SOURCE_EXT_TO_TYPE:
            sr_files.append(os.path.join(source_dir, fname))

    if not sr_files:
        print(f"No .sr* source files found in: {source_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[1/2] Packaging {len(sr_files)} source files -> {pbl_path}")
    t0 = time.time()

    writer = PblWriter(pb_version=args.pb_version, encoding=args.encoding)
    for fpath in sr_files:
        fname = os.path.basename(fpath)
        name = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1].lower()
        obj_type = SOURCE_EXT_TO_TYPE[ext]
        with open(fpath, encoding="utf-8", errors="replace") as f:
            source = f.read()
        writer.add_entry(name, obj_type, source)
        print(f"  + {fname}")

    size = writer.write(pbl_path)
    print(f"  Packaged {len(sr_files)} objects ({size:,} bytes) "
          f"in {time.time()-t0:.2f}s\n")

    print(f"[2/2] Note: Application rebuild (PCode compilation) requires PB IDE.")
    print(f"  To rebuild in PB IDE: File -> Rebuild All (Full Rebuild)")
    print(f"\nDone: {pbl_path}")
