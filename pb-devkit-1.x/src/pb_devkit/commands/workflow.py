"""pb workflow command - Full workflow: export → analyze → refactor."""
import argparse
import json
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("workflow",
                       help="Full workflow: export->analyze->refactor")
    p.add_argument("pbl", help="PBL file or project directory")
    p.add_argument("work_dir", nargs="?", help="Working directory")
    p.add_argument("--apply", action="store_true",
                   help="Apply safe auto-fixes")
    p.add_argument("--import-pbl", help="Import changes back to this PBL")
    return p


def run(args):
    """Full workflow: export → analyze → refactor → (optional import)."""
    from pb_devkit.pbl_parser import PBLParser, PBLBatchExporter
    from pb_devkit.sr_parser import PBSourceAnalyzer
    from pb_devkit.refactoring import RefactoringEngine

    pbl_path = Path(args.pbl)
    work_dir = Path(args.work_dir or "./pb-workflow")

    print(f"\n{'='*60}")
    print(f"  PB DevKit - Full Workflow")
    print(f"{'='*60}")

    # Step 1: Export
    export_dir = work_dir / "exported"
    print(f"\n[1/4] Exporting: {pbl_path}")
    if pbl_path.is_file():
        with PBLParser(pbl_path) as parser:
            exported = parser.export_to_directory(str(export_dir))
            print(f"  Exported {len(exported)} objects")
    elif pbl_path.is_dir():
        exporter = PBLBatchExporter(pbl_path, str(export_dir))
        results = exporter.export_all()
        total = sum(len(v) for v in results.values())
        print(f"  Exported {total} objects from {len(results)} PBLs")

    # Step 2: Analyze
    print(f"\n[2/4] Analyzing code quality...")
    analyzer = PBSourceAnalyzer()
    report = analyzer.analyze_project(export_dir)
    summary = report["summary"]
    print(f"  {summary['total_issues']} issues found "
          f"(E:{summary['by_severity'].get('error',0)} "
          f"W:{summary['by_severity'].get('warning',0)} "
          f"I:{summary['by_severity'].get('info',0)})")

    if not args.apply:
        print("\n  Issues detected (dry run):")
        for obj_name, issues in report["issues"].items():
            for iss in issues[:5]:
                sev = iss.get("severity", "info")
                icon = {"error": "E", "warning": "W", "info": "I"}.get(sev, "?")
                print(f"    [{icon}] {obj_name}: {iss['message']}")
        if summary["total_issues"] > 0:
            print(f"    ... and more")
        print(f"\n  Use --apply to apply safe auto-fixes")

    # Step 3: Refactor (only if --apply)
    if args.apply:
        print(f"\n[3/4] Applying safe refactoring fixes...")
        from pb_devkit.config import PBConfig
        config = PBConfig.load(args.config if hasattr(args, "config") and args.config else None)
        engine = RefactoringEngine(config=config)
        ref_result = engine.run(export_dir, dry_run=False)
        print(f"  Applied {ref_result['by_severity'].get('safe', 0)} safe fixes")
        if ref_result["files_modified"]:
            print(f"  Modified {len(ref_result['files_modified'])} files")
    else:
        print(f"\n[3/4] Skipping refactoring (use --apply)")

    # Step 4: Pack back to PBL (only with --apply and --import-pbl)
    if args.apply and args.import_pbl:
        print(f"\n[4/4] Packing source back to PBL: {args.import_pbl}")
        try:
            from pb_devkit.pbl_writer import pack_directory
            count = pack_directory(str(export_dir), args.import_pbl)
            print(f"  ✅ Packed {count} objects to {args.import_pbl}")
        except Exception as e:
            print(f"  [warn] Pack failed: {e}")
            print(f"  Tip: use 'pb pack {export_dir} -o {args.import_pbl}' manually")
    else:
        if args.apply:
            print(f"\n[4/4] Use --import-pbl <path.pbl> to pack changes back to PBL")

    print(f"\n{'='*60}")
    print(f"  Workflow complete. Working directory: {work_dir.resolve()}")
    print(f"{'='*60}")

    # Save report
    report_path = work_dir / "report.json"
    work_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"  Report saved to: {report_path}")
