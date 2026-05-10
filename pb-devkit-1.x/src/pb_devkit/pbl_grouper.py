"""PBL Grouper - Infer PBL grouping for objects from EXE/PBD exports.

When an EXE is compiled with all PBLs embedded, the PBL structure is lost.
This module uses naming conventions to infer which original PBL each object
belonged to, then exports them organized by PBL directory.

Usage:
    from pb_devkit.pbl_grouper import export_pbl_tree, infer_pbl_groups

    # Export with inferred PBL grouping
    stats = export_pbl_tree("app.exe", "./src")

    # Just get the grouping map
    groups = infer_pbl_groups(entry_names, project_name="myapp")
"""

from __future__ import annotations

import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .decompiler import DecompileResult, decompile_file


# ---------------------------------------------------------------------------
# Object type detection by extension (from chunk_engine.py)
# ---------------------------------------------------------------------------
_SOURCE_EXTS = {
    ".srw": "window", ".srd": "datawindow", ".srm": "menu",
    ".srf": "function", ".srs": "structure", ".sru": "userobject",
    ".srq": "query", ".srp": "pipeline", ".srj": "project",
    ".srx": "proxy", ".sre": "embedded_sql", ".sra": "webservice",
    ".src": "component", ".pra": "project",
}
_COMPILED_EXTS = {
    ".win": "window", ".dwo": "datawindow", ".prp": "userobject",
    ".udo": "userobject", ".fun": "function", ".str": "structure",
    ".apl": "application", ".men": "menu",
}
_ALL_TYPE_MAP = {}
_ALL_TYPE_MAP.update(_SOURCE_EXTS)
_ALL_TYPE_MAP.update(_COMPILED_EXTS)

_IMAGE_EXTS = {".bmp", ".jpg", ".jpeg", ".gif", ".png", ".ico", ".cur", ".wmf"}


def _get_ext(name: str) -> str:
    """Extract lowercase extension from entry name."""
    dot = name.rfind(".")
    return name[dot:].lower() if dot > 0 else ""


def _get_base(name: str) -> str:
    """Extract base name without extension."""
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def _is_resource(name: str) -> bool:
    """Check if entry is a binary resource (image, etc.)."""
    ext = _get_ext(name)
    # Path-like entries (bmp\s1.gif) are resources
    if "\\" in name or "/" in name:
        return True
    return ext in _IMAGE_EXTS


# ---------------------------------------------------------------------------
# PBL Group Inference Rules
# ---------------------------------------------------------------------------

# Default PBL names
_PBL_APP = "app"
_PBL_FW = "framework"
_PBL_DW = "dw_{app}"
_PBL_COMMON = "common"
_PBL_FUN = "common_fun"
_PBL_SYS = "sys"


def _classify_by_convention(
    name: str,
    project_name: str,
    custom_rules: Optional[List[Tuple[str, str]]] = None,
) -> Optional[str]:
    """Classify an entry to a PBL by PB naming conventions.

    Returns PBL name (without .pbl suffix) or None to skip.

    Args:
        name: Entry name from PBD/PBL (e.g. "w_login.win", "d_orders.dwo")
        project_name: Base project name for PBL naming (e.g. "logistic")
        custom_rules: Optional list of (pattern, pbl_name) tuples.
                     pattern is matched as prefix against base name.
    """
    if _is_resource(name):
        return None

    ext = _get_ext(name)
    base = _get_base(name).lower()
    app = project_name.lower()

    # Application entry
    if ext == ".apl":
        return _PBL_APP
    # Special: ob.exe -> application index
    if name.lower() == "ob.exe":
        return _PBL_APP

    # --- Custom rules (highest priority) ---
    if custom_rules:
        for pattern, pbl_name in custom_rules:
            if base.startswith(pattern.lower()):
                return pbl_name

    # --- DataWindows: always go to dw_<app>.pbl ---
    if ext in (".dwo", ".srd"):
        return _PBL_DW.format(app=app)

    # --- Global functions: always go to common_fun.pbl ---
    if ext in (".fun", ".srf"):
        return _PBL_FUN

    # --- Menus: framework ---
    if ext in (".men", ".srm"):
        return _PBL_FW

    # --- Structures: common ---
    if ext in (".str", ".srs"):
        return _PBL_COMMON

    # --- Window classification ---
    if ext in (".win", ".srw"):
        # System management windows
        if any(base.startswith(p) for p in ("w_sys_", "w_users", "w_operator",
                                             "w_user_", "w_role_", "w_permission")):
            return _PBL_SYS

        # Framework windows (login, splash, about, MDI, password)
        fw_patterns = ("w_login", "w_splash", "w_about", "w_md", "w_password",
                       "w_change_pass", "w_main", "w_base", "w_frame",
                       "w_toolbar", "w_status")
        if any(base == p or base.startswith(p + "_") for p in fw_patterns):
            return _PBL_FW

        # Project-specific business windows (w_<app>_*)
        if base.startswith(f"w_{app}_"):
            return app

        # Shared business windows (w_orders, w_find_*, w_dw*, w_print*, w_report*)
        shared_prefixes = ("w_orders", "w_find", "w_list", "w_dw",
                           "w_print", "w_report", "w_tv_dw", "w_column_visible",
                           "w_input_", "w_select_", "w_select")
        if any(base == p or base.startswith(p + "_") or base.startswith(p) for p in shared_prefixes):
            return app

        # Other windows default to framework
        return _PBL_FW

    # --- User objects: common ---
    if ext in (".prp", ".udo", ".sru"):
        return _PBL_COMMON

    # --- Remaining types default to common ---
    if ext in (".srq", ".srp", ".srj", ".srx", ".sre", ".sra", ".src"):
        return _PBL_COMMON

    # Default: project main PBL
    return app


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class PBLGroupStats:
    """Statistics for a PBL group export."""
    total_saved: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    pbl_files: Dict[str, int] = field(default_factory=dict)


