"""CLI entry point for `pb` console command.

This module is the target of the [project.scripts] entry in pyproject.toml.
It re-exports the main function from pb.py for pip-installed usage.
"""
import sys
from pathlib import Path

# Ensure we can find the pb.py module when installed via pip
# For direct usage: python pb.py <command>
# For pip install:  pb <command>
_SRC_DIR = Path(__file__).parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Re-export main from the CLI module
# The actual pb.py at project root handles the path setup and dispatch
def main():
    """Entry point for the `pb` console command."""
    # Try to import the CLI main directly
    try:
        # When installed via pip, pb.py is not directly accessible
        # Instead, we set up the path and import from commands
        import argparse
        import logging

        # Fix Windows console encoding
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        # Ensure src is on path
        if str(_SRC_DIR) not in sys.path:
            sys.path.insert(0, str(_SRC_DIR))

        # Lazy import to avoid circular dependency
        from pb_devkit.commands import (
            doctor, init, list as list_mod, export, import_,
            build, compile as compile_mod, analyze, analyze_project,
            search, report, refactor, diff, workflow, stats, snapshot,
            decompile,
        )
        from pb_devkit.commands import (
            run_doctor, run_init, run_list, run_export,
            run_import, run_build, run_compile,
            run_analyze, run_analyze_project, run_search,
            run_report, run_refactor, run_diff, run_workflow,
            run_stats, run_snapshot, run_decompile,
        )

        parser = argparse.ArgumentParser(
            prog="pb",
            description="PB DevKit - PowerBuilder Developer Toolkit v1.2.0")
        parser.add_argument("--version", action="version", version="PB DevKit 1.2.0")
        parser.add_argument("--pb-version", type=int, default=None)
        parser.add_argument("--config", "-c", default=None)
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

        sub = parser.add_subparsers(dest="command", help="Available commands")

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

        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            sys.exit(0)

        if args.verbose:
            logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

        _COMMAND_MAP = {
            "doctor": run_doctor, "init": run_init, "list": run_list,
            "export": run_export, "import": run_import, "build": run_build,
            "compile": run_compile, "analyze": run_analyze,
            "analyze-project": run_analyze_project, "search": run_search,
            "report": run_report, "refactor": run_refactor, "diff": run_diff,
            "workflow": run_workflow, "stats": run_stats,
            "snapshot": run_snapshot, "decompile": run_decompile,
        }

        handler = _COMMAND_MAP.get(args.command)
        if not handler:
            parser.print_help()
            sys.exit(1)

        handler(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
