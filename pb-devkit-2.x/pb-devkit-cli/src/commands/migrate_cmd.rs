/// pb-devkit CLI — `migrate` command
///
/// Migrate a PowerBuilder EXE/PBL project to an Angular web scaffold.
///
/// Generates:
///   - Angular components (one per Window: .ts + .html + .scss)
///   - TypeScript model interfaces (one per DataWindow)
///   - Angular Reactive Form factories (for DW columns)
///   - Injectable service stubs (one per global function)
///   - AppRoutingModule with all Window routes
///   - MIGRATION.md with effort estimates and checklist
///
/// Usage:
///   pbdevkit migrate <source> [OPTIONS]

use std::fs;
use std::path::{Path, PathBuf};

// ── Public entry point ────────────────────────────────────────────────────────

pub fn run_migrate(args: &[String]) -> Result<String, String> {
    if args.is_empty() || args[0] == "--help" || args[0] == "-h" {
        return Ok(migrate_help());
    }

    let source = PathBuf::from(&args[0]);
    if !source.exists() {
        return Err(format!("Source path does not exist: {}", source.display()));
    }

    // Parse flags
    let output_dir = extract_flag_value(args, &["-o", "--output"]);
    let project_name_override = extract_flag_value(args, &["--project-name"]);
    let suffix = extract_flag_value(args, &["--suffix"]).unwrap_or_else(|| ".ps".to_string());
    let no_forms = args.contains(&"--no-forms".to_string());
    let no_services = args.contains(&"--no-services".to_string());

    let source_parent = if source.is_file() {
        source.parent().unwrap_or(Path::new(".")).to_path_buf()
    } else {
        source.clone()
    };

    let out_dir = match output_dir {
        Some(ref o) => PathBuf::from(o),
        None => source_parent.join("pb-migrate-output"),
    };
    fs::create_dir_all(&out_dir)
        .map_err(|e| format!("Cannot create output dir: {}", e))?;

    let mut output = Vec::new();

    // ── Step 1: Export PB source ──────────────────────────────────────────────
    output.push(format!("[1/3] Parsing {} ...", source.display()));
    let pb_source_dir = out_dir.join("pb_source");
    let (exported, failed, skipped) = export_pb_source(&source, &pb_source_dir, &suffix, &mut output);
    output.push(format!("      → {} files exported, {} failed, {} skipped", exported, failed, skipped));

    if exported == 0 {
        return Err(
            "No source files exported. Check if the input is a valid PB EXE/PBL.".to_string()
        );
    }

    // ── Step 2: Categorize objects ────────────────────────────────────────────
    let objects = scan_exported_objects(&pb_source_dir, &suffix);
    output.push(format!(
        "[2/3] Categorized: {} DataWindows, {} Windows, {} Functions, {} UserObjects",
        objects.dw_files.len(),
        objects.window_files.len(),
        objects.function_files.len(),
        objects.uo_files.len()
    ));

    // ── Step 3: Generate Angular scaffold ────────────────────────────────────
    let project_name = project_name_override.unwrap_or_else(|| {
        source.file_stem()
            .and_then(|s| s.to_str())
            .map(|s| format!("{}-web", s))
            .unwrap_or_else(|| "pb-web".to_string())
    });

    let project_dir = out_dir.join(&project_name);
    make_scaffold_dirs(&project_dir)?;

    write_package_json(&project_dir, &project_name, &source)?;
    write_components(&project_dir, &objects.window_files, &pb_source_dir, &suffix)?;
    write_dw_models(&project_dir, &objects.dw_files, &pb_source_dir, &suffix, no_forms)?;
    write_service_stubs(&project_dir, &objects.function_files, &pb_source_dir, &suffix, no_services)?;
    write_app_routing(&project_dir, &objects.window_files)?;
    write_migration_md(
        &project_dir, &project_name, &source,
        &objects, exported,
        &pb_source_dir, &suffix,
    )?;

    output.push(format!("[3/3] Angular scaffold → {}", project_dir.display()));
    output.push(String::new());
    output.push(format!(
        "Done! {} PB objects → {} components, {} DW models, {} services",
        exported,
        objects.window_files.len(),
        objects.dw_files.len(),
        objects.function_files.len()
    ));
    output.push(String::new());
    output.push("Output structure:".to_string());
    output.push(format!("  {}/", out_dir.display()));
    output.push("    pb_source/       ← PowerScript source (按 PBL 分组)".to_string());
    output.push(format!("    {}/  ← Angular 18 project scaffold", project_name));
    output.push("      MIGRATION.md   ← Migration checklist & statistics".to_string());

    Ok(output.join("\n"))
}

