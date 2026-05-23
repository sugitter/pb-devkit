"""pb doctor command - Environment diagnostics (pure Python, no DLL required)."""
import argparse
import json
import os
import platform
import sys
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser("doctor", help="Run environment diagnostics")
    p.add_argument("target", nargs="?", help="Project directory to check")
    p.add_argument("--json", action="store_true")
    return p


def run(args):
    """Run environment diagnostics."""
    print(f"\n{'='*60}")
    print(f"  PB DevKit - Environment Diagnostics")
    print(f"{'='*60}")

    issues = []
    ok_count = 0

    # 1. Python version
    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 8)
    status = "OK" if py_ok else "WARN"
    print(f"\n  [{status}] Python {py_ver}")
    if py_ok:
        ok_count += 1
    else:
        issues.append("Python 3.8+ required")

    # 2. Platform
    print(f"  [OK]   Platform: {platform.system()} {platform.release()}")
    ok_count += 1

    # 3. Working directory
    print(f"  [OK]   CWD: {os.getcwd()}")

    # 4. Tool directory
    tool_dir = Path(__file__).parent.parent.parent.parent.resolve()
    print(f"  [OK]   Tool dir: {tool_dir}")
    ok_count += 1

    # 5. Check if target project exists
    target = getattr(args, "target", None)
    pbls = []
    sr_files = []
    target_path = None
    total_size = 0

    if target:
        target_path = Path(target)
        if target_path.exists():
            print(f"\n  [OK]   Project: {target_path}")
            ok_count += 1

            pbls = list(target_path.glob("**/*.pbl"))
            print(f"  [OK]   PBL files: {len(pbls)}")
            ok_count += 1

            sr_files = list(target_path.glob("**/*.sr*"))
            if sr_files:
                print(f"  [OK]   Exported sources: {len(sr_files)}")
            else:
                print(f"  [INFO] No exported sources found yet")

            total_size = sum(p.stat().st_size for p in pbls)
            print(f"  [OK]   Total PBL size: {total_size / 1024 / 1024:.1f} MB")
        else:
            print(f"\n  [FAIL] Project path does not exist: {target}")
            issues.append(f"Project path not found: {target}")

    # 6. Module import tests
    print(f"\n  Checking modules...")
    for mod_name, import_path in [
        ("pbl_parser", "pb_devkit.pbl_parser.PBLParser"),
        ("pbl_writer", "pb_devkit.pbl_writer.PblWriter"),
        ("sr_parser", "pb_devkit.sr_parser.PBSourceAnalyzer"),
        ("refactoring", "pb_devkit.refactoring.RefactoringEngine"),
        ("chunk_engine", "pb_devkit.chunk_engine.ChunkEngine"),
    ]:
        module_path, class_name = import_path.rsplit(".", 1)
        try:
            mod = __import__(module_path, fromlist=[class_name])
            getattr(mod, class_name)
            print(f"  [OK]   {mod_name}")
            ok_count += 1
        except (ImportError, AttributeError) as e:
            print(f"  [FAIL] {mod_name}: {e}")
            issues.append(f"{mod_name} import failed: {e}")

    # Summary
    print(f"\n{'='*60}")
    if issues:
        print(f"  Issues: {len(issues)}")
        for iss in issues:
            print(f"    - {iss}")
    else:
        print(f"  All checks passed! (no external DLLs required)")
    print(f"{'='*60}")

    if args.json:
        result = {
            "python_version": py_ver,
            "platform": f"{platform.system()} {platform.release()}",
            "tool_dir": str(tool_dir),
            "dll_required": False,
            "modules_ok": ok_count >= 6,
            "issues": issues,
        }
        if target:
            result["project_exists"] = target_path.exists() if target_path else False
            if target_path and target_path.exists():
                result["pbl_count"] = len(pbls)
                result["total_pbl_size_mb"] = round(total_size / 1024 / 1024, 1)
        print(json.dumps(result, indent=2, ensure_ascii=False))
