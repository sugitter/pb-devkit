import sys; sys.path.insert(0,'src')
from pb_devkit.commands.dw import _parse_dw_file
from pathlib import Path

# Test with a real .ps file from logistic dw_logistic.pbl
dw_dir = Path(r'c:\Users\Administrator\WorkBuddy\20260414101957\src\logistic\dw_logistic.pbl')
files = list(dw_dir.glob('*.ps'))[:5]
for f in files:
    text = f.read_text(encoding='utf-8-sig', errors='replace')
    result = _parse_dw_file(f.stem, text, '.ps')
    print('--- ' + f.stem + ' ---')
    print('  style: ' + str(result['style']))
    print('  tables: ' + str(result['tables']))
    print('  columns: ' + str(len(result['columns'])))
    sql_preview = result['sql'][:100] if result['sql'] else ''
    print('  sql: ' + sql_preview)
    print()