// ── Object catalogue ──────────────────────────────────────────────────────────

struct ScannedObjects {
    window_files: Vec<(String, String)>,   // (pbl_dir, name)
    dw_files: Vec<(String, String)>,
    function_files: Vec<(String, String)>,
    uo_files: Vec<(String, String)>,
}

fn scan_exported_objects(src_base: &Path, suffix: &str) -> ScannedObjects {
    let mut window_files = Vec::new();
    let mut dw_files = Vec::new();
    let mut function_files = Vec::new();
    let mut uo_files = Vec::new();

    if let Ok(entries) = fs::read_dir(src_base) {
        let mut pbl_dirs: Vec<_> = entries
            .flatten()
            .filter(|e| e.path().is_dir())
            .collect();
        pbl_dirs.sort_by_key(|e| e.path());

        for pbl_entry in pbl_dirs {
            let pbl_dir = pbl_entry.file_name().to_string_lossy().to_string();
            let pbl_path = pbl_entry.path();

            if let Ok(files) = fs::read_dir(&pbl_path) {
                let mut sorted_files: Vec<_> = files.flatten().collect();
                sorted_files.sort_by_key(|e| e.path());

                for fe in sorted_files {
                    let fname = fe.file_name().to_string_lossy().to_string();
                    if !fname.ends_with(suffix) { continue; }
                    let name = fname[..fname.len() - suffix.len()].to_string();

                    if name.starts_with("d_") {
                        dw_files.push((pbl_dir.clone(), name));
                    } else if name.starts_with("w_") {
                        window_files.push((pbl_dir.clone(), name));
                    } else if name.starts_with("f_") || name.starts_with("gf_") {
                        function_files.push((pbl_dir.clone(), name));
                    } else if name.starts_with("n_") || name.starts_with("u_") {
                        uo_files.push((pbl_dir.clone(), name));
                    }
                }
            }
        }
    }

    ScannedObjects { window_files, dw_files, function_files, uo_files }
}

// ── PB source export helper ──────────────────────────────────────────────────

fn export_pb_source(
    source: &Path,
    pb_source_dir: &Path,
    _suffix: &str,
    output: &mut Vec<String>,
) -> (usize, usize, usize) {
    use std::process::Command;

    let _ = fs::create_dir_all(pb_source_dir);

    let exe = std::env::current_exe()
        .unwrap_or_else(|_| PathBuf::from("pbdevkit"));

    if source.is_dir() {
        // Export all PBL files in directory
        let mut total = 0usize;
        let failed = 0usize;
        if let Ok(entries) = fs::read_dir(source) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.extension().and_then(|e| e.to_str()) == Some("pbl") {
                    let stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("pbl");
                    let sub = pb_source_dir.join(stem);
                    let out = Command::new(&exe)
                        .args(["export-pbl", &p.to_string_lossy(), &sub.to_string_lossy()])
                        .output();
                    if let Ok(o) = out {
                        if o.status.success() {
                            let n = count_files_in(&sub);
                            total += n;
                            output.push(format!("  Exported {} → {} objects", p.file_name().unwrap_or_default().to_string_lossy(), n));
                        }
                    }
                }
            }
        }
        (total, failed, 0)
    } else {
        // Single EXE/PBL
        let ext = source.extension().and_then(|e| e.to_str()).unwrap_or("");
        if ext == "pbl" {
            let out = Command::new(&exe)
                .args(["export-pbl", &source.to_string_lossy(), &pb_source_dir.to_string_lossy()])
                .output();
            match out {
                Ok(o) if o.status.success() => {
                    let n = count_files_in(pb_source_dir);
                    (n, 0, 0)
                }
                Ok(o) => {
                    let e = String::from_utf8_lossy(&o.stderr).to_string();
                    output.push(format!("  Warning: {}", e));
                    (0, 1, 0)
                }
                Err(e) => {
                    output.push(format!("  Error: {}", e));
                    (0, 1, 0)
                }
            }
        } else {
            // EXE — use decompile-all
            let out = Command::new(&exe)
                .args(["decompile-all", &source.to_string_lossy(), &pb_source_dir.to_string_lossy()])
                .output();
            match out {
                Ok(o) if o.status.success() => {
                    let n = count_files_in(pb_source_dir);
                    (n, 0, 0)
                }
                Ok(o) => {
                    let e = String::from_utf8_lossy(&o.stderr).to_string();
                    output.push(format!("  Note: EXE decompile - {}", e.trim()));
                    output.push("  Tip: For PBL source projects, pass the project directory or .pbl file.".to_string());
                    (0, 1, 0)
                }
                Err(e) => {
                    output.push(format!("  Error running decompile-all: {}", e));
                    (0, 1, 0)
                }
            }
        }
    }
}

