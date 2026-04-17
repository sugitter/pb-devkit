"""Tests for PEExtractor and ChunkEngine memory mode."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pb_devkit.pe_extractor import PEExtractor, PBDResource, SectionInfo
from pb_devkit.chunk_engine import ChunkEngine, PBEntry, PBObjectType


def _build_minimal_pe_with_resource(resource_data: bytes) -> bytes:
    """Build a minimal PE file with a single embedded resource.

    Structure:
      DOS Header (64 bytes min, e_lfanew at 0x3C)
      PE Signature (4 bytes)
      COFF Header (20 bytes)
      Optional Header PE32 (96 bytes min + data dirs)
      Section Table: .rsrc (40 bytes)
      .rsrc section data:
        Resource Directory (level 1: 1 type, level 2: 1 id, level 3: 1 lang)
        Resource Data Entry (8 bytes)
        Resource Data (resource_data)
    """
    # Layout constants
    DOS_SIZE = 64
    PE_SIG_OFFSET = DOS_SIZE  # e_lfanew = 64
    PE_SIG_SIZE = 4
    COFF_OFFSET = PE_SIG_OFFSET + PE_SIG_SIZE
    COFF_SIZE = 20
    OPT_OFFSET = COFF_OFFSET + COFF_SIZE
    # PE32 Optional Header: 96 bytes standard + 128 bytes data dirs (16 * 8)
    OPT_SIZE = 96 + 128
    SECTION_TABLE_OFFSET = OPT_OFFSET + OPT_SIZE
    NUM_SECTIONS = 1
    SECTION_TABLE_SIZE = NUM_SECTIONS * 40
    SECTION_START = SECTION_TABLE_OFFSET + SECTION_TABLE_SIZE

    # Resource section layout:
    # Level 1 Dir (16 bytes) + 1 entry (8 bytes) = 24
    # Level 2 Dir (16 bytes) + 1 entry (8 bytes) = 24
    # Level 3 Dir (16 bytes) + 1 entry (8 bytes) = 24
    # Resource Data Entry (8 bytes)
    # Resource data (len(resource_data))
    RES_DIR1_OFFSET = SECTION_START
    RES_DIR1_ENTRY = RES_DIR1_OFFSET + 16
    RES_DIR2_OFFSET = RES_DIR1_ENTRY + 8
    RES_DIR2_ENTRY = RES_DIR2_OFFSET + 16
    RES_DIR3_OFFSET = RES_DIR2_ENTRY + 8
    RES_DIR3_ENTRY = RES_DIR3_OFFSET + 16
    RES_DATA_ENTRY_OFFSET = RES_DIR3_ENTRY + 8
    RES_DATA_OFFSET = RES_DATA_ENTRY_OFFSET + 8
    RES_SECTION_SIZE = RES_DATA_OFFSET - SECTION_START + len(resource_data)

    # Align section to 512 bytes
    RES_SECTION_ALIGNED = ((RES_SECTION_SIZE + 511) // 512) * 512
    TOTAL_SIZE = SECTION_START + RES_SECTION_ALIGNED

    buf = bytearray(TOTAL_SIZE)

    # DOS Header
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, PE_SIG_OFFSET)

    # PE Signature
    buf[PE_SIG_OFFSET:PE_SIG_OFFSET + 4] = b"PE\x00\x00"

    # COFF Header
    coff = COFF_OFFSET
    struct.pack_into("<H", buf, coff + 0, 0x014C)      # Machine: i386
    struct.pack_into("<H", buf, coff + 2, NUM_SECTIONS)  # NumberOfSections
    struct.pack_into("<H", buf, coff + 16, OPT_SIZE)     # SizeOfOptionalHeader
    struct.pack_into("<H", buf, coff + 18, 0x0002)       # Characteristics: EXECUTABLE_IMAGE

    # Optional Header PE32
    opt = OPT_OFFSET
    struct.pack_into("<H", buf, opt + 0, 0x010B)         # Magic: PE32
    # SizeOfImage, SizeOfHeaders, etc — not critical for parsing
    # Data Directory [2] = Resource Directory
    # Standard fields: 96 bytes, then 16 data dirs * 8 bytes each
    # Data dir offset = opt + 96 + 2*8 = opt + 112
    rsrc_rva = SECTION_START  # Use file offset as RVA (image base = 0)
    rsrc_size = RES_SECTION_SIZE
    # Data Directories start at opt + 96 (PE32); DD[2] = Resource at opt + 96 + 2*8
    struct.pack_into("<I", buf, opt + 96 + 2 * 8, rsrc_rva)       # Resource Directory RVA
    struct.pack_into("<I", buf, opt + 96 + 2 * 8 + 4, rsrc_size)   # Resource Directory Size

    # Section Table: .rsrc
    sec = SECTION_TABLE_OFFSET
    buf[sec:sec + 8] = b".rsrc\x00\x00\x00"
    struct.pack_into("<I", buf, sec + 8, RES_SECTION_ALIGNED)   # VirtualSize
    struct.pack_into("<I", buf, sec + 12, SECTION_START)         # VirtualAddress (RVA)
    struct.pack_into("<I", buf, sec + 16, RES_SECTION_SIZE)     # SizeOfRawData
    struct.pack_into("<I", buf, sec + 20, SECTION_START)         # PointerToRawData
    struct.pack_into("<I", buf, sec + 36, 0x40000040)            # Characteristics (INITIALIZED_DATA | READ)

    # Resource Directory Level 1 (Type)
    struct.pack_into("<I", buf, RES_DIR1_OFFSET + 0, 0)     # Characteristics
    struct.pack_into("<H", buf, RES_DIR1_OFFSET + 12, 0)    # NumberOfNamedEntries
    struct.pack_into("<H", buf, RES_DIR1_OFFSET + 14, 1)    # NumberOfIdEntries

    # Sub-directory offsets are RELATIVE to .rsrc section base (SECTION_START)
    dir2_rel = RES_DIR2_OFFSET - SECTION_START
    dir3_rel = RES_DIR3_OFFSET - SECTION_START
    data_entry_rel = RES_DATA_ENTRY_OFFSET - SECTION_START

    # Entry: type ID = 6 (RT_RCDATA), points to level 2 dir
    # High bit set on offset = subdirectory (offset relative to .rsrc base)
    struct.pack_into("<I", buf, RES_DIR1_ENTRY + 0, 6)                  # Type ID = RT_RCDATA
    struct.pack_into("<I", buf, RES_DIR1_ENTRY + 4, dir2_rel | 0x80000000)  # Sub-dir offset (rel)

    # Resource Directory Level 2 (Resource ID)
    struct.pack_into("<I", buf, RES_DIR2_OFFSET + 0, 0)
    struct.pack_into("<H", buf, RES_DIR2_OFFSET + 12, 0)
    struct.pack_into("<H", buf, RES_DIR2_OFFSET + 14, 1)
    struct.pack_into("<I", buf, RES_DIR2_ENTRY + 0, 1)                   # Resource ID = 1
    struct.pack_into("<I", buf, RES_DIR2_ENTRY + 4, dir3_rel | 0x80000000)

    # Resource Directory Level 3 (Language)
    struct.pack_into("<I", buf, RES_DIR3_OFFSET + 0, 0)
    struct.pack_into("<H", buf, RES_DIR3_OFFSET + 12, 0)
    struct.pack_into("<H", buf, RES_DIR3_OFFSET + 14, 1)
    struct.pack_into("<I", buf, RES_DIR3_ENTRY + 0, 0x0409)              # Language = English
    # Data entry offset is relative to .rsrc base (no high bit = data entry)
    struct.pack_into("<I", buf, RES_DIR3_ENTRY + 4, data_entry_rel)  # Data Entry offset (rel)

    # Resource Data Entry (8 bytes) — contains a TRUE RVA + Size
    # RVA uses the section's VirtualAddress (which equals SECTION_START in this test)
    struct.pack_into("<I", buf, RES_DATA_ENTRY_OFFSET + 0, RES_DATA_OFFSET)  # Data RVA
    struct.pack_into("<I", buf, RES_DATA_ENTRY_OFFSET + 4, len(resource_data))  # Size

    # Resource Data
    buf[RES_DATA_OFFSET:RES_DATA_OFFSET + len(resource_data)] = resource_data

    return bytes(buf)


class TestPEExtractorBasic(unittest.TestCase):
    """Tests for PEExtractor with synthetic PE files."""

    def test_is_pe_file(self):
        """Test PE file detection."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ" + b"\x00" * 62)
            pe_path = f.name
        try:
            self.assertTrue(PEExtractor.is_pe_file(pe_path))
        finally:
            Path(pe_path).unlink()

    def test_is_pe_file_not_pe(self):
        """Test non-PE file detection."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"This is not a PE file")
            not_pe_path = f.name
        try:
            self.assertFalse(PEExtractor.is_pe_file(not_pe_path))
        finally:
            Path(not_pe_path).unlink()

    def test_is_pe_file_missing(self):
        """Test missing file."""
        self.assertFalse(PEExtractor.is_pe_file("/nonexistent/file.exe"))

    def test_reject_non_mz(self):
        """PEExtractor should raise ValueError for non-MZ files."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"This is not a PE file at all, but big enough" + b"\x00" * 40)
            bad_path = f.name
        try:
            with self.assertRaises(ValueError):
                PEExtractor(bad_path).extract_pbd_resources()
        finally:
            Path(bad_path).unlink()

    def test_reject_bad_pe_signature(self):
        """PEExtractor should raise ValueError for bad PE signature."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ" + b"\x00" * 62)  # e_lfanew = 0
            bad_path = f.name
        try:
            with self.assertRaises(ValueError):
                PEExtractor(bad_path).extract_pbd_resources()
        finally:
            Path(bad_path).unlink()

    def test_extract_pbd_resource_with_hdr(self):
        """Extract a PBD resource (starts with HDR*) from a synthetic PE."""
        # Build a minimal valid PB library header (HDR* block)
        # HDR*(512b) + FRE*(512b) — minimal valid PB library
        hdr_block = bytearray(1024)
        hdr_block[0:4] = b"HDR*"
        hdr_block[4:20] = b"PowerBuilder\x00\x00\x00"
        hdr_block[512:516] = b"FRE*"
        # NOD* block (3072 bytes)
        nod_block = bytearray(3072)
        nod_block[0:4] = b"NOD*"
        # entry_count = 0
        struct.pack_into("<H", nod_block, 20, 0)

        pbd_data = bytes(hdr_block) + bytes(nod_block)
        pe_data = _build_minimal_pe_with_resource(pbd_data)

        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(pe_data)
            pe_path = f.name
        try:
            ext = PEExtractor(pe_path)
            resources = ext.extract_pbd_resources()
            self.assertEqual(len(resources), 1)
            self.assertTrue(resources[0].is_valid_pbd)
            self.assertTrue(resources[0].data[:4] == b"HDR*")
            self.assertEqual(resources[0].type_id, 6)  # RT_RCDATA
            self.assertEqual(resources[0].resource_id, 1)
            self.assertEqual(resources[0].size, len(pbd_data))
        finally:
            Path(pe_path).unlink()

    def test_extract_no_pbd_resources(self):
        """Non-HDR* resources should be filtered out."""
        pe_data = _build_minimal_pe_with_resource(b"This is just random data, not HDR*")
        with tempfile.NamedTemporaryFile(suffix=".dll", delete=False) as f:
            f.write(pe_data)
            pe_path = f.name
        try:
            ext = PEExtractor(pe_path)
            resources = ext.extract_pbd_resources()
            self.assertEqual(len(resources), 0)
        finally:
            Path(pe_path).unlink()

    def test_extract_multiple_pbd_resources(self):
        """Test that we can construct and validate a basic PE."""
        # Simple smoke test with a minimal PBD
        pbd_data = b"HDR*" + b"\x00" * 500 + b"FRE*" + b"\x00" * 508 + b"NOD*" + b"\x00" * 3068
        pe_data = _build_minimal_pe_with_resource(pbd_data)

        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(pe_data)
            pe_path = f.name
        try:
            ext = PEExtractor(pe_path)
            resources = ext.extract_pbd_resources()
            self.assertEqual(len(resources), 1)
            self.assertTrue(resources[0].is_valid_pbd)
        finally:
            Path(pe_path).unlink()

    def test_pbd_resource_properties(self):
        """Test PBDResource dataclass properties."""
        res = PBDResource(
            type_id=6, resource_id=1, language_id=0x0409,
            rva=0x1000, file_offset=0x800, size=1024,
            data=b"HDR*" + b"\x00" * 1020,
            name="RT_RCDATA/1",
        )
        self.assertTrue(res.is_valid_pbd)
        self.assertEqual(res.name, "RT_RCDATA/1")

    def test_pbd_resource_not_valid(self):
        """Test PBDResource with non-HDR* data."""
        res = PBDResource(
            type_id=6, resource_id=2, language_id=0,
            rva=0, file_offset=0, size=100,
            data=b"Some random data",
        )
        self.assertFalse(res.is_valid_pbd)


class TestChunkEngineMemoryMode(unittest.TestCase):
    """Test ChunkEngine with in-memory bytes (simulating PE-extracted PBD)."""

    def test_chunk_engine_memory_basic(self):
        """ChunkEngine should parse a valid PB library from bytes (Unicode mode)."""
        # Build minimal PB library: HDR*(1024 Unicode) + FRE*(512) + NOD*(3072, empty tree)
        hdr = bytearray(1024)
        hdr[0:4] = b"HDR*"
        # In a real Unicode PBL, the HDR block is 1024 bytes.
        # FRE* starts at offset 1024, NOT 512.
        # We must NOT have FRE* at offset 512.
        hdr[4:6] = b"\xff\xfe"  # BOM to help unicode detection
        # Clear offset 512 area to ensure no false FRE* match
        for i in range(512, 520):
            hdr[i] = 0

        fre = bytearray(512)
        fre[0:4] = b"FRE*"

        nod = bytearray(3072)
        nod[0:4] = b"NOD*"
        struct.pack_into("<H", nod, 20, 0)  # 0 entries

        data = bytes(hdr) + bytes(fre) + bytes(nod)
        with ChunkEngine(data=data) as engine:
            self.assertEqual(len(engine.entries), 0)
            self.assertTrue(engine.is_unicode)
            self.assertEqual(engine.header_size, 1024)

    def test_chunk_engine_memory_ansi(self):
        """ChunkEngine should detect ANSI PB library from bytes."""
        # ANSI: HDR* at offset 0 (512 bytes), FRE* at offset 512
        hdr = bytearray(512)
        hdr[0:4] = b"HDR*"
        hdr[512-4:512] = b"\x00\x00\x00\x00"  # Will be overwritten by FRE*

        # Full buffer
        buf = bytearray(1536)
        buf[0:512] = hdr
        buf[0:4] = b"HDR*"
        buf[512:516] = b"FRE*"
        buf[1024:1028] = b"NOD*"
        struct.pack_into("<H", buf, 1024 + 20, 0)

        with ChunkEngine(data=bytes(buf)) as engine:
            self.assertEqual(len(engine.entries), 0)
            self.assertFalse(engine.is_unicode)
            self.assertEqual(engine.header_size, 512)

    def test_chunk_engine_memory_invalid(self):
        """ChunkEngine should raise ValueError for non-PB data."""
        with self.assertRaises(ValueError):
            ChunkEngine(data=b"This is not a PB library").open()

    def test_chunk_engine_memory_file_path_none(self):
        """ChunkEngine should require either path or data."""
        with self.assertRaises(ValueError):
            ChunkEngine()

    def test_pb_entry_binary_type_name(self):
        """PBEntry with BINARY type should return 'Binary' as type_name."""
        entry = PBEntry(name="test.win", object_type=PBObjectType.BINARY)
        self.assertEqual(entry.type_name, "Binary")

    def test_section_info_dataclass(self):
        """Test SectionInfo dataclass."""
        sec = SectionInfo(
            name=".rsrc",
            virtual_size=4096,
            rva=0x4000,
            raw_offset=0x2000,
            raw_size=4096,
            characteristics=0x40000040,
        )
        self.assertEqual(sec.name, ".rsrc")
        self.assertEqual(sec.rva, 0x4000)
        self.assertEqual(sec.raw_offset, 0x2000)


class TestPEExtractorResourceNaming(unittest.TestCase):
    """Test resource naming logic."""

    def test_make_resource_name_known_types(self):
        """Known resource types should use their standard names."""
        self.assertEqual(PEExtractor._make_resource_name(1, 100), "RT_CURSOR/100")
        self.assertEqual(PEExtractor._make_resource_name(2, 200), "RT_BITMAP/200")
        self.assertEqual(PEExtractor._make_resource_name(6, 1), "RT_RCDATA/1")
        self.assertEqual(PEExtractor._make_resource_name(24, 1), "RT_MANIFEST/1")

    def test_make_resource_name_unknown_type(self):
        """Unknown resource types should use numeric ID."""
        self.assertEqual(PEExtractor._make_resource_name(999, 42), "999/42")

    def test_make_resource_name_string_ids(self):
        """String resource IDs should work."""
        self.assertEqual(PEExtractor._make_resource_name(6, "my_res"), "RT_RCDATA/my_res")


if __name__ == "__main__":
    unittest.main()
