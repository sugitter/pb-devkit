import sys; sys.path.insert(0,'src')
from pb_devkit.commands.dw import _scan_dw_references, _parse_dw_file, _build_table_schema
from pathlib import Path

src_dir = Path(r'c:\Users\Administrator\WorkBuddy\20260414101957\src\logistic')

print('Scanning DW references...')
refs = _scan_dw_references(src_dir)
print('Found ' + str(len(refs)) + ' DataWindow references:')
for dw_name, windows in sorted(refs.items())[:20]:
    print('  ' + dw_name + ' <- ' + ', '.join(windows))
