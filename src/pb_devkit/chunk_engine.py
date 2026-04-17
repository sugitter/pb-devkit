"""Sybase PB file four-layer Chunk chain parsing engine.

Extracted from PBLParser (v1.3), with the following enhancements:
- Support for in-memory bytes (for PE-extracted PBD sub-streams)
- PB version detection from first ENT*
- Improved validation (entry_count sanity check)

Format reference (verified against PbdViewer + PbdCli):
  HDR*(512/1024b) -> FRE*(512b) -> NOD*(3072b B-tree) -> ENT*/DAT*(512b chain)

ENT* layout (NO comment field — Arnd Schmidt doc was wrong):
  ANSI:    ENT*(4) + version(4) + offset(4) + size(4) + ts(4) + ?(2) + name_len(2) = 24 bytes
  Unicode: ENT*(4) + version(8) + offset(4) + size(4) + ts(4) + ?(2) + name_len(2) = 28 bytes
  After header: [name buffer (name_len bytes)] -> next ENT*
"""
from __future__ import annotations

import io
import logging
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BLOCK_SIZE = 512
BLOCK_SIZE_UNICODE = 1024
NODE_BLOCK_SIZE = 3072  # 6 x 512

# Comment-based type keywords (ANSI PBLs store type in comment field)
KW_TYPE = {
    "application": 0, "datawindow": 1, "window": 2, "menu": 3, "function": 4,
    "structure": 5, "user object": 6, "userobject": 6, "query": 7, "pipeline": 8,
    "project": 9,     "proxy": 10, "embedded sql": 12,
}

# Extension-based type mapping (PB12+ Unicode PBLs store extension in name)
SOURCE_EXT_MAP = {
    ".srw": 2,   # WINDOW
    ".srd": 1,   # DATAWINDOW
    ".srm": 3,   # MENU
    ".srf": 4,   # FUNCTION
    ".srs": 5,   # STRUCTURE
    ".sru": 6,   # USEROBJECT
    ".srq": 7,   # QUERY
    ".srp": 8,   # PIPELINE
    ".srj": 9,   # PROJECT
    ".srx": 10,  # PROXY
    ".sre": 12,  # EMBEDDED_SQL
    ".sra": 0,   # APPLICATION
}

COMPILED_EXT_SET = {".win", ".dwo", ".prp", ".udo", ".fun", ".str", ".apl", ".men", ".pra"}


# ---------------------------------------------------------------------------
# PBObjectType enum (kept in sync with pbl_parser.py)
# ---------------------------------------------------------------------------
class PBObjectType(IntEnum):
    APPLICATION = 0
    DATAWINDOW = 1
    WINDOW = 2
    MENU = 3
    FUNCTION = 4
    STRUCTURE = 5
    USEROBJECT = 6
    QUERY = 7
    PIPELINE = 8
    PROJECT = 9
    PROXY = 10
    BINARY = 11
    EMBEDDED_SQL = 12
    WEB_SERVICE = 13
    COMPONENT = 14


# ---------------------------------------------------------------------------
# PBEntry — the universal entry metadata
# ---------------------------------------------------------------------------
@dataclass
class PBEntry:
    """Metadata for a single PB library entry."""
    name: str
    object_type: PBObjectType = PBObjectType.BINARY
    comment: str = ""
    version: str = ""  # ENT* version string (e.g. "0500", "0600")
    first_data_offset: int = 0
    data_size: int = 0
    creation_time: Optional[datetime] = None

    # Derived properties
    @property
    def is_source(self) -> bool:
        """True if this entry contains exportable source text."""
        ext = self._get_ext()
        return ext in SOURCE_EXT_MAP or self.object_type not in (
            PBObjectType.BINARY,
        )

    @property
    def extension(self) -> str:
        """File extension for export."""
        ext = self._get_ext()
        if ext in SOURCE_EXT_MAP:
            return ext
        if ext in COMPILED_EXT_SET:
            return ".bin"
        return OBJ_EXT.get(self.object_type, ".bin")

    @property
    def base_name(self) -> str:
        dot = self.name.rfind(".")
        return self.name[:dot] if dot > 0 else self.name

    @property
    def type_name(self) -> str:
        if self.object_type == PBObjectType.BINARY:
            return "Binary"
        for n, c in KW_TYPE.items():
            if c == self.object_type:
                return n.title()
        return "Unknown"

    def _get_ext(self) -> str:
        dot = self.name.rfind(".")
        return self.name[dot:].lower() if dot > 0 else ""


