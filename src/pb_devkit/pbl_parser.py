"""PowerBuilder PBL binary format parser (PB4-PB12+).

PBL structure: HDR*(512/1024b) -> FRE*(512b) -> NOD*(3072b, B-Tree) -> ENT* -> DAT*(512b chain)

Format details:
- HDR*: Library header (512b for PB4-PB10, 1024b for PB11+)
- FRE*: Free space bitmap (512b blocks)
- NOD*: B-Tree index nodes (6x512b = 3072b per node group)
- DAT*: Data blocks (512b chain, linked via offset at block end-4)
"""
from __future__ import annotations
import logging, os, struct, time, re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

class PBObjectType(IntEnum):
    APPLICATION=0; DATAWINDOW=1; WINDOW=2; MENU=3; FUNCTION=4
    STRUCTURE=5; USEROBJECT=6; QUERY=7; PIPELINE=8; PROJECT=9; PROXY=10; BINARY=11
    # PB12+ additions
    EMBEDDED_SQL=12; WEB_SERVICE=13; COMPONENT=14

OBJ_EXT = {
    PBObjectType.APPLICATION:".sra", PBObjectType.DATAWINDOW:".srd",
    PBObjectType.WINDOW:".srw", PBObjectType.MENU:".srm",
    PBObjectType.FUNCTION:".srf", PBObjectType.STRUCTURE:".srs",
    PBObjectType.USEROBJECT:".sru", PBObjectType.QUERY:".srq",
    PBObjectType.PIPELINE:".srp", PBObjectType.PROJECT:".srj",
    PBObjectType.PROXY:".srx", PBObjectType.EMBEDDED_SQL:".sre",
    PBObjectType.WEB_SERVICE:".srw", PBObjectType.COMPONENT:".src",
}
# Comment-based type keywords (from PBL entry comments)
KW_TYPE = {
    "application":0, "datawindow":1, "window":2, "menu":3, "function":4,
    "structure":5, "user object":6, "userobject":6, "query":7, "pipeline":8,
    "project":9, "proxy":10, "embedded sql":12,
}
# Known PB type codes (for PB12+ header parsing)
PB_TYPE_CODES = {
    0: "application", 1: "datawindow", 2: "window", 3: "menu",
    4: "function", 5: "structure", 6: "userobject", 7: "query",
    8: "pipeline", 9: "project", 10: "proxy",
}

@dataclass
class PBLEntry:
    name: str; object_type: PBObjectType; comment: str = ""
    first_data_offset: int = 0; data_size: int = 0
    creation_time: datetime = field(default_factory=lambda: datetime(2000,1,1,tzinfo=timezone.utc))
    compile_time: datetime = field(default_factory=lambda: datetime(2000,1,1,tzinfo=timezone.utc))
    @property
    def extension(self): return OBJ_EXT.get(self.object_type, ".bin")
    @property
    def type_name(self):
        for n,c in KW_TYPE.items():
            if c == self.object_type: return n.title()
        return "Unknown"

@dataclass
class PBLSource:
    entry: PBLEntry; source: bytes; filename: str = ""
    @property
    def source_text(self):
        # Try UTF-8 first (PB12+ often uses UTF-8), fall back to latin-1
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return self.source.decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
        return self.source.decode("latin-1", errors="replace")

BLOCK = 512
HEADER_SIZE_PB_OLD = 512   # PB4-PB10
HEADER_SIZE_PB_NEW = 1024  # PB11+


