"""pbl_writer.py — Pure-Python PowerBuilder Library Writer.

Creates valid .pbl binary files from source entries, with NO external
dependencies and NO PBORCA DLL required.

Format reference (verified against chunk_engine.py + PbdViewer):
  HDR*  (512B ANSI / 1024B Unicode)  — library header
  FRE*  (512B)                        — free-block sentinel
  NOD*  (3072B, 6 × 512B)            — B-tree node(s) containing ENT* entries
  DAT*  (512B per block, chained)    — data blocks for each entry

All blocks are 512-byte aligned.
ENT* header layout:
  ANSI:    ENT*(4) + ver(4) + offset(4) + size(4) + ts(4) + pad(6) + name_len(2) = 24B
  Unicode: ENT*(4) + ver(8) + offset(4) + size(4) + ts(4) + pad(6) + name_len(2) = 28B

DAT* block layout (each block 512B):
  DAT*(4) + next_offset(4) + data_len(2) + payload(up to 502B) + padding

Usage::

    from pb_devkit.pbl_writer import PblWriter
    from pb_devkit.chunk_engine import PBObjectType

    w = PblWriter(pb_version=12, encoding="unicode")
    w.add_source_file("my_window.srw")     # auto-detect type
    w.add_entry("w_login.srw", PBObjectType.WINDOW, source_bytes)
    w.write("output.pbl")
"""
from __future__ import annotations

import io
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .chunk_engine import OBJ_EXT, SOURCE_EXT_MAP, PBObjectType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BLOCK_SIZE = 512
NODE_BLOCK_SIZE = 3072      # 6 × 512B
MAX_DATA_PER_BLOCK = 502    # DAT* payload capacity
ENTRIES_PER_NODE = 40       # Conservative upper bound per NOD* block
VERSION_ANSI = b"0600"      # 4-byte ANSI version string (PB6 compat)
VERSION_UNICODE = b"1" + b"\x00" + b"2" + b"\x00"  # "12" in UTF-16LE (8 bytes with pad)
VERSION_UNICODE_FULL = b"1\x002\x005\x000\x00"       # "1250" UTF-16LE (8 bytes)


# ---------------------------------------------------------------------------
# Internal entry representation
# ---------------------------------------------------------------------------
@dataclass
class _PblEntry:
    name: str                       # full name with extension (e.g. "w_login.srw")
    obj_type: PBObjectType
    data: bytes                     # raw source bytes (UTF-16LE for Unicode PBLs)
    timestamp: int = 0              # unix timestamp

    @property
    def encoded_name_ansi(self) -> bytes:
        return self.name.encode("latin-1", errors="replace")

    @property
    def encoded_name_unicode(self) -> bytes:
        return self.name.encode("utf-16-le")


