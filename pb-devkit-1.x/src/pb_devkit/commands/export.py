"""pb export command - Export PBL/EXE source to organized directory structure.

Modes:
  1. PBL files (--by-type or flat): Parse PBL binary, extract source entries
  2. EXE/PBD (--pbl-tree): Decompile + infer PBL grouping by naming convention
  3. Multi-PBL directory: Batch export preserving PBL directory structure
"""
import argparse
import json
import sys
from datetime import datetime
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
    p.add_argument("--manifest", action="store_true",
                   help="Generate export-manifest.json with object metadata")
    return p


def run(args):
    """Export PB source files."""
    targets = args.target
    output = args.output
    pbl_tree = args.pbl_tree
    use_orca = args.orca
    by_type = args.by_type
    write_manifest = getattr(args, "manifest", False)

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
                        if write_manifest:
                            _write_manifest(
                                output_dir=output,
                                source_file=str(p),
                                exported_files=exported,
                            )
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

    if getattr(args, "manifest", False):
        # Collect file list from output dir
        out = Path(output)
        exported = sorted(str(f) for f in out.rglob("*") if f.is_file()
                          and f.name != "README.md")
        _write_manifest(
            output_dir=output,
            source_file=str(target),
            exported_files=exported,
            stats=stats,
        )


def _write_manifest(
    output_dir: str,
    source_file: str,
    exported_files: list,
    stats=None,
) -> None:
    """Write export-manifest.json to the output directory."""
    out = Path(output_dir)

    # Build per-file metadata
    objects = []
    for fp in exported_files:
        p = Path(fp)
        ext = p.suffix.lower()
        type_map = {
            ".srw": "window", ".srd": "datawindow", ".srm": "menu",
            ".srf": "function", ".srs": "structure", ".sru": "userobject",
            ".sra": "application", ".srq": "query", ".srp": "pipeline",
            ".ps": "unknown",  # decompiled
        }
        objects.append({
            "file": str(p.relative_to(out)) if p.is_relative_to(out) else fp,
            "name": p.stem,
            "type": type_map.get(ext, "unknown"),
            "size": p.stat().st_size if p.exists() else 0,
        })

    manifest = {
        "pb_devkit_version": "1.x",
        "exported_at": datetime.now().isoformat(),
        "source_file": str(Path(source_file).name),
        "output_dir": str(out.resolve()),
        "total_objects": len(objects),
        "stats": {
            "saved": getattr(stats, "total_saved", len(objects)),
            "failed": getattr(stats, "total_failed", 0),
            "skipped": getattr(stats, "total_skipped", 0),
            "pbl_groups": getattr(stats, "pbl_files", {}),
        } if stats else {},
        "objects": objects,
    }

    manifest_path = out / "export-manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[manifest] Written: {manifest_path}")


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
