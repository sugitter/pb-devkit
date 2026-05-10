import sys; sys.path.insert(0, 'src')
from pb_devkit.decompiler import decompile_bytes

with open(r'F:\workspace\X6\logistic\logistic\logistic.exe', 'rb') as f:
    data = f.read()

idx = data.find(b'HDR*')
print(f'HDR* at offset: 0x{idx:X}')
pbd_data = data[idx:]
print(f'PBD data size: {len(pbd_data)}')

results = decompile_bytes(pbd_data, decompile_all=False)
print(f'Results: {len(results)}')
for r in results[:20]:
    status = 'OK' if r.success else 'ERR'
    print(f'  [{status}] {r.entry_name}')
if results and not results[0].success:
    print('Error:', results[0].error)