def infer_pbl_groups(
    entry_names: List[str],
    project_name: str = "app",
    custom_rules: Optional[List[Tuple[str, str]]] = None,
) -> Dict[str, List[str]]:
    """Infer PBL grouping from a list of entry names.

    Args:
        entry_names: List of entry names from PBD/PBL
        project_name: Base project name (used for PBL naming)
        custom_rules: Optional (pattern, pbl_name) tuples

    Returns:
        Dict mapping PBL name -> list of entry names
    """
    groups: Dict[str, List[str]] = defaultdict(list)
    for name in entry_names:
        pbl = _classify_by_convention(name, project_name, custom_rules)
        if pbl:
            groups[pbl].append(name)
    return dict(groups)


def export_pbl_tree(
    file_path: str,
    output_dir: str,
    project_name: Optional[str] = None,
    custom_rules: Optional[List[Tuple[str, str]]] = None,
    suffix: str = ".ps",
    clean: bool = True,
    generate_readme: bool = True,
) -> PBLGroupStats:
    """Export source from EXE/PBL/PBD organized by inferred PBL groups.

    Creates output structure:
        output_dir/
          <pbl_name_1>.pbl/
            obj1.ps
            obj2.ps
          <pbl_name_2>.pbl/
            ...
          README.md

    Args:
        file_path: Path to .exe, .pbl, .pbd, or .dll file (PB DLL mode)
        output_dir: Output directory path
        project_name: Base name for PBL inference (auto-detected from filename if None)
        custom_rules: Optional (pattern, pbl_name) tuples for custom classification
        suffix: Output file suffix (default: ".ps")
        clean: If True, clean output directory before export
        generate_readme: If True, generate README.md with structure summary

    Returns:
        PBLGroupStats with export statistics
    """
    from .pbl_parser import PBLParser

    file_path = str(file_path)
    out = Path(output_dir)
    fp = Path(file_path)

    # Auto-detect project name from filename
    if project_name is None:
        project_name = fp.stem  # e.g. "logistic" from "logistic.exe"

    # Clean output directory
    if clean and out.exists():
        shutil.rmtree(out)

    stats = PBLGroupStats()

    # Detect file type and decide export strategy
    suffix_lower = fp.suffix.lower()

    if suffix_lower in (".exe", ".pbd", ".dll"):
        # Use decompiler for EXE/PBD/DLL (binary -> PowerScript)
        # DLLs compiled from PBL (PowerBuilder DLL mode) embed PBD the same way EXEs do
        print(f"[*] Decompiling {file_path} ...")
        results: List[DecompileResult] = decompile_file(
            file_path, decompile_all=True
        )

        # Infer PBL for each result
        for r in results:
            if not r.success:
                stats.total_failed += 1
                continue
            if not r.source or not r.source.strip():
                stats.total_skipped += 1
                continue
            if _is_resource(r.entry_name):
                stats.total_skipped += 1
                continue

            pbl = _classify_by_convention(
                r.entry_name, project_name, custom_rules
            )
            if pbl is None:
                stats.total_skipped += 1
                continue

            # Write file
            pbl_dir = out / f"{pbl}.pbl"
            pbl_dir.mkdir(parents=True, exist_ok=True)
            base = _get_base(r.entry_name)
            out_name = base + suffix
            out_file = pbl_dir / out_name
            out_file.write_text(r.source, encoding="utf-8")
            stats.pbl_files[pbl] = stats.pbl_files.get(pbl, 0) + 1
            stats.total_saved += 1
            print(f"  {pbl}.pbl/{out_name}")

    elif suffix_lower == ".pbl":
        # Use PBLParser for .pbl files (export raw source)
        print(f"[*] Exporting {file_path} ...")
        with PBLParser(fp) as parser:
            for ps in parser.export_all():
                if ps.entry.extension == ".bin":
                    continue
                name = ps.entry.name
                pbl = _classify_by_convention(
                    name, project_name, custom_rules
                )
                if pbl is None:
                    stats.total_skipped += 1
                    continue

                pbl_dir = out / f"{pbl}.pbl"
                pbl_dir.mkdir(parents=True, exist_ok=True)
                out_file = pbl_dir / ps.filename
                data = ps.to_utf8_bytes().replace(b"\x00", b"")
                if not data or len(data) < 10:
                    stats.total_skipped += 1
                    continue
                out_file.write_bytes(data)
                stats.pbl_files[pbl] = stats.pbl_files.get(pbl, 0) + 1
                stats.total_saved += 1
                print(f"  {pbl}.pbl/{ps.filename}")
    else:
        print(f"[error] Unsupported file type: {suffix_lower}", file=__import__("sys").stderr)
        return stats

    # Print summary
    print(f"\n[*] Summary: {stats.total_saved} saved, "
          f"{stats.total_failed} failed, {stats.total_skipped} skipped")
    print(f"[*] Output: {out.resolve()}")
    print(f"[*] PBL breakdown:")
    for pbl in sorted(stats.pbl_files.keys()):
        print(f"    {pbl}.pbl/: {stats.pbl_files[pbl]} files")

    # Generate README
    if generate_readme and stats.total_saved > 0:
        _generate_readme(out, stats, project_name, file_path)

    return stats


