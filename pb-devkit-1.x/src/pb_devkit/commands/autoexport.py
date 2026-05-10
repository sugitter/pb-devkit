"""pb autoexport command - Smart auto-detect + full export to src/ directory.

Detects the project type from a directory and automatically chooses the
correct export strategy:

  PBL_PROJECT:    Export all .pbl files to src/<pbl_name>/ directories
  BINARY_PROJECT: Decompile EXE/PBD to src/ with PBL tree inference
  MIXED_PROJECT:  Export PBL source files + decompile any EXE/PBD alongside

Output structure:
  src/
    <pbl_name>.pbl/     (for PBL and MIXED)
      w_main.srw
      d_order.srd
      ...
    <pbl_name>.pbl/
      ...
    README.md           (auto-generated)

Usage:
    python pb.py autoexport <project_dir>
    python pb.py autoexport <project_dir> -o ./src
    python pb.py autoexport <project_dir> --quick     # Skip deep PE scan
    python pb.py autoexport <project_dir> --detect    # Detect only, no export
    python pb.py autoexport <project_dir> --force     # Overwrite existing src/
"""
import argparse
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "autoexport",
        help="Auto-detect project type and export all sources to src/",
        description=(
            "Automatically detect whether the project is PBL source, "
            "compiled EXE/PBD, or mixed — then export everything to a "
            "structured src/ directory."
        ),
    )
    p.add_argument(
        "target",
        help="Project directory (containing .pbl, .exe, .pbd, .dll files)",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        metavar="DIR",
        help="Output directory (default: <target>/src)",
    )
    p.add_argument(
        "--detect",
        action="store_true",
        help="Detect project type only — do not export",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="Skip deep PE binary scan (faster, may miss embedded PBD in EXE/DLL)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output directory without prompting",
    )
    p.add_argument(
        "--no-readme",
        action="store_true",
        help="Do not generate README.md in output directory",
    )
    p.add_argument(
        "--suffix",
        default=".ps",
        help="File suffix for exported entries (default: .ps)",
    )
    p.add_argument(
        "--by-type",
        action="store_true",
        help="For PBL projects: organize files by object type instead of PBL grouping",
    )
    p.add_argument(
        "--project-name",
        default=None,
        metavar="NAME",
        help="Override project name for PBL tree inference",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output detection result as JSON",
    )
    return p