class PBLParser:
    """Parse PowerBuilder PBL library files.

    Supports PB4 through PB12+ format variations:
    - Different header sizes (512b vs 1024b)
    - Variable NOD* block counts
    - Different entry encoding (comment-length field, type codes)
    - Unicode source in PB12+
    """
    def __init__(self, fp: str|Path, strict: bool = False):
        self.fp = Path(fp)
        self._fh: Optional[BinaryIO] = None
        self.entries: list[PBLEntry] = []
        self.strict = strict  # True = skip entries on any validation error
        self._header_size = 0
        self._version_hints: list[str] = []

    def open(self):
        self._fh = open(self.fp, "rb")
        self._detect_format()
        self._parse()
        logger.debug("Parsed %d entries from %s", len(self.entries), self.fp)
        return self
    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None
    def __enter__(self): return self.open()
    def __exit__(self, *a): self.close()
    def _read(self, off, sz):
        self._fh.seek(off)
        return self._fh.read(sz)

    def _detect_format(self):
        """Detect header size and format version."""
        sz = self._fh.seek(0, 2)
        # Read first bytes to determine format
        header_data = self._read(0, min(1024, sz))
        if not header_data:
            raise ValueError("Empty PBL file")

        # Check for PB11+ magic/signature patterns
        # PB11+ uses 1024-byte header with specific layout
        self._header_size = HEADER_SIZE_PB_NEW  # Default to new format
        self._version_hints = []

        # Look for version indicators in the header area
        if len(header_data) >= 1024:
            # Check if offset 512 looks like the start of FRE* (old format)
            # vs new format which uses full 1024b for header
            mid = header_data[512:516]
            if mid == b"FRE*":
                self._header_size = HEADER_SIZE_PB_OLD
                self._version_hints.append("PB_old_header_512b")
            else:
                # Check for unicode markers or PB12+ signatures
                if b"\xff\xfe" in header_data[:32] or b"\xfe\xff" in header_data[:32]:
                    self._version_hints.append("unicode_BOM_detected")
                self._version_hints.append("PB_new_header_1024b")
        else:
            self._header_size = HEADER_SIZE_PB_OLD

        logger.debug("Header size: %d, hints: %s", self._header_size, self._version_hints)

    def _parse(self):
        sz = self._fh.seek(0, 2)
        # Strategy 1: Scan for NOD* blocks (primary B-tree index)
        for off in range(0, sz, BLOCK):
            self._fh.seek(off)
            h = self._fh.read(4)
            if h == b"NOD*":
                self._parse_nod(off)
        # Strategy 2: If no entries found, try header-entry format
        if not self.entries:
            self._parse_header_entries()
        # Strategy 3: Last resort - sequential scan
        if not self.entries:
            self._scan_entries()
        # Deduplicate by (name, type)
        seen = set()
        unique = []
        for e in self.entries:
            key = (e.name, e.object_type)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        self.entries = unique

    def _parse_nod(self, base_off):
        """Parse a NOD* B-tree node block."""
        sz = self._fh.seek(0, 2)
        data = self._read(base_off, 8 * BLOCK)  # Read up to 8 blocks (4096b)
        if data[:4] != b"NOD*":
            return

        # NOD* header: first 16 bytes
        # Bytes 0-3: "NOD*"
        # Bytes 4-7: ? (node flags)
        # Bytes 8-11: number of entries
        # Bytes 12-15: next node pointer
        pos = 16
        entry_count = 0
        max_entries = 200  # Safety limit

        while pos < len(data) - 20 and entry_count < max_entries:
            # Find null-terminated entry name
            ne = data.find(b"\x00", pos)
            if ne < 0 or ne - pos > 256:
                # No more valid names in this block
                break
            name = data[pos:ne].decode("ascii", errors="replace").strip()
            if not name:
                pos = ne + 1
                continue
            pos = ne + 1

            # Need at least 14 bytes for offset+size+timestamp
            if pos + 14 > len(data):
                break

            off = struct.unpack_from("<I", data, pos)[0]; pos += 4
            size = struct.unpack_from("<I", data, pos)[0]; pos += 4
            ts = struct.unpack_from("<I", data, pos)[0]; pos += 4

            # Optional: compile timestamp (PB11+)
            compile_ts = 0
            if pos + 4 <= len(data):
                test_val = struct.unpack_from("<I", data, pos)[0]
                # Heuristic: if it looks like a timestamp (after 1990)
                if 600000000 < test_val < 2200000000:
                    compile_ts = test_val
                    pos += 4

            # Comment: length-prefixed or null-terminated
            comment = ""
            comment_len = struct.unpack_from("<H", data, pos)[0]; pos += 2
            if 0 < comment_len < 512 and pos + comment_len <= len(data):
                comment = data[pos:pos + comment_len].decode("ascii", errors="replace")
                pos += comment_len
            elif comment_len == 0 or comment_len >= 512:
                # Try null-terminated comment
                ce = data.find(b"\x00", pos)
                if 0 < ce - pos < 256:
                    comment = data[pos:ce].decode("ascii", errors="replace")
                    pos = ce + 1

            # Validate offsets
            if off == 0 and size == 0:
                continue  # Empty/deleted entry
            if off > sz:
                if self.strict:
                    continue
                # Try interpreting as relative offset
                off = base_off + off
                if off > sz:
                    continue
            if size > 10_000_000:
                continue  # Unreasonably large

            ot = self._detect_type(name, comment)
            try:
                t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else datetime(2000, 1, 1, tzinfo=timezone.utc)
            except (OSError, OverflowError):
                t = datetime(2000, 1, 1, tzinfo=timezone.utc)

            exists = any(x.name == name and x.object_type == ot for x in self.entries)
            if not exists:
                entry = PBLEntry(name=name, object_type=ot, comment=comment,
                                 first_data_offset=off, data_size=size, creation_time=t)
                if compile_ts > 0:
                    try:
                        entry.compile_time = datetime.fromtimestamp(compile_ts, tz=timezone.utc)
                    except (OSError, OverflowError):
                        pass
                self.entries.append(entry)
                entry_count += 1

    def _parse_header_entries(self):
        """Parse entries from header area (some PB formats store entries there)."""
        sz = self._fh.seek(0, 2)
        # Scan header + first few blocks for entry-like patterns
        data = self._read(0, min(8192, sz))
        pos = self._header_size  # Start after header
        while pos < len(data) - 20:
            ne = data.find(b"\x00", pos)
            if ne < 0 or ne - pos < 2 or ne - pos > 64:
                break
            name = data[pos:ne].decode("ascii", errors="replace").strip()
            if not name:
                pos = ne + 1
                continue
            pos = ne + 1
            if pos + 10 > len(data):
                break
            off = struct.unpack_from("<I", data, pos)[0]; pos += 4
            size = struct.unpack_from("<I", data, pos)[0]; pos += 4
            pos += 2  # skip unknown field
            if off > sz or size > 5_000_000 or size == 0:
                continue
            if any(x.name == name for x in self.entries):
                continue
            ot = self._detect_type(name, "")
            self.entries.append(PBLEntry(name=name, object_type=ot,
                                         first_data_offset=off, data_size=size))

    def _read_entry(self, data, pos):
        """Read a single entry from NOD* data at given position."""
        if pos + 20 >= len(data):
            return None, pos
        ne = data.find(b"\x00", pos)
        if ne < 0 or ne - pos > 256:
            return None, pos + 1
        name = data[pos:ne].decode("ascii", errors="replace").strip()
        if not name:
            return None, pos + 1
        pos = ne + 1
        if pos + 14 >= len(data):
            return None, pos
        off = struct.unpack_from("<I", data, pos)[0]; pos += 4
        size = struct.unpack_from("<I", data, pos)[0]; pos += 4
        ts = struct.unpack_from("<I", data, pos)[0]; pos += 4
        cl = struct.unpack_from("<H", data, pos)[0]; pos += 2
        comment = ""
        if 0 < cl < 512 and pos + cl <= len(data):
            comment = data[pos:pos + cl].decode("ascii", errors="replace")
            pos += cl
        ot = self._detect_type(name, comment)
        try:
            t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else datetime(2000, 1, 1, tzinfo=timezone.utc)
        except (OSError, OverflowError):
            t = datetime(2000, 1, 1, tzinfo=timezone.utc)
        return PBLEntry(name=name, object_type=ot, comment=comment,
                        first_data_offset=off, data_size=size, creation_time=t), pos

    def _scan_entries(self):
        """Fallback: scan NOD* blocks with strict validation.
        Used when the standard NOD* parsing finds no entries.
        """
        sz = self._fh.seek(0, 2)
        for off in range(0, sz, 6 * BLOCK):
            self._fh.seek(off)
            h = self._fh.read(4)
            if h != b"NOD*":
                continue
            data = self._read(off, 6 * BLOCK)
            pos = 16
            while pos < len(data) - 20:
                ne = data.find(b"\x00", pos)
                if ne < 0 or ne - pos < 2 or ne - pos > 64:
                    break
                name = data[pos:ne].decode("ascii", errors="replace").strip()
                if not name:
                    pos = ne + 1
                    continue
                pos = ne + 1
                if pos + 14 > len(data):
                    break
                eoff = struct.unpack_from("<I", data, pos)[0]
                esz = struct.unpack_from("<I", data, pos + 4)[0]
                pos += 14
                cl = struct.unpack_from("<H", data, pos)[0]; pos += 2
                if 0 < cl < 512 and pos + cl <= len(data):
                    pos += cl
                # Validate: offset must be within file, size reasonable
                if eoff < 0 or eoff > sz or esz > 5_000_000 or esz == 0:
                    continue
                if any(x.name == name for x in self.entries):
                    continue
                ot = self._detect_type(name, "")
                self.entries.append(PBLEntry(name=name, object_type=ot,
                                             first_data_offset=eoff, data_size=esz))

    def _detect_type(self, name: str, comment: str) -> PBObjectType:
        """Detect object type from comment keyword or naming convention."""
        cl = comment.lower()
        for kw, tc in KW_TYPE.items():
            if kw in cl:
                return PBObjectType(tc)
        # Heuristic: name prefix convention
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
        if nl.startswith("p_") and "project" in cl:
            return PBObjectType.PROJECT
        # Default: if name matches common app name patterns, treat as Application
        if nl in ("dgsauna", "dgapp", "app_dgsauna"):
            return PBObjectType.APPLICATION
        return PBObjectType.BINARY  # Unknown type

    def export_source(self, entry: PBLEntry, max_size: int = 10_000_000) -> Optional[bytes]:
        """Extract source data for an entry by following the DAT* block chain.

        Args:
            entry: The PBL entry to extract.
            max_size: Maximum bytes to read (safety limit).
        """
        if not self._fh or entry.first_data_offset == 0:
            return None
        sz = self._fh.seek(0, 2)
        if entry.first_data_offset > sz:
            return None

        src = bytearray()
        cur = entry.first_data_offset
        rem = min(entry.data_size, max_size) if entry.data_size > 0 else max_size

        while cur != 0 and rem > 0:
            if cur > sz:
                logger.warning("Data offset %d exceeds file size %d for %s",
                               cur, sz, entry.name)
                break
            blk = self._read(cur, BLOCK)
            if not blk or len(blk) < BLOCK:
                break

            # Check for DAT* marker (skip 4 bytes)
            ds = 4 if blk[:4] == b"DAT*" else 0
            cs = min(rem, BLOCK - ds)
            if cs <= 0:
                break
            src.extend(blk[ds:ds + cs])
            rem -= cs

            # Next block offset is at the end of the current block
            if BLOCK >= 8:
                nxt = struct.unpack_from("<I", blk, BLOCK - 4)[0]
                # 0xFFFFFFFF or 0 = end of chain
                cur = 0 if nxt == 0xFFFFFFFF or nxt == 0 else nxt
            else:
                cur = 0

        return bytes(src) if src else None

    def export_all(self):
        res=[]
        for e in self.entries:
            s = self.export_source(e)
            if s: res.append(PBLSource(entry=e, source=s, filename=e.name+e.extension))
        return res

    def export_to_directory(self, out, source_only=True):
        op=Path(out); op.mkdir(parents=True,exist_ok=True); exp=[]
        for ps in self.export_all():
            if source_only and ps.entry.extension==".bin": continue
            fp=op/ps.filename; fp.write_bytes(ps.source); exp.append(str(fp))
        return exp

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
        """Export a single entry by name."""
        entry = self.get_entry(name)
        if not entry:
            return None
        src = self.export_source(entry)
        if not src:
            return None
        return PBLSource(entry=entry, source=src, filename=name + entry.extension)


class PBLBatchExporter:
    def __init__(self, proj, out): self.proj=Path(proj); self.out=Path(out)
    def find_pbls(self, recursive=True):
        return sorted(self.proj.glob("**/*.pbl") if recursive else "*.pbl")
    def export_all(self, recursive=True):
        res={}; pbls=self.find_pbls(recursive)
        for p in pbls:
            sub = self.out / p.stem
            try:
                with PBLParser(p) as pr: res[str(p)]=pr.export_to_directory(sub)
            except Exception as e: res[str(p)]=[f"ERROR: {e}"]
        return res