// ── Scaffold generators ───────────────────────────────────────────────────────

fn make_scaffold_dirs(project_dir: &Path) -> Result<(), String> {
    for sub in &[
        "src/app/components",
        "src/app/datawindows",
        "src/app/services",
        "src/app/models",
        "src/environments",
        "docs",
    ] {
        fs::create_dir_all(project_dir.join(sub))
            .map_err(|e| format!("Cannot create {}: {}", sub, e))?;
    }
    Ok(())
}

fn write_package_json(project_dir: &Path, name: &str, source: &Path) -> Result<(), String> {
    let src_file = source.file_name().and_then(|s| s.to_str()).unwrap_or("unknown");
    let pkg = format!(
        r#"{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "Migrated from PowerBuilder {src_file}",
  "scripts": {{
    "start": "ng serve",
    "build": "ng build --configuration production",
    "test": "ng test"
  }},
  "dependencies": {{
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
    "zone.js": "~0.14.0"
  }},
  "devDependencies": {{
    "@angular/cli": "^18.0.0",
    "@angular/compiler-cli": "^18.0.0",
    "typescript": "^5.4.0"
  }}
}}
"#,
        name = name, src_file = src_file
    );
    fs::write(project_dir.join("package.json"), pkg)
        .map_err(|e| format!("Cannot write package.json: {}", e))
}

fn to_class_name(name: &str, prefix: &str) -> String {
    name.strip_prefix(prefix)
        .unwrap_or(name)
        .split('_')
        .map(|w| {
            let mut c = w.chars();
            match c.next() {
                None => String::new(),
                Some(f) => f.to_uppercase().to_string() + c.as_str(),
            }
        })
        .collect()
}

fn read_source(src_base: &Path, pbl_dir: &str, name: &str, suffix: &str) -> String {
    let path = src_base.join(pbl_dir).join(format!("{}{}", name, suffix));
    fs::read_to_string(&path).unwrap_or_default()
}

fn extract_window_events(source: &str) -> Vec<String> {
    let mut events = Vec::new();
    for line in source.lines() {
        let lower = line.to_lowercase();
        if let Some(rest) = lower.trim().strip_prefix("event ") {
            let ev = rest.split_whitespace().next().unwrap_or("").to_string();
            if !ev.is_empty() && !ev.starts_with("pbm_") && !events.contains(&ev) {
                events.push(ev);
                if events.len() >= 20 { break; }
            }
        }
    }
    events
}

fn extract_dw_columns(source: &str) -> Vec<(String, &'static str)> {
    let mut columns = Vec::new();
    for line in source.lines() {
        let lower = line.to_lowercase();
        if let Some(rest) = lower.find("column name=").map(|i| &lower[i + 12..]) {
            let col = rest.split_whitespace().next()
                .unwrap_or("")
                .trim_matches('"')
                .trim_matches('\'')
                .to_string();
            if col.is_empty() { continue; }
            if columns.iter().any(|(c, _): &(String, _)| c == &col) { continue; }
            let ts_type = if col.ends_with("_date") || col.ends_with("_time") || col.ends_with("_dt") {
                "string  // Date"
            } else if col.ends_with("_id") || col.ends_with("_no") || col.ends_with("_num")
                || col.ends_with("_amt") || col.ends_with("_qty") || col.ends_with("_count") {
                "number"
            } else if col.ends_with("_flag") || col.ends_with("_yn") || col.ends_with("_bool") {
                "boolean"
            } else {
                "string"
            };
            columns.push((col, ts_type));
            if columns.len() >= 60 { break; }
        }
    }
    columns
}