# ---------------------------------------------------------------------------
# PblWriter
# ---------------------------------------------------------------------------
class PblWriter:
    """Builds a valid PBL binary from in-memory entries.

    Args:
        pb_version: Target PB version (6, 9, 10, 11, 12, etc.)
        encoding:   "unicode" (PB10+) or "ansi" (PB5-9)
    """

    def __init__(self, pb_version: int = 12, encoding: str = "unicode"):
        self.pb_version = pb_version
        self.encoding = encoding.lower()
        self._is_unicode = self.encoding == "unicode"
        self._entries: List[_PblEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_entry(
        self,
        name: str,
        obj_type: PBObjectType,
        source: Union[str, bytes],
        timestamp: Optional[int] = None,
    ) -> None:
        """Add a named PB object entry.

        Args:
            name:      Full entry name including extension (e.g. "w_login.srw")
            obj_type:  PBObjectType enum value
            source:    Source text (str) or raw bytes
            timestamp: Unix timestamp (defaults to now)
        """
        ts = timestamp or int(time.time())

        if isinstance(source, str):
            if self._is_unicode:
                data = source.encode("utf-16-le")
            else:
                data = source.encode("latin-1", errors="replace")
        else:
            data = source

        # Deduplicate
        if any(e.name.lower() == name.lower() for e in self._entries):
            logger.warning("Duplicate entry '%s' — skipping", name)
            return

        self._entries.append(_PblEntry(
            name=name,
            obj_type=obj_type,
            data=data,
            timestamp=ts,
        ))
        logger.debug("PblWriter: added %s (%s, %d bytes)", name, obj_type.name, len(data))

    def add_source_file(self, path: Union[str, Path], timestamp: Optional[int] = None) -> bool:
        """Add a source file by path, auto-detecting type from extension.

        Returns True on success, False if file is unsupported/missing.
        """
        p = Path(path)
        if not p.exists():
            logger.warning("Source file not found: %s", p)
            return False

        ext = p.suffix.lower()
        if ext not in SOURCE_EXT_MAP:
            logger.debug("Unsupported extension '%s' — skip %s", ext, p.name)
            return False

        obj_type = PBObjectType(SOURCE_EXT_MAP[ext])
        ts = timestamp or int(p.stat().st_mtime)

        try:
            raw = p.read_bytes()
            # Detect encoding: UTF-16LE BOM → keep as-is; otherwise re-encode
            if raw[:2] == b"\xff\xfe":
                # Already UTF-16LE
                if self._is_unicode:
                    data = raw[2:]  # strip BOM
                else:
                    text = raw[2:].decode("utf-16-le", errors="replace")
                    data = text.encode("latin-1", errors="replace")
            elif raw[:2] == b"\xfe\xff":
                # UTF-16BE → convert
                text = raw[2:].decode("utf-16-be", errors="replace")
                if self._is_unicode:
                    data = text.encode("utf-16-le")
                else:
                    data = text.encode("latin-1", errors="replace")
            else:
                # Assume UTF-8 / ASCII / Latin-1
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")
                if self._is_unicode:
                    data = text.encode("utf-16-le")
                else:
                    data = text.encode("latin-1", errors="replace")
        except OSError as e:
            logger.error("Cannot read %s: %s", p, e)
            return False

        self.add_entry(p.name, obj_type, data, ts)
        return True

    def add_source_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = False,
    ) -> int:
        """Add all supported source files from a directory.

        Returns count of files added.
        """
        d = Path(directory)
        if not d.is_dir():
            raise ValueError(f"Not a directory: {d}")

        pattern = "**/*" if recursive else "*"
        added = 0
        for p in sorted(d.glob(pattern)):
            if p.is_file() and p.suffix.lower() in SOURCE_EXT_MAP:
                if self.add_source_file(p):
                    added += 1
        return added

    def write(self, output_path: Union[str, Path]) -> int:
        """Write the PBL binary to disk.

        Returns: file size in bytes.
        Raises: ValueError if no entries have been added.
        """
        if not self._entries:
            raise ValueError("No entries to write — add entries first.")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        buf = io.BytesIO()
        self._build(buf)

        size = buf.tell()
        out.write_bytes(buf.getvalue())
        logger.info("PblWriter: wrote %d bytes to %s (%d entries)",
                    size, out, len(self._entries))
        return size

    def to_bytes(self) -> bytes:
        """Return the PBL binary as bytes without writing to disk."""
        if not self._entries:
            raise ValueError("No entries to write.")
        buf = io.BytesIO()
        self._build(buf)
        return buf.getvalue()

    def entry_count(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Internal build logic
    # ------------------------------------------------------------------

    def _build(self, buf: io.BytesIO) -> None:
        """Main builder: HDR* → FRE* → NOD* nodes → DAT* chains."""
        hdr_size = 1024 if self._is_unicode else 512

        # ── Layout plan ───────────────────────────────────────────────
        # 1. Calculate DAT* block layout for every entry
        # 2. Calculate NOD* block count
        # 3. Calculate absolute offsets
        # Offsets: HDR*(1B) + FRE*(1B) + NOD*(N blocks of 6 × 512B) + DAT* chains

        node_count = max(1, (len(self._entries) + ENTRIES_PER_NODE - 1) // ENTRIES_PER_NODE)
        dat_start = hdr_size + BLOCK_SIZE + node_count * NODE_BLOCK_SIZE

        # Assign DAT* offsets per entry
        entry_offsets: List[int] = []
        cur_dat_offset = dat_start
        for e in self._entries:
            entry_offsets.append(cur_dat_offset)
            block_count = max(1, (len(e.data) + MAX_DATA_PER_BLOCK - 1) // MAX_DATA_PER_BLOCK)
            cur_dat_offset += block_count * BLOCK_SIZE

        # ── Write sections ────────────────────────────────────────────
        self._write_hdr(buf, hdr_size)
        self._write_fre(buf)

        # Write NOD* node(s)
        for node_idx in range(node_count):
            start = node_idx * ENTRIES_PER_NODE
            end = min(start + ENTRIES_PER_NODE, len(self._entries))
            slice_entries = self._entries[start:end]
            slice_offsets = entry_offsets[start:end]
            self._write_nod(buf, slice_entries, slice_offsets)

        # Write DAT* chains for each entry
        for e in self._entries:
            self._write_dat_chain(buf, e.data)

        # Final alignment to 512B
        pos = buf.tell()
        rem = pos % BLOCK_SIZE
        if rem:
            buf.write(b"\x00" * (BLOCK_SIZE - rem))

    def _write_hdr(self, buf: io.BytesIO, hdr_size: int) -> None:
        """Write HDR* header block."""
        block = bytearray(hdr_size)

        # Signature
        block[0:4] = b"HDR*"

        if self._is_unicode:
            # Unicode PBL (PB10+): "PowerBuilder" as UTF-16LE at offset 4
            pb_str = "PowerBuilder Library\x00"
            pb_encoded = pb_str.encode("utf-16-le")
            block[4:4 + len(pb_encoded)] = pb_encoded

            # Version string e.g. "1250" for PB12.5
            ver_str = f"{self.pb_version}50\x00" if self.pb_version < 10 else f"{self.pb_version}00\x00"
            ver_encoded = ver_str.encode("utf-16-le")
            offset = 4 + len(pb_encoded)
            block[offset:offset + len(ver_encoded)] = ver_encoded
        else:
            # ANSI PBL (PB5-9)
            pb_str = b"PowerBuilder Library\x00"
            block[4:4 + len(pb_str)] = pb_str
            ver_str = f"0{self.pb_version}00\x00".encode("ascii")
            block[4 + len(pb_str): 4 + len(pb_str) + len(ver_str)] = ver_str

        # Entry count at a known offset (informational, not strictly parsed)
        struct.pack_into("<I", block, hdr_size - 8, len(self._entries))

        buf.write(bytes(block))

    def _write_fre(self, buf: io.BytesIO) -> None:
        """Write FRE* free-block sentinel (512 bytes)."""
        block = bytearray(BLOCK_SIZE)
        block[0:4] = b"FRE*"
        buf.write(bytes(block))

    def _write_nod(
        self,
        buf: io.BytesIO,
        entries: List[_PblEntry],
        offsets: List[int],
    ) -> None:
        """Write a single NOD* block (3072 bytes = 6 × 512B) containing ENT* entries."""
        block = bytearray(NODE_BLOCK_SIZE)
        pos = 0

        # NOD* header (32 bytes)
        block[0:4] = b"NOD*"
        # right_sibling offset (0 = no sibling)
        struct.pack_into("<I", block, 12, 0)
        # entry count
        struct.pack_into("<H", block, 20, len(entries))
        pos = 32

        # ENT* entries
        num = 2 if self._is_unicode else 1  # version word count

        for e, dat_offset in zip(entries, offsets):
            if self._is_unicode:
                name_bytes = e.encoded_name_unicode
                ver_bytes = VERSION_UNICODE_FULL  # 8 bytes: "1250" in UTF-16LE
                ent_hdr_size = 28
            else:
                name_bytes = e.encoded_name_ansi
                ver_bytes = VERSION_ANSI          # 4 bytes
                ent_hdr_size = 24

            # name_buf layout (verified from ChunkEngine parser):
            #   name_buf = name_bytes + ver_suffix
            #   ver_suffix: 2B for Unicode (\x01\x00), 1B for ANSI (\x01)
            # Parser reads: name = name_buf[:name_buf_len - num]
            # So: actual name data = name_bytes, trailing num bytes discarded
            if self._is_unicode:
                ver_suffix = b"\x01\x00"   # 2 bytes appended after name
            else:
                ver_suffix = b"\x01"       # 1 byte appended after name

            name_buf = name_bytes + ver_suffix
            name_buf_len = len(name_buf)

            total_ent_size = ent_hdr_size + name_buf_len

            if pos + total_ent_size > NODE_BLOCK_SIZE:
                logger.warning("NOD* block overflow — entry '%s' won't fit, truncating", e.name)
                break

            # ENT* header
            block[pos:pos + 4] = b"ENT*"
            block[pos + 4:pos + 4 + len(ver_bytes)] = ver_bytes

            num2 = 4 + num * 4  # start of fixed fields

            struct.pack_into("<I", block, pos + num2, dat_offset)          # data_offset
            struct.pack_into("<I", block, pos + num2 + 4, len(e.data))     # data_size
            struct.pack_into("<I", block, pos + num2 + 8, e.timestamp)     # timestamp
            # 2 unknown bytes at num2+12 and num2+13 — leave as zero
            struct.pack_into("<H", block, pos + num2 + 14, name_buf_len)   # name_buf_len

            pos += ent_hdr_size

            # Name buffer
            block[pos:pos + name_buf_len] = name_buf
            pos += name_buf_len

        buf.write(bytes(block))

    def _write_dat_chain(self, buf: io.BytesIO, data: bytes) -> None:
        """Write a DAT* block chain for the given data bytes."""
        total = len(data)
        offset = 0
        blocks: List[bytes] = []

        while offset < total:
            chunk = data[offset:offset + MAX_DATA_PER_BLOCK]
            chunk_len = len(chunk)

            block = bytearray(BLOCK_SIZE)
            block[0:4] = b"DAT*"
            # next_offset placeholder — filled in after all blocks are built
            struct.pack_into("<I", block, 4, 0)
            struct.pack_into("<H", block, 8, chunk_len)
            block[10:10 + chunk_len] = chunk

            blocks.append(bytes(block))
            offset += chunk_len

        if not blocks:
            # Zero-length data: write one empty DAT* block
            block = bytearray(BLOCK_SIZE)
            block[0:4] = b"DAT*"
            blocks.append(bytes(block))

        # Patch next_offset fields
        # We need the absolute file position of each block.
        # Since we don't know the base offset here, we pre-write and then fix up.
        # Strategy: calculate base from current buf position.
        base = buf.tell()

        patched: List[bytes] = []
        for i, blk in enumerate(blocks):
            ba = bytearray(blk)
            if i < len(blocks) - 1:
                next_off = base + (i + 1) * BLOCK_SIZE
                struct.pack_into("<I", ba, 4, next_off)
            else:
                struct.pack_into("<I", ba, 4, 0)  # last block
            patched.append(bytes(ba))

        for blk in patched:
            buf.write(blk)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def pack_directory(
    source_dir: Union[str, Path],
    output_pbl: Union[str, Path],
    pb_version: int = 12,
    encoding: str = "unicode",
    recursive: bool = False,
) -> int:
    """One-shot: scan a source directory and write a .pbl file.

    Args:
        source_dir:  Directory with .sr* source files
        output_pbl:  Path for the output .pbl file
        pb_version:  Target PB version (default 12)
        encoding:    "unicode" or "ansi"
        recursive:   If True, scan subdirectories recursively

    Returns:
        Number of entries written.
    """
    w = PblWriter(pb_version=pb_version, encoding=encoding)
    added = w.add_source_directory(source_dir, recursive=recursive)
    if added == 0:
        logger.warning("No source files found in %s", source_dir)
        return 0
    w.write(output_pbl)
    return added


def pack_pbl_tree(
    pbl_tree_dir: Union[str, Path],
    output_dir: Union[str, Path],
    pb_version: int = 12,
    encoding: str = "unicode",
) -> dict:
    """Pack a pb_source/ PBL tree (output of export_pbl_tree) back into .pbl files.

    Expects structure like::

        pbl_tree_dir/
          common.pbl/
            w_base.srw
            n_ds.sru
          dw_app.pbl/
            d_orders.srd
            ...

    Creates one .pbl per subdirectory.

    Returns:
        Dict mapping pbl_name -> entry count
    """
    src = Path(pbl_tree_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = {}

    pbl_dirs = sorted([d for d in src.iterdir() if d.is_dir()])
    for pbl_dir in pbl_dirs:
        pbl_name = pbl_dir.name  # e.g. "common.pbl"
        if not pbl_name.endswith(".pbl"):
            pbl_name += ".pbl"

        w = PblWriter(pb_version=pb_version, encoding=encoding)
        added = w.add_source_directory(pbl_dir, recursive=False)

        if added == 0:
            logger.debug("No source files in %s — skip", pbl_dir.name)
            continue

        output_path = out / pbl_name
        w.write(output_path)
        results[pbl_name] = added
        logger.info("Packed %s: %d entries", pbl_name, added)

    return results
