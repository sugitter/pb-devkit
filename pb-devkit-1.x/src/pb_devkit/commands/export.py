"""pb export command - Export PBL/EXE source to organized directory structure.

Modes:
  1. PBL files (--by-type or flat): Parse PBL binary, extract source entries
  2. EXE/PBD (--pbl-tree): Decompile + infer PBL grouping by naming convention
  3. Multi-PBL directory: Batch export preserving PBL directory structure
"""
import argparse
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("export", help="Export PBL/EXE source to files",
                       description=(
                           "Export PowerBuilder source code from PBL libraries "
                           "or decompile from EXE/PBD binaries."
                       ))
    p.add_argument("target", nargs="+", help="PBL/PBD/EXE file or directory")
    p.add_argument("-o", "--output", default="./exported",
                   help="Output directory (default: ./exported)")
    p.add_argument("--orca", action="store_true",
                   help="Use PBORCA DLL for export (PBL only)")
    p.add_argument("--no-headers", action="store_true",
                   help="Strip export header lines (--orca only)")
    p.add_argument("--by-type", action="store_true",
                   help="Organize files by object type "
                        "(window/, datawindow/, menu/, etc.)")
    p.add_argument("--pbl-tree", action="store_true",
                   help="Infer PBL grouping and export as PBL directory tree "
                        "(best for EXE/PBD with embedded libraries)")
    p.add_argument("--project-name", default=None,
                   help="Project name for PBL inference (default: auto from filename)")
    p.add_argument("--suffix", default=".ps",
                   help="Output file suffix for decompiled files (default: .ps)")
    p.add_argument("--no-clean", action="store_true",
                   help="Do not clean output directory before export")
    p.add_argument("--no-readme", action="store_true",
                   help="Do not generate README.md")
    return p


def run(args):
    """Export PB source files."""
    targets = args.target
    output = args.output
    pbl_tree = args.pbl_tree
    use_orca = args.orca
    by_type = args.by_type

    for target in targets:
        p = Path(target)

        # --- PBL Tree mode (EXE/PBD decompile + PBL inference) ---
        if pbl_tree:
            _export_pbl_tree(p, output, args)
            continue

        # --- Standard PBL export ---
        if p.is_file():
            suffix_lower = p.suffix.lower()

            if suffix_lower in (".exe", ".pbd"):
                # Auto-enable pbl-tree for EXE/PBD if not explicitly set
                print(f"[info] EXE/PBD detected, using --pbl-tree mode. "
                      f"Use --by-type for flat type-based export.",
                      file=sys.stderr)
                _export_pbl_tree(p, output, args)
                continue

            if suffix_lower == ".pbl":
                print(f"Exporting: {p}")
                if use_orca:
                    _export_with_orca(p, output, args)
                else:
                    from pb_devkit.pbl_parser import PBLParser
                    with PBLParser(p) as parser:
                        exported = parser.export_to_directory(
                            output, by_type=by_type)
                        for f in exported:
                            print(f"  -> {f}")
                        print(f"  Total: {len(exported)} objects")
            else:
                print(f"Error: unsupported file type: {suffix_lower}",
                      file=sys.stderr)
                sys.exit(1)

        elif p.is_dir():
            print(f"Batch exporting: {p}/*")
            from pb_devkit.pbl_parser import PBLBatchExporter
            exporter = PBLBatchExporter(p, output)
            results = exporter.export_all(by_type=by_type)
            total = sum(len(v) for v in results.values())
            print(f"  Total: {total} objects from {len(results)} PBLs")
        else:
            print(f"Error: not a PBL/PBD/EXE file or directory: {target}",
                  file=sys.stderr)
            sys.exit(1)

    print(f"\nExported to: {Path(output).resolve()}")


def _export_pbl_tree(target: Path, output: str, args):
    """Export using PBL tree mode (decompile + infer PBL grouping)."""
    from pb_devkit.pbl_grouper import export_pbl_tree

    stats = export_pbl_tree(
        file_path=str(target),
        output_dir=output,
        project_name=args.project_name,
        suffix=args.suffix,
        clean=not args.no_clean,
        generate_readme=not args.no_readme,
    )

    if stats.total_failed > 0:
        print(f"\n[warn] {stats.total_failed} entries failed to decompile",
              file=sys.stderr)


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
