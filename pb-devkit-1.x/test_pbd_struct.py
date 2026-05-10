import sys, struct
sys.path.insert(0, 'src')
sys.path.insert(0, r'c:\Users\Administrator\WorkBuddy\20260414101957\thirdparty\PbdCli')

with open(r'F:\workspace\X6\logistic\logistic\logistic.exe', 'rb') as f:
    data = f.read()

idx = data.find(b'HDR*')
print(f'HDR* at: 0x{idx:X}')
pbd = data[idx:]

# Show first 1024 bytes in hex
print('\nFirst 128 bytes of PBD:')
for i in range(0, min(128, len(pbd)), 16):
    hex_str = ' '.join(f'{b:02X}' for b in pbd[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in pbd[i:i+16])
    print(f'  {idx+i:06X}: {hex_str:<48} {ascii_str}')

# Check if there's a NOD* nearby
print('\nSearching for NOD* after HDR*:')
nod_idx = pbd.find(b'NOD*')
if nod_idx >= 0:
    print(f'  NOD* at +0x{nod_idx:X} (absolute: 0x{idx+nod_idx:X})')
    print(f'  Distance from HDR*: {nod_idx} bytes')
    # Should be 1024 for ANSI, 1536 for Unicode
    # HDR*(512) + FRE*(512) = 1024 for ANSI PBL
else:
    print('  NOD* not found in first 4096 bytes')
    nod_idx = data[idx:idx+4096].find(b'NOD*')

# Check what's at offset 512 from HDR*
print(f'\nAt HDR*+512: {pbd[512:516]}')
print(f'At HDR*+1024: {pbd[1024:1028]}')
print(f'At HDR*+1536: {pbd[1536:1540]}')

# Try original PbdCli directly on the .exe
import importlib
pbdcli = importlib.import_module('pbdcli')
print('\nTrying pbdcli directly on logistic.exe:')
try:
    proj = pbdcli.PbProject(r'F:\workspace\X6\logistic\logistic\logistic.exe')
    print(f'Version: {proj.version}, Unicode: {proj.is_unicode}')
    for f in proj.files:
        for e in sorted(f.entries, key=lambda x: x.entry_name)[:5]:
            print(f'  {e.entry_name}')
except Exception as ex:
    print(f'Error: {ex}')