fn write_components(
    project_dir: &Path,
    window_files: &[(String, String)],
    src_base: &Path,
    suffix: &str,
) -> Result<(), String> {
    let comp_root = project_dir.join("src/app/components");
    for (pbl_dir, name) in window_files {
        let source = read_source(src_base, pbl_dir, name, suffix);
        let events = extract_window_events(&source);

        let comp_name = name.strip_prefix("w_").unwrap_or(name).replace('_', "-");
        let class_name = format!("{}Component", to_class_name(name, "w_"));
        let cdir = comp_root.join(&comp_name);
        fs::create_dir_all(&cdir).ok();

        let mut event_methods = String::new();
        for ev in &events {
            let ev_camel: String = ev.split('_').map(|w| {
                let mut c = w.chars();
                match c.next() {
                    None => String::new(),
                    Some(f) => f.to_uppercase().to_string() + c.as_str(),
                }
            }).collect();
            event_methods.push_str(&format!(
                "\n  /** PB event: {} */\n  on{}(): void {{\n    // TODO: migrate PB logic from pb_source/{}/{}{}\n  }}\n",
                ev, ev_camel, pbl_dir, name, suffix
            ));
        }

        let ts = format!(
            "import {{ Component, OnInit }} from '@angular/core';\n\n\
            /**\n * Migrated from PowerBuilder Window: {name}\n\
            * Original PBL: {pbl_dir}\n\
            * Reference: ../../../pb_source/{pbl_dir}/{name}{suffix}\n */\n\
            @Component({{\n  selector: 'app-{comp_name}',\n\
            templateUrl: './{comp_name}.component.html',\n\
            styleUrls: ['./{comp_name}.component.scss']\n}})\n\
            export class {class_name} implements OnInit {{\n\
            constructor() {{}}\n\n  ngOnInit(): void {{\n\
            // TODO: initialize component (was PB Open event)\n  }}\n\
            {event_methods}}}\n",
            name = name, pbl_dir = pbl_dir, suffix = suffix,
            comp_name = comp_name, class_name = class_name,
            event_methods = event_methods
        );
        let html = format!(
            "<!-- Migrated from PB Window: {name} (PBL: {pbl_dir}) -->\n\
            <div class=\"{comp_name}-container\">\n  <mat-toolbar color=\"primary\">\n\
            <span>{name}</span>\n  </mat-toolbar>\n\n\
            <!-- TODO: reconstruct controls from pb_source/{pbl_dir}/{name}{suffix} -->\n\
            <div class=\"content\">\n    <p>Window: {name}</p>\n  </div>\n</div>\n",
            name = name, pbl_dir = pbl_dir, suffix = suffix, comp_name = comp_name
        );
        let scss = format!(
            ".{comp_name}-container {{\n  display: flex;\n  flex-direction: column;\n\
            height: 100%;\n\n  .content {{\n    padding: 16px;\n    flex: 1;\n  }}\n}}\n",
            comp_name = comp_name
        );

        fs::write(cdir.join(format!("{}.component.ts", comp_name)), ts).ok();
        fs::write(cdir.join(format!("{}.component.html", comp_name)), html).ok();
        fs::write(cdir.join(format!("{}.component.scss", comp_name)), scss).ok();
    }
    Ok(())
}

