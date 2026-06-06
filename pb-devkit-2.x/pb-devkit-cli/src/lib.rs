// PB DevKit CLI v2.2.1 - Library interface
// Exposes execute_command() for both main.rs and integration tests.
//
// Usage: pbdevkit <command> [args...]
// All commands delegate to pb-devkit-core.

use std::env;
use std::process;

mod commands;
use commands::{pbl_cmd, pe_cmd, project_cmd, search_cmd, dw_cmd, decompile_cmd, report_cmd, diff_cmd, workflow_cmd, refactor_cmd, snapshot_cmd, review_cmd, autoexport_cmd, migrate_cmd, build_cmd};

/// Main entry point — parses CLI args and dispatches to execute_command.
pub fn run() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_usage();
        return;
    }

    let cmd = &args[1];

    // Interactive mode
    if cmd == "interactive" || cmd == "shell" || cmd == "repl" {
        if let Err(e) = start_interactive_mode() {
            eprintln!("Error: {}", e);
            process::exit(1);
        }
        return;
    }

    let subargs: Vec<String> = args[2..].to_vec();
    let result = execute_command(cmd, &subargs);

    match result {
        Ok(output) => println!("{}", output),
        Err(e) => {
            eprintln!("Error: {}", e);
            process::exit(1);
        }
    }
}

/// Execute a single CLI command.
/// Public so integration tests can call it directly.
pub fn execute_command(cmd: &str, subargs: &[String]) -> Result<String, String> {
    match cmd {
        // ── PBL commands ──
        "parse" | "pbl" => pbl_cmd::parse_pbl(subargs),
        "info" => pbl_cmd::get_pbl_info(subargs),
        "list" => pbl_cmd::list_entries(subargs),
        "export" => pbl_cmd::export_entry(subargs),
        "export-pbl" => pbl_cmd::export_pbl(subargs),
        // ── PE commands ──
        "file-type" => pe_cmd::detect_file_type(subargs),
        "analyze-pe" => pe_cmd::analyze_pe(subargs),
        "extract-pbd" => pe_cmd::extract_pbd(subargs),
        // ── Project commands ──
        "project" | "detect" => project_cmd::detect_project(subargs),
        "find-pbl" => project_cmd::find_pbl_files(subargs),
        "scan-export" => project_cmd::scan_and_export(subargs),
        "pack-to-pbl" => project_cmd::pack_sources_to_pbl(subargs),
        "doctor" => project_cmd::run_doctor(),
        // ── Search commands ──
        "search" => search_cmd::search_in_files(subargs),
        "search-type" => search_cmd::search_by_type(subargs),
        "search-regex" => search_cmd::search_with_regex(subargs),
        // ── DataWindow commands ──
        "analyze-dw" => dw_cmd::analyze_datawindows(subargs),
        "dw-sql" => dw_cmd::get_dw_sql(subargs),
        // ── Decompile commands ──
        "list-decompile" => decompile_cmd::list_decompile_entries(subargs),
        "decompile" => decompile_cmd::decompile_entry(subargs),
        "decompile-all" => decompile_cmd::decompile_all(subargs),
        // ── Report commands ──
        "report" => report_cmd::generate_report(subargs),
        "export-report" => report_cmd::export_report(subargs),
        // ── Diff command ──
        "diff" => diff_cmd::run_diff(subargs),
        // ── Workflow command ──
        "workflow" => workflow_cmd::run_workflow(subargs),
        // ── Code analysis commands ──
        "refactor" => refactor_cmd::run_refactor(subargs),
        "snapshot" => snapshot_cmd::run_snapshot(subargs),
        "review" => review_cmd::run_review(subargs),
        // ── Migration commands (ported from 1.x) ──
        "autoexport" | "auto-export" => autoexport_cmd::run_autoexport(subargs),
        "migrate" => migrate_cmd::run_migrate(subargs),
        "build" => build_cmd::run_build(subargs),
        // ── Help ──
        "--help" | "-h" | "help" => {
            let _usage = format_usage();
            Ok(_usage)
        }
        _ => Err(format!("Unknown command: {}", cmd)),
    }
}

/// Print usage information to stdout.
pub fn print_usage() {
    println!("{}", format_usage());
}

