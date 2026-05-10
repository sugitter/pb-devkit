"""PowerBuilder PBL binary format parser (PB5-PB12+).

Backward-compatible facade that delegates to ChunkEngine for the actual
NOD*/ENT* parsing.  This module preserves every public API that existed in
v1.3 so that existing code (CLI commands, tests, external callers) keeps
working unchanged.

Improvements in this version (via ChunkEngine):
- Complete ENT* comment field parsing (v1.3 always returned "")
- Arbitrary ENT* version strings (not limited to "0500"/"0600")
- PB version detection
- Memory mode for embedded PBD streams (PEExtractor Phase 2)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Optional

from .chunk_engine import (
    BLOCK_SIZE as BLOCK,
    BLOCK_SIZE_UNICODE as BLOCK_UNICODE,
    COMPILED_EXT_SET,
    KW_TYPE,
    NODE_BLOCK_SIZE,
    OBJ_EXT,
    PBEntry,
    PBObjectType,
    SOURCE_EXT_MAP,
    ChunkEngine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backward-compatible aliases (used by tests and external code)
# ---------------------------------------------------------------------------
HEADER_SIZE_PB_OLD = BLOCK          # 512, ANSI PB5-PB9
HEADER_SIZE_PB_NEW = BLOCK_UNICODE  # 1024, Unicode PB10+

# Re-export OBJ_EXT / KW_TYPE so old imports still work
# (they are already imported from chunk_engine above)


# ---------------------------------------------------------------------------
# PBLEntry — thin wrapper around PBEntry for backward compatibility
# ---------------------------------------------------------------------------
@dataclass
class PBLEntry:
    """PBL entry metadata.  Delegates most logic to the shared PBEntry."""

    name: str
    object_type: PBObjectType
    comment: str = ""
    first_data_offset: int = 0
    data_size: int = 0
    creation_time: datetime = field(
        default_factory=lambda: datetime(2000, 1, 1, tzinfo=timezone.utc)
    )
    compile_time: datetime = field(
        default_factory=lambda: datetime(2000, 1, 1, tzinfo=timezone.utc)
    )

    # -- properties identical to PBEntry -----------------------------------

    @property
    def extension(self) -> str:
        """Get file extension.

        For PB12+ Unicode PBLs, the name already includes the extension.
        Compiled formats (.win, .dwo, .prp) return '.bin' so source_only
        filtering works.
        """
        dot = self.name.rfind(".")
        if dot > 0:
            ext = self.name[dot:].lower()
            if ext in (
                ".srw", ".srd", ".srm", ".srf", ".srs", ".sru", ".srq",
                ".srp", ".srj", ".srx", ".sre", ".sra", ".src",
            ):
                return ext
            if ext in (".win", ".dwo", ".prp", ".udo", ".fun", ".str",
                       ".apl", ".men", ".pra"):
                return ".bin"
        return OBJ_EXT.get(self.object_type, ".bin")

    @property
    def type_name(self) -> str:
        for n, c in KW_TYPE.items():
            if c == self.object_type:
                return n.title()
        return "Unknown"

    @property
    def base_name(self) -> str:
        """Object name without extension."""
        dot = self.name.rfind(".")
        return self.name[:dot] if dot > 0 else self.name

    # -- conversion helpers ------------------------------------------------

    @classmethod
    def from_pb_entry(cls, e: PBEntry) -> PBLEntry:
        """Create a PBLEntry from a ChunkEngine PBEntry."""
        ct = e.creation_time or datetime(2000, 1, 1, tzinfo=timezone.utc)
        return cls(
            name=e.name,
            object_type=e.object_type,
            comment=e.comment,
            first_data_offset=e.first_data_offset,
            data_size=e.data_size,
            creation_time=ct,
        )


# ---------------------------------------------------------------------------
# PBLSource — unchanged
# ---------------------------------------------------------------------------
@dataclass
class PBLSource:
    entry: PBLEntry
    source: bytes
    filename: str = ""

    @property
    def source_text(self) -> str:
        """Decode source bytes to text, auto-detecting encoding.

        PB PBL files store source data in different encodings depending on version:
        - PB5-PB9 (ANSI): Windows-1252 / ASCII
        - PB10-PB11 (Unicode header, but data may still be ANSI): UTF-8
        - PB12+ (Unicode): DAT* blocks store source as **UTF-16LE**

        Detection heuristic for UTF-16LE:
        1. Bytes at positions 1, 3, 5 are all 0x00
        2. First byte is a printable ASCII character
        3. Decoded text contains PB source markers ($PBExportHeader$, global type, etc.)
        """
        src = self.source
        if len(src) < 4:
            return src.decode("latin-1", errors="replace")

        # Detect UTF-16LE: check for alternating null bytes (BOM-less)
        # PB12+ stores all DAT* source data as UTF-16LE without BOM
        if src[1] == 0 and src[3] == 0 and 0x20 <= src[0] <= 0x7e:
            try:
                sample = src[:512].decode("utf-16-le", errors="strict")
                sl = sample.lower()
                if any(kw in sl for kw in (
                    "$pbexportheader$", "export by", "global type",
                    "forward", "forward prototypes", "type ",
                    "end type", "function ", "event ", "subroutine ",
                    "on ", "string ", "long ", "integer ",
                )):
                    return src.decode("utf-16-le", errors="replace")
            except (UnicodeDecodeError, ValueError):
                pass

        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return src.decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
        return src.decode("latin-1", errors="replace")

    def to_utf8_bytes(self) -> bytes:
        """Convert source to UTF-8 bytes, handling UTF-16LE PBL data."""
        text = self.source_text
        result = text.encode("utf-8")
        if b"\x00" in result:
            return self.source
        return result


# ---------------------------------------------------------------------------
# PBLParser — backward-compatible facade over ChunkEngine
# ---------------------------------------------------------------------------
class PBLParser:
    """Parse PowerBuilder PBL library files.

    Delegates all chunk-level parsing to ChunkEngine.  The public API
    (entries, open/close, export_*, list_entries, get_entry, …) is 100 %
    backward-compatible with v1.3.

    New behaviour (via ChunkEngine):
    - ``comment`` field is now populated from ENT* comment data
    - ENT* version strings are no longer limited to "0500"/"0600"
    - ``pb_version`` property exposes detected PB version number
    """

    def __init__(self, fp: str | Path, strict: bool = False):
        self.fp = Path(fp)
        self.strict = strict
        self._engine: Optional[ChunkEngine] = None
        self.entries: list[PBLEntry] = []
        self._is_unicode = False
        self._header_size = 0

    # -- lifecycle ---------------------------------------------------------

    def open(self):
        self._engine = ChunkEngine(path=self.fp)
        self._engine.open()
        self._is_unicode = self._engine.is_unicode
        self._header_size = self._engine.header_size
        # Convert PBEntry list to PBLEntry list
        self.entries = [PBLEntry.from_pb_entry(e) for e in self._engine.entries]
        logger.debug("Parsed %d entries from %s (unicode=%s)",
                     len(self.entries), self.fp, self._is_unicode)
        return self

    def close(self):
        if self._engine:
            self._engine.close()
            self._engine = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    # -- new properties ----------------------------------------------------

    @property
    def pb_version(self) -> int:
        """Detected PB version number (e.g. 500, 600).  0 if unknown."""
        return self._engine.pb_version if self._engine else 0

    # -- low-level (kept for any code that references _read / _fh) ----------

    def _read(self, off, sz):
        if self._engine and self._engine._stream:
            self._engine._stream.seek(off)
            return self._engine._stream.read(sz)
        raise RuntimeError("Engine not open")

    # -- type detection (kept for backward compat; ChunkEngine does this) --

    def _detect_type_from_name_ext(self, name: str, comment: str) -> PBObjectType:
        """Detect object type from extension in name (PB12+ Unicode PBLs)."""
        nl = name.lower()
        for ext, otype in SOURCE_EXT_MAP.items():
            if nl.endswith(ext):
                return PBObjectType(otype)
        for ext in COMPILED_EXT_SET:
            if nl.endswith(ext):
                return PBObjectType.BINARY
        return self._detect_type(name, comment)

    def _detect_type(self, name: str, comment: str) -> PBObjectType:
        """Detect object type from comment keyword or naming convention."""
        if comment:
            cl = comment.lower()
            for kw, tc in KW_TYPE.items():
                if kw in cl:
                    return PBObjectType(tc)
        nl = name.lower()
        if nl.startswith("d_"):
            return PBObjectType.DATAWINDOW
        if nl.startswith("w_"):
            return PBObjectType.WINDOW
        if nl.startswith("m_"):
            return PBObjectType.MENU
        if nl.startswith("n_") or nl.startswith("u_"):
            return PBObjectType.USEROBJECT
        if nl.startswith("f_") or nl.startswith("gf_"):
            return PBObjectType.FUNCTION
        if nl.startswith("s_"):
            return PBObjectType.STRUCTURE
        if nl.startswith("p_") and comment and "project" in comment.lower():
            return PBObjectType.PROJECT
        if nl in ("dgsauna", "dgapp", "app_dgsauna"):
            return PBObjectType.APPLICATION
        return PBObjectType.BINARY

    # -- export methods (delegate to ChunkEngine.read_data_chain) ----------

    def export_source(self, entry: PBLEntry, max_size: int = 10_000_000) -> Optional[bytes]:
        """Extract source data for an entry by following the DAT* block chain."""
        if not self._engine:
            return None
        return self._engine.read_data_chain(
            entry.first_data_offset,
            min(entry.data_size, max_size) if entry.data_size > 0 else max_size,
        )

    def export_all(self):
        res = []
        for e in self.entries:
            s = self.export_source(e)
            if s:
                fname = e.name if "." in e.name else e.name + e.extension
                res.append(PBLSource(entry=e, source=s, filename=fname))
        return res

    def export_to_directory(self, out, source_only=True, by_type=False):
        """Export source files to directory.

        Args:
            out: Output directory path.
            source_only: If True, skip compiled binary entries.
            by_type: If True, organize into subdirectories by object type.
        """
        op = Path(out)
        op.mkdir(parents=True, exist_ok=True)
        exp = []
        for ps in self.export_all():
            if source_only and ps.entry.extension == ".bin":
                continue
            if by_type:
                subdir = self._type_subdir(ps.entry.object_type)
                fp = op / subdir / ps.filename
            else:
                fp = op / ps.filename
            fp.parent.mkdir(parents=True, exist_ok=True)
            data = ps.to_utf8_bytes()
            data = data.replace(b"\x00", b"")
            if not data or len(data) < 10:
                continue
            fp.write_bytes(data)
            exp.append(str(fp))
        return exp

    @staticmethod
    def _type_subdir(obj_type: PBObjectType) -> str:
        """Map PBObjectType to subdirectory name for by_type export."""
        return {
            PBObjectType.APPLICATION: "application",
            PBObjectType.DATAWINDOW: "datawindow",
            PBObjectType.WINDOW: "window",
            PBObjectType.MENU: "menu",
            PBObjectType.FUNCTION: "function",
            PBObjectType.STRUCTURE: "structure",
            PBObjectType.USEROBJECT: "userobject",
            PBObjectType.QUERY: "query",
            PBObjectType.PIPELINE: "pipeline",
            PBObjectType.PROJECT: "project",
            PBObjectType.PROXY: "proxy",
            PBObjectType.EMBEDDED_SQL: "embedded_sql",
            PBObjectType.WEB_SERVICE: "webservice",
            PBObjectType.COMPONENT: "component",
            PBObjectType.BINARY: "binary",
        }.get(obj_type, "other")

    # -- query methods -----------------------------------------------------

    def list_entries(self) -> list[dict]:
        return [
            {
                "name": e.name,
                "type": e.type_name,
                "type_code": int(e.object_type),
                "extension": e.extension,
                "size": e.data_size,
                "comment": e.comment,
                "created": e.creation_time.isoformat() if e.creation_time else "",
            }
            for e in self.entries
        ]

    def get_entry(self, name: str) -> Optional[PBLEntry]:
        """Find an entry by name (case-insensitive)."""
        nl = name.lower()
        for e in self.entries:
            if e.name.lower() == nl:
                return e
        return None

    def get_entries_by_type(self, obj_type: PBObjectType) -> list[PBLEntry]:
        """Get all entries of a specific type."""
        return [e for e in self.entries if e.object_type == obj_type]

    def export_single(self, name: str) -> Optional[PBLSource]:
        """Export a single entry by name (with or without extension)."""
        entry = self.get_entry(name)
        if not entry:
            return None
        src = self.export_source(entry)
        if not src:
            return None
        fname = entry.name if "." in entry.name else entry.name + entry.extension
        return PBLSource(entry=entry, source=src, filename=fname)


# ---------------------------------------------------------------------------
# PBLBatchExporter — unchanged
# ---------------------------------------------------------------------------
class PBLBatchExporter:
    def __init__(self, proj, out):
        self.proj = Path(proj)
        self.out = Path(out)

    def find_pbls(self, recursive=True):
        return sorted(self.proj.glob("**/*.pbl") if recursive else "*.pbl")

    def export_all(self, recursive=True, by_type=False):
        res = {}
        pbls = self.find_pbls(recursive)
        for p in pbls:
            sub = self.out / p.stem
            try:
                with PBLParser(p) as pr:
                    res[str(p)] = pr.export_to_directory(sub, by_type=by_type)
            except Exception as e:
                res[str(p)] = [f"ERROR: {e}"]
        return res