fn write_dw_models(
    project_dir: &Path,
    dw_files: &[(String, String)],
    src_base: &Path,
    suffix: &str,
    no_forms: bool,
) -> Result<(), String> {
    let dw_dir = project_dir.join("src/app/datawindows");
    for (pbl_dir, name) in dw_files {
        let source = read_source(src_base, pbl_dir, name, suffix);
        let columns = extract_dw_columns(&source);

        let model_name = name.strip_prefix("d_").unwrap_or(name).replace('_', "-");
        let interface_name = format!("{}Model", to_class_name(name, "d_"));

        let fields = if columns.is_empty() {
            "  id?: number;\n  // TODO: map DW columns to typed fields".to_string()
        } else {
            columns.iter().map(|(col, ts)| format!("  {}?: {};", col, ts)).collect::<Vec<_>>().join("\n")
        };

        let mut ts = format!(
            "/**\n * DataWindow migrated: {name}\n\
            * Original PBL: {pbl_dir}\n\
            * Reference: ../../../pb_source/{pbl_dir}/{name}{suffix}\n */\n\
            export interface {interface_name} {{\n{fields}\n}}\n",
            name = name, pbl_dir = pbl_dir, suffix = suffix,
            interface_name = interface_name, fields = fields
        );

        if !columns.is_empty() && !no_forms {
            let form_controls = columns.iter().take(20)
                .map(|(col, _)| format!("      {}: [null]", col))
                .collect::<Vec<_>>()
                .join(",\n");
            ts.push_str(&format!(
                "\n// Angular Reactive Form factory\nimport {{ FormBuilder, FormGroup }} from '@angular/forms';\n\n\
                export function build{}Form(fb: FormBuilder): FormGroup {{\n  return fb.group({{\n{}\n  }});\n}}\n",
                interface_name, form_controls
            ));
        }

        if !columns.is_empty() {
            let displayed = columns.iter().take(8).map(|(col, _)| format!("'{}'", col)).collect::<Vec<_>>().join(", ");
            ts.push_str(&format!(
                "\n// Angular Material table displayed columns\nexport const {}_COLUMNS = [{}];\n",
                interface_name.to_uppercase(), displayed
            ));
        }

        fs::write(dw_dir.join(format!("{}.model.ts", model_name)), ts).ok();
    }
    Ok(())
}

fn write_service_stubs(
    project_dir: &Path,
    function_files: &[(String, String)],
    _src_base: &Path,
    _suffix: &str,
    no_services: bool,
) -> Result<(), String> {
    if no_services { return Ok(()); }
    let svc_dir = project_dir.join("src/app/services");
    for (pbl_dir, name) in function_files {
        let prefix = if name.starts_with("gf_") { "gf_" } else { "f_" };
        let svc_name = name.strip_prefix(prefix).unwrap_or(name).replace('_', "-");
        let class_name = format!("{}Service", to_class_name(name, prefix));
        let method_name_parts: Vec<_> = name.strip_prefix(prefix).unwrap_or(name).split('_').collect();
        let method_name = method_name_parts.iter().enumerate().map(|(i, w)| {
            if i == 0 { w.to_string() } else {
                let mut c = w.chars();
                match c.next() { None => String::new(), Some(f) => f.to_uppercase().to_string() + c.as_str() }
            }
        }).collect::<String>();

        let ts = format!(
            "import {{ Injectable }} from '@angular/core';\n\
            import {{ HttpClient }} from '@angular/common/http';\n\
            import {{ Observable }} from 'rxjs';\n\n\
            /**\n * Migrated global function: {name}\n * Original PBL: {pbl_dir}\n */\n\
            @Injectable({{ providedIn: 'root' }})\nexport class {class_name} {{\n\
            constructor(private http: HttpClient) {{}}\n\n\
            /** Migrated from PB global function: {name} */\n\
            {method_name}(): any {{\n\
            // TODO: implement based on PB source\n\
            throw new Error('Not implemented');\n  }}\n}}\n",
            name = name, pbl_dir = pbl_dir, class_name = class_name, method_name = method_name
        );
        fs::write(svc_dir.join(format!("{}.service.ts", svc_name)), ts).ok();
    }
    Ok(())
}