def run(args):
    """Auto-detect project type and export all sources."""
    import json as _json
    from pb_devkit.project_detector import detect_project, ProjectType

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"[error] Not a directory: {target}", file=sys.stderr)
        sys.exit(1)

    # --- Step 1: Detect ---
    print(f"\n{'='*60}")
    print(f"  pb autoexport — Smart Project Export")
    print(f"{'='*60}")
    print(f"\n[1/3] Scanning project: {target}")

    info = detect_project(target, quick=args.quick)

    # Print detection summary
    print(f"\n  {info.summary()}")

    if args.json:
        result = {
            "project_type": info.project_type.value,
            "project_name": info.project_name,
            "pb_version": info.pb_version,
            "pbl_files": [str(p) for p in info.pbl_files],
            "pbl_unreadable": [str(p) for p in info.pbl_unreadable],
            "exe_files": [str(p) for p in info.exe_files],
            "pbd_files": [str(p) for p in info.pbd_files],
            "dll_files": [str(p) for p in info.dll_files],
            "embedded_pbd_exes": [str(p) for p in info.embedded_pbd_exes],
            "embedded_pbd_dlls": [str(p) for p in info.embedded_pbd_dlls],
        }
        print(_json.dumps(result, indent=2, ensure_ascii=False))

    if args.detect:
        print(f"\n[detect-only] Done.")
        return

    if info.project_type == ProjectType.UNKNOWN:
        print(f"\n[error] No recognizable PB files found in: {target}", file=sys.stderr)
        print(f"  Expected: .pbl, .exe (with embedded PBD), or .pbd files", file=sys.stderr)
        sys.exit(1)

    # --- Step 2: Determine output directory ---
    if args.output:
        out_dir = Path(args.output).resolve()
    else:
        out_dir = target / "src"

    # Check if output exists
    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.force:
            print(f"\n[warn] Output directory already exists: {out_dir}")
            print(f"  Use --force to overwrite, or specify a different -o path.")
            sys.exit(1)
        else:
            print(f"\n[warn] Overwriting existing output: {out_dir}")

    project_name = args.project_name or info.project_name

    # --- Step 3: Export ---
    print(f"\n[2/3] Exporting [{info.project_type.value.upper()}] → {out_dir}")

    total_exported = 0
    total_failed = 0

    if info.project_type == ProjectType.PBL_PROJECT:
        total_exported, total_failed = _export_pbl_project(
            info, out_dir, project_name, args
        )

    elif info.project_type == ProjectType.BINARY_PROJECT:
        total_exported, total_failed = _export_binary_project(
            info, out_dir, project_name, args
        )

    elif info.project_type == ProjectType.MIXED_PROJECT:
        total_exported, total_failed = _export_mixed_project(
            info, out_dir, project_name, args
        )

    # --- Step 3.5: Extract resources ---
    res_count = _extract_all_resources(info, out_dir)
    if res_count > 0:
        total_exported += res_count
        print(f"\n  Resources extracted: {res_count} files → {out_dir / 'resources'}")

    # --- Summary ---
    print(f"\n[3/3] Complete")
    print(f"{'='*60}")
    print(f"  Project type:  {info.project_type.value.upper()}")
    print(f"  Project name:  {project_name}")
    print(f"  Output:        {out_dir}")
    print(f"  Exported:      {total_exported} files")
    if total_failed:
        print(f"  Failed:        {total_failed} entries")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Export strategies
# ---------------------------------------------------------------------------

def _extract_all_resources(info, out_dir: Path) -> int:
    """Extract binary resources (images, icons) from all EXE/PBD/PBL files.

    Returns the number of resource files extracted.
    """
    from pb_devkit.decompiler import extract_resources, is_resource_entry, list_resource_entries

    # Collect all binary files that may contain resources
    binary_files = []
    for p in info.embedded_pbd_exes:
        binary_files.append(p)
    for p in info.pbd_files:
        binary_files.append(p)
    for p in info.embedded_pbd_dlls:
        binary_files.append(p)
    # Also check PBL files
    for p in info.pbl_files:
        binary_files.append(p)

    if not binary_files:
        return 0

    res_dir = out_dir / "resources"
    total = 0

    for fpath in sorted(binary_files):
        try:
            # First check if the file has any resource entries
            res_list = list_resource_entries(str(fpath))
            if not res_list:
                continue
            # Extract
            results = extract_resources(str(fpath), str(res_dir))
            ok = sum(1 for r in results if r.success)
            total += ok
            if ok:
                print(f"\n  Resources from {fpath.name}: {ok} files")
        except Exception:
            pass  # Silently skip files that don't support resource extraction

    return total


def _export_pbl_project(info, out_dir: Path, project_name: str, args) -> tuple:
    """Export a PBL source project.

    Two modes:
      - Default: organize into PBL-named subdirectories (preserving PBL structure)
      - --by-type: flat export organized by object type
    """
    total = 0
    failed = 0

    if args.by_type:
        # Flat export organized by object type
        from pb_devkit.pbl_parser import PBLParser
        for pbl_path in sorted(info.pbl_files):
            print(f"\n  Exporting {pbl_path.name} ...")
            try:
                with PBLParser(pbl_path) as parser:
                    exported = parser.export_to_directory(
                        str(out_dir / pbl_path.stem), by_type=True
                    )
                    total += len(exported)
                    print(f"    -> {len(exported)} objects")
            except Exception as e:
                print(f"    -> ERROR: {e}", file=sys.stderr)
                failed += 1
    else:
        # PBL-tree mode: each PBL gets its own subdirectory
        from pb_devkit.pbl_parser import PBLParser
        for pbl_path in sorted(info.pbl_files):
            pbl_out = out_dir / pbl_path.stem
            print(f"\n  Exporting {pbl_path.name} → {pbl_out.name}/")
            try:
                with PBLParser(pbl_path) as parser:
                    exported = parser.export_to_directory(str(pbl_out))
                    total += len(exported)
                    print(f"    -> {len(exported)} objects")
            except Exception as e:
                print(f"    -> ERROR: {e}", file=sys.stderr)
                failed += 1

        if not args.no_readme:
            _write_pbl_project_readme(out_dir, info, project_name, total)

    return total, failed


