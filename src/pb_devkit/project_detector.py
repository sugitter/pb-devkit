"""PB Project Detector - Auto-detect PowerBuilder project type.

Three project types:
  1. PBL_PROJECT   - Source project with .pbl files (PBL binary libraries)
  2. BINARY_PROJECT - Deployment package with .exe + .pbd/.dll (compiled only)
  3. MIXED_PROJECT  - EXE with embedded PBD(s) or combination of both

Detection logic:
  - Scan directory for .pbl, .exe, .pbd, .dll files
  - Try to validate PBL files (HDR* signature check)
  - Try to validate EXE/DLL as PE files with embedded PBD resources
  - Mixed = has both valid PBL sources AND compiled EXE/PBD

Usage:
    from pb_devkit.project_detector import detect_project, ProjectType, ProjectInfo

    info = detect_project("/path/to/project")
    print(info.project_type)   # ProjectType.PBL_PROJECT
    print(info.pbl_files)      # list of .pbl paths
    print(info.exe_files)      # list of .exe paths
    print(info.pbd_files)      # list of standalone .pbd paths
    print(info.embedded_pbd_exes) # list of EXE paths that contain embedded PBDs
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ProjectType
# ---------------------------------------------------------------------------

class ProjectType(Enum):
    PBL_PROJECT    = "pbl"      # Source-based: has .pbl files with readable content
    BINARY_PROJECT = "binary"   # Deployment: EXE + standalone PBD/DLL (no PBL source)
    MIXED_PROJECT  = "mixed"    # Has both: EXE/PBD alongside PBL source files
    UNKNOWN        = "unknown"  # Nothing recognizable found


# ---------------------------------------------------------------------------
# ProjectInfo
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    """Result of project detection."""
    root: Path
    project_type: ProjectType = ProjectType.UNKNOWN

    # Source artifacts
    pbl_files: List[Path] = field(default_factory=list)       # Readable .pbl files
    pbl_unreadable: List[Path] = field(default_factory=list)   # .pbl present but HDR* invalid

    # Binary artifacts
    exe_files: List[Path] = field(default_factory=list)        # .exe files found
    pbd_files: List[Path] = field(default_factory=list)        # Standalone .pbd files
    dll_files: List[Path] = field(default_factory=list)        # .dll files with PBD inside

    # Derived: which EXEs have embedded PBD resources
    embedded_pbd_exes: List[Path] = field(default_factory=list)
    embedded_pbd_dlls: List[Path] = field(default_factory=list)

    # Project metadata
    project_name: Optional[str] = None      # Auto-guessed from main EXE or directory
    pb_version: Optional[str] = None        # Detected PB version string (e.g. "0900")
    workspace_file: Optional[Path] = None   # .pbw if found
    app_target_file: Optional[Path] = None  # .pbt if found

    @property
    def has_pbl_source(self) -> bool:
        return len(self.pbl_files) > 0

    @property
    def has_binary(self) -> bool:
        return (len(self.exe_files) > 0 or len(self.pbd_files) > 0
                or len(self.embedded_pbd_exes) > 0)

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Project: {self.root}",
            f"Type:    {self.project_type.value.upper()}",
        ]
        if self.project_name:
            lines.append(f"Name:    {self.project_name}")
        if self.pbl_files:
            lines.append(f"PBL:     {len(self.pbl_files)} files")
            for p in self.pbl_files[:5]:
                lines.append(f"           {p.name}")
            if len(self.pbl_files) > 5:
                lines.append(f"           ... +{len(self.pbl_files) - 5} more")
        if self.pbl_unreadable:
            lines.append(f"PBL (unreadable): {len(self.pbl_unreadable)} files")
        if self.exe_files:
            lines.append(f"EXE:     {len(self.exe_files)} files")
            for p in self.exe_files[:3]:
                emb = " [embedded PBD]" if p in self.embedded_pbd_exes else ""
                lines.append(f"           {p.name}{emb}")
        if self.pbd_files:
            lines.append(f"PBD:     {len(self.pbd_files)} standalone files")
        if self.dll_files:
            lines.append(f"DLL:     {len(self.dll_files)} files with embedded PBD")
        if self.workspace_file:
            lines.append(f"Workspace: {self.workspace_file.name}")
        if self.app_target_file:
            lines.append(f"Target:  {self.app_target_file.name}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_hdr_signature(path: Path) -> bool:
    """Quick check: first 4 bytes == HDR*"""
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
        return sig == b"HDR*"
    except (OSError, IOError):
        return False


def _is_pe_file(path: Path) -> bool:
    """Quick check: first 2 bytes == MZ"""
    try:
        with open(path, "rb") as f:
            sig = f.read(2)
        return sig == b"MZ"
    except (OSError, IOError):
        return False


def _pe_has_embedded_pbd(path: Path) -> bool:
    """Check whether a PE EXE/DLL contains embedded PBD resources.

    Uses two strategies:
      1. PEExtractor resource scan (.rsrc section, HDR* signature)
      2. Scan for HDR* signature appended after PE sections
    """
    try:
        from .pe_extractor import PEExtractor
        ext = PEExtractor(path)
        # Try .rsrc scan first
        resources = ext.extract_pbd_resources()
        if resources:
            return True
        # Try appended PBD scan
        appended = ext.scan_appended_pbds()
        return len(appended) > 0
    except Exception as e:
        logger.debug("PE scan failed for %s: %s", path, e)
        return False


def _guess_project_name(info: ProjectInfo) -> str:
    """Guess the project name from available artifacts."""
    # Prefer main EXE with embedded PBD
    if info.embedded_pbd_exes:
        return info.embedded_pbd_exes[0].stem
    # Prefer standalone PBD
    if info.pbd_files:
        return info.pbd_files[0].stem
    # Prefer PBL file that looks like a main app (has 'app' or matches dir name)
    dir_name = info.root.name.lower()
    for pbl in info.pbl_files:
        if pbl.stem.lower() in ("app", dir_name):
            return pbl.stem
    # Use directory name
    return info.root.name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_project(
    directory: str | Path,
    max_scan_depth: int = 3,
    quick: bool = False,
) -> ProjectInfo:
    """Detect PowerBuilder project type from a directory.

    Args:
        directory: Directory to scan.
        max_scan_depth: Maximum directory depth to scan (default: 3).
        quick: If True, skip deep PE scan and rely on file extensions only.

    Returns:
        ProjectInfo with project type and file lists.
    """
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    info = ProjectInfo(root=root)

    # --- Collect candidate files ---
    all_files: List[Path] = []
    try:
        for p in root.rglob("*"):
            # Respect max_scan_depth
            try:
                rel = p.relative_to(root)
                depth = len(rel.parts)
            except ValueError:
                depth = 0
            if depth > max_scan_depth:
                continue
            if p.is_file():
                all_files.append(p)
    except PermissionError as e:
        logger.warning("Permission error scanning %s: %s", root, e)

    # --- Classify files ---
    pbt_files: List[Path] = []
    pbw_files: List[Path] = []

    for f in all_files:
        sfx = f.suffix.lower()
        if sfx == ".pbl":
            if _has_hdr_signature(f):
                info.pbl_files.append(f)
            else:
                info.pbl_unreadable.append(f)

        elif sfx == ".pbd":
            if _has_hdr_signature(f):
                info.pbd_files.append(f)

        elif sfx == ".exe":
            if _is_pe_file(f):
                info.exe_files.append(f)
                if not quick and _pe_has_embedded_pbd(f):
                    info.embedded_pbd_exes.append(f)

        elif sfx == ".dll":
            if _is_pe_file(f):
                info.dll_files.append(f)
                if not quick and _pe_has_embedded_pbd(f):
                    info.embedded_pbd_dlls.append(f)

        elif sfx == ".pbt":
            pbt_files.append(f)

        elif sfx == ".pbw":
            pbw_files.append(f)

    # Store workspace / target
    if pbw_files:
        info.workspace_file = pbw_files[0]
    if pbt_files:
        info.app_target_file = pbt_files[0]

    # --- Determine project type ---
    has_source = len(info.pbl_files) > 0
    has_binary = (
        len(info.exe_files) > 0
        or len(info.pbd_files) > 0
        or len(info.embedded_pbd_exes) > 0
        or len(info.embedded_pbd_dlls) > 0
    )

    if has_source and has_binary:
        info.project_type = ProjectType.MIXED_PROJECT
    elif has_source:
        info.project_type = ProjectType.PBL_PROJECT
    elif has_binary:
        info.project_type = ProjectType.BINARY_PROJECT
    else:
        info.project_type = ProjectType.UNKNOWN

    # --- Guess project name ---
    info.project_name = _guess_project_name(info)

    # --- Try to detect PB version from first PBL/PBD ---
    try:
        _detect_pb_version(info)
    except Exception as e:
        logger.debug("PB version detection failed: %s", e)

    logger.info(
        "detect_project: %s -> %s (pbl=%d, exe=%d, pbd=%d, emb_exe=%d)",
        root, info.project_type.value,
        len(info.pbl_files), len(info.exe_files),
        len(info.pbd_files), len(info.embedded_pbd_exes),
    )
    return info


def _detect_pb_version(info: ProjectInfo):
    """Try to detect PB version from first available binary."""
    candidate = None
    if info.pbl_files:
        candidate = info.pbl_files[0]
    elif info.pbd_files:
        candidate = info.pbd_files[0]

    if not candidate:
        return

    try:
        with open(candidate, "rb") as f:
            header = f.read(32)
        # HDR* + "PowerBuilder" at offset 4, then version bytes around 18-22
        if header[:4] == b"HDR*":
            ver_bytes = header[18:22]
            if ver_bytes.isdigit() or all(48 <= b <= 57 for b in ver_bytes):
                info.pb_version = ver_bytes.decode("ascii", errors="replace")
    except Exception:
        pass
