"""PB DevKit - PowerBuilder Developer Toolkit.

A command-line toolkit for maintaining and modernizing PowerBuilder legacy systems.
Provides PBL binary parsing, source code analysis, automated refactoring,
and project intelligence — all without needing the PowerBuilder IDE.

Quick Start:
    from pb_devkit import PBLParser, PBSourceAnalyzer, RefactoringEngine

    # Parse a PBL file
    with PBLParser("app.pbl") as parser:
        entries = parser.list_entries()
        sources = parser.export_all()

    # Analyze code quality
    analyzer = PBSourceAnalyzer()
    issues = analyzer.analyze_directory("./exported")

    # Refactor
    engine = RefactoringEngine()
    results = engine.run("./exported", dry_run=True)

    # Check ORCA DLL availability
    from pb_devkit.pborca_engine import is_available, get_dll_info
    if is_available():
        info = get_dll_info()

CLI Usage:
    python pb.py init <project_dir>
    python pb.py export <pbl_or_dir> [output]
    python pb.py analyze-project <source_dir>
    python pb.py search <pattern> <source_dir>
    python pb.py stats <source_dir>
    python pb.py report <source_dir>
"""
__version__ = "1.3.0"

# Parsers
from .pbl_parser import (
    PBObjectType,
    PBLEntry,
    PBLSource,
    PBLParser,
    PBLBatchExporter,
    OBJ_EXT,
    KW_TYPE,
    BLOCK,
)

# Source analysis
from .sr_parser import (
    SRObjectType,
    SRFileParser,
    PBRoutine,
    PBVariable,
    PBSourceObject,
    PBSourceAnalyzer,
    DependencyAnalyzer,
    ComplexityAnalyzer,
)

# Refactoring
from .refactoring import (
    FixSeverity,
    FixResult,
    RefactoringRule,
    RefactoringEngine,
    FixEmptyCatchRule,
    FixSelectStarRule,
    FixMagicNumbersRule,
    FixDeprecatedFunctionsRule,
    FixLongRoutineRule,
)

# Configuration
from .config import PBConfig

__all__ = [
    # Version
    "__version__",
    # PBL Parsing
    "PBObjectType", "PBLEntry", "PBLSource", "PBLParser", "PBLBatchExporter",
    "OBJ_EXT", "KW_TYPE", "BLOCK",
    # Source Parsing & Analysis
    "SRObjectType", "SRFileParser", "PBRoutine", "PBVariable", "PBSourceObject",
    "PBSourceAnalyzer", "DependencyAnalyzer", "ComplexityAnalyzer",
    # Refactoring
    "FixSeverity", "FixResult", "RefactoringRule", "RefactoringEngine",
    "FixEmptyCatchRule", "FixSelectStarRule", "FixMagicNumbersRule",
    "FixDeprecatedFunctionsRule", "FixLongRoutineRule",
    # Configuration
    "PBConfig",
]