def _export_binary_project(info, out_dir: Path, project_name: str, args) -> tuple:
    """Export a binary project (EXE/PBD with embedded or standalone PBD).

    Strategy:
      1. EXEs with embedded PBD: decompile via pbl_grouper.export_pbl_tree
      2. Standalone PBD files: decompile via pbl_grouper.export_pbl_tree
    """
    from pb_devkit.pbl_grouper import export_pbl_tree

    total = 0
    failed = 0

    # EXEs with embedded PBD (main source of code)
    for exe_path in sorted(info.embedded_pbd_exes):
        exe_out = out_dir  # All go to same output for main EXE
        print(f"\n  Decompiling {exe_path.name} (embedded PBD) → {exe_out}")
        try:
            stats = export_pbl_tree(
                file_path=str(exe_path),
                output_dir=str(exe_out),
                project_name=project_name,
                suffix=args.suffix,
                clean=False,             # Don't clean; may have multiple EXEs
                generate_readme=not args.no_readme,
            )
            total += stats.total_saved
            failed += stats.total_failed
        except Exception as e:
            print(f"    -> ERROR: {e}", file=sys.stderr)
            failed += 1

    # Standalone PBD files
    for pbd_path in sorted(info.pbd_files):
        pbd_out = out_dir / pbd_path.stem
        print(f"\n  Decompiling {pbd_path.name} (standalone PBD) → {pbd_out.name}/")
        try:
            stats = export_pbl_tree(
                file_path=str(pbd_path),
                output_dir=str(pbd_out),
                project_name=pbd_path.stem,
                suffix=args.suffix,
                clean=False,
                generate_readme=False,
            )
            total += stats.total_saved
            failed += stats.total_failed
        except Exception as e:
            print(f"    -> ERROR: {e}", file=sys.stderr)
            failed += 1

    # DLLs with embedded PBD
    for dll_path in sorted(info.embedded_pbd_dlls):
        dll_out = out_dir / dll_path.stem
        print(f"\n  Decompiling {dll_path.name} (DLL with embedded PBD) → {dll_out.name}/")
        try:
            stats = export_pbl_tree(
                file_path=str(dll_path),
                output_dir=str(dll_out),
                project_name=dll_path.stem,
                suffix=args.suffix,
                clean=False,
                generate_readme=False,
            )
            total += stats.total_saved
            failed += stats.total_failed
        except Exception as e:
            print(f"    -> ERROR: {e}", file=sys.stderr)
            failed += 1

    if not args.no_readme and total > 0:
        _write_binary_project_readme(out_dir, info, project_name, total)

    return total, failed


