"""
Build script: generates pb_devkit/decompiler.py from thirdparty/PbdCli/pbdcli.py
with the following modifications:
  1. Replace CLI header with library docstring
  2. Add io, dataclasses imports
  3. Fix ANSI get_string: latin-1 -> gbk (Chinese support)
  4. dump_function: return str instead of print
  5. dump_entry: return str instead of print
  6. Add library API: DecompileResult, decompile_file, decompile_bytes, list_entries, get_tree
"""

import os
import sys
import re

src = r"c:\Users\Administrator\WorkBuddy\20260414101957\thirdparty\PbdCli\pbdcli.py"
dst = r"c:\Users\Administrator\WorkBuddy\20260414101957\pb-devkit\src\pb_devkit\decompiler.py"

with open(src, "r", encoding="utf-8") as f:
    code = f.read()

# ---- 1. Replace shebang + CLI docstring with library docstring ----
cli_header_end = code.index('import struct')
code = code[cli_header_end:]  # strip everything before imports

lib_doc = '"""\npb_devkit.decompiler - PowerBuilder PBD/PBL Decompiler (library)\nBased on PbdCli (https://github.com/Hucxy/PbdViewer).\n\nChanges from original:\n- RESOURCE_DIR points to package-internal resoures/\n- get_string: ANSI uses gbk encoding for Chinese support (fallback latin-1)\n- dump_function / dump_entry: return str instead of printing\n- Library API: DecompileResult, decompile_file, decompile_bytes, list_entries, get_tree\n"""\n\n'
code = lib_doc + code

# ---- 2. Add io and dataclasses imports ----
code = code.replace(
    "import struct\nimport sys\nimport os\nimport re\nimport gzip\nfrom datetime",
    "import struct\nimport sys\nimport os\nimport re\nimport gzip\nimport io\nfrom dataclasses import dataclass\nfrom datetime"
)

# ---- 3. Fix ANSI get_string encoding ----
code = code.replace(
    "        return buf[offset:end].decode('latin-1', errors='replace')",
    "        raw = buf[offset:end]\n        try:\n            return raw.decode('gbk', errors='strict')\n        except (UnicodeDecodeError, LookupError):\n            return raw.decode('latin-1', errors='replace')"
)

# ---- 4. dump_function: return str ----
old_dump_fn = 'def dump_function(f: PbFunction, indent="  "):\n    print(f"\\n{indent}//{f.definition}")\n    for v in f.variables:\n        if any(p.name == v.name for p in f.definition.params): continue\n        if v.is_referenced_global or v.name.startswith("\\x01"): continue\n        print(f"{indent}{v.to_string(f.buffer)}")\n    print()\n    for line in parse_pcode(f):\n        print(f"{indent}{line}")'
new_dump_fn = 'def dump_function(f: PbFunction, indent="  ") -> str:\n    _out = []\n    _out.append(f"\\n{indent}//{f.definition}")\n    for v in f.variables:\n        if any(p.name == v.name for p in f.definition.params): continue\n        if v.is_referenced_global or v.name.startswith("\\x01"): continue\n        _out.append(f"{indent}{v.to_string(f.buffer)}")\n    _out.append("")\n    for line in parse_pcode(f):\n        _out.append(f"{indent}{line}")\n    return "\\n".join(_out)'
code = code.replace(old_dump_fn, new_dump_fn)

# ---- 5. dump_entry: return str ----
# Find dump_entry function and replace print calls
old_sig = "def dump_entry(entry: PbEntry):"
new_sig = "def dump_entry(entry: PbEntry) -> str:"
code = code.replace(old_sig, new_sig)

# Now we need to transform dump_entry body
# Strategy: find the function body and replace print with _out.append
lines = code.split('\n')
in_dump_entry = False
brace_depth = 0
new_lines = []
out_var_inserted = False