fn write_app_routing(project_dir: &Path, window_files: &[(String, String)]) -> Result<(), String> {
    let first_route = window_files.first()
        .map(|(_, n)| n.strip_prefix("w_").unwrap_or(n).replace('_', "-"))
        .unwrap_or_else(|| "home".to_string());

    let imports: String = window_files.iter().map(|(_, n)| {
        let comp = n.strip_prefix("w_").unwrap_or(n).replace('_', "-");
        let class = format!("{}Component", to_class_name(n, "w_"));
        format!("import {{ {class} }} from './components/{comp}/{comp}.component';\n",
            class = class, comp = comp)
    }).collect();

    let routes: String = window_files.iter().map(|(_, n)| {
        let comp = n.strip_prefix("w_").unwrap_or(n).replace('_', "-");
        let class = format!("{}Component", to_class_name(n, "w_"));
        format!("  {{ path: '{comp}', component: {class} }}", comp = comp, class = class)
    }).collect::<Vec<_>>().join(",\n");

    let content = format!(
        "import {{ NgModule }} from '@angular/core';\n\
        import {{ RouterModule, Routes }} from '@angular/router';\n\
        {imports}\n\
        const routes: Routes = [\n  {{ path: '', redirectTo: '{first}', pathMatch: 'full' }},\n{routes}\n];\n\n\
        @NgModule({{\n  imports: [RouterModule.forRoot(routes)],\n  exports: [RouterModule]\n}})\n\
        export class AppRoutingModule {{}}\n",
        imports = imports, first = first_route, routes = routes
    );
    fs::write(project_dir.join("src/app/app-routing.module.ts"), content)
        .map_err(|e| format!("Cannot write routing: {}", e))
}

fn write_migration_md(
    project_dir: &Path,
    project_name: &str,
    source: &Path,
    objects: &ScannedObjects,
    total_exported: usize,
    src_base: &Path,
    _suffix: &str,
) -> Result<(), String> {
    let src_file = source.file_name().and_then(|s| s.to_str()).unwrap_or("unknown");
    let n_win = objects.window_files.len();
    let n_dw = objects.dw_files.len();
    let n_fn = objects.function_files.len();
    let n_uo = objects.uo_files.len();

    let est_low = ((n_win as f64 * 0.5) + (n_dw as f64 * 0.3) + (n_fn as f64 * 0.2)) as usize;
    let est_high = ((n_win as f64 * 2.0) + (n_dw as f64 * 1.0) + (n_fn as f64 * 0.5)) as usize;

    // Count PBL modules
    let mut pbl_stats: Vec<(String, usize)> = Vec::new();
    if let Ok(entries) = fs::read_dir(src_base) {
        let mut dirs: Vec<_> = entries.flatten().filter(|e| e.path().is_dir()).collect();
        dirs.sort_by_key(|e| e.path());
        for d in dirs {
            let name = d.file_name().to_string_lossy().to_string();
            let count = fs::read_dir(d.path()).map(|e| e.flatten().count()).unwrap_or(0);
            if count > 0 { pbl_stats.push((name, count)); }
        }
    }

    // Phase classification
    let phase1: Vec<_> = objects.window_files.iter()
        .filter(|(_, n)| ["w_login", "w_main", "w_frame", "w_splash"].iter().any(|p| n.starts_with(p)))
        .collect();
    let phase2: Vec<_> = objects.window_files.iter()
        .filter(|(_, n)| !phase1.iter().any(|(_, p)| p == n))
        .filter(|(_, n)| ["w_sngl_", "w_find_", "w_list_", "w_print_"].iter().any(|p| n.starts_with(p)))
        .collect();

    let mut lines = vec![
        format!("# {} — Migration Plan", project_name),
        String::new(),
        format!("> Source: `{}`", src_file),
        String::new(),
        "## Summary Statistics".to_string(),
        String::new(),
        "| Category | Count | Effort (days, rough) |".to_string(),
        "|----------|-------|----------------------|".to_string(),
        format!("| Windows → Angular Components | {} | {}–{} |", n_win, (n_win as f64 * 0.5) as usize, n_win * 2),
        format!("| DataWindows → TS Models + Forms | {} | {}–{} |", n_dw, (n_dw as f64 * 0.3) as usize, n_dw),
        format!("| Global Functions → Services | {} | {}–{} |", n_fn, (n_fn as f64 * 0.2) as usize, (n_fn as f64 * 0.5) as usize),
        format!("| UserObjects | {} | varies |", n_uo),
        format!("| **Total (estimated)** | **{}** | **{}–{} days** |", total_exported, est_low, est_high),
        String::new(),
        "## PBL Breakdown".to_string(),
        String::new(),
        "| PBL Module | Files |".to_string(),
        "|------------|-------|".to_string(),
    ];
    for (pbl, count) in &pbl_stats {
        lines.push(format!("| {} | {} |", pbl, count));
    }

    lines.push(String::new());
    lines.push("## Migration Phases".to_string());
    lines.push(String::new());
    lines.push("### Phase 1 — Core Shell (Priority: HIGH)".to_string());
    lines.push(String::new());
    for (_, n) in &phase1 {
        lines.push(format!("- [ ] `{}` — login / framework window", n));
    }
    if phase1.is_empty() {
        lines.push("- [ ] Set up Angular project skeleton".to_string());
    }

    lines.push(String::new());
    lines.push("### Phase 2 — Core Business Screens (Priority: HIGH)".to_string());
    lines.push(String::new());
    for (_, n) in phase2.iter().take(15) {
        lines.push(format!("- [ ] `{}`", n));
    }
    if phase2.is_empty() {
        lines.push("- [ ] Implement remaining business windows".to_string());
    }

    lines.push(String::new());
    lines.push("## Developer Checklist".to_string());
    lines.push(String::new());
    lines.push("- [ ] Set up REST API backend (Node.js / Spring Boot / .NET)".to_string());
    lines.push("- [ ] Replace PB Transaction → Angular HttpClient".to_string());
    lines.push("- [ ] Validate DW models against actual DB schema".to_string());
    lines.push("- [ ] Fill HTML templates (controls are NOT auto-migrated)".to_string());
    lines.push("- [ ] Add Angular routing guards (authentication)".to_string());
    lines.push("- [ ] End-to-end testing".to_string());
    lines.push(String::new());
    lines.push("---".to_string());
    lines.push("*Generated by pb-devkit `pbdevkit migrate` — https://github.com/sugitter/pb-devkit*".to_string());

    fs::write(project_dir.join("MIGRATION.md"), lines.join("\n"))
        .map_err(|e| format!("Cannot write MIGRATION.md: {}", e))
}

