"""Extract .srw source from PBL using PbdCli, fixing Chinese encoding."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "thirdparty", "PbdCli"))

from pbdcli import PbProject, dump_entry

pbl = r"F:\workspace\X6\3.5\datasync\datasync.pbl"
out_dir = r"c:\Users\Administrator\WorkBuddy\20260414101957\datasync_export"
os.makedirs(out_dir, exist_ok=True)

print(f"Loading {pbl}...")
project = PbProject(pbl)
print(f"PB Version: {project.version}, Unicode: {project.is_unicode}")

# Extract all source entries
source_extensions = ('srw', 'sru', 'srf', 'srd', 'srm', 'srs', 'sra', 'srj', 'men')
exported = 0

for f in project.files:
    for e in f.entries:
        if e.suffix.lower() not in source_extensions:
            continue
        
        raw = e._entry_data
        # PB12 Unicode PBL stores data as UTF-16LE
        # Detect: check for BOM-like pattern or alternating null bytes
        is_utf16 = len(raw) >= 4 and raw[1] == 0 and raw[3] == 0
        if is_utf16:
            text = raw.decode('utf-16-le')
            enc = 'utf-16-le'
        else:
            # Try ANSI encodings for non-Unicode PBL
            for enc in ('gbk', 'gb2312', 'utf-8', 'latin-1'):
                try:
                    text = raw.decode(enc)
                    if any(ord(c) > 127 for c in text[:500]):
                        break
                except:
                    continue
        
        out_path = os.path.join(out_dir, e.entry_name)
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(text)
        
        lines = text.count('\n')
        print(f"  {e.entry_name}: {len(text)} chars, {lines} lines ({enc})")
        exported += 1

print(f"\nExported {exported} source files to {out_dir}")
