import sys; sys.path.insert(0, 'src')
sys.path.insert(0, r'c:\Users\Administrator\WorkBuddy\20260414101957\thirdparty\PbdCli')

import importlib
pbdcli = importlib.import_module('pbdcli')
import os

# Test logistic.exe with original pbdcli
with open(r'F:\workspace\X6\logistic\logistic\logistic.exe', 'rb') as f:
    data = f.read()

idx = data.find(b'HDR*')
print(f'HDR* at: 0x{idx:X}')

# Look at the PBD structure
pbd = data[idx:]
print('First 512 bytes after HDR*:')
# Check HDR* header
print(f'  HDR*: {pbd[:4]}')
print(f'  Next 12 bytes: {pbd[4:16]}')
# Check if it's PB5 ANSI or Unicode
try:
    sig = pbd[4:16].decode('ascii')
    print(f'  ASCII: {repr(sig)}')
except:
    pass
try:
    sig = pbd[4:28].decode('utf-16-le')
    print(f'  UTF16LE: {repr(sig)}')
except:
    pass

# Check bytes at various offsets
print(f'  Bytes 16-20: {pbd[16:20]}')  # Version string
print(f'  Bytes 18-22: {pbd[18:22]}')

# Try pbdcli on the raw PBD bytes via temp file
import tempfile
with tempfile.NamedTemporaryFile(suffix='.pbd', delete=False) as tmp:
    tmp.write(pbd)
    tmp_path = tmp.name

print(f'\nTrying pbdcli on extracted PBD ({len(pbd)} bytes) at {tmp_path}')
try:
    proj = pbdcli.PbProject(tmp_path)
    print(f'Version: {proj.version}, Unicode: {proj.is_unicode}, PB5: {proj.is_pb5}')
    for f in proj.files:
        print(f'File: {f.file_name}, Entries: {len(f.entries)}')
        for e in sorted(f.entries, key=lambda x: x.entry_name)[:10]:
            print(f'  {e.entry_name}')
except Exception as ex:
    print(f'Error: {ex}')
    import traceback
    traceback.print_exc()
finally:
    try: os.unlink(tmp_path)
    except: pass
