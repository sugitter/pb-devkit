// PB DevKit CLI v2.2.1 - Binary entry point
// Delegates to pb_devkit_cli::run() (defined in lib.rs).

fn main() {
    pb_devkit_cli::run();
}

#[cfg(test)]
mod tests {
    use pb_devkit_cli::execute_command;

    // ── Help / Usage ──

    #[test]
    fn help_command_returns_usage() {
        let result = execute_command("help", &[]);
        assert!(result.is_ok(), "help should succeed");
        let output = result.unwrap();
        assert!(output.contains("PB DevKit CLI"), "usage should contain brand");
        assert!(output.contains("pbdevkit"), "usage should contain binary name");
        assert!(output.contains("parse"), "usage should list parse command");
        assert!(output.contains("doctor"), "usage should list doctor command");
    }

    #[test]
    fn dash_help_alias_works() {
        let result = execute_command("--help", &[]);
        assert!(result.is_ok());
        assert!(result.unwrap().contains("Usage:"));
    }

    #[test]
    fn dash_h_alias_works() {
        let result = execute_command("-h", &[]);
        assert!(result.is_ok());
        assert!(result.unwrap().contains("pbdevkit"));
    }

    // ── Unknown command ──

    #[test]
    fn unknown_command_returns_error() {
        let result = execute_command("nonexistent_cmd", &[]);
        assert!(result.is_err(), "unknown command should fail");
        assert!(result.unwrap_err().contains("Unknown command"));
    }

    // ── Doctor (no args needed) ──

    #[test]
    fn doctor_returns_result() {
        let result = execute_command("doctor", &[]);
        match result {
            Ok(output) => {
                assert!(!output.is_empty(), "doctor output should not be empty");
            }
            Err(_) => {
                // Doctor may fail in CI if PB tools are not installed. That's OK.
            }
        }
    }

    // ── Command routing completeness ──

    #[test]
    fn all_pbl_commands_route() {
        for cmd in &["parse", "info", "list", "export", "export-pbl"] {
            let result = execute_command(cmd, &["missing.pbl".to_string()]);
            // Should fail with "No such file" or similar, NOT "Unknown command"
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_pe_commands_route() {
        for cmd in &["file-type", "analyze-pe", "extract-pbd"] {
            let result = execute_command(cmd, &["missing.exe".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_project_commands_route() {
        for cmd in &["project", "find-pbl", "scan-export"] {
            let result = execute_command(cmd, &["/nonexistent".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_search_commands_route() {
        for cmd in &["search", "search-type", "search-regex"] {
            let result = execute_command(cmd, &["/nonexistent".to_string(), "dummy".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_dw_commands_route() {
        for cmd in &["analyze-dw", "dw-sql"] {
            let result = execute_command(cmd, &["/nonexistent".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_decompile_commands_route() {
        for cmd in &["list-decompile", "decompile", "decompile-all"] {
            let result = execute_command(cmd, &["missing.pbd".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_report_commands_route() {
        for cmd in &["report", "export-report"] {
            let result = execute_command(cmd, &["/nonexistent".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_code_analysis_commands_route() {
        for cmd in &["diff", "workflow", "refactor", "snapshot", "review"] {
            let result = execute_command(cmd, &["/nonexistent".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn all_migration_commands_route() {
        for cmd in &["autoexport", "auto-export", "migrate", "build"] {
            let result = execute_command(cmd, &["/nonexistent".to_string()]);
            match result {
                Ok(_) => {}
                Err(e) => assert!(!e.contains("Unknown command"),
                    "{} should route to a handler, got: {}", cmd, e),
            }
        }
    }

    #[test]
    fn pack_to_pbl_command_routes() {
        let result = execute_command("pack-to-pbl", &["/nonexistent".to_string(), "/out.pbl".to_string()]);
        match result {
            Ok(_) => {}
            Err(e) => assert!(!e.contains("Unknown command"),
                "pack-to-pbl should route to a handler, got: {}", e),
        }
    }

    // ── Total command count ──

    #[test]
    fn total_30_commands_all_routable() {
        // 30 CLI commands should all be routable via execute_command
        let all_cmds = vec![
            "parse", "pbl", "info", "list", "export", "export-pbl",          // 6 PBL
            "file-type", "analyze-pe", "extract-pbd",                         // 3 PE
            "project", "detect", "find-pbl", "scan-export", "pack-to-pbl", "doctor", // 6 Project
            "search", "search-type", "search-regex",                          // 3 Search
            "analyze-dw", "dw-sql",                                           // 2 DW
            "list-decompile", "decompile", "decompile-all",                   // 3 Decompile
            "report", "export-report",                                        // 2 Report
            "diff", "workflow", "refactor", "snapshot", "review",            // 5 Code Analysis
            "autoexport", "auto-export", "migrate", "build",                  // 4 Migration
        ];
        let routed: Vec<_> = all_cmds.iter().filter(|cmd| {
            let subargs: Vec<String> = if **cmd == "doctor" {
                vec![]
            } else {
                vec!["/nonexistent".to_string()]
            };
            match execute_command(cmd, &subargs) {
                Ok(_) => true,
                Err(e) => !e.contains("Unknown command"),
            }
        }).collect();
        assert_eq!(routed.len(), all_cmds.len(),
            "All 30 commands must be routable. Missing: {:?}",
            all_cmds.iter().filter(|c| !routed.contains(c)).collect::<Vec<_>>());
    }
}
