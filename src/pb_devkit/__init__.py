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
    python pb.py export <pbl_or_exe> [output]          # PBL export or EXE decompile
    python pb.py export <exe> --pbl-tree [output]      # Infer PBL grouping
    python pb.py decompile <exe> --output ./src        # Decompile to .ps files
    python pb.py analyze-project <source_dir>          # Auto-detect PBL tree
    python pb.py analyze-project <src> --html report.html
    python pb.py search <pattern> <source_dir>
    python pb.py stats <source_dir>
    python pb.py report <source_dir>
"""
__version__ = "1.5.0"

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

# PE Extraction
from .pe_extractor import PEExtractor, PBDResource

# PBL Grouper
from .pbl_grouper import (
    PBLGroupStats,
    infer_pbl_groups,
    export_pbl_tree,
    export_multi_pbl_tree,
)

# Chunk Engine
from .chunk_engine import ChunkEngine, PBEntry

# Project Detector
from .project_detector import (
    ProjectType,
    ProjectInfo,
    detect_project,
)

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
    # PE Extraction
    "PEExtractor", "PBDResource",
    # Chunk Engine
    "ChunkEngine", "PBEntry",
    # PBL Grouper
    "PBLGroupStats", "infer_pbl_groups", "export_pbl_tree", "export_multi_pbl_tree",
    # Project Detector
    "ProjectType", "ProjectInfo", "detect_project",
]
