"""Quick test: parse all PBLs and dump entry list."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')
from pb_devkit.pbl_parser import PBLParser

pbl_dir = r'F:\workspace\X6\3.5\dgsauna'
pbls = sorted([f for f in os.listdir(pbl_dir) if f.lower().endswith('.pbl')])
print(f'Found {len(pbls)} PBL files\n')

total = 0
for pbl_name in pbls:
    pbl_path = os.path.join(pbl_dir, pbl_name)
    size = os.path.getsize(pbl_path)
    try:
        with PBLParser(pbl_path) as parser:
            entries = parser.entries
            total += len(entries)
            print(f'{pbl_name} ({size:,}b) -> {len(entries)} entries')
            for e in entries[:10]:
                name = e.name.encode('ascii', 'replace').decode('ascii')
                comment = e.comment.encode('ascii', 'replace').decode('ascii')
                print(f'  {name:40s} type={e.object_type:2d} off={e.first_data_offset:8d} size={e.data_size:6d} {comment[:50]}')
            if len(entries) > 10:
                print(f'  ... +{len(entries)-10} more')
            print()
    except Exception as ex:
        print(f'{pbl_name} -> ERROR: {ex}\n')

print(f'TOTAL: {total} entries across {len(pbls)} PBL files')
