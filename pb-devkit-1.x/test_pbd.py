import sys; sys.path.insert(0, 'src')
from pb_devkit.decompiler import decompile_file, list_entries

# Test with datasync.pbd first
pbd_path = r'F:\workspace\X6\3.5\datasync\datasync.pbl'
import os
if os.path.exists(pbd_path):
    print(f'Testing: {pbd_path}')
    entries = list_entries(pbd_path)
    print(f'Entries: {len(entries)}')
    for e in entries[:10]:
        print(f'  {e}')
else:
    print(f'File not found: {pbd_path}')

# Also check what PbdCli's original CLI produces
# Import original pbdcli
sys.path.insert(0, r'c:\Users\Administrator\WorkBuddy\20260414101957\thirdparty\PbdCli')
import importlib
pbdcli = importlib.import_module('pbdcli')

print('\n--- Using original pbdcli on datasync.pbl ---')
if os.path.exists(pbd_path):
    try:
        proj = pbdcli.PbProject(pbd_path)
        print(f'PB Version: {proj.version}, Unicode: {proj.is_unicode}')
        for f in proj.files:
            print(f'  File: {f.file_name}')
            for e in sorted(f.entries, key=lambda x: x.entry_name)[:5]:
                print(f'    {e.entry_name}')
    except Exception as ex:
        print(f'Error: {ex}')
