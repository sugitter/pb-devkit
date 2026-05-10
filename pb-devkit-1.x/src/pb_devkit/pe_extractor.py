"""PE format extractor — extracts embedded PBD resources from PE executables/DLLs.

PE file structure:
  DOS Header (e_lfanew → PE offset)
  → PE Signature ("PE\\x00\\x00")
  → COFF Header (machine, num_sections, optional_hdr_size, ...)
  → Optional Header (PE32 or PE32+, Data Directories)
  → Section Table (one entry per section: .text, .rdata, .rsrc, ...)
  → Sections

PB embeds PBD data as custom resources in the .rsrc section.
This module:
  1. Parses DOS/PE/COFF/Optional headers
  2. Locates .rsrc section (RVA → file offset mapping)
  3. Traverses the Resource Directory tree (Type → ID → Language → Data)
  4. Checks each resource for HDR* signature (valid PB library)
  5. Returns extracted PBD bytes for further parsing by ChunkEngine

Zero external dependencies — uses only Python stdlib struct module.
"""
from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SectionInfo:
    """A PE section header entry."""
    name: str
    virtual_size: int      # SizeOfRawData (actual)
    rva: int               # VirtualAddress
    raw_offset: int        # PointerToRawData
    raw_size: int          # SizeOfRawData
    characteristics: int = 0


@dataclass
class PBDResource:
    """An embedded PBD resource extracted from a PE file."""
    type_id: int | str
    resource_id: int | str
    language_id: int
    rva: int
    file_offset: int
    size: int
    data: bytes
    name: str = ""

    @property
    def is_valid_pbd(self) -> bool:
        """Check if this resource starts with HDR* (valid PB library signature)."""
        return len(self.data) >= 4 and self.data[:4] == b"HDR*"


# ---------------------------------------------------------------------------
# PEExtractor
# ---------------------------------------------------------------------------

