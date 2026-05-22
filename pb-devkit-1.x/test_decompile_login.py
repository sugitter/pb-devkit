import sys; sys.path.insert(0, 'src')
from pb_devkit.decompiler import decompile_file

results = decompile_file(
    r'F:\workspace\X6\logistic\logistic\logistic.exe',
    entry_name='w_login',
    decompile_all=True
)
print(f'Results: {len(results)}')
for r in results:
    if r.success:
        print(f'Entry: {r.entry_name}')
        print(r.source[:3000])
    else:
        print(f'Error [{r.entry_name}]: {r.error}')
