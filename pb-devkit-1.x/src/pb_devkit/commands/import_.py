"""pb import command - Import .sr* files into PBL (pure Python, no DLL required).

Uses pbl_writer.py to create/update PBL files from source directories.
This replaces the previous PBORCA DLL dependency.
"""
import argparse
import os
import sys


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("import", help="Import .sr* files into PBL (pure Python)")
    p.add_argument("pbl", help="Target PBL file (created if not exists)")
    p.add_argument("source_dir", help="Source directory with .sr* files")
    p.add_argument("--pb-version", type=int, default=12,
                   help="PB version for encoding (default: 12 = Unicode)")
    p.add_argument("--encoding", choices=["unicode", "ansi"], default="unicode",
                   help="PBL encoding (default: unicode)")
    p.add_argument("--merge", action="store_true",
                   help="Merge into existing PBL (not yet supported, builds fresh)")
    return p


def run(args):
    """Import source files into PBL using pure Python PBL writer."""
    from pb_devkit.pbl_writer import PblWriter, SOURCE_EXT_TO_TYPE

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

    print(f"Importing {len(sr_files)} source files -> {pbl_path}")

    writer = PblWriter(
        pb_version=args.pb_version,
        encoding=args.encoding,
    )

    imported = []
    for fpath in sr_files:
        fname = os.path.basename(fpath)
        name = os.path.splitext(fname)[0]
        ext = os.path.splitext(fname)[1].lower()
        obj_type = SOURCE_EXT_TO_TYPE[ext]

        with open(fpath, encoding="utf-8", errors="replace") as f:
            source = f.read()

        writer.add_entry(name, obj_type, source)
        imported.append(fname)
        print(f"  + {fname}")

    size = writer.write(pbl_path)
    print(f"\nImported {len(imported)} objects into {pbl_path}")
    print(f"PBL file size: {size:,} bytes")