/// Returns usage string for testing.
pub fn format_usage() -> String {
    let lines = vec![
        "PB DevKit CLI v2.2.1".to_string(),
        "PowerBuilder Legacy System Toolkit".to_string(),
        String::new(),
        "Usage: pbdevkit <command> [args...]".to_string(),
        String::new(),
        "Commands:".to_string(),
        "  PBL:".to_string(),
        "  parse <pbl>           Parse PBL file".to_string(),
        "  info <pbl>            Get PBL file info".to_string(),
        "  list <pbl>            List all entries in PBL".to_string(),
        "  export <pbl> <name>   Export a single entry".to_string(),
        "  export-pbl <pbl> <dir> [--by-type]".to_string(),
        "                        Export all source entries from PBL".to_string(),
        String::new(),
        "  PE:".to_string(),
        "  file-type <file>      Detect file type from magic bytes".to_string(),
        "  analyze-pe <file>     Analyze PE file (EXE/DLL)".to_string(),
        "  extract-pbd <exe> <dir>".to_string(),
        "                        Extract PBD resources from EXE/DLL".to_string(),
        String::new(),
        "  Project:".to_string(),
        "  project <path>        Detect PowerBuilder project".to_string(),
        "  find-pbl <path>       List all PBL files recursively".to_string(),
        "  scan-export <path> <dir>".to_string(),
        "                        Scan project and export all sources".to_string(),
        "  pack-to-pbl <src_dir> <output.pbl>".to_string(),
        "                        Pack source files into a PBL".to_string(),
        "  doctor                 Run environment diagnostics".to_string(),
        String::new(),
        "  Search:".to_string(),
        "  search <path> <query> Search in source files".to_string(),
        "  search-type <path> <type>".to_string(),
        "                        Search by object type".to_string(),
        "  search-regex <path> <pattern>".to_string(),
        "                        Search using regex pattern".to_string(),
        String::new(),
        "  DataWindow:".to_string(),
        "  analyze-dw <path>     Analyze DataWindow objects".to_string(),
        "  dw-sql <path>         Get DataWindow SQL".to_string(),
        String::new(),
        "  Decompile:".to_string(),
        "  list-decompile <file>  List entries in PBD/EXE".to_string(),
        "  decompile <file> <name>".to_string(),
        "                        Decompile a single entry".to_string(),
        "  decompile-all <file> <dir>".to_string(),
        "                        Decompile all entries".to_string(),
        String::new(),
        "  Report:".to_string(),
        "  report <path>         Generate project report".to_string(),
        "  export-report <path> <output.json>".to_string(),
        "                        Export report to JSON file".to_string(),
        String::new(),
        "  Workflow & Diff:".to_string(),
        "  workflow <path>       Run workflow analysis".to_string(),
        "  diff <a> <b>          Compare two source files or dirs".to_string(),
        String::new(),
        "  Code Analysis:".to_string(),
        "  refactor <dir>        Scan source for anti-patterns".to_string(),
        "  snapshot <dir>        Capture project snapshot".to_string(),
        "  review <dir>          Full review: structure/quality/DW/deps".to_string(),
        String::new(),
        "  Migration:".to_string(),
        "  autoexport <dir>      Auto-detect and export all sources".to_string(),
        "  migrate <source>      Migrate PB to Angular web scaffold".to_string(),
        "  build <pbl> <app>     Rebuild PB app via PBGen.exe".to_string(),
        String::new(),
        "  Interactive mode:".to_string(),
        "  interactive            Start interactive REPL mode".to_string(),
        String::new(),
        "Examples:".to_string(),
        "  pbdevkit parse myapp.pbl".to_string(),
        "  pbdevkit list myapp.pbl".to_string(),
        "  pbdevkit project C:/projects/myapp".to_string(),
        "  pbdevkit search C:/projects/myapp dw_".to_string(),
        "  pbdevkit analyze-pe myapp.exe".to_string(),
        "  pbdevkit interactive".to_string(),
    ];
    lines.join("\n")
}

/// Interactive REPL mode.
fn start_interactive_mode() -> Result<(), String> {
    use rustyline::error::ReadlineError;
    use rustyline::history::FileHistory;
    use rustyline::{Config, EditMode, Editor};

    let config = Config::builder()
        .history_ignore_space(true)
        .edit_mode(EditMode::Emacs)
        .build();

    let mut rl: Editor<(), FileHistory> = Editor::with_config(config)
        .map_err(|e| format!("Failed to create editor: {}", e))?;

    let history_path = dirs::home_dir().map(|mut d| {
        d.push(".pbdevkit_history");
        d
    });
    if let Some(ref p) = history_path {
        let _ = rl.load_history(p);
    }

    println!("PB DevKit CLI v2.2.1 - Interactive Mode");
    println!("Type 'help' for available commands, 'exit' / 'quit' / 'q' to quit.");
    println!();

    loop {
        let readline = rl.readline("pbdevkit> ");
        match readline {
            Ok(line) => {
                let trimmed: &str = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                let _ = rl.add_history_entry(trimmed);

                if trimmed == "exit" || trimmed == "quit" || trimmed == "q" {
                    println!("Goodbye!");
                    break;
                }
                if trimmed == "help" || trimmed == "?" {
                    print_usage();
                    continue;
                }

                let parts: Vec<&str> = trimmed.split_whitespace().collect();
                if parts.is_empty() {
                    continue;
                }
                let cmd = parts[0];
                let subargs: Vec<String> = parts[1..]
                    .iter()
                    .map(|s: &&str| s.to_string())
                    .collect();

                match execute_command(cmd, &subargs) {
                    Ok(output) => println!("{}", output),
                    Err(e) => eprintln!("Error: {}", e),
                }
            }
            Err(ReadlineError::Interrupted) => {
                println!("^C");
                continue;
            }
            Err(ReadlineError::Eof) => {
                println!("\nGoodbye!");
                break;
            }
            Err(err) => {
                eprintln!("Error: {}", err);
                break;
            }
        }
    }

    if let Some(ref p) = history_path {
        let _ = rl.save_history(p);
    }

    Ok(())
}
