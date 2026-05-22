import sys; sys.path.insert(0, 'src')
from pb_devkit.decompiler import decompile_file
from pathlib import Path
import os

out_dir = Path(r'F:\workspace\X6\logistic\logistic\src')
out_dir.mkdir(parents=True, exist_ok=True)

results = decompile_file(
    r'F:\workspace\X6\logistic\logistic\logistic.exe',
    decompile_all=True
)

ok = 0
fail = 0
skipped = 0

for r in results:
    if not r.success:
        print(f'[ERR] {r.entry_name}: {r.error}')
        fail += 1
        continue
    if not r.source or r.source.strip() == '':
        skipped += 1
        continue
    
    # Derive safe filename
    name = r.entry_name
    if '\\' in name or '/' in name:
        # Skip image/resource paths like bmp\s1.gif
        skipped += 1
        continue
    
    base = name.rsplit('.', 1)[0] if '.' in name else name
    out_file = out_dir / (base + '.ps')
    out_file.write_text(r.source, encoding='utf-8')
    print(f'  {r.entry_name} -> {out_file.name}')
    ok += 1

print(f'\n[done] {ok} saved, {fail} failed, {skipped} skipped (binary/image)')
print(f'Output: {out_dir}')

# Count files
files = list(out_dir.glob('*.ps'))
print(f'Total .ps files: {len(files)}')
