"""CLI command handlers for pb-devkit."""
from pb_devkit.commands.doctor import run as run_doctor
from pb_devkit.commands.init import run as run_init
from pb_devkit.commands.list import run as run_list
from pb_devkit.commands.export import run as run_export
from pb_devkit.commands.import_ import run as run_import
from pb_devkit.commands.build import run as run_build
from pb_devkit.commands.compile import run as run_compile
from pb_devkit.commands.analyze import run as run_analyze
from pb_devkit.commands.analyze_project import run as run_analyze_project
from pb_devkit.commands.search import run as run_search
from pb_devkit.commands.report import run as run_report
from pb_devkit.commands.refactor import run as run_refactor
from pb_devkit.commands.diff import run as run_diff
from pb_devkit.commands.workflow import run as run_workflow
from pb_devkit.commands.stats import run as run_stats
from pb_devkit.commands.snapshot import run as run_snapshot
from pb_devkit.commands.decompile import run as run_decompile
from pb_devkit.commands.autoexport import run as run_autoexport

__all__ = [
    "run_doctor", "run_init", "run_list", "run_export",
    "run_import", "run_build", "run_compile",
    "run_analyze", "run_analyze_project", "run_search",
    "run_report", "run_refactor", "run_diff", "run_workflow",
    "run_stats", "run_snapshot", "run_decompile",
    "run_autoexport",
]
