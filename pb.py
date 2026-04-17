#!/usr/bin/env python3
"""
PB DevKit CLI - PowerBuilder Developer Toolkit

A comprehensive toolkit for analyzing, refactoring, and maintaining
PowerBuilder legacy systems without the PB IDE.

Commands:
  pb doctor                             Environment diagnostics
  pb init <dir>                         Initialize project structure
  pb export <pbl_or_dir> [output_dir]   Export PBL source to .sr* files
  pb import <pbl> <source_dir>          Import .sr* files into PBL
  pb build <pbl> <app_name>             Rebuild application
  pb compile <pbl> <source_dir>         Import + Rebuild in one step
  pb list <pbl_or_dir>                  List objects in PBL
  pb analyze <dir>                      Analyze code quality
  pb analyze-project <dir>              Full project analysis (deps + complexity)
  pb search <pattern> <dir>             Search source code (text/sql/function)
  pb report <dir>                       Generate Markdown analysis report
  pb refactor <dir>                     Auto-refactor source files
  pb diff <dir1> <dir2>                 Compare two source directories
  pb stats <dir>                        Project statistics dashboard
  pb workflow <pbl> [dir]               Full workflow: export->analyze->refactor
  pb snapshot <pbl_or_dir> [output_dir]  Export + diff + git commit for version tracking
"""
import argparse
import logging
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure src/ is on Python path
_SRC_DIR = Path(__file__).parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="pb",
        description="PB DevKit - PowerBuilder Developer Toolkit v1.2.0")
    parser.add_argument(
        "--version", action="version", version="PB DevKit 1.2.0")
    parser.add_argument(
        "--pb-version", type=int, default=None,
        help="PowerBuilder version (default: 125 = PB 12.5, "
             "or from .pbdevkit.json)")
    parser.add_argument(
        "--config", "-c", default=None,
        help="Path to config file (default: auto-detect .pbdevkit.json)")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate without making changes (global override)")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # Register all commands
    from pb_devkit.commands import (
        run_doctor, run_init, run_list, run_export,
        run_import, run_build, run_compile,
        run_analyze, run_analyze_project, run_search,
        run_report, run_refactor, run_diff, run_workflow,
        run_stats, run_snapshot, run_decompile,
        run_autoexport,
    )

    # Import command modules to trigger register() calls
    # Each module has register() which adds its subparser
    from pb_devkit.commands import (
        doctor, init, list as list_mod, export, import_,
        build, compile as compile_mod, analyze, analyze_project,
        search, report, refactor, diff, workflow, stats, snapshot,
        decompile, autoexport,
    )

    doctor.register(sub)
    init.register(sub)
    list_mod.register(sub)
    export.register(sub)
    import_.register(sub)
    build.register(sub)
    compile_mod.register(sub)
    analyze.register(sub)
    analyze_project.register(sub)
    search.register(sub)
    report.register(sub)
    refactor.register(sub)
    diff.register(sub)
    workflow.register(sub)
    stats.register(sub)
    snapshot.register(sub)
    decompile.register(sub)
    autoexport.register(sub)

    return parser


# Command dispatch table
_COMMAND_MAP = {
    "doctor": "run_doctor",
    "init": "run_init",
    "list": "run_list",
    "export": "run_export",
    "import": "run_import",
    "build": "run_build",
    "compile": "run_compile",
    "analyze": "run_analyze",
    "analyze-project": "run_analyze_project",
    "search": "run_search",
    "report": "run_report",
    "refactor": "run_refactor",
    "diff": "run_diff",
    "workflow": "run_workflow",
    "stats": "run_stats",
    "snapshot": "run_snapshot",
    "decompile": "run_decompile",
    "autoexport": "run_autoexport",
}


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    # Inject global flags into args
    if args.dry_run and not hasattr(args, "dry_run"):
        pass  # Already on args

    # Dispatch to command handler
    handler_name = _COMMAND_MAP.get(args.command)
    if not handler_name:
        parser.print_help()
        sys.exit(1)

    from pb_devkit import commands
    handler = getattr(commands, handler_name, None)
    if not handler:
        print(f"Error: unknown command '{args.command}'", file=sys.stderr)
        sys.exit(1)

    try:
        handler(args)
    except FileNotFoundError as e:
        print(f"\n  File not found: {e}", file=sys.stderr)
        print(f"  Check the path and try again.", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"\n  Permission denied: {e}", file=sys.stderr)
        print(f"  Check file/directory permissions.", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        msg = str(e)
        print(f"\n  {msg}", file=sys.stderr)
        # ORCA DLL errors get exit code 10
        if "PBORCA DLL" in msg or "PBSpy" in msg:
            sys.exit(10)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrupted.", file=sys.stderr)
        sys.exit(130)
    except BrokenPipeError:
        # Happens when output is piped to head/less and they close early
        sys.exit(0)
    except Exception as e:
        print(f"\n  Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"  Run with --verbose for more details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