# Extension → ObjectType mapping for source entries (public for backward compat)
OBJ_EXT = {
    PBObjectType.APPLICATION: ".sra",
    PBObjectType.DATAWINDOW: ".srd",
    PBObjectType.WINDOW: ".srw",
    PBObjectType.MENU: ".srm",
    PBObjectType.FUNCTION: ".srf",
    PBObjectType.STRUCTURE: ".srs",
    PBObjectType.USEROBJECT: ".sru",
    PBObjectType.QUERY: ".srq",
    PBObjectType.PIPELINE: ".srp",
    PBObjectType.PROJECT: ".srj",
    PBObjectType.PROXY: ".srx",
    PBObjectType.EMBEDDED_SQL: ".sre",
    PBObjectType.WEB_SERVICE: ".srw",
    PBObjectType.COMPONENT: ".src",
}


# ---------------------------------------------------------------------------
# ChunkEngine — the core parser
# ---------------------------------------------------------------------------
class ChunkEngine:
    """Sybase PB file four-layer Chunk chain parsing engine.

    Strictly follows the original Sybase format:
    - HDR* (512/1024b) -> FRE* (512b) -> NOD* (3072b B-tree) -> ENT*/DAT*

    Supports two modes:
    1. File mode: reads from a .pbl / .pbd file path
    2. Memory mode: parses in-memory bytes (for PE-extracted PBD sub-streams)

    Improvements over PBLParser v1.3:
    - Memory mode for embedded PBD streams
    - PB version detection
    - Validation improvements
    """

    def __init__(self, path: str | Path | None = None, data: bytes | None = None):
        if path is None and data is None:
            raise ValueError("Either path or data must be provided")
        self.path = Path(path) if path else None
        self._data = data
        self._fh: Optional[BinaryIO] = None
        self._stream: BinaryIO | None = None
        self.entries: list[PBEntry] = []
        self._is_unicode = False
        self._header_size = 0
        self._pb_version = 0  # numeric PB version (e.g. 500, 600)
        self._stream_size = 0

    # ----- lifecycle -----

    def open(self) -> ChunkEngine:
        if self._data is not None:
            self._stream = io.BytesIO(self._data)
            self._stream_size = len(self._data)
        else:
            self._fh = open(self.path, "rb")  # noqa: SIM115
            self._stream = self._fh
            self._stream_size = self._fh.seek(0, 2)
        self._detect_format()
        self._parse_tree()
        return self

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None
        self._stream = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    # ----- public properties -----

    @property
    def is_unicode(self) -> bool:
        return self._is_unicode

    @property
    def header_size(self) -> int:
        return self._header_size

    @property
    def pb_version(self) -> int:
        return self._pb_version

    # ----- low-level read -----

    def _read(self, offset: int, size: int) -> bytes:
        self._stream.seek(offset)
        return self._stream.read(size)

    # ----- format detection -----

    def _detect_format(self):
        """Detect HDR* format (ANSI vs Unicode) and extract PB version."""
        read_size = min(BLOCK_SIZE_UNICODE + 4, self._stream_size)
        header = self._read(0, read_size)

        if not header or header[:4] != b"HDR*":
            raise ValueError("Not a valid PB library file (missing HDR* signature)")

        # ANSI vs Unicode: check where FRE* is located
        if len(header) >= 516 and header[512:516] == b"FRE*":
            self._is_unicode = False
            self._header_size = BLOCK_SIZE
        elif len(header) >= BLOCK_SIZE_UNICODE + 4 and header[BLOCK_SIZE_UNICODE:BLOCK_SIZE_UNICODE + 4] == b"FRE*":
            self._is_unicode = True
            self._header_size = BLOCK_SIZE_UNICODE
        else:
            # Fallback: check for BOM or unicode markers
            self._is_unicode = b"\xff\xfe" in header[:32] or b"\xfe\xff" in header[:32]
            self._header_size = BLOCK_SIZE_UNICODE if self._is_unicode else BLOCK_SIZE

        # Try to extract PB version from HDR* body
        self._detect_pb_version_from_hdr(header)

        logger.debug(
            "ChunkEngine: header=%d, unicode=%s, stream_size=%d",
            self._header_size, self._is_unicode, self._stream_size,
        )

    def _detect_pb_version_from_hdr(self, header: bytes):
        """Attempt to detect PB version from HDR* header body.

        HDR* contains "PowerBuilder" followed by version info.
        After that, around offset 30-40, there may be a version number.
        We'll try to find it, but the definitive version comes from ENT*.
        """
        # Look for version-like numbers in the header
        # "PowerBuilder 12.5" or similar patterns appear after the signature
        if not self._is_unicode:
            # ANSI: search for "PB " or version numbers
            # The HDR block has "PowerBuilder" at offset 4, version info follows
            # Not reliably parseable — defer to ENT* version
            pass
        else:
            # Unicode: same issue
            pass

    # ----- NOD* / ENT* tree parsing -----

    def _parse_tree(self):
        """Traverse NOD* B-tree and parse all ENT* entries.

        Format (verified against PbdViewer + PbdCli):
        ENT* header layout:
          ANSI:    ENT*(4) + version(4) + offset(4) + size(4) + ts(4) + *(8) + name_len(2) = 24 bytes
          Unicode: ENT*(4) + version(8) + offset(4) + size(4) + ts(4) + *(8) + name_len(2) = 28 bytes

        After header: [name buffer (name_len bytes)] → next ENT*
        There is NO comment_len field in the ENT* header.
        """
        nod_start = self._header_size + BLOCK_SIZE
        if nod_start + 4 > self._stream_size:
            logger.warning("Stream too small for NOD* block")
            return

        # Pre-calculate ENT* header field offsets
        # ANSI:    num=1, num2=4+1*4=8,  num3=8+16=24
        # Unicode:  num=2, num2=4+2*4=12, num3=12+16=28
        num = 2 if self._is_unicode else 1
        num2 = 4 + num * 4      # start of fixed fields (offset, size, ts, ..., name_len)
        num3 = num2 + 16        # total fixed header size

        visited: set[int] = set()
        current_offset = nod_start

        while current_offset > 0 and current_offset not in visited:
            visited.add(current_offset)

            if current_offset + NODE_BLOCK_SIZE > self._stream_size:
                logger.warning("NOD* at offset %d exceeds stream size %d",
                               current_offset, self._stream_size)
                break

            nod_data = self._read(current_offset, NODE_BLOCK_SIZE)
            if not nod_data or nod_data[:4] != b"NOD*":
                break

            entry_count = struct.unpack_from("<H", nod_data, 20)[0]
            right_offset = struct.unpack_from("<I", nod_data, 12)[0]

            if entry_count > 200:
                logger.warning("NOD* entry_count=%d seems too large, stopping", entry_count)
                break

            pos_in_nod = 32

            for _ in range(entry_count):
                if pos_in_nod + num3 > len(nod_data):
                    break

                ent_header = nod_data[pos_in_nod:pos_in_nod + num3]
                if ent_header[:4] != b"ENT*":
                    break

                # Version string
                ver_bytes = ent_header[4:4 + num * 4]
                if self._is_unicode:
                    ver_text = ver_bytes.decode("utf-16-le", errors="replace")
                else:
                    ver_text = ver_bytes.decode("ascii", errors="replace")
                ver_text = ver_text.strip("\x00")

                if not ver_text:
                    break

                # Fixed fields
                data_offset = struct.unpack_from("<I", ent_header, num2)[0]
                obj_size = struct.unpack_from("<I", ent_header, num2 + 4)[0]
                raw_ts = struct.unpack_from("<I", ent_header, num2 + 8)[0]

                # name_buf_len at num2+14 (the ONLY ushort after the fixed fields)
                name_buf_len = struct.unpack_from("<H", ent_header, num2 + 14)[0]

                # Name buffer starts immediately after ENT* header
                name_buf_start = pos_in_nod + num3
                name_buf_end = name_buf_start + name_buf_len
                if name_buf_end > len(nod_data):
                    break

                name_buf = nod_data[name_buf_start:name_buf_end]

                # Decode name: name_buf_len includes version prefix bytes
                actual_name_len = name_buf_len - num
                if actual_name_len <= 0:
                    pos_in_nod = name_buf_end
                    continue

                if self._is_unicode:
                    name = name_buf[:actual_name_len].decode("utf-16-le", errors="replace")
                else:
                    name = name_buf[:actual_name_len].decode("latin-1", errors="replace")
                name = name.rstrip("\x00").strip()

                pos_in_nod = name_buf_end

                # Timestamp
                ts = raw_ts
                if ts > 3_000_000_000:
                    ts //= 1000
                try:
                    t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else None
                except (OSError, OverflowError, ValueError):
                    t = None

                # Type detection: extension (Unicode) or prefix (ANSI)
                obj_type = self._detect_type(name, "")

                # Record PB version from first valid ENT*
                if not self._pb_version and ver_text.isdigit():
                    self._pb_version = int(ver_text)

                entry = PBEntry(
                    name=name,
                    object_type=obj_type,
                    comment="",  # ENT* has no comment field
                    version=ver_text,
                    first_data_offset=data_offset,
                    data_size=obj_size,
                    creation_time=t,
                )

                # Validate and deduplicate
                if (entry.first_data_offset > 0
                        and entry.data_size > 0
                        and entry.first_data_offset <= self._stream_size
                        and entry.data_size <= 10_000_000
                        and not any(x.name == entry.name for x in self.entries)):
                    self.entries.append(entry)
                    logger.debug(
                        "  Entry: %s type=%s offset=%d size=%d ver=%s",
                        entry.name, entry.type_name,
                        entry.first_data_offset, entry.data_size,
                        entry.version,
                    )

            current_offset = right_offset

        logger.info("ChunkEngine: parsed %d entries, pb_version=%s",
                     len(self.entries), self._pb_version)

    # ----- type detection -----

    def _detect_type(self, name: str, comment: str) -> PBObjectType:
        """Detect object type: comment keywords > extension > name prefix."""
        # 1. Comment-based detection (most reliable for ANSI PBLs)
        if comment:
            cl = comment.lower()
            for kw, tc in KW_TYPE.items():
                if kw in cl:
                    return PBObjectType(tc)

        # 2. Extension-based detection (PB12+ Unicode PBLs)
        nl = name.lower()
        dot = nl.rfind(".")
        if dot > 0:
            ext = nl[dot:]
            if ext in SOURCE_EXT_MAP:
                return PBObjectType(SOURCE_EXT_MAP[ext])
            if ext in COMPILED_EXT_SET:
                return PBObjectType.BINARY

        # 3. Name prefix heuristic
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

        # 4. Known application names
        if nl in ("dgsauna", "dgapp", "app_dgsauna"):
            return PBObjectType.APPLICATION

        return PBObjectType.BINARY

    # ----- DAT* chain reading -----

    def read_data_chain(self, offset: int, size: int = 0) -> bytes | None:
        """Read DAT* block chain and concatenate all data.

        Args:
            offset: Start offset of the first DAT* block.
            size: Expected total data size (0 = unknown, use max 10MB).

        Returns:
            Concatenated data bytes, or None if no data.
        """
        if offset > self._stream_size or offset <= 0:
            return None

        result = bytearray()
        cur = offset
        rem = min(size, 10_000_000) if size > 0 else 10_000_000

        while cur != 0 and rem > 0:
            if cur > self._stream_size:
                break

            blk = self._read(cur, BLOCK_SIZE)
            if not blk or len(blk) < 10:
                break

            if blk[:4] != b"DAT*":
                # No DAT* marker — read raw and stop
                result.extend(blk[:min(rem, len(blk))])
                break

            next_offset = struct.unpack_from("<I", blk, 4)[0]
            data_len = struct.unpack_from("<H", blk, 8)[0]

            if data_len <= 0 or data_len > 502:
                data_len = BLOCK_SIZE - 10

            actual_len = min(data_len, rem)
            result.extend(blk[10:10 + actual_len])
            rem -= actual_len

            if next_offset == 0 or next_offset > self._stream_size or next_offset == 0xFFFFFFFF:
                cur = 0
            else:
                cur = next_offset

        return bytes(result) if result else None

    # ----- convenience methods -----

    def get_entry(self, name: str) -> PBEntry | None:
        """Find entry by name (case-insensitive)."""
        nl = name.lower()
        for e in self.entries:
            if e.name.lower() == nl:
                return e
        return None

    def get_entries_by_type(self, obj_type: PBObjectType) -> list[PBEntry]:
        """Get all entries of a specific type."""
        return [e for e in self.entries if e.object_type == obj_type]

    def list_entries(self) -> list[dict]:
        """Return entries as list of dicts (for CLI display)."""
        return [
            {
                "name": e.name,
                "type": e.type_name,
                "type_code": int(e.object_type),
                "extension": e.extension,
                "size": e.data_size,
                "comment": e.comment,
                "version": e.version,
                "created": e.creation_time.isoformat() if e.creation_time else "",
            }
            for e in self.entries
        ]
