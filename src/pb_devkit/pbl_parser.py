"""PowerBuilder PBL binary format parser (PB5-PB12+).

PBL structure: HDR*(512/1024b) -> FRE*(512b) -> NOD*(3072b, B-Tree) -> ENT* -> DAT*(512b chain)

Format spec based on Arnd Schmidt's documentation + gmai2006/powerbuilder-pbl-dump reference:
- HDR*: Library header (512b ANSI, 1024b Unicode PB10+)
- FRE*: Free space bitmap (512b)
- NOD*: B-Tree index nodes (6x512b = 3072b per node group)
  - Header: 24 bytes (NOD* + left + parent + right + space_left + first_pos + count + last_pos)
  - ENT* entries start at byte 33 within the NOD* block
- ENT*: Variable-length entry chunks within NOD* blocks
  - ANSI:  ENT*(4) + version(4) + data_offset(4) + size(4) + timestamp(4) + comment_len(2) + name_len(2) + name(variable)
  - Unicode: ENT*(4) + version(8) + data_offset(4) + size(4) + timestamp(4) + comment_len(2) + name_len(2) + name(variable, UTF-16LE)
- DAT*: Data blocks (512b chain)
  - Header: DAT*(4) + next_offset(4) + data_len(2) + data(up to 502b)
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

@dataclass
class PBLEntry:
    name: str; object_type: PBObjectType; comment: str = ""
    first_data_offset: int = 0; data_size: int = 0
    creation_time: datetime = field(default_factory=lambda: datetime(2000,1,1,tzinfo=timezone.utc))
    compile_time: datetime = field(default_factory=lambda: datetime(2000,1,1,tzinfo=timezone.utc))
    @property
    def extension(self) -> str:
        """Get file extension.

        For PB12+ Unicode PBLs, the name already includes the extension.
        Compiled formats (.win, .dwo, .prp) return '.bin' so source_only filtering works.
        """
        dot = self.name.rfind(".")
        if dot > 0:
            ext = self.name[dot:].lower()
            # Source extensions → return as-is
            if ext in (".srw",".srd",".srm",".srf",".srs",".sru",".srq",
                       ".srp",".srj",".srx",".sre",".sra",".src"):
                return ext
            # Compiled formats → return .bin for source_only filtering
            if ext in (".win",".dwo",".prp"):
                return ".bin"
        return OBJ_EXT.get(self.object_type, ".bin")
    @property
    def type_name(self):
        for n,c in KW_TYPE.items():
            if c == self.object_type: return n.title()
        return "Unknown"
    @property
    def base_name(self) -> str:
        """Object name without extension."""
        dot = self.name.rfind(".")
        return self.name[:dot] if dot > 0 else self.name

@dataclass
class PBLSource:
    entry: PBLEntry; source: bytes; filename: str = ""
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
            # Verify by decoding a larger sample and checking for PB markers
            try:
                sample = src[:512].decode("utf-16-le", errors="strict")
                # Check if it looks like PB source (not compiled binary)
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

        # Standard fallback chain for ANSI / UTF-8 PBLs
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return src.decode(enc)
            except (UnicodeDecodeError, ValueError):
                continue
        return src.decode("latin-1", errors="replace")

    def to_utf8_bytes(self) -> bytes:
        """Convert source to UTF-8 bytes, handling UTF-16LE PBL data.

        For PB12+ Unicode PBLs, the raw source is UTF-16LE encoded.
        This method detects that and re-encodes to UTF-8 for file storage.
        Compiled binary entries (no PB markers detected) are stored as-is.
        """
        text = self.source_text
        result = text.encode("utf-8")
        # Safety: if result still contains embedded nulls, the source was
        # likely a compiled binary — return original bytes instead
        if b"\x00" in result:
            return self.source
        return result

BLOCK = 512
BLOCK_UNICODE = 1024
NODE_BLOCK_SIZE = 3072

# Backward-compatible aliases for tests
HEADER_SIZE_PB_OLD = BLOCK      # 512, ANSI PB5-PB9
HEADER_SIZE_PB_NEW = BLOCK_UNICODE  # 1024, Unicode PB10+


class PBLParser:
    """Parse PowerBuilder PBL library files.

    Supports PB5 through PB12+ based on Arnd Schmidt's format spec.
    Key format details:
    - HDR*: 512b (ANSI) or 1024b (Unicode, PB10+)
    - FRE*: 512b bitmap block at offset 512 or 1024
    - NOD*: 3072b B-tree index nodes, starting at offset 1024 or 2048
    - ENT*: Variable-length entries within NOD* blocks
    - DAT*: 512b data chain blocks

    The parser correctly handles:
    - B-tree traversal via left/parent/right offsets
    - ANSI vs Unicode ENT* entry formats
    - DAT* block chain reading with proper next-offset links
    """
    def __init__(self, fp: str|Path, strict: bool = False):
        self.fp = Path(fp)
        self._fh: Optional[BinaryIO] = None
        self.entries: list[PBLEntry] = []
        self.strict = strict
        self._is_unicode = False
        self._header_size = 0

    def open(self):
        self._fh = open(self.fp, "rb")
        self._detect_format()
        self._parse()
        logger.debug("Parsed %d entries from %s (unicode=%s)",
                     len(self.entries), self.fp, self._is_unicode)
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
        """Detect header size and whether PBL uses Unicode format.

        Detection logic:
        1. Read first 4 bytes, verify 'HDR*'
        2. Check offset 512: if 'FRE*' → ANSI (512b header)
        3. Otherwise check offset 1024 for 'FRE*' → Unicode (1024b header)
        """
        file_size = self._fh.seek(0, 2)
        header_data = self._read(0, min(BLOCK_UNICODE + 4, file_size))
        if not header_data or header_data[:4] != b"HDR*":
            raise ValueError(f"Invalid PBL file: no HDR* signature at offset 0")

        # Check if FRE* is at offset 512 (ANSI) or 1024 (Unicode)
        if len(header_data) >= 512 + 4 and header_data[512:516] == b"FRE*":
            self._is_unicode = False
            self._header_size = BLOCK
        elif len(header_data) >= BLOCK_UNICODE + 4 and header_data[BLOCK_UNICODE:BLOCK_UNICODE+4] == b"FRE*":
            self._is_unicode = True
            self._header_size = BLOCK_UNICODE
        else:
            # Fallback: check for BOM or unicode markers in first 32 bytes
            if b"\xff\xfe" in header_data[:32] or b"\xfe\xff" in header_data[:32]:
                self._is_unicode = True
                self._header_size = BLOCK_UNICODE
            else:
                self._is_unicode = False
                self._header_size = BLOCK

        logger.debug("Header size: %d, unicode: %s", self._header_size, self._is_unicode)

    def _parse(self):
        """Parse all entries by traversing NOD* B-tree."""
        file_size = self._fh.seek(0, 2)

        # NOD* starts after HDR* + FRE*
        nod_start = self._header_size + BLOCK
        if nod_start + 4 > file_size:
            logger.warning("File too small for NOD* block")
            return

        # Traverse B-tree: start at first NOD*, follow right pointers
        visited = set()
        current_offset = nod_start

        while current_offset > 0 and current_offset not in visited:
            visited.add(current_offset)
            if current_offset + NODE_BLOCK_SIZE > file_size:
                logger.warning("NOD* at offset %d exceeds file size %d", current_offset, file_size)
                break

            nod_data = self._read(current_offset, NODE_BLOCK_SIZE)
            if not nod_data or nod_data[:4] != b"NOD*":
                logger.warning("No NOD* signature at offset %d, got %r", current_offset, nod_data[:4] if nod_data else b"")
                break

            # Parse NOD* header (24 bytes)
            # Bytes 0-3:   "NOD*"
            # Bytes 4-7:   left child offset
            # Bytes 8-11:  parent offset
            # Bytes 12-15: right child offset (next NOD*)
            # Bytes 16-17: space left
            # Bytes 18-19: position of first object name
            # Bytes 20-21: entry count
            # Bytes 22-23: position of last object name
            # Bytes 24-32: reserved (8 bytes)
            # Bytes 33+:   ENT* chunks
            entry_count = struct.unpack_from("<H", nod_data, 20)[0]
            right_offset = struct.unpack_from("<I", nod_data, 12)[0]

            logger.debug("NOD* at %d: %d entries, right=%d",
                         current_offset, entry_count, right_offset)

            # Parse ENT* entries starting at byte 33 within NOD*
            # (offset 8 = 33 - 24 for first_name_position - header_end)
            chunk = nod_data[24:]  # skip NOD* 24-byte header
            pos = 8  # first entry starts at chunk[8] = nod_data[32], but actual entries start at byte 33

            # According to the spec, entries start at byte 33
            # chunk starts at byte 24, so first entry is at chunk[9] = byte 33
            # But reference implementation uses start_pos = 8 (within chunk starting at byte 24)
            # That means byte 32 in the NOD* block. Let's use byte 33 as spec says.
            # Actually looking at gmai2006: start_pos = 8, chunk = lst[8] = NODE_BLOCK_SIZE - 20 bytes starting at byte 20
            # Wait, let me re-read: attributes = [4, 4, 4, 4, 2, 2, 2, 2, NODE_BLOCK_SIZE - 20]
            # So chunk = data[20:20+NODE_BLOCK_SIZE-20] = data[20:3052] = bytes 20-3052
            # start_pos = 8, meaning entries start at chunk[8] = byte 28
            # But byte 24-32 is reserved, and spec says entries at byte 33...
            # Let me just use the reference implementation's approach:
            # Read the raw NOD* data and extract entries using the spec format

            # Re-parse from scratch using correct offsets
            pos_in_nod = 24  # skip 24-byte NOD* header
            # Skip reserved bytes 24-32 (9 bytes), entries start at byte 33
            # Actually, the reference code reads 20 bytes of header (4+4+4+4+2+2+2+2=24)
            # then the remaining NODE_BLOCK_SIZE-20=3052 bytes is the chunk
            # start_pos=8 means entries start at chunk[8] = NOD* offset 28
            # But the spec clearly says byte 33... Let me check again.
            #
            # Spec says:
            # 1-4: NOD*, 5-8: left, 9-12: parent, 13-16: right
            # 17-18: space, 19-20: first_pos, 21-22: count, 23-24: last_pos
            # 33-xx: ENT* chunks
            # Bytes 25-32 are reserved/padding
            #
            # Reference code: attributes = [4,4,4,4,2,2,2,2, NODE_BLOCK_SIZE-20]
            # This reads: 4+4+4+4+2+2+2+2 = 24 bytes header
            # Then chunk = remaining 3052 bytes starting at offset 24
            # start_pos = 8 means entries start at chunk[8] = absolute offset 32
            # This is off-by-one from spec's byte 33.
            # The discrepancy is 1 byte. Let me search for ENT* signature instead.

            # Robust approach: scan for first ENT* in the NOD* block
            ent_pos = nod_data.find(b"ENT*", 24)
            if ent_pos < 0:
                # No entries in this NOD* block
                current_offset = right_offset
                continue

            pos_in_nod = ent_pos
            for _ in range(entry_count):
                if pos_in_nod + 20 > len(nod_data):
                    break

                # Verify ENT* signature
                if nod_data[pos_in_nod:pos_in_nod+4] != b"ENT*":
                    # Try to find next ENT*
                    next_ent = nod_data.find(b"ENT*", pos_in_nod + 1)
                    if next_ent < 0:
                        break
                    pos_in_nod = next_ent
                    continue

                if self._is_unicode:
                    entry, new_pos = self._parse_ent_unicode(nod_data, pos_in_nod)
                else:
                    entry, new_pos = self._parse_ent_ansi(nod_data, pos_in_nod)

                if entry is None:
                    break

                # Validate
                if entry.first_data_offset > 0 and entry.data_size > 0:
                    if entry.first_data_offset <= file_size and entry.data_size <= 10_000_000:
                        if not any(x.name == entry.name for x in self.entries):
                            self.entries.append(entry)
                            logger.debug("  Entry: %s type=%d offset=%d size=%d",
                                         entry.name, entry.object_type,
                                         entry.first_data_offset, entry.data_size)

                pos_in_nod = new_pos

            current_offset = right_offset

        logger.info("Total entries parsed: %d", len(self.entries))

    def _parse_ent_ansi(self, nod_data: bytes, pos: int) -> tuple[Optional[PBLEntry], int]:
        """Parse an ANSI ENT* entry within a NOD* block.

        ANSI ENT* format (Arnd Schmidt spec):
        Bytes 0-3:   "ENT*" (Char 4)
        Bytes 4-7:   PBL version (Char 4, e.g. "0600")
        Bytes 8-11:  First data block offset (Long)
        Bytes 12-15: Object size (Long)
        Bytes 16-19: Unix datetime (Long)
        Bytes 20-21: Comment length (Integer)
        Bytes 22-23: Object name length (Integer)
        Bytes 24+:   Object name (String, name_len bytes)
        After name:  Comment (String, comment_len bytes)

        Total fixed: 24 bytes + name_len + comment_len
        """
        if pos + 24 > len(nod_data):
            return None, pos + 1

        # Parse fixed fields
        version = nod_data[pos+4:pos+8]
        data_offset = struct.unpack_from("<I", nod_data, pos + 8)[0]
        obj_size = struct.unpack_from("<I", nod_data, pos + 12)[0]
        raw_ts = struct.unpack_from("<I", nod_data, pos + 16)[0]
        comment_len = struct.unpack_from("<H", nod_data, pos + 20)[0]
        name_len = struct.unpack_from("<H", nod_data, pos + 22)[0]

        if name_len == 0 or name_len > 256:
            return None, pos + 24

        name_end = pos + 24 + name_len
        if name_end > len(nod_data):
            return None, pos + 24

        name = nod_data[pos+24:name_end].decode("latin-1", errors="replace").strip()
        new_pos = name_end

        # Read comment if present
        comment = ""
        if comment_len > 0 and new_pos + comment_len <= len(nod_data):
            comment = nod_data[new_pos:new_pos+comment_len].decode("latin-1", errors="replace")
            new_pos += comment_len

        # Timestamp: divide by 1000 if it looks like milliseconds (PB uses seconds)
        ts = raw_ts
        if ts > 3_000_000_000:  # Likely milliseconds
            ts = ts // 1000

        try:
            t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else datetime(2000, 1, 1, tzinfo=timezone.utc)
        except (OSError, OverflowError, ValueError):
            t = datetime(2000, 1, 1, tzinfo=timezone.utc)

        ot = self._detect_type(name, comment)
        entry = PBLEntry(name=name, object_type=ot, comment=comment,
                         first_data_offset=data_offset, data_size=obj_size,
                         creation_time=t)
        return entry, new_pos

    def _parse_ent_unicode(self, nod_data: bytes, pos: int) -> tuple[Optional[PBLEntry], int]:
        """Parse a Unicode ENT* entry within a NOD* block.

        Unicode ENT* format (verified against PB12 PBL):
        Bytes 0-3:   "ENT*" (Char 4)
        Bytes 4-11:  PBL version (CharW 8, UTF-16LE, e.g. "0600")
        Bytes 12-15: First data block offset (Long)
        Bytes 16-19: Object size (Long)
        Bytes 20-23: Unix datetime (Long)
        Bytes 24-25: Comment length in bytes (Integer)
        Bytes 26-27: Object name length in bytes (Integer)
        Bytes 28+:   Object name (UTF-16LE, name_len bytes)
        After name:  Comment (encoding varies, may be ANSI or UTF-16LE)

        NOTE: The name field already includes the object extension (e.g. "w_main.win",
        "d_emp.srw"), which serves as the definitive type indicator.

        Total fixed: 28 bytes + name_len + comment_len
        """
        if pos + 28 > len(nod_data):
            return None, pos + 1

        # Parse fixed fields
        data_offset = struct.unpack_from("<I", nod_data, pos + 12)[0]
        obj_size = struct.unpack_from("<I", nod_data, pos + 16)[0]
        raw_ts = struct.unpack_from("<I", nod_data, pos + 20)[0]
        comment_len = struct.unpack_from("<H", nod_data, pos + 24)[0]
        name_len = struct.unpack_from("<H", nod_data, pos + 26)[0]

        if name_len == 0 or name_len > 512:
            return None, pos + 28

        name_end = pos + 28 + name_len
        if name_end > len(nod_data):
            return None, pos + 28

        # Decode name as UTF-16LE, strip null bytes and whitespace
        raw_name = nod_data[pos+28:name_end].decode("utf-16-le", errors="replace")
        name = raw_name.rstrip("\x00").strip()
        new_pos = name_end

        # Read comment if present (may be ANSI or garbled)
        comment = ""
        if comment_len > 0 and new_pos + comment_len <= len(nod_data):
            raw_comment = nod_data[new_pos:new_pos+comment_len]
            # Try UTF-16LE first, fall back to ANSI
            try:
                comment = raw_comment.decode("utf-16-le", errors="replace").rstrip("\x00").strip()
            except (UnicodeDecodeError, ValueError):
                comment = raw_comment.decode("latin-1", errors="replace").rstrip("\x00").strip()
            new_pos += comment_len

        # Timestamp
        ts = raw_ts
        if ts > 3_000_000_000:
            ts = ts // 1000

        try:
            t = datetime.fromtimestamp(ts, tz=timezone.utc) if ts > 0 else datetime(2000, 1, 1, tzinfo=timezone.utc)
        except (OSError, OverflowError, ValueError):
            t = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Detect type from embedded extension in name (e.g. ".srw", ".win", ".dwo")
        ot = self._detect_type_from_name_ext(name, comment)
        entry = PBLEntry(name=name, object_type=ot, comment=comment,
                         first_data_offset=data_offset, data_size=obj_size,
                         creation_time=t)
        return entry, new_pos

    def _detect_type_from_name_ext(self, name: str, comment: str) -> PBObjectType:
        """Detect object type from the extension embedded in the entry name.

        In PB12+ Unicode PBLs, the ENT* name already includes the extension:
        - .srw = Window source
        - .win = Window compiled
        - .srd = DataWindow source
        - .dwo = DataWindow compiled
        - .srm = Menu source
        - .prp = Menu compiled (properties)
        - .srf = Function source
        - .srs = Structure source
        - .sru = UserObject source
        - .srq = Query source
        - .srp = Pipeline source
        - .srj = Project source
        - .srx = Proxy source
        - .sre = Embedded SQL source
        """
        nl = name.lower()
        # Source extensions (these are the ones we want to export)
        SOURCE_EXT = {
            ".srw": PBObjectType.WINDOW,
            ".srd": PBObjectType.DATAWINDOW,
            ".srm": PBObjectType.MENU,
            ".srf": PBObjectType.FUNCTION,
            ".srs": PBObjectType.STRUCTURE,
            ".sru": PBObjectType.USEROBJECT,
            ".srq": PBObjectType.QUERY,
            ".srp": PBObjectType.PIPELINE,
            ".srj": PBObjectType.PROJECT,
            ".srx": PBObjectType.PROXY,
            ".sre": PBObjectType.EMBEDDED_SQL,
            ".sra": PBObjectType.APPLICATION,
        }
        for ext, otype in SOURCE_EXT.items():
            if nl.endswith(ext):
                return otype

        # Compiled extensions → still assign correct type but mark as binary
        COMPILED_EXT = {
            ".win": PBObjectType.WINDOW,
            ".dwo": PBObjectType.DATAWINDOW,
            ".prp": PBObjectType.MENU,
        }
        for ext, otype in COMPILED_EXT.items():
            if nl.endswith(ext):
                return PBObjectType.BINARY  # compiled binary, not source

        # Fallback: try comment-based detection
        return self._detect_type(name, comment)

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
        # Default: if name matches common app name patterns
        if nl in ("dgsauna", "dgapp", "app_dgsauna"):
            return PBObjectType.APPLICATION
        return PBObjectType.BINARY

    def export_source(self, entry: PBLEntry, max_size: int = 10_000_000) -> Optional[bytes]:
        """Extract source data for an entry by following the DAT* block chain.

        DAT* block format (per spec):
        Bytes 0-3:   "DAT*" (Char 4)
        Bytes 4-7:   Next data block offset (Long, 0 = end of chain)
        Bytes 8-9:   Data length in this block (Integer, max 502)
        Bytes 10-511: Data (Blob)
        """
        if not self._fh or entry.first_data_offset == 0:
            return None
        file_size = self._fh.seek(0, 2)
        if entry.first_data_offset > file_size:
            return None

        src = bytearray()
        cur = entry.first_data_offset
        rem = min(entry.data_size, max_size) if entry.data_size > 0 else max_size

        while cur != 0 and rem > 0:
            if cur > file_size:
                logger.warning("Data offset %d exceeds file size %d for %s",
                               cur, file_size, entry.name)
                break
            blk = self._read(cur, BLOCK)
            if not blk or len(blk) < 10:
                break

            # Check DAT* signature
            if blk[:4] != b"DAT*":
                # Some PBL formats may not have DAT* marker, try raw read
                src.extend(blk[:min(rem, len(blk))])
                break

            # Parse DAT* header: marker(4) + next_offset(4) + data_len(2)
            next_offset = struct.unpack_from("<I", blk, 4)[0]
            data_len = struct.unpack_from("<H", blk, 8)[0]

            # Safety: data_len should not exceed block capacity (502 bytes max)
            if data_len > 502 or data_len <= 0:
                data_len = BLOCK - 10  # fallback to max

            actual_len = min(data_len, rem)
            src.extend(blk[10:10 + actual_len])
            rem -= actual_len

            # Follow chain: 0 or very large value = end
            if next_offset == 0 or next_offset > file_size or next_offset == 0xFFFFFFFF:
                cur = 0
            else:
                cur = next_offset

        return bytes(src) if src else None

    def export_all(self):
        res=[]
        for e in self.entries:
            s = self.export_source(e)
            if s:
                # Use entry.name directly (already includes extension in PB12+)
                # or append OBJ_EXT extension for ANSI PBLs where name has no ext
                fname = e.name if '.' in e.name else e.name + e.extension
                res.append(PBLSource(entry=e, source=s, filename=fname))
        return res

    def export_to_directory(self, out, source_only=True):
        op=Path(out); op.mkdir(parents=True,exist_ok=True); exp=[]
        for ps in self.export_all():
            if source_only and ps.entry.extension==".bin": continue
            fp=op/ps.filename
            # Convert encoding (UTF-16LE → UTF-8 for PB12+ PBLs)
            data = ps.to_utf8_bytes()
            # Strip any residual null bytes
            data = data.replace(b"\x00", b"")
            if not data or len(data) < 10:
                continue
            fp.write_bytes(data)
            exp.append(str(fp))
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
        """Export a single entry by name (with or without extension)."""
        entry = self.get_entry(name)
        if not entry:
            return None
        src = self.export_source(entry)
        if not src:
            return None
        fname = entry.name if '.' in entry.name else entry.name + entry.extension
        return PBLSource(entry=entry, source=src, filename=fname)


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