// ── Utilities ──────────────────────────────────────────────────────────────────

fn extract_flag_value(args: &[String], flags: &[&str]) -> Option<String> {
    for (i, arg) in args.iter().enumerate() {
        if flags.contains(&arg.as_str()) {
            return args.get(i + 1).cloned();
        }
        for flag in flags {
            if let Some(val) = arg.strip_prefix(&format!("{}=", flag)) {
                return Some(val.to_string());
            }
        }
    }
    None
}

fn count_files_in(dir: &Path) -> usize {
    fs::read_dir(dir)
        .map(|entries| entries.flatten().filter(|e| e.path().is_file()).count())
        .unwrap_or(0)
}

fn migrate_help() -> String {
    r#"pbdevkit migrate — Migrate PB EXE/PBL to Angular Web Scaffold

USAGE:
    pbdevkit migrate <source> [OPTIONS]

ARGS:
    <source>    Path to PB EXE file or directory containing PBL files

OPTIONS:
    -o, --output <DIR>         Output directory (default: <source_dir>/pb-migrate-output)
    --project-name <NAME>      Override project name
    --suffix <EXT>             Source file extension (default: .ps)
    --no-forms                 Skip Angular Reactive Forms for DataWindows
    --no-services              Skip service stub generation
    -h, --help                 Show this help

OUTPUTS:
    pb_source/                 Exported PowerScript source (by PBL)
    <project-name>/
      src/app/components/      Angular Components (one per Window)
      src/app/datawindows/     TypeScript Models + Reactive Forms
      src/app/services/        Injectable Service stubs (global functions)
      src/app/app-routing.module.ts
      package.json             Angular 18 + Material
      MIGRATION.md             Effort estimates + checklist

EXAMPLES:
    pbdevkit migrate C:/projects/myapp.pbl
    pbdevkit migrate C:/projects/myapp -o D:/output
    pbdevkit migrate C:/projects/myapp.exe --no-forms
"#.to_string()
}