def _generate_readme(out: Path, stats: PBLGroupStats,
                     project_name: str, source_file: str):
    """Generate README.md summarizing the PBL tree export."""
    total = sum(stats.pbl_files.values())
    lines = [
        f"# {project_name} - 源码目录（按 PBL 组织）",
        "",
        f"> 从 `{Path(source_file).name}` 导出，共 {total} 个源码文件",
        f'> 导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        "",
        "## 目录结构",
        "",
        "```",
        "src/",
    ]
    for pbl in sorted(stats.pbl_files.keys()):
        lines.append(f"  {pbl}.pbl/          # {stats.pbl_files[pbl]} 个文件")
    lines.extend([
        "  README.md     # 本文件",
        "```",
        "",
        "## PBL 说明",
        "",
        "| PBL | 文件数 | 推断用途 |",
        "|-----|--------|----------|",
    ])
    for pbl in sorted(stats.pbl_files.keys()):
        desc = _pbl_description(pbl, project_name)
        lines.append(f"| {pbl}.pbl/ | {stats.pbl_files[pbl]} | {desc} |")

    lines.extend([
        "",
        "## 备注",
        "",
        "- PBL 组织基于 PB 命名惯例自动推断",
        "- 文件后缀 `.ps` = PowerScript 源码",
        "- **工具**: pb-devkit (`pb export --pbl-tree`)",
        "",
    ])

    out.mkdir(parents=True, exist_ok=True)
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[*] Generated {out / 'README.md'}")


def _pbl_description(pbl: str, project_name: str) -> str:
    """Return a description for a PBL based on its name."""
    descs = {
        project_name: f"主业务模块（{project_name}）",
        f"dw_{project_name}": "数据窗口对象（DataWindow）",
        "framework": "框架层：应用入口、菜单、登录/启动窗口",
        "common": "公共库：工具对象、DW运行时、用户对象、结构体",
        "common_fun": "全局函数",
        "sys": "系统管理：用户/权限/基础数据管理",
        "app": "应用入口（Application 对象）",
    }
    return descs.get(pbl, "其他模块")


def export_multi_pbl_tree(
    pbl_dir: str,
    output_dir: str,
    by_type: bool = False,
) -> Dict[str, List[str]]:
    """Export multiple PBL files from a directory, preserving PBL structure.

    For directories with actual .pbl files (non-embedded mode), this exports
    each PBL into its own subdirectory, preserving the original organization.

    Args:
        pbl_dir: Directory containing .pbl files
        output_dir: Output directory
        by_type: If True, further organize by object type within each PBL

    Returns:
        Dict mapping PBL name -> list of exported file paths
    """
    from .pbl_parser import PBLParser

    proj = Path(pbl_dir)
    out = Path(output_dir)
    results = {}
    pbls = sorted(proj.glob("**/*.pbl"))

    if not pbls:
        print(f"[warn] No .pbl files found in {pbl_dir}")
        return results

    print(f"[*] Found {len(pbls)} PBL files")

    for pbl_path in pbls:
        print(f"  Exporting: {pbl_path.name}")
        sub = out / pbl_path.stem
        try:
            with PBLParser(pbl_path) as parser:
                exported = parser.export_to_directory(sub, by_type=by_type)
            results[pbl_path.stem] = exported
            print(f"    -> {len(exported)} objects")
        except Exception as e:
            print(f"    -> ERROR: {e}")
            results[pbl_path.stem] = []

    total = sum(len(v) for v in results.values())
    print(f"\n[*] Total: {total} objects from {len(results)} PBLs")
    return results
