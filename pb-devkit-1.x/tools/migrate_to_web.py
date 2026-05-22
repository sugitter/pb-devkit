#!/usr/bin/env python3
"""
pb-devkit: EXE → Web Project Migration Tool
Usage: python migrate_to_web.py <exe_path> <output_dir>
"""
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pb_devkit.pbl_grouper import export_pbl_tree


def migrate(exe_path: str, output_dir: str):
    print(f"[1/3] Parsing {exe_path} ...")
    stats = export_pbl_tree(
        file_path=exe_path,
        output_dir=os.path.join(output_dir, 'pb_source'),
        project_name=None,
        suffix='.ps',
        clean=True,
        generate_readme=True,
    )
    print(f"      → {stats.total_saved} files, {stats.total_failed} failed, {stats.total_skipped} skipped")

    # Categorize
    src_base = os.path.join(output_dir, 'pb_source')
    dw_files, window_files, function_files, uo_files, app_files = [], [], [], [], []

    for pbl_dir in sorted(os.listdir(src_base)):
        pbl_path = os.path.join(src_base, pbl_dir)
        if not os.path.isdir(pbl_path):
            continue
        for f in sorted(os.listdir(pbl_path)):
            if not f.endswith('.ps'):
                continue
            name = f[:-3]
            if name.startswith('d_'):
                dw_files.append((pbl_dir, name))
            elif name.startswith('w_'):
                window_files.append((pbl_dir, name))
            elif name.startswith('f_') or name.startswith('gf_'):
                function_files.append((pbl_dir, name))
            elif name.startswith('n_') or name.startswith('u_'):
                uo_files.append((pbl_dir, name))
            elif name.startswith('a_'):
                app_files.append((pbl_dir, name))

    print(f"[2/3] Categorized: {len(dw_files)} DW, {len(window_files)} Windows, "
          f"{len(function_files)} Functions, {len(uo_files)} UserObjects")

    # Derive project name from exe
    project_name = os.path.splitext(os.path.basename(exe_path))[0] + '-web'
    project_dir = os.path.join(output_dir, project_name)

    # Create Angular project dirs
    dirs = [
        'src/app/components',
        'src/app/datawindows',
        'src/app/services',
        'src/app/models',
        'src/environments',
        'docs',
    ]
    for d in dirs:
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)

    # package.json
    pkg = {
        "name": project_name,
        "version": "1.0.0",
        "description": f"Migrated from PowerBuilder {os.path.basename(exe_path)}",
        "scripts": {
            "start": "ng serve",
            "build": "ng build --configuration production",
            "test": "ng test"
        },
        "dependencies": {
            "@angular/core": "^18.0.0",
            "@angular/common": "^18.0.0",
            "@angular/forms": "^18.0.0",
            "@angular/router": "^18.0.0",
            "@angular/material": "^18.0.0",
            "rxjs": "^7.8.0",
            "zone.js": "~0.14.0"
        },
        "devDependencies": {
            "@angular/cli": "^18.0.0",
            "@angular/compiler-cli": "^18.0.0",
            "typescript": "^5.4.0"
        }
    }
    with open(os.path.join(project_dir, 'package.json'), 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=2, ensure_ascii=False)

    # Angular component stubs for all Windows
    comp_dir = os.path.join(project_dir, 'src/app/components')
    for pbl_dir, name in window_files:
        comp_name = name.replace('w_', '').replace('_', '-')
        class_name = ''.join(w.capitalize() for w in name.replace('w_', '').split('_')) + 'Component'
        cdir = os.path.join(comp_dir, comp_name)
        os.makedirs(cdir, exist_ok=True)

        ts = (
            f"import {{ Component, OnInit }} from '@angular/core';\n\n"
            f"/**\n"
            f" * Migrated from PowerBuilder Window: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../pb_source/{pbl_dir}/{name}.ps\n"
            f" */\n"
            f"@Component({{\n"
            f"  selector: 'app-{comp_name}',\n"
            f"  templateUrl: './{comp_name}.component.html',\n"
            f"  styleUrls: ['./{comp_name}.component.scss']\n"
            f"}})\n"
            f"export class {class_name} implements OnInit {{\n"
            f"  constructor() {{}}\n"
            f"  ngOnInit(): void {{}}\n"
            f"}}\n"
        )
        html = (
            f"<!-- Migrated from PB Window: {name} (pbl: {pbl_dir}) -->\n"
            f"<div class=\"{comp_name}-container\">\n"
            f"  <h2>TODO: {name}</h2>\n"
            f"  <!-- Reference pb_source/{pbl_dir}/{name}.ps for controls & events -->\n"
            f"</div>\n"
        )
        scss = f".{comp_name}-container {{\n  // TODO: styles\n}}\n"

        with open(os.path.join(cdir, f'{comp_name}.component.ts'), 'w', encoding='utf-8') as f:
            f.write(ts)
        with open(os.path.join(cdir, f'{comp_name}.component.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        with open(os.path.join(cdir, f'{comp_name}.component.scss'), 'w', encoding='utf-8') as f:
            f.write(scss)

    # TypeScript model stubs for DataWindows
    dw_dir = os.path.join(project_dir, 'src/app/datawindows')
    for pbl_dir, name in dw_files:
        model_name = name.replace('d_', '').replace('_', '-')
        interface_name = ''.join(w.capitalize() for w in name.replace('d_', '').split('_')) + 'Model'
        ts = (
            f"/**\n"
            f" * DataWindow migrated: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../pb_source/{pbl_dir}/{name}.ps\n"
            f" * TODO: Define columns/fields based on DW SQL in the source file\n"
            f" */\n"
            f"export interface {interface_name} {{\n"
            f"  id?: number;\n"
            f"  // TODO: map DW columns to typed fields\n"
            f"}}\n"
        )
        with open(os.path.join(dw_dir, f'{model_name}.model.ts'), 'w', encoding='utf-8') as f:
            f.write(ts)

    # Function service stubs
    svc_dir = os.path.join(project_dir, 'src/app/services')
    for pbl_dir, name in function_files:
        svc_name = name.replace('f_', '').replace('gf_', '').replace('_', '-')
        class_name = ''.join(w.capitalize() for w in name.replace('f_', '').replace('gf_', '').split('_')) + 'Service'
        ts = (
            f"import {{ Injectable }} from '@angular/core';\n\n"
            f"/**\n"
            f" * Migrated global function: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../pb_source/{pbl_dir}/{name}.ps\n"
            f" */\n"
            f"@Injectable({{ providedIn: 'root' }})\n"
            f"export class {class_name} {{\n"
            f"  // TODO: implement based on PB source\n"
            f"}}\n"
        )
        with open(os.path.join(svc_dir, f'{svc_name}.service.ts'), 'w', encoding='utf-8') as f:
            f.write(ts)

    # app-routing.module.ts
    route_imports = '\n'.join(
        f"import {{ {(''.join(w.capitalize() for w in n.replace('w_','').split('_')))}Component }} from './components/{n.replace('w_','').replace('_','-')}/{n.replace('w_','').replace('_','-')}.component';"
        for _, n in window_files[:10]
    )
    routes = ',\n  '.join(
        f"{{ path: '{n.replace('w_','').replace('_','-')}', component: {(''.join(w.capitalize() for w in n.replace('w_','').split('_')))}Component }}"
        for _, n in window_files[:10]
    )
    routing_ts = (
        f"import {{ NgModule }} from '@angular/core';\n"
        f"import {{ RouterModule, Routes }} from '@angular/router';\n"
        f"{route_imports}\n\n"
        f"const routes: Routes = [\n"
        f"  {{ path: '', redirectTo: '{window_files[0][1].replace('w_','').replace('_','-') if window_files else 'home'}', pathMatch: 'full' }},\n"
        f"  {routes}\n"
        f"];\n\n"
        f"@NgModule({{\n"
        f"  imports: [RouterModule.forRoot(routes)],\n"
        f"  exports: [RouterModule]\n"
        f"}})\n"
        f"export class AppRoutingModule {{}}\n"
    )
    with open(os.path.join(project_dir, 'src/app/app-routing.module.ts'), 'w', encoding='utf-8') as f:
        f.write(routing_ts)

    # MIGRATION.md
    pbl_stats = {}
    for pbl_dir in sorted(os.listdir(src_base)):
        pbl_path = os.path.join(src_base, pbl_dir)
        if os.path.isdir(pbl_path):
            count = len([f for f in os.listdir(pbl_path) if f.endswith('.ps')])
            pbl_stats[pbl_dir] = count

    migration_md = '\n'.join([
        f"# {project_name} - Migration Summary",
        f"",
        f"> Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Source: {os.path.basename(exe_path)}",
        f"",
        f"## Statistics",
        f"",
        f"| Type | Count |",
        f"|------|-------|",
        f"| DataWindows (d_*) | {len(dw_files)} |",
        f"| Windows (w_*) | {len(window_files)} |",
        f"| Functions (f_*/gf_*) | {len(function_files)} |",
        f"| UserObjects (n_*/u_*) | {len(uo_files)} |",
        f"| **Total exported** | **{stats.total_saved}** |",
        f"",
        f"## Web Project Structure",
        f"",
        "```",
        f"{project_name}/",
        f"  src/app/",
        f"    components/     # {len(window_files)} Window → Angular Component stubs",
        f"    datawindows/    # {len(dw_files)} DW → TypeScript Model interfaces",
        f"    services/       # {len(function_files)} Global Functions → Angular Services",
        f"    models/         # Data models",
        f"  package.json      # Angular 18 + Angular Material",
        f"  app-routing.module.ts  # Route stubs for each Window",
        "```",
        f"",
        f"## PBL Breakdown",
        f"",
        f"| PBL | Files |",
        f"|-----|-------|",
    ] + [f"| {k} | {v} |" for k, v in pbl_stats.items()] + [
        f"",
        f"## Migration Checklist",
        f"",
        f"- [ ] Review `pb_source/` — understand business logic per module",
        f"- [ ] Fill component HTML templates (components/*/)",
        f"- [ ] Map DataWindow SQL → REST API + Angular Material table",
        f"- [ ] Convert global functions to Angular Injectable services",
        f"- [ ] Set up Angular routing (app-routing.module.ts already scaffolded)",
        f"- [ ] Connect to backend API (replace SQL Server direct access)",
        f"- [ ] Test each Window component end-to-end",
    ])
    with open(os.path.join(project_dir, 'MIGRATION.md'), 'w', encoding='utf-8') as f:
        f.write(migration_md)

    print(f"[3/3] Web scaffold written to: {project_dir}")
    print()
    # Print tree summary
    for root, dirs_l, files_l in os.walk(project_dir):
        level = root.replace(project_dir, '').count(os.sep)
        indent = '  ' * level
        folder = os.path.basename(root)
        print(f"{indent}{folder}/ ({len(files_l)} files)")
    print()
    print(f"Done! Total: {stats.total_saved} PB objects → Angular {len(window_files)} components, "
          f"{len(dw_files)} DW models, {len(function_files)} services")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <exe_path> <output_dir>")
        sys.exit(1)
    migrate(sys.argv[1], sys.argv[2])
