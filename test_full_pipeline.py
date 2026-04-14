"""Export all PBLs and run full analysis pipeline."""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')
from pb_devkit.pbl_parser import PBLParser
from pb_devkit.sr_parser import PBSourceAnalyzer, DependencyAnalyzer, ComplexityAnalyzer
from pb_devkit.config import PBConfig

pbl_dir = r'F:\workspace\X6\3.5\dgsauna'
out_dir = r'F:\workspace\X6\3.5\dgsauna\pb_export'

# Clean output
if os.path.exists(out_dir):
    shutil.rmtree(out_dir)
os.makedirs(out_dir)

pbls = sorted([f for f in os.listdir(pbl_dir) if f.lower().endswith('.pbl')])
print(f'=== Exporting {len(pbls)} PBL files ===\n')

total_exported = 0
total_failed = 0

for pbl_name in pbls:
    pbl_path = os.path.join(pbl_dir, pbl_name)
    try:
        with PBLParser(pbl_path) as parser:
            entries = parser.entries
            exported = 0
            for entry in entries:
                src = parser.export_source(entry)
                if not src or len(src) < 10:
                    continue
                
                # Check if content is text source (not compiled binary)
                try:
                    # PB12 Unicode PBL stores data as UTF-16LE
                    # Try UTF-16LE first (check for alternating null bytes)
                    is_utf16 = len(src) >= 4 and src[1] == 0 and src[3] == 0
                    if is_utf16:
                        text = src.decode('utf-16-le', errors='replace')
                    else:
                        text = src.decode('utf-8', errors='replace')
                    
                    first_200 = text[:200].lower()
                    is_source = any(kw in first_200 for kw in ['export by', '$pbexportheader$', 'global type'])
                    if not is_source:
                        continue  # Compiled binary, skip
                    
                    # Re-encode to UTF-8 for file storage
                    src = text.encode('utf-8')
                except:
                    continue
                
                # Use entry name as filename (it already has extension like .srf, .srd, etc.)
                safe_name = entry.name.replace('\x00', '').replace('/', '_').replace('\\', '_')
                fpath = os.path.join(out_dir, safe_name)
                with open(fpath, 'wb') as f:
                    f.write(src)
                exported += 1
            
            print(f'{pbl_name}: {exported}/{len(entries)} source entries exported')
            total_exported += exported
            total_failed += len(entries) - exported
    except Exception as ex:
        print(f'{pbl_name}: ERROR - {ex}')

print(f'\n=== Total: {total_exported} source files exported, {total_failed} binary skipped ===')

# Now analyze
print(f'\n=== Analyzing exported sources ===\n')
config = PBConfig()
config_dict = config.to_dict()

all_files = []
for root, dirs, files in os.walk(out_dir):
    for fname in files:
        fpath = os.path.join(root, fname)
        all_files.append(fpath)

analyzer = PBSourceAnalyzer(config=config_dict)
dep_analyzer = DependencyAnalyzer()
cx_analyzer = ComplexityAnalyzer()

issues = []
deps = []
functions = []
total_lines = 0

for fpath in sorted(all_files):
    try:
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            source = f.read()
        lines = source.count('\n') + 1
        total_lines += lines
        
        # Analyze
        file_issues = analyzer.analyze(source, os.path.basename(fpath))
        issues.extend(file_issues)
        
        # Dependencies
        file_deps = dep_analyzer.analyze(source, os.path.basename(fpath))
        deps.extend(file_deps)
        
        # Complexity
        routines = cx_analyzer.analyze(source, os.path.basename(fpath))
        functions.extend(routines)
    except Exception as ex:
        print(f'  Error analyzing {fpath}: {ex}')

print(f'Files: {len(all_files)}')
print(f'Total lines: {total_lines:,}')
print(f'Issues: {len(issues)}')
print(f'Dependencies: {len(deps)}')
print(f'Functions: {len(functions)}')

# Issue summary
from collections import Counter
severity_counts = Counter(i.severity for i in issues)
print(f'\n--- Issue Summary ---')
for sev, count in severity_counts.most_common():
    print(f'  {sev}: {count}')

rule_counts = Counter(i.rule for i in issues)
print(f'\n--- By Rule ---')
for rule, count in rule_counts.most_common():
    print(f'  {rule}: {count}')

# Top 10 longest functions
print(f'\n--- Top 10 Longest Functions ---')
funcs_sorted = sorted(functions, key=lambda f: f.lines, reverse=True)[:10]
for f in funcs_sorted:
    cx_grade = cx_analyzer.grade(f.complexity) if hasattr(cx_analyzer, 'grade') else '?'
    print(f'  {f.name:40s} {f.lines:4d} lines  cx={f.complexity:3d} ({cx_grade})  in {f.file}')

print(f'\nDone!')