def _write_binary_project_readme(out_dir: Path, info, project_name: str, total: int):
    """Write README.md for binary project export (EXE/PBD/DLL decompiled)."""
    from datetime import datetime

    # Collect all binary sources
    sources = []
    for exe in info.embedded_pbd_exes:
        sources.append(f"{exe.name} (EXE, 内嵌 PBD)")
    for pbd in info.pbd_files:
        sources.append(f"{pbd.name} (独立 PBD)")
    for dll in info.embedded_pbd_dlls:
        sources.append(f"{dll.name} (DLL, 内嵌 PBD)")

    lines = [
        f"# {project_name} — 项目源码目录",
        "",
        f"> 从 {len(sources)} 个文件梳理导出，共 {total} 个文件",
        f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 源文件",
        "",
    ]
    for src in sources:
        lines.append(f"- `{src}`")
    lines.extend([
        "",
        "## 说明",
        "",
        "- 从编译后的 EXE/PBD/DLL 梳理导出的 PowerScript 源码",
        "- 子目录 `*.pbl/` 为按命名惯例推断的 PBL 分组（非原始 PBL 文件）",
        "- `resources/` 目录包含项目中的图标、图片等资源文件",
        "- 文件后缀默认 `.ps`（可用 `--suffix` 自定义）",
        "- **工具**: pb-devkit (`pb autoexport`)",
    ])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _export_mixed_project(info, out_dir: Path, project_name: str, args) -> tuple:
    """Export a mixed project (PBL sources + compiled binaries).

    Strategy:
      - Export PBL source files first (primary source of truth)
      - Then decompile any EXE/PBD that has content NOT already in PBL sources
        (placed in a separate decompiled/ subdirectory)
    """
    total = 0
    failed = 0

    # 1. Export PBL source (primary)
    print(f"\n  [Phase 1/2] Exporting PBL source files ...")
    t, f = _export_pbl_project(info, out_dir, project_name, args)
    total += t
    failed += f

    # 2. Decompile binaries into a "decompiled" subdirectory for reference
    has_binaries = (info.embedded_pbd_exes or info.pbd_files
                    or info.embedded_pbd_dlls)
    if has_binaries:
        decompiled_out = out_dir / "_decompiled"
        print(f"\n  [Phase 2/2] Decompiling binaries → {decompiled_out.name}/")
        print(f"    (supplementary reference; PBL sources are authoritative)")

        # Create a temporary info with only binary paths
        from pb_devkit.project_detector import ProjectInfo, ProjectType
        bin_info = ProjectInfo(root=info.root)
        bin_info.exe_files = info.exe_files
        bin_info.pbd_files = info.pbd_files
        bin_info.dll_files = info.dll_files
        bin_info.embedded_pbd_exes = info.embedded_pbd_exes
        bin_info.embedded_pbd_dlls = info.embedded_pbd_dlls
        bin_info.project_type = ProjectType.BINARY_PROJECT

        t, f = _export_binary_project(bin_info, decompiled_out, project_name, args)
        total += t
        failed += f

    if not args.no_readme:
        _write_mixed_project_readme(out_dir, info, project_name, total)

    return total, failed


# ---------------------------------------------------------------------------
# README generators
# ---------------------------------------------------------------------------

def _write_pbl_project_readme(out_dir: Path, info, project_name: str, total: int):
    """Write README.md for PBL project export."""
    from datetime import datetime
    lines = [
        f"# {project_name} — 源码目录",
        "",
        f"> 从 {len(info.pbl_files)} 个 PBL 文件导出，共 {total} 个源码文件",
        f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 目录结构",
        "",
        "```",
        "src/",
    ]
    for pbl in sorted(info.pbl_files):
        lines.append(f"  {pbl.stem}/     # 从 {pbl.name} 导出")
    lines.extend([
        "  README.md",
        "```",
        "",
        "## 说明",
        "",
        "- 每个子目录对应一个原始 PBL 文件",
        "- 文件后缀: `.srw` = 窗口, `.srd` = 数据窗口, `.srm` = 菜单, "
        "`.srf` = 函数, `.srs` = 结构体, `.sru` = 用户对象",
        "- `resources/` 目录包含项目中的图标、图片等资源文件",
        "- **工具**: pb-devkit (`pb autoexport`)",
    ])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _write_mixed_project_readme(out_dir: Path, info, project_name: str, total: int):
    """Write README.md for mixed project export."""
    from datetime import datetime
    lines = [
        f"# {project_name} — 源码目录（混合模式）",
        "",
        f"> PBL 源码 + 梳理导出二进制，共导出 {total} 个文件",
        f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 说明",
        "",
        "- **PBL 源码目录**（子目录名 = PBL 文件名）: 以源码 PBL 为权威来源",
        "- **`_decompiled/`**: 从 EXE/PBD 梳理导出的源码（仅供参考）",
        "- **工具**: pb-devkit (`pb autoexport`)",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