for i, line in enumerate(lines):
    stripped = line.strip()
    
    if 'def dump_entry(entry: PbEntry) -> str:' in line:
        in_dump_entry = True
        out_var_inserted = False
        new_lines.append(line)
        continue
    
    if in_dump_entry and not out_var_inserted:
        # Insert _out = [] after the def line
        indent = '    '
        new_lines.append(f'{indent}_out = []')
        out_var_inserted = True
    
    if in_dump_entry:
        # Check if we've left the function (new def at top level)
        if stripped.startswith('def ') and not line.startswith(' ') and not line.startswith('\t'):
            # Emit the return before leaving
            in_dump_entry = False
            new_lines.append('    return "\\n".join(_out)\n')
            new_lines.append(line)
            continue
        
        # Transform lines
        # print(f"...") -> _out.append(f"...")
        # print("...") -> _out.append("...")
        # dump_function(f) -> _out.append(dump_function(f))
        
        if re.match(r'\s+print\(', line):
            line = re.sub(r'^(\s+)print\(', r'\1_out.append(', line)
            # Close paren check - print(...) -> _out.append(...)
            # Already done by the sub above if there's one call per line
            new_lines.append(line)
            continue
        
        if re.match(r'\s+for f in (events|funcs|ctrl_events|ctrl_funcs).*dump_function\(f\)', line):
            line = re.sub(r'dump_function\(f\)', '_out.append(dump_function(f))', line)
            new_lines.append(line)
            continue
        
        # return -> return "\n".join(_out)
        if stripped == 'return':
            indent_str = line[:len(line) - len(line.lstrip())]
            new_lines.append(f'{indent_str}return "\\n".join(_out)')
            continue
        
        new_lines.append(line)
        continue
    
    new_lines.append(line)

# If still in dump_entry at end (shouldn't happen)
if in_dump_entry:
    new_lines.append('    return "\\n".join(_out)')

code = '\n'.join(new_lines)

# ---- 6. Add library API at end (before main()) ----
library_api = '''

# ==================== Library API ====================

@dataclass
class DecompileResult:
    """Structured result of a decompile operation."""
    entry_name: str
    source: str
    success: bool = True
    error: str = None


def decompile_file(file_path: str, entry_name: str = None,
                   decompile_all: bool = True) -> list:
    """
    Decompile entries from a PBD/PBL file.

    Args:
        file_path: Path to .pbd or .pbl file
        entry_name: Specific entry name (None = all)
        decompile_all: If False, return entry list only

    Returns:
        List[DecompileResult]
    """
    results = []
    try:
        project = PbProject(file_path)
    except Exception as e:
        return [DecompileResult(entry_name="", source="", success=False, error=str(e))]

    for pbf in project.files:
        for entry in sorted(pbf.entries, key=lambda e: e.entry_name):
            if entry_name and entry.name.lower() != entry_name.lower() \
               and entry.entry_name.lower() != entry_name.lower():
                continue
            if not decompile_all:
                results.append(DecompileResult(entry_name=entry.entry_name, source=""))
                continue
            try:
                src = dump_entry(entry)
                results.append(DecompileResult(entry_name=entry.entry_name, source=src))
            except Exception as e:
                results.append(DecompileResult(
                    entry_name=entry.entry_name, source="", success=False, error=str(e)
                ))
    return results


def decompile_bytes(data: bytes, label: str = "<memory>",
                    entry_name: str = None,
                    decompile_all: bool = True) -> list:
    """
    Decompile PBD data from bytes (e.g. extracted from EXE by PEExtractor).

    Args:
        data: Raw PBD bytes
        label: Display label
        entry_name: Specific entry (None = all)
        decompile_all: Decompile all entries

    Returns:
        List[DecompileResult]
    """
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(suffix=".pbd", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return decompile_file(tmp_path, entry_name=entry_name, decompile_all=decompile_all)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        return [DecompileResult(entry_name=label, source="", success=False, error=str(e))]


def list_entries(file_path: str) -> list:
    """List all entry names in a PBD/PBL file."""
    try:
        project = PbProject(file_path)
        names = []
        for pbf in project.files:
            for e in sorted(pbf.entries, key=lambda e: e.entry_name):
                names.append(e.entry_name)
        return names
    except Exception:
        return []


def get_tree_str(file_path: str) -> str:
    """Return tree view of a PBD/PBL as string."""
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        project = PbProject(file_path)
        print_tree(project)
    finally:
        sys.stdout = old_out
    return buf.getvalue()

'''

code = code.replace('\ndef main():', library_api + '\ndef main():')

with open(dst, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Generated {dst} ({len(code)} chars)")
print("Verifying imports...", end=" ")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("decompiler", dst)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("OK - module loads successfully")
    print(f"  Functions: decompile_file={hasattr(mod,'decompile_file')}, decompile_bytes={hasattr(mod,'decompile_bytes')}")
    print(f"  DecompileResult: {hasattr(mod,'DecompileResult')}")
except Exception as e:
    print(f"LOAD ERROR: {e}")
    import traceback
    traceback.print_exc()
