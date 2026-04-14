"""
PBORCA SDK Python wrapper via ctypes.

Wraps PBORCA C API (or PBSpyORCA replacement) for Python.
Supports: export, import, compile, build.

DLL: PBSpyORCA.dll (MIT, PB5-PB2025) -> tools/pb-devkit/orca/
     Download: https://github.com/Hucxy/PBSpyORCA

This module supports graceful degradation when the DLL is not available:
- is_available() checks without raising
- PBORCAEngine raises RuntimeError with helpful messages
- CLI commands that need ORCA show installation instructions
"""
from __future__ import annotations
import ctypes
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PBORCA_OK = 0
PBORCA_BUFFERTOOSMALL = -10
PBORCA_UTF8 = 2

DLL_NAMES = [
    "PBSpy.dll", "PBORC125.dll", "PBORC120.dll", "PBORC115.dll",
    "PBORC110.dll", "PBORC105.dll", "PBORC100.dll", "PBORC090.dll",
]
EXT_TO_TYPE = {
    ".sra": 0, ".srd": 1, ".srw": 2, ".srm": 3, ".srf": 4,
    ".srs": 5, ".sru": 6, ".srq": 7, ".srp": 8, ".srj": 9,
}
TYPE_TO_EXT = {v: k for k, v in EXT_TO_TYPE.items()}

# Error message templates
_DLL_NOT_FOUND_MSG = (
    "PBORCA DLL not found.\n"
    "\n"
    "To enable import/build/compile features:\n"
    "  1. Download PBSpyORCA from https://github.com/Hucxy/PBSpyORCA/releases\n"
    "  2. Copy PBSpy.dll to the 'orca/' directory of pb-devkit\n"
    "\n"
    "Alternatively, set PBORCA_PATH environment variable to the DLL directory.\n"
    "\n"
    "Note: export, list, analyze, search, report, refactor, diff, stats, "
    "and workflow commands work WITHOUT the DLL."
)


class ORCAError(Exception):
    """Raised when a PBORCA operation fails."""

    def __init__(self, operation: str, code: int, message: str = ""):
        self.operation = operation
        self.code = code
        self.message = message
        super().__init__(f"PBORCA error (code={code}) in {operation}: {message}")


def find_dll() -> Optional[Path]:
    """Search for PBORCA DLL in standard locations. Returns path or None."""
    search_paths = [Path(__file__).parent.parent.parent / "orca"]
    env = os.environ.get("PBORCA_PATH", "")
    if env:
        search_paths.append(Path(env))

    for d in search_paths:
        if not d.exists():
            continue
        for name in DLL_NAMES:
            f = d / name
            if f.exists():
                return f
    return None


def is_available() -> bool:
    """Check if PBORCA DLL is available without raising."""
    return find_dll() is not None


def get_dll_info() -> dict:
    """Get DLL availability info for diagnostics."""
    dll = find_dll()
    if dll:
        return {
            "available": True,
            "path": str(dll),
            "name": dll.name,
        }
    return {
        "available": False,
        "search_paths": [str(p) for p in [
            Path(__file__).parent.parent.parent / "orca",
            Path(os.environ.get("PBORCA_PATH", "")),
        ]],
        "hint": _DLL_NOT_FOUND_MSG,
    }


