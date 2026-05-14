// PB DevKit CLI v2.0 - Command-line interface
// Usage: pbdevkit <command> [args...]
//
// All commands delegate to pb-devkit-core.

use std::env;
use std::process;

mod commands;
use commands::{pbl_cmd, pe_cmd, project_cmd, search_cmd, dw_cmd, decompile_cmd, report_cmd, diff_cmd, workflow_cmd};

fn main() {
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

/// Execute a single CLI command. Extracted so both `main()` and
/// `start_interactive_mode()` can share the same logic.
fn execute_command(cmd: &str, subargs: &[String]) -> Result<String, String> {
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
        "doctor" => project_cmd::run_doctor(),
        // ── Search commands ──
        "search" => search_cmd::search_in_files(subargs),
        "search-type" => search_cmd::search_by_type(subargs),
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
        // ── Help ──
        "--help" | "-h" | "help" => {
            print_usage();
            Ok(String::new())
        }
        _ => Err(format!("Unknown command: {}", cmd)),
    }
}

/// Interactive REPL mode.
/// Supports command-line editing, history (persisted to ~/.pbdevkit_history),
/// and the special commands: help, exit, quit, q.
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

    // Try to load history from ~/.pbdevkit_history
    let history_path = dirs::home_dir().map(|mut d| {
        d.push(".pbdevkit_history");
        d
    });
    if let Some(ref p) = history_path {
        let _ = rl.load_history(p);
    }

    println!("PB DevKit CLI v2.0.0 - Interactive Mode");
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

                // Parse command + args
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
                // Ctrl+C — just continue
                println!("^C");
                continue;
            }
            Err(ReadlineError::Eof) => {
                // Ctrl+D
                println!("\nGoodbye!");
                break;
            }
            Err(err) => {
                eprintln!("Error: {}", err);
                break;
            }
        }
    }

    // Save history
    if let Some(ref p) = history_path {
        let _ = rl.save_history(p);
    }

    Ok(())
}

fn print_usage() {
    println!("PB DevKit CLI v2.0.0");
    println!("PowerBuilder Legacy System Toolkit");
    println!();
    println!("Usage: pbdevkit <command> [args...]");
    println!();
    println!("Commands:");
    println!("  PBL:");
    println!("  parse <pbl>           Parse PBL file");
    println!("  info <pbl>            Get PBL file info");
    println!("  list <pbl>            List all entries in PBL");
    println!("  export <pbl> <name>   Export a single entry");
    println!("  export-pbl <pbl> <dir> [--by-type]");
    println!("                        Export all source entries from PBL");
    println!();
    println!("  PE:");
    println!("  file-type <file>      Detect file type from magic bytes");
    println!("  analyze-pe <file>     Analyze PE file (EXE/DLL)");
    println!("  extract-pbd <exe> <dir>");
    println!("                        Extract PBD resources from EXE/DLL");
    println!();
    println!("  Project:");
    println!("  project <path>        Detect PowerBuilder project");
    println!("  find-pbl <path>       List all PBL files recursively");
    println!("  doctor                 Run environment diagnostics");
    println!();
    println!("  Search:");
    println!("  search <path> <query> Search in source files");
    println!("  search-type <path> <type>");
    println!("                        Search by object type");
    println!();
    println!("  DataWindow:");
    println!("  analyze-dw <path>     Analyze DataWindow objects");
    println!("  dw-sql <path>         Get DataWindow SQL");
    println!();
    println!("  Decompile:");
    println!("  list-decompile <file>  List entries in PBD/EXE");
    println!("  decompile <file> <name>");
    println!("                        Decompile a single entry");
    println!("  decompile-all <file> <dir>");
    println!("                        Decompile all entries");
    println!();
    println!("  Report:");
    println!("  report <path>         Generate project report");
    println!("  export-report <path> <output.json>");
    println!("                        Export report to JSON file");
    println!();
    println!("  Interactive mode:");
    println!("  interactive            Start interactive REPL mode");
    println!();
    println!("Examples:");
    println!("  pbdevkit parse myapp.pbl");
    println!("  pbdevkit list myapp.pbl");
    println!("  pbdevkit project C:/projects/myapp");
    println!("  pbdevkit search C:/projects/myapp dw_");
    println!("  pbdevkit analyze-pe myapp.exe");
    println!("  pbdevkit interactive");
}
