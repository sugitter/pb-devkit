"""
pb migrate — One-click PowerBuilder EXE/PBL → Angular Web project migration

Generates a production-ready Angular 18 scaffold from PB source:
  - Window  → Angular Component (TypeScript + HTML + SCSS)
  - DataWindow → TypeScript Model interface + Reactive Form + Material table
  - Global Function → Angular Injectable Service stub
  - AppRoutingModule with all Window routes
  - MIGRATION.md with effort estimates and priority checklist
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
import re
import sys


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "migrate",
        help="Migrate a PB EXE/PBL project to a modern Angular Web scaffold",
    )
    p.add_argument(
        "source",
        help="Path to PB EXE file or directory containing PBL files",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (default: <source_dir>/pb-migrate-output)",
    )
    p.add_argument(
        "--project-name",
        default=None,
        help="Override project name (default: derived from source filename)",
    )
    p.add_argument(
        "--suffix",
        default=".ps",
        help="Extension for exported PB source files (default: .ps)",
    )
    p.add_argument(
        "--no-forms",
        action="store_true",
        help="Skip Angular Reactive Forms generation for DataWindows",
    )
    p.add_argument(
        "--no-services",
        action="store_true",
        help="Skip service stub generation from PB functions",
    )


def run_migrate(args: argparse.Namespace) -> None:
    """Execute the migrate command."""
    from pb_devkit.pbl_grouper import export_pbl_tree

    source = os.path.abspath(args.source)
    if not os.path.exists(source):
        print(f"Error: Source path does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    # Determine output dir
    if args.output:
        output_dir = os.path.abspath(args.output)
    else:
        parent = os.path.dirname(source) if os.path.isfile(source) else source
        output_dir = os.path.join(parent, "pb-migrate-output")

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Export PB source
    print(f"[1/3] Parsing {source} ...")
    stats = export_pbl_tree(
        file_path=source,
        output_dir=os.path.join(output_dir, "pb_source"),
        project_name=args.project_name,
        suffix=args.suffix,
        clean=True,
        generate_readme=True,
    )
    print(f"      → {stats.total_saved} files exported, {stats.total_failed} failed, {stats.total_skipped} skipped")

    if stats.total_saved == 0:
        print("Error: No source files exported. Check if the input is a valid PB EXE/PBL.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Categorize objects
    src_base = os.path.join(output_dir, "pb_source")
    dw_files, window_files, function_files, uo_files = [], [], [], []

    for pbl_dir in sorted(os.listdir(src_base)):
        pbl_path = os.path.join(src_base, pbl_dir)
        if not os.path.isdir(pbl_path):
            continue
        for f in sorted(os.listdir(pbl_path)):
            if not f.endswith(args.suffix):
                continue
            name = f[: -len(args.suffix)]
            if name.startswith("d_"):
                dw_files.append((pbl_dir, name))
            elif name.startswith("w_"):
                window_files.append((pbl_dir, name))
            elif name.startswith("f_") or name.startswith("gf_"):
                function_files.append((pbl_dir, name))
            elif name.startswith("n_") or name.startswith("u_"):
                uo_files.append((pbl_dir, name))

    print(
        f"[2/3] Categorized: {len(dw_files)} DataWindows, {len(window_files)} Windows, "
        f"{len(function_files)} Functions, {len(uo_files)} UserObjects"
    )

    # Step 3: Generate Angular scaffold
    project_name = args.project_name
    if not project_name:
        base = os.path.basename(source)
        project_name = os.path.splitext(base)[0] + "-web"
    project_dir = os.path.join(output_dir, project_name)

    no_forms = getattr(args, "no_forms", False)
    no_services = getattr(args, "no_services", False)

    _make_dirs(project_dir, [
        "src/app/components",
        "src/app/datawindows",
        "src/app/services",
        "src/app/models",
        "src/environments",
        "docs",
    ])

    _write_package_json(project_dir, project_name, os.path.basename(source))
    _write_components(project_dir, window_files, args.suffix, src_base)
    _write_dw_models(project_dir, dw_files, src_base, args.suffix, no_forms)
    _write_service_stubs(project_dir, function_files, src_base, args.suffix, no_services)
    _write_app_routing(project_dir, window_files)
    _write_migration_md(
        project_dir, project_name, source, stats,
        dw_files, window_files, function_files, uo_files, src_base, args.suffix,
    )

    print(f"[3/3] Angular scaffold → {project_dir}")
    print()
    print(f"Done! {stats.total_saved} PB objects → {len(window_files)} components, "
          f"{len(dw_files)} DW models, {len(function_files)} services")
    print(f"\nOutput structure:")
    print(f"  {output_dir}/")
    print(f"    pb_source/       ← PowerScript source (按 PBL 分组)")
    print(f"    {project_name}/  ← Angular 18 project scaffold")
    print(f"      MIGRATION.md   ← Migration checklist & statistics")


# ── Source parsing helpers ────────────────────────────────────────────────────

def _read_source(src_base: str, pbl_dir: str, name: str, suffix: str) -> str:
    """Read PB source file, return empty string on error."""
    path = os.path.join(src_base, pbl_dir, name + suffix)
    if not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _extract_dw_columns(source: str) -> list:
    """Extract column names from DataWindow source. Returns [(name, ts_type), ...]."""
    columns = []
    # column name=xxx
    for m in re.finditer(r'\bcolumn\s+name\s*=\s*["\']?(\w+)["\']?', source, re.IGNORECASE):
        col = m.group(1).lower()
        if col not in (c[0] for c in columns):
            # Guess TS type from common PB column naming conventions
            if any(col.endswith(s) for s in ("_date", "_time", "_dt")):
                ts_type = "string  // Date"
            elif any(col.endswith(s) for s in ("_id", "_no", "_num", "_amt", "_qty", "_count")):
                ts_type = "number"
            elif any(col.endswith(s) for s in ("_flag", "_yn", "_bool", "_active")):
                ts_type = "boolean"
            else:
                ts_type = "string"
            columns.append((col, ts_type))
    return columns[:60]


def _extract_dw_sql(source: str) -> str:
    """Extract SQL SELECT from DataWindow retrieve= line."""
    m = re.search(r'retrieve\s*=\s*"([^"]{10,})"', source, re.IGNORECASE | re.DOTALL)
    if m:
        sql = m.group(1).replace("~n", "\n").replace("~t", "\t").strip()
        return sql[:800]
    return ""


def _extract_window_events(source: str) -> list:
    """Extract event names defined in a Window source."""
    events = []
    for m in re.finditer(r'\bevent\s+(\w+)\b', source, re.IGNORECASE):
        ev = m.group(1).lower()
        if ev not in events and not ev.startswith("pbm_"):
            events.append(ev)
    return events[:20]


def _extract_function_signature(source: str, func_name: str) -> tuple:
    """Return (return_type_ts, params_ts) by parsing global function source."""
    _pb_to_ts = {
        "integer": "number", "long": "number", "double": "number",
        "decimal": "number", "string": "string", "boolean": "boolean",
        "datetime": "string", "date": "string", "time": "string",
        "any": "any", "void": "void",
    }
    m = re.search(
        r'(?:global\s+)?function\s+(\w+)\s+' + re.escape(func_name) + r'\s*\(([^)]*)\)',
        source, re.IGNORECASE,
    )
    if not m:
        return "any", ""
    ret_pb = m.group(1).lower()
    ret_ts = _pb_to_ts.get(ret_pb, "any")
    raw_params = m.group(2).strip()
    if not raw_params:
        return ret_ts, ""
    # Convert params: "string as_name, integer ai_id" → "name: string, id: number"
    params = []
    for part in raw_params.split(","):
        part = part.strip()
        words = part.split()
        if len(words) >= 3 and words[1].lower() == "as":
            ts_type = _pb_to_ts.get(words[0].lower(), "any")
            p_name = words[2].lower().lstrip("a").lstrip("s").lstrip("i") or words[2]
            params.append(f"{p_name}: {ts_type}")
        elif len(words) >= 2:
            ts_type = _pb_to_ts.get(words[0].lower(), "any")
            params.append(f"arg: {ts_type}")
    return ret_ts, ", ".join(params)


# ── Layout helpers ─────────────────────────────────────────────────────────────

def _make_dirs(project_dir: str, dirs: list) -> None:
    for d in dirs:
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)


def _to_class(name: str, prefix: str) -> str:
    return "".join(w.capitalize() for w in name.replace(prefix, "").split("_"))


def _write_package_json(project_dir: str, project_name: str, source_file: str) -> None:
    pkg = {
        "name": project_name,
        "version": "1.0.0",
        "description": f"Migrated from PowerBuilder {source_file}",
        "scripts": {
            "start": "ng serve",
            "build": "ng build --configuration production",
            "test": "ng test",
        },
        "dependencies": {
            "@angular/core": "^18.0.0",
            "@angular/common": "^18.0.0",
            "@angular/forms": "^18.0.0",
            "@angular/router": "^18.0.0",
            "@angular/material": "^18.0.0",
            "@angular/cdk": "^18.0.0",
            "@angular/platform-browser": "^18.0.0",
            "@angular/platform-browser-dynamic": "^18.0.0",
            "@angular/animations": "^18.0.0",
            "rxjs": "^7.8.0",
            "zone.js": "~0.14.0",
        },
        "devDependencies": {
            "@angular/cli": "^18.0.0",
            "@angular/compiler-cli": "^18.0.0",
            "typescript": "^5.4.0",
        },
    }
    with open(os.path.join(project_dir, "package.json"), "w", encoding="utf-8") as f:
        json.dump(pkg, f, indent=2, ensure_ascii=False)


def _write_components(
    project_dir: str, window_files: list, suffix: str, src_base: str
) -> None:
    comp_root = os.path.join(project_dir, "src/app/components")
    for pbl_dir, name in window_files:
        source = _read_source(src_base, pbl_dir, name, suffix)
        events = _extract_window_events(source) if source else []

        comp_name = name.replace("w_", "").replace("_", "-")
        class_name = _to_class(name, "w_") + "Component"
        cdir = os.path.join(comp_root, comp_name)
        os.makedirs(cdir, exist_ok=True)

        # Build event method stubs
        event_methods = ""
        for ev in events:
            ev_camel = "".join(w.capitalize() for w in ev.split("_"))
            event_methods += f"\n  /** PB event: {ev} */\n  on{ev_camel}(): void {{\n    // TODO: migrate PB logic from pb_source/{pbl_dir}/{name}{suffix}\n  }}\n"

        ts = (
            f"import {{ Component, OnInit }} from '@angular/core';\n\n"
            f"/**\n"
            f" * Migrated from PowerBuilder Window: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../../pb_source/{pbl_dir}/{name}{suffix}\n"
            f" */\n"
            f"@Component({{\n"
            f"  selector: 'app-{comp_name}',\n"
            f"  templateUrl: './{comp_name}.component.html',\n"
            f"  styleUrls: ['./{comp_name}.component.scss']\n"
            f"}})\n"
            f"export class {class_name} implements OnInit {{\n"
            f"  constructor() {{}}\n\n"
            f"  ngOnInit(): void {{\n"
            f"    // TODO: initialize component (was PB Open event)\n"
            f"  }}\n"
            f"{event_methods}}}\n"
        )
        html = (
            f"<!-- Migrated from PB Window: {name} (PBL: {pbl_dir}) -->\n"
            f"<div class=\"{comp_name}-container\">\n"
            f"  <mat-toolbar color=\"primary\">\n"
            f"    <span>{name}</span>\n"
            f"  </mat-toolbar>\n\n"
            f"  <!-- TODO: reconstruct controls from pb_source/{pbl_dir}/{name}{suffix} -->\n"
            f"  <div class=\"content\">\n"
            f"    <p>Window: {name}</p>\n"
            f"  </div>\n"
            f"</div>\n"
        )
        scss = (
            f".{comp_name}-container {{\n"
            f"  display: flex;\n"
            f"  flex-direction: column;\n"
            f"  height: 100%;\n\n"
            f"  .content {{\n"
            f"    padding: 16px;\n"
            f"    flex: 1;\n"
            f"  }}\n"
            f"}}\n"
        )

        _write(os.path.join(cdir, f"{comp_name}.component.ts"), ts)
        _write(os.path.join(cdir, f"{comp_name}.component.html"), html)
        _write(os.path.join(cdir, f"{comp_name}.component.scss"), scss)


def _write_dw_models(
    project_dir: str, dw_files: list,
    src_base: str, suffix: str, no_forms: bool = False,
) -> None:
    dw_dir = os.path.join(project_dir, "src/app/datawindows")
    for pbl_dir, name in dw_files:
        source = _read_source(src_base, pbl_dir, name, suffix)
        columns = _extract_dw_columns(source) if source else []
        sql = _extract_dw_sql(source) if source else ""

        model_name = name.replace("d_", "").replace("_", "-")
        interface_name = _to_class(name, "d_") + "Model"

        # Interface fields
        if columns:
            fields = "\n".join(f"  {col}?: {ts_type};" for col, ts_type in columns)
        else:
            fields = "  id?: number;\n  // TODO: map DW columns to typed fields"

        sql_comment = f"\n * SQL: {sql[:200]}" if sql else ""

        ts = (
            f"/**\n"
            f" * DataWindow migrated: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../../pb_source/{pbl_dir}/{name}{suffix}{sql_comment}\n"
            f" */\n"
            f"export interface {interface_name} {{\n"
            f"{fields}\n"
            f"}}\n"
        )

        # Reactive Form if columns available and not disabled
        if columns and not no_forms:
            form_controls = ",\n".join(
                f"      {col}: [null]" for col, _ in columns[:20]
            )
            ts += (
                f"\n"
                f"// Angular Reactive Form factory\n"
                f"import {{ FormBuilder, FormGroup }} from '@angular/forms';\n\n"
                f"export function build{interface_name}Form(fb: FormBuilder): FormGroup {{\n"
                f"  return fb.group({{\n"
                f"{form_controls}\n"
                f"  }});\n"
                f"}}\n"
            )

        # Material table column config
        if columns:
            displayed = ", ".join(f"'{col}'" for col, _ in columns[:8])
            ts += (
                f"\n"
                f"// Angular Material table displayed columns\n"
                f"export const {interface_name.upper()}_COLUMNS = [{displayed}];\n"
            )

        _write(os.path.join(dw_dir, f"{model_name}.model.ts"), ts)


def _write_service_stubs(
    project_dir: str, function_files: list,
    src_base: str, suffix: str, no_services: bool = False,
) -> None:
    if no_services:
        return
    svc_dir = os.path.join(project_dir, "src/app/services")
    for pbl_dir, name in function_files:
        source = _read_source(src_base, pbl_dir, name, suffix)
        ret_type, params = _extract_function_signature(source, name) if source else ("any", "")

        prefix = "gf_" if name.startswith("gf_") else "f_"
        svc_name = name.replace(prefix, "").replace("_", "-")
        class_name = _to_class(name, prefix) + "Service"
        method_name = "".join(
            (w if i == 0 else w.capitalize())
            for i, w in enumerate(name.replace(prefix, "").split("_"))
        )

        ts = (
            f"import {{ Injectable }} from '@angular/core';\n"
            f"import {{ HttpClient }} from '@angular/common/http';\n"
            f"import {{ Observable }} from 'rxjs';\n\n"
            f"/**\n"
            f" * Migrated global function: {name}\n"
            f" * Original PBL: {pbl_dir}\n"
            f" * Reference: ../../../pb_source/{pbl_dir}/{name}{suffix}\n"
            f" */\n"
            f"@Injectable({{ providedIn: 'root' }})\n"
            f"export class {class_name} {{\n"
            f"  constructor(private http: HttpClient) {{}}\n\n"
            f"  /** Migrated from PB global function: {name} */\n"
            f"  {method_name}({params}): {ret_type} {{\n"
            f"    // TODO: implement based on PB source\n"
            f"    throw new Error('Not implemented');\n"
            f"  }}\n"
            f"}}\n"
        )
        _write(os.path.join(svc_dir, f"{svc_name}.service.ts"), ts)


def _write_app_routing(project_dir: str, window_files: list) -> None:
    first_route = window_files[0][1].replace("w_", "").replace("_", "-") if window_files else "home"
    imports = "\n".join(
        f"import {{ {_to_class(n, 'w_')}Component }} from "
        f"'./components/{n.replace('w_','').replace('_','-')}"
        f"/{n.replace('w_','').replace('_','-')}.component';"
        for _, n in window_files
    )
    routes = ",\n  ".join(
        f"{{ path: '{n.replace('w_','').replace('_','-')}', "
        f"component: {_to_class(n, 'w_')}Component }}"
        for _, n in window_files
    )
    content = (
        f"import {{ NgModule }} from '@angular/core';\n"
        f"import {{ RouterModule, Routes }} from '@angular/router';\n"
        f"{imports}\n\n"
        f"const routes: Routes = [\n"
        f"  {{ path: '', redirectTo: '{first_route}', pathMatch: 'full' }},\n"
        f"  {routes}\n"
        f"];\n\n"
        f"@NgModule({{\n"
        f"  imports: [RouterModule.forRoot(routes)],\n"
        f"  exports: [RouterModule]\n"
        f"}})\n"
        f"export class AppRoutingModule {{}}\n"
    )
    _write(os.path.join(project_dir, "src/app/app-routing.module.ts"), content)


def _write_migration_md(
    project_dir: str, project_name: str, source: str,
    stats, dw_files: list, window_files: list, function_files: list,
    uo_files: list, src_base: str, suffix: str,
) -> None:
    pbl_stats = {}
    for pbl_dir in sorted(os.listdir(src_base)):
        pbl_path = os.path.join(src_base, pbl_dir)
        if os.path.isdir(pbl_path):
            count = len([f for f in os.listdir(pbl_path) if not f.startswith(".")])
            if count:
                pbl_stats[pbl_dir] = count

    # Effort estimation (rough)
    total_components = len(window_files)
    total_dw = len(dw_files)
    total_services = len(function_files)
    est_days_low = round((total_components * 0.5 + total_dw * 0.3 + total_services * 0.2), 1)
    est_days_high = round((total_components * 2.0 + total_dw * 1.0 + total_services * 0.5), 1)

    # Priority phases
    phase1 = [n for _, n in window_files if any(
        n == p or n.startswith(p + "_")
        for p in ("w_login", "w_main", "w_frame", "w_splash", "w_md")
    )]
    phase2 = [n for _, n in window_files if n not in phase1 and any(
        n.startswith(p) for p in ("w_sngl_", "w_find_", "w_list_", "w_print_")
    )]
    phase3 = [n for _, n in window_files if n not in phase1 and n not in phase2]

    lines = [
        f"# {project_name} — Migration Plan",
        f"",
        f"> Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Source: `{os.path.basename(source)}`",
        f"",
        f"## Summary Statistics",
        f"",
        f"| Category | Count | Effort (days, rough) |",
        f"|----------|-------|----------------------|",
        f"| Windows → Angular Components | {total_components} | {round(total_components * 0.5, 0):.0f} – {round(total_components * 2, 0):.0f} |",
        f"| DataWindows → TS Models + Forms | {total_dw} | {round(total_dw * 0.3, 0):.0f} – {round(total_dw * 1, 0):.0f} |",
        f"| Global Functions → Services | {total_services} | {round(total_services * 0.2, 0):.0f} – {round(total_services * 0.5, 0):.0f} |",
        f"| UserObjects → Angular Services | {len(uo_files)} | varies |",
        f"| **Total (estimated)** | **{stats.total_saved}** | **{est_days_low}–{est_days_high} days** |",
        f"",
        f"## Generated Project Structure",
        f"",
        "```",
        f"{project_name}/",
        f"  src/app/",
        f"    components/           # {total_components} Window → Component (.ts + .html + .scss)",
        f"    datawindows/          # {total_dw} DW → Model interface + Reactive Form",
        f"    services/             # {total_services} Function → Injectable Service",
        f"    app-routing.module.ts # All {total_components} Window routes wired up",
        f"  package.json           # Angular 18 + Material + CDK",
        f"  MIGRATION.md           # This file",
        "```",
        f"",
        f"## PBL Breakdown",
        f"",
        f"| PBL Module | Files | Role |",
        f"|------------|-------|------|",
    ]

    _pbl_roles = {
        "framework": "Login / main window / menu",
        "common": "Shared user objects / base classes",
        "common_fun": "Global utility functions",
        "sys": "System admin / user management",
        "app": "Application entry point",
    }
    for k, v in pbl_stats.items():
        pbl_base = k.replace(".pbl", "")
        role = _pbl_roles.get(pbl_base, "Business module")
        lines.append(f"| {k} | {v} | {role} |")

    lines += [
        f"",
        f"## Migration Phases",
        f"",
        f"### Phase 1 — Core Shell (Priority: HIGH)",
        f"> Estimated: {len(phase1) * 1}–{len(phase1) * 3} days",
        f"",
    ]
    for n in phase1[:10]:
        lines.append(f"- [ ] `{n}` — login / framework window")
    if not phase1:
        lines.append("- [ ] Set up Angular project skeleton")
        lines.append("- [ ] Configure Angular Material theme")

    lines += [
        f"",
        f"### Phase 2 — Core Business Screens (Priority: HIGH)",
        f"> Estimated: {max(1, len(phase2))}–{max(3, len(phase2) * 2)} days",
        f"",
    ]
    for n in phase2[:15]:
        lines.append(f"- [ ] `{n}`")
    if not phase2:
        lines.append("- [ ] Implement remaining business windows")

    lines += [
        f"",
        f"### Phase 3 — Remaining Windows (Priority: MEDIUM)",
        f"> Estimated: {max(1, len(phase3))}–{max(3, len(phase3) * 2)} days",
        f"",
        f"  {len(phase3)} windows remaining — see `src/app/components/`",
        f"",
        f"## Developer Checklist",
        f"",
        f"### Backend Setup",
        f"- [ ] Set up REST API backend (Node.js / Spring Boot / .NET)",
        f"- [ ] Migrate SQL Server stored procedures → REST endpoints",
        f"- [ ] Replace PB Transaction object with Angular HttpClient",
        f"",
        f"### DataWindow Migration",
        f"- [ ] Review generated DW models in `src/app/datawindows/`",
        f"- [ ] Validate column names against actual DB schema",
        f"- [ ] Replace DW retrieve/update with Angular Material table + HTTP",
        f"- [ ] Implement search/filter/pagination for list DWs",
        f"",
        f"### Component Migration",
        f"- [ ] Fill HTML templates (controls are NOT auto-migrated)",
        f"- [ ] Wire event methods to HTTP calls",
        f"- [ ] Test each component with real backend data",
        f"",
        f"### Final Steps",
        f"- [ ] Set up Angular routing guards (authentication)",
        f"- [ ] Add error handling (PB MessageBox → Angular snackbar/dialog)",
        f"- [ ] End-to-end testing",
        f"- [ ] Performance optimization (lazy loading, OnPush detection)",
        f"",
        f"---",
        f"*Generated by pb-devkit `pb migrate` — https://github.com/sugitter/pb-devkit*",
    ]

    _write(os.path.join(project_dir, "MIGRATION.md"), "\n".join(lines))


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