class PEExtractor:
    """Extract embedded PBD resources from a PE format executable or DLL.

    Usage::

        ext = PEExtractor("dgsauna.exe")
        resources = ext.extract_pbd_resources()
        for res in resources:
            print(f"PBD: {res.name}, {len(res.data)} bytes, {len(res.entries)} entries")

        # Or integrate with ChunkEngine directly:
        from pb_devkit.chunk_engine import ChunkEngine
        for res in resources:
            with ChunkEngine(data=res.data) as engine:
                for entry in engine.entries:
                    print(f"  {entry.name}")
    """

    # PE signature
    PE_SIGNATURE = b"PE\x00\x00"
    # DOS signature
    MZ_SIGNATURE = b"MZ"
    # HDR* signature for PB libraries
    HDR_SIGNATURE = b"HDR*"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: bytes = b""
        self._sections: list[SectionInfo] = []
        self._is_pe32_plus: bool = False

    def extract_pbd_resources(self) -> list[PBDResource]:
        """Extract all embedded PBD resources from the PE file.

        Returns:
            List of PBDResource objects. Only resources with valid HDR* signature
            are included in the result.
        """
        self._data = self.path.read_bytes()
        if len(self._data) < 64:
            logger.warning("File too small to be a valid PE: %s", self.path)
            return []

        # 1. Validate DOS header
        if self._data[:2] != self.MZ_SIGNATURE:
            raise ValueError(f"Not a valid PE file (missing MZ signature): {self.path}")

        # 2. Get PE header offset from e_lfanew
        pe_offset = struct.unpack_from("<I", self._data, 0x3C)[0]
        if pe_offset + 4 > len(self._data):
            raise ValueError(f"Invalid e_lfanew offset: {pe_offset}")
        if self._data[pe_offset:pe_offset + 4] != self.PE_SIGNATURE:
            raise ValueError(f"Invalid PE signature at offset {pe_offset}")

        logger.debug("PE offset: 0x%X", pe_offset)

        # 3. Parse COFF Header
        coff_offset = pe_offset + 4
        self._parse_coff_header(coff_offset)

        # 4. Parse Optional Header → Resource Directory RVA/Size
        opt_offset = coff_offset + 20
        rsrc_rva, rsrc_size = self._parse_optional_header(opt_offset)

        if rsrc_rva == 0 or rsrc_size == 0:
            logger.info("No resource directory found in %s", self.path)
            return []

        logger.debug("Resource Directory: RVA=0x%X, Size=%d", rsrc_rva, rsrc_size)

        # 5. Parse Section Table
        coff_num_sections = struct.unpack_from("<H", self._data, coff_offset + 2)[0]
        coff_opt_size = struct.unpack_from("<H", self._data, coff_offset + 16)[0]
        section_table_offset = opt_offset + coff_opt_size
        self._parse_section_table(section_table_offset, coff_num_sections)

        logger.debug("Sections: %s", [s.name for s in self._sections])

        # 6. Traverse Resource Directory tree
        return self._traverse_resource_tree(rsrc_rva, rsrc_size)

    # ------------------------------------------------------------------
    # Header parsing
    # ------------------------------------------------------------------

    def _parse_coff_header(self, offset: int):
        """Parse and validate COFF header (20 bytes)."""
        if offset + 20 > len(self._data):
            raise ValueError("COFF header exceeds file size")

        machine = struct.unpack_from("<H", self._data, offset)[0]
        num_sections = struct.unpack_from("<H", self._data, offset + 2)[0]
        timestamp = struct.unpack_from("<I", self._data, offset + 4)[0]
        opt_hdr_size = struct.unpack_from("<H", self._data, offset + 16)[0]
        characteristics = struct.unpack_from("<H", self._data, offset + 18)[0]

        logger.debug(
            "COFF: machine=0x%04X, sections=%d, opt_hdr_size=%d, chars=0x%04X",
            machine, num_sections, opt_hdr_size, characteristics,
        )

        if opt_hdr_size == 0:
            raise ValueError("Optional header size is 0 — not a valid PE image")

    def _parse_optional_header(self, offset: int) -> tuple[int, int]:
        """Parse Optional Header and return (Resource RVA, Resource Size).

        The Resource Directory is Data Directory entry [2].
        PE32:  offset + 96, +100
        PE32+: offset + 112, +116
        """
        if offset + 2 > len(self._data):
            raise ValueError("Optional header exceeds file size")

        magic = struct.unpack_from("<H", self._data, offset)[0]
        if magic == 0x010B:  # PE32
            self._is_pe32_plus = False
            if offset + 112 > len(self._data):
                raise ValueError("PE32 optional header too small for data directories")
            # Data Directories start at offset + 96; each is 8 bytes
            # DD[0]=Export, DD[1]=Import, DD[2]=Resource
            rsrc_rva = struct.unpack_from("<I", self._data, offset + 96 + 2 * 8)[0]
            rsrc_size = struct.unpack_from("<I", self._data, offset + 96 + 2 * 8 + 4)[0]
        elif magic == 0x020B:  # PE32+
            self._is_pe32_plus = True
            if offset + 128 > len(self._data):
                raise ValueError("PE32+ optional header too small for data directories")
            rsrc_rva = struct.unpack_from("<I", self._data, offset + 112 + 2 * 8)[0]
            rsrc_size = struct.unpack_from("<I", self._data, offset + 112 + 2 * 8 + 4)[0]
        else:
            raise ValueError(f"Unknown Optional Header magic: 0x{magic:04X}")

        return rsrc_rva, rsrc_size

    def _parse_section_table(self, offset: int, num_sections: int):
        """Parse Section Table entries (40 bytes each)."""
        self._sections = []
        for i in range(num_sections):
            sec_off = offset + i * 40
            if sec_off + 40 > len(self._data):
                logger.warning("Section table entry %d exceeds file size", i)
                break

            name_bytes = self._data[sec_off:sec_off + 8]
            name = name_bytes.rstrip(b"\x00").decode("ascii", errors="replace")
            vsize = struct.unpack_from("<I", self._data, sec_off + 8)[0]
            rva = struct.unpack_from("<I", self._data, sec_off + 12)[0]
            raw_size = struct.unpack_from("<I", self._data, sec_off + 16)[0]
            raw_offset = struct.unpack_from("<I", self._data, sec_off + 20)[0]
            chars = struct.unpack_from("<I", self._data, sec_off + 36)[0]

            sec = SectionInfo(
                name=name,
                virtual_size=vsize,
                rva=rva,
                raw_offset=raw_offset,
                raw_size=raw_size,
                characteristics=chars,
            )
            self._sections.append(sec)
            logger.debug(
                "  Section[%d]: %s  RVA=0x%08X  Raw=0x%08X  VSize=%d  RawSize=%d",
                i, name, rva, raw_offset, vsize, raw_size,
            )

    # ------------------------------------------------------------------
    # RVA ↔ File Offset conversion
    # ------------------------------------------------------------------

    def _rva_to_offset(self, rva: int) -> int:
        """Convert an RVA (Relative Virtual Address) to a file offset.

        The RVA is mapped to the section that contains it:
            file_offset = rva - section.rva + section.raw_offset

        Note: Some PE linkers set VirtualSize to 0 while providing a valid
        SizeOfRawData. In that case we fall back to raw_size for the range check.
        """
        for sec in self._sections:
            effective_size = sec.virtual_size if sec.virtual_size > 0 else sec.raw_size
            if effective_size > 0 and sec.rva <= rva < sec.rva + effective_size:
                return rva - sec.rva + sec.raw_offset
        # Fallback: some PE files have RVA == file offset for resources
        logger.warning("RVA 0x%X does not fall within any section, using as-is", rva)
        return rva

    # ------------------------------------------------------------------
    # Resource Directory traversal
    # ------------------------------------------------------------------

    def _traverse_resource_tree(self, rsrc_rva: int, rsrc_size: int) -> list[PBDResource]:
        """Traverse the Resource Directory tree and find PBD resources.

        Resource Directory is a 3-level tree:
          Level 1: Resource Type (e.g. RT_RCDATA=6, or custom type ID)
          Level 2: Resource ID (or name)
          Level 3: Language ID

        Key PE Resource layout detail:
          - All sub-directory offsets within the resource tree are RELATIVE
            to the .rsrc section start (NOT global RVAs).
          - Only the Resource Data Entry contains a true RVA pointing to
            the actual resource data in memory.

        Each leaf points to a Resource Data Entry (8 bytes):
          [uint32 DataRVA, uint32 Size]

        We check every resource's data for HDR* signature.
        """
        rsrc_base = self._rva_to_offset(rsrc_rva)
        resources: list[PBDResource] = []

        if rsrc_base + 16 > len(self._data):
            logger.warning("Resource directory exceeds file size")
            return resources

        # Level 1: Resource Type directory (at start of .rsrc)
        num_named, num_id = self._read_directory_counts(rsrc_base)
        total_entries = num_named + num_id

        logger.debug("Resource Type directory at 0x%X: %d named + %d ID = %d total",
                     rsrc_base, num_named, num_id, total_entries)

        for i in range(total_entries):
            entry_offset = rsrc_base + 16 + i * 8
            if entry_offset + 8 > len(self._data):
                break

            type_id = self._read_dir_entry_id(entry_offset, named_prefix="type", rsrc_base=rsrc_base)
            sub_dir_off = self._read_sub_dir_offset(entry_offset)

            if sub_dir_off == 0:
                continue

            # Sub-directory offset is relative to .rsrc section base
            id_dir_file_offset = rsrc_base + sub_dir_off
            if id_dir_file_offset + 16 > len(self._data):
                continue

            # Level 2: Resource ID directory
            num_named2, num_id2 = self._read_directory_counts(id_dir_file_offset)

            for j in range(num_named2 + num_id2):
                entry_offset2 = id_dir_file_offset + 16 + j * 8
                if entry_offset2 + 8 > len(self._data):
                    break

                res_id = self._read_dir_entry_id(entry_offset2, named_prefix="res", rsrc_base=rsrc_base)
                sub_dir_off2 = self._read_sub_dir_offset(entry_offset2)

                if sub_dir_off2 == 0:
                    continue

                # Level 3: Language directory
                lang_dir_file_offset = rsrc_base + sub_dir_off2
                if lang_dir_file_offset + 16 > len(self._data):
                    continue

                num_named3, num_id3 = self._read_directory_counts(lang_dir_file_offset)

                for k in range(num_named3 + num_id3):
                    entry_offset3 = lang_dir_file_offset + 16 + k * 8
                    if entry_offset3 + 8 > len(self._data):
                        break

                    lang_id = self._read_dir_entry_id(entry_offset3, named_prefix=None, rsrc_base=rsrc_base)
                    data_entry_off = self._read_data_entry_offset(entry_offset3)

                    if data_entry_off == 0:
                        continue

                    # Data entry offset is relative to .rsrc section base
                    data_entry_file_offset = rsrc_base + data_entry_off
                    if data_entry_file_offset + 8 > len(self._data):
                        continue

                    # Resource Data Entry contains a TRUE RVA + Size
                    data_rva = struct.unpack_from("<I", self._data, data_entry_file_offset)[0]
                    data_size = struct.unpack_from("<I", self._data, data_entry_file_offset + 4)[0]

                    if data_size == 0 or data_size > len(self._data):
                        continue

                    # Convert data RVA to file offset (standard RVA→offset conversion)
                    data_file_offset = self._rva_to_offset(data_rva)
                    if data_file_offset + data_size > len(self._data):
                        data_size = len(self._data) - data_file_offset

                    res_data = self._data[data_file_offset:data_file_offset + data_size]

                    # Build name from type and resource IDs
                    name = self._make_resource_name(type_id, res_id)

                    resource = PBDResource(
                        type_id=type_id,
                        resource_id=res_id,
                        language_id=lang_id,
                        rva=data_rva,
                        file_offset=data_file_offset,
                        size=data_size,
                        data=res_data,
                        name=name,
                    )
                    resources.append(resource)

        # Filter: only keep resources with valid HDR* signature
        pbd_resources = [r for r in resources if r.is_valid_pbd]

        logger.info(
            "Found %d total resources, %d with valid HDR* (PBD) signature",
            len(resources), len(pbd_resources),
        )

        if pbd_resources:
            for pbd in pbd_resources:
                logger.info(
                    "  PBD: %s, type=%s, size=%d bytes",
                    pbd.name, pbd.type_id, pbd.size,
                )

        return pbd_resources

    # ------------------------------------------------------------------
    # Resource Directory helpers
    # ------------------------------------------------------------------

    def _read_directory_counts(self, dir_offset: int) -> tuple[int, int]:
        """Read named and ID entry counts from a Resource Directory header.

        Layout (16 bytes):
          uint32  Characteristics
          uint32  TimeDateStamp
          uint16  MajorVersion
          uint16  MinorVersion
          uint16  NumberOfNamedEntries
          uint16  NumberOfIdEntries
        """
        if dir_offset + 16 > len(self._data):
            return 0, 0
        num_named = struct.unpack_from("<H", self._data, dir_offset + 12)[0]
        num_id = struct.unpack_from("<H", self._data, dir_offset + 14)[0]
        return num_named, num_id

    def _read_dir_entry_id(self, entry_offset: int, named_prefix: str | None,
                           rsrc_base: int = 0) -> int | str:
        """Read the ID or name from a Resource Directory entry.

        Entry layout (8 bytes):
          uint32  Name/ID offset (bit 31 set = pointer to name entry)
          uint32  Offset to subdirectory or data entry (bit 31 set = subdirectory)

        If the high bit (bit 31) of the first uint32 is set, the lower 31 bits
        are a RELATIVE offset (to .rsrc section base) pointing to an
        IMAGE_RESOURCE_DIR_STRING_U structure.

        Args:
            entry_offset: File offset of this directory entry.
            named_prefix: Prefix for named entry labels.
            rsrc_base: File offset of the .rsrc section start (for resolving names).
        """
        if entry_offset + 8 > len(self._data):
            return 0

        raw = struct.unpack_from("<I", self._data, entry_offset)[0]

        if raw & 0x80000000:
            # Named entry: lower 31 bits = offset to IMAGE_RESOURCE_DIR_STRING_U
            # (relative to .rsrc section base)
            name_rel_offset = raw & 0x7FFFFFFF
            name_file_offset = rsrc_base + name_rel_offset
            # Try to read the actual name string
            if rsrc_base > 0 and name_file_offset + 2 <= len(self._data):
                str_len = struct.unpack_from("<H", self._data, name_file_offset)[0]
                if str_len > 0 and name_file_offset + 2 + str_len * 2 <= len(self._data):
                    name_str = self._data[name_file_offset + 2:
                                           name_file_offset + 2 + str_len * 2]
                    try:
                        return name_str.decode("utf-16-le", errors="replace")
                    except Exception:
                        pass
            return f"{named_prefix}_named_{name_rel_offset:X}" if named_prefix else f"named_{name_rel_offset:X}"
        else:
            return raw

    def _read_sub_dir_offset(self, entry_offset: int) -> int:
        """Read the sub-directory offset from a directory entry.

        The second uint32 of the entry: bit 31 set = subdirectory.
        The offset is RELATIVE to the .rsrc section start (not a global RVA).
        """
        if entry_offset + 8 > len(self._data):
            return 0
        raw = struct.unpack_from("<I", self._data, entry_offset + 4)[0]
        if raw & 0x80000000:
            return raw & 0x7FFFFFFF
        return 0  # This is a data entry, not a subdirectory

    def _read_data_entry_offset(self, entry_offset: int) -> int:
        """Read the offset pointing to a Resource Data Entry.

        The second uint32 of the entry: bit 31 NOT set = data entry.
        The offset is RELATIVE to the .rsrc section start (not a global RVA).
        """
        if entry_offset + 8 > len(self._data):
            return 0
        raw = struct.unpack_from("<I", self._data, entry_offset + 4)[0]
        if raw & 0x80000000:
            return 0  # This is a subdirectory, not data
        return raw

    @staticmethod
    def _make_resource_name(type_id: int | str, res_id: int | str) -> str:
        """Generate a human-readable name for a resource."""
        # Common PE resource type names
        type_names = {
            1: "RT_CURSOR", 2: "RT_BITMAP", 3: "RT_ICON", 4: "RT_MENU",
            5: "RT_DIALOG", 6: "RT_RCDATA", 7: "RT_FONTDIR", 8: "RT_FONT",
            9: "RT_ACCELERATOR", 10: "RT_RCDATA", 11: "RT_MESSAGETABLE",
            12: "RT_GROUP_CURSOR", 14: "RT_GROUP_ICON",
            16: "RT_VERSION", 24: "RT_MANIFEST",
        }

        if isinstance(type_id, int) and type_id in type_names:
            type_name = type_names[type_id]
        else:
            type_name = str(type_id)

        return f"{type_name}/{res_id}"


    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def scan_appended_pbds(self) -> list:
        """Scan for PBD data appended after all PE sections.

        Some PowerBuilder EXEs store the embedded PBD not in the .rsrc
        resource section, but directly appended at the end of the file,
        after all section data. This method scans for HDR* signatures
        in the area beyond the last section raw data.

        Returns:
            List of PBDResource objects found in the appended area.
        """
        if not self._data:
            self._data = self.path.read_bytes()
        if not self._sections:
            # Need to parse PE header first
            try:
                result = self.extract_pbd_resources()
                # If extract_pbd_resources already found some, return them
                if result:
                    return result
            except Exception:
                pass
            # Re-read sections
            try:
                if len(self._data) < 64:
                    return []
                pe_offset = struct.unpack_from("<I", self._data, 0x3C)[0]
                coff_offset = pe_offset + 4
                self._parse_coff_header(coff_offset)
                opt_offset = coff_offset + 20
                self._parse_optional_header(opt_offset)
                coff_num_sections = struct.unpack_from("<H", self._data, coff_offset + 2)[0]
                coff_opt_size = struct.unpack_from("<H", self._data, coff_offset + 16)[0]
                section_table_offset = opt_offset + coff_opt_size
                self._parse_section_table(section_table_offset, coff_num_sections)
            except Exception as e:
                logger.warning("Failed to parse PE sections for appended scan: %s", e)
                return []

        # Find the end of all sections (highest raw_offset + raw_size)
        if not self._sections:
            return []

        last_section_end = max(
            s.raw_offset + s.raw_size
            for s in self._sections
            if s.raw_offset > 0 and s.raw_size > 0
        )

        logger.debug("Last section ends at file offset 0x%X, file size 0x%X",
                     last_section_end, len(self._data))

        # Scan from last_section_end onwards for HDR* signature
        resources = []
        scan_start = last_section_end
        pos = scan_start

        while pos + 512 < len(self._data):
            block = self._data[pos:pos + 4]
            if block == self.HDR_SIGNATURE:
                # Found HDR* — determine the PBD length by reading until EOF
                # or until another EXE signature (MZ)
                end = len(self._data)
                pbd_data = self._data[pos:end]
                resource = PBDResource(
                    type_id=0, resource_id=0, language_id=0,
                    rva=0, file_offset=pos, size=len(pbd_data),
                    data=pbd_data,
                    name=f"appended_pbd_at_{pos:08X}",
                )
                if resource.is_valid_pbd:
                    logger.info("Found appended PBD at file offset 0x%X (%d bytes)",
                                pos, len(resource.data))
                    resources.append(resource)
                break  # Only one appended PBD expected
            pos += 512  # scan in 512-byte blocks (matches PBL HDR block size)

        if not resources:
            # Also try a byte-granular scan near the end of sections
            # (in case there's alignment padding before HDR*)
            for offset in range(max(0, last_section_end - 4096), min(last_section_end + 8192, len(self._data) - 4)):
                if self._data[offset:offset + 4] == self.HDR_SIGNATURE:
                    pbd_data = self._data[offset:]
                    resource = PBDResource(
                        type_id=0, resource_id=0, language_id=0,
                        rva=0, file_offset=offset, size=len(pbd_data),
                        data=pbd_data,
                        name=f"appended_pbd_at_{offset:08X}",
                    )
                    if resource.is_valid_pbd:
                        logger.info("Found appended PBD (fine scan) at 0x%X (%d bytes)",
                                    offset, len(resource.data))
                        resources.append(resource)
                        break

        return resources

    @staticmethod
    def is_pe_file(path: str | Path) -> bool:
        """Quick check if a file is a PE executable/DLL."""
        try:
            p = Path(path)
            if not p.exists() or p.stat().st_size < 64:
                return False
            with open(p, "rb") as f:
                header = f.read(2)
            return header == b"MZ"
        except (OSError, IOError):
            return False
