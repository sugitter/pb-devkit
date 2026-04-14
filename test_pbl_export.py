"""Test: export source from a real PBL and verify content."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')
from pb_devkit.pbl_parser import PBLParser

pbl_path = r'F:\workspace\X6\3.5\dgsauna\dgsauna01.pbl'
out_dir = r'F:\workspace\X6\3.5\dgsauna\exported'

os.makedirs(out_dir, exist_ok=True)

with PBLParser(pbl_path) as parser:
    print(f'PBL: {pbl_path}')
    print(f'Entries: {len(parser.entries)}')
    print(f'Unicode: {parser._is_unicode}')
    print(f'Header size: {parser._header_size}')
    print()
    
    exported = 0
    failed = 0
    for entry in parser.entries:
        name = entry.name.encode('ascii', 'replace').decode('ascii')
        src = parser.export_source(entry)
        if src and len(src) > 10:
            fname = (name + entry.extension).replace('\x00', '').replace('/', '_').replace('\\', '_')
            fpath = os.path.join(out_dir, fname)
            with open(fpath, 'wb') as f:
                f.write(src)
            
            # Show first 200 chars of text content
            try:
                text = src.decode('utf-8', errors='replace')[:200].replace('\r\n', '\n').replace('\r', '\n')
            except:
                text = src[:200].decode('latin-1', errors='replace')
            
            print(f'OK: {fname:45s} {len(src):6d} bytes')
            print(f'    Preview: {text[:120]}...')
            exported += 1
        else:
            print(f'SKIP: {name:45s} src={len(src) if src else 0} bytes')
            failed += 1
    
    print(f'\nExported: {exported}, Failed: {failed}')