class PBORCAEngine:
    """Python wrapper around PBORCA/PBSpyORCA DLL.

    Usage:
        try:
            engine = PBORCAEngine(pb_version=125)
            engine.session_open()
            entries = engine.library_directory("app.pbl")
        except RuntimeError:
            print("DLL not available - using Python parser instead")
        finally:
            engine.session_close()
    """

    def __init__(self, dll_path: Optional[str] = None, pb_version: int = 125):
        self.pb_version = pb_version
        self._dll = None
        self._session = 0
        self._has_version_open = False
        self._load_dll(dll_path)

    def _load_dll(self, dll_path):
        """Load the PBORCA DLL. Raises RuntimeError with helpful message if not found."""
        if dll_path:
            p = Path(dll_path)
            if not p.exists():
                raise FileNotFoundError(
                    f"DLL not found: {dll_path}\n\n{_DLL_NOT_FOUND_MSG}")
            self._dll = ctypes.WinDLL(str(p))
            logger.info("Loaded PBORCA DLL from: %s", p)
            return

        dll = find_dll()
        if dll:
            self._dll = ctypes.WinDLL(str(dll))
            logger.info("Loaded PBORCA DLL: %s", dll)
            return

        raise RuntimeError(_DLL_NOT_FOUND_MSG)

    def _setup(self):
        """Configure DLL function signatures."""
        dll = self._dll
        try:
            dll.PBORCA_SessionOpenWithVersion.argtypes = [ctypes.c_int]
            dll.PBORCA_SessionOpenWithVersion.restype = ctypes.c_void_p
            self._has_version_open = True
        except AttributeError:
            dll.PBORCA_SessionOpen.argtypes = []
            dll.PBORCA_SessionOpen.restype = ctypes.c_void_p
        dll.PBORCA_SessionClose.argtypes = [ctypes.c_void_p]
        dll.PBORCA_SessionClose.restype = None
        dll.PBORCA_SessionGetError.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        dll.PBORCA_SessionGetError.restype = ctypes.c_int
        dll.PBORCA_LibraryDirectory.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
            ctypes.c_char_p, ctypes.c_long]
        dll.PBORCA_LibraryDirectory.restype = ctypes.c_int
        dll.PBORCA_LibraryEntryExport.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_int, ctypes.c_char_p, ctypes.c_long]
        dll.PBORCA_LibraryEntryExport.restype = ctypes.c_int
        dll.PBORCA_CompileEntryImport.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_int, ctypes.c_char_p, ctypes.c_long,
            ctypes.c_char_p, ctypes.c_long]
        dll.PBORCA_CompileEntryImport.restype = ctypes.c_int
        dll.PBORCA_ApplicationRebuild.argtypes = [ctypes.c_void_p]
        dll.PBORCA_ApplicationRebuild.restype = ctypes.c_int
        dll.PBORCA_ExecutableCreate.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        dll.PBORCA_ExecutableCreate.restype = ctypes.c_int
        dll.PBORCA_SessionSetLibraryList.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p]
        dll.PBORCA_SessionSetLibraryList.restype = ctypes.c_int
        dll.PBORCA_SessionSetCurrentAppl.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        dll.PBORCA_SessionSetCurrentAppl.restype = ctypes.c_int
        dll.PBORCA_LibraryCreate.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        dll.PBORCA_LibraryCreate.restype = ctypes.c_int

    def _check(self, result, op=""):
        """Check PBORCA return code. Raises ORCAError on failure."""
        if result != PBORCA_OK:
            raise ORCAError(op, result, self.get_last_error())

    def session_open(self):
        """Open a PBORCA session."""
        self._setup()
        if self._has_version_open:
            self._session = self._dll.PBORCA_SessionOpenWithVersion(
                self.pb_version)
        else:
            self._session = self._dll.PBORCA_SessionOpen()
        if not self._session:
            raise RuntimeError("Failed to open PBORCA session. "
                             "Check that the DLL matches your PB version.")

    def session_close(self):
        """Close the PBORCA session."""
        if self._session and self._dll:
            self._dll.PBORCA_SessionClose(self._session)
            self._session = 0

    def get_last_error(self) -> str:
        """Get the last error message from PBORCA session."""
        if not self._session or not self._dll:
            return "Session not open"
        buf = ctypes.create_string_buffer(1024)
        self._dll.PBORCA_SessionGetError(self._session, buf, 1024)
        return buf.value.decode("ascii", errors="replace")

    def library_directory(self, lib_path: str) -> list:
        """List entries: [(name, type_code, comment), ...]"""
        buf = ctypes.create_string_buffer(1024 * 1024)
        r = self._dll.PBORCA_LibraryDirectory(
            self._session, lib_path.encode("ascii"), -1, buf, 1024 * 1024)
        entries = []
        if r in (PBORCA_OK, PBORCA_BUFFERTOOSMALL):
            for line in buf.value.decode("ascii", errors="replace").split("\n"):
                p = line.strip().split(";")
                if len(p) >= 2 and p[0].strip():
                    entries.append((
                        p[0].strip(), int(p[1].strip()),
                        p[5].strip() if len(p) > 5 else ""))
        return entries

    def export_entry(self, lib_path: str, entry_name: str,
                     entry_type: int = -1) -> str:
        """Export single entry source code."""
        buf = ctypes.create_string_buffer(1)
        r = self._dll.PBORCA_LibraryEntryExport(
            self._session, lib_path.encode("ascii"),
            entry_name.encode("ascii"), entry_type, buf, 1)
        if r == PBORCA_BUFFERTOOSMALL:
            buf = ctypes.create_string_buffer(1024 * 1024)
            r = self._dll.PBORCA_LibraryEntryExport(
                self._session, lib_path.encode("ascii"),
                entry_name.encode("ascii"), entry_type, buf, 1024 * 1024)
            self._check(r, f"Export({entry_name})")
            return buf.value.decode("utf-8", errors="replace")
        self._check(r, f"Export({entry_name})")
        return buf.value.decode("utf-8", errors="replace")

    def export_all(self, lib_path: str, output_dir: str,
                   headers: bool = True) -> list:
        """Export all entries to .sr* files."""
        entries = self.library_directory(lib_path)
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        exported = []
        errors = []
        for name, tc, _ in entries:
            ext = TYPE_TO_EXT.get(tc, ".bin")
            try:
                src = self.export_entry(lib_path, name, tc)
                if not headers:
                    lines = src.splitlines()
                    if len(lines) > 2 and lines[0].startswith("$PBExportHeader"):
                        src = "\n".join(lines[2:])
                fp = out / (name + ext)
                fp.write_text(src, encoding="utf-8")
                exported.append(str(fp))
            except ORCAError as e:
                errors.append((name, str(e)))
                print(f"  Warning: {name}: {e.message}", file=sys.stderr)
            except Exception as e:
                errors.append((name, str(e)))
                print(f"  Warning: {name}: {e}", file=sys.stderr)
        if errors:
            logger.warning("Exported %d/%d entries (%d errors)",
                          len(exported), len(entries), len(errors))
        return exported

    def import_entry(self, lib_path: str, entry_name: str,
                     entry_type: int, source: str, comment: str = ""):
        """Import and compile a source entry into PBL."""
        sb = source.encode("utf-8")
        cb = comment.encode("ascii") if comment else b""
        r = self._dll.PBORCA_CompileEntryImport(
            self._session, lib_path.encode("ascii"),
            entry_name.encode("ascii"), entry_type,
            sb, len(sb), cb, len(cb))
        self._check(r, f"Import({entry_name})")

    def import_from_directory(self, lib_path: str, source_dir: str) -> list:
        """Import all .sr* files from directory into PBL."""
        src = Path(source_dir)
        imported = []
        errors = []
        for f in sorted(src.glob("*.sr*")):
            tc = EXT_TO_TYPE.get(f.suffix.lower())
            if tc is None:
                continue
            text = f.read_text(encoding="utf-8")
            lines = text.splitlines()
            if len(lines) > 2 and lines[0].startswith("$PBExportHeader"):
                text = "\n".join(lines[2:])
            try:
                self.import_entry(lib_path, f.stem, tc, text)
                imported.append(f.stem)
            except ORCAError as e:
                errors.append((f.stem, str(e)))
                print(f"  Error {f.stem}: {e.message}", file=sys.stderr)
            except Exception as e:
                errors.append((f.stem, str(e)))
                print(f"  Error {f.stem}: {e}", file=sys.stderr)
        if errors:
            logger.warning("Imported %d/%d files (%d errors)",
                          len(imported), len(imported) + len(errors), len(errors))
        return imported

    def rebuild_application(self, lib_path: str, app_name: str):
        """Full rebuild of application."""
        self._dll.PBORCA_SessionSetLibraryList(
            self._session, lib_path.encode("ascii"))
        self._dll.PBORCA_SessionSetCurrentAppl(
            self._session, lib_path.encode("ascii"),
            app_name.encode("ascii"))
        self._check(
            self._dll.PBORCA_ApplicationRebuild(self._session),
            "ApplicationRebuild")

    def build_executable(self, exe_path: str, icon_path: str = "",
                         pbr_path: str = "", pbd_flags: str = "nnnn",
                         machine_code: bool = False):
        """Build .exe from application."""
        self._check(self._dll.PBORCA_ExecutableCreate(
            self._session, exe_path.encode("ascii"),
            icon_path.encode("ascii") if icon_path else b"",
            pbr_path.encode("ascii") if pbr_path else b"",
            pbd_flags.encode("ascii"), 1 if machine_code else 0),
            "ExecutableCreate")
