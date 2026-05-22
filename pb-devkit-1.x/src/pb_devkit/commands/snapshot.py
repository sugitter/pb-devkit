"""pb snapshot command - Version tracking: export + diff + git commit.

Workflow:
  1. Export PBL(s) to source dir (reuse export logic)
  2. Compare with previous snapshot (reuse diff logic)
  3. Generate human-readable changelog
  4. Optional auto git commit with changelog message
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "snapshot",
        help="Export PBL + diff + optional git commit for version tracking")
    p.add_argument("target", nargs="+", help="PBL file(s) or directory")
    p.add_argument("output", nargs="?", default="./src",
                   help="Output directory for exported sources (default: ./src)")
    p.add_argument("--snapshot-dir", default=".pb-snapshots",
                   help="Directory to store snapshot metadata (default: .pb-snapshots)")
    p.add_argument("--no-git", action="store_true",
                   help="Skip git operations (export + diff only)")
    p.add_argument("--no-diff", action="store_true",
                   help="Skip diff against previous snapshot")
    p.add_argument("--message", "-m", default=None,
                   help="Custom commit message (auto-generated if omitted)")
    p.add_argument("--json", action="store_true",
                   help="Output diff report in JSON format")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Show detailed changes")
    p.add_argument("--orca", action="store_true",
                   help="Use PBORCA DLL for export")
    return p


def run(args):
    """Execute snapshot workflow."""
    import shutil
    from pb_devkit.pbl_parser import PBLParser, PBLBatchExporter

    target = args.target
    output = Path(args.output)
    snapshot_dir = Path(args.snapshot_dir)
    use_git = not args.no_git
    do_diff = not args.no_diff
    use_orca = args.orca

    # --- Step 1: Export ---
    print(f"\n{'='*60}")
    print(f"  pb snapshot v1.0")
    print(f"{'='*60}")

    output.mkdir(parents=True, exist_ok=True)
    print(f"\n[1/4] Exporting to {output.resolve()} ...")

    total_objects = 0
    exported_files = []

    for t in target:
        p = Path(t)
        if p.is_file() and p.suffix.lower() == ".pbl":
            print(f"  Exporting: {p}")
            if use_orca:
                exported_files.extend(_export_with_orca(p, str(output), args))
            else:
                with PBLParser(p) as parser:
                    files = parser.export_to_directory(str(output))
                    exported_files.extend(files)
                    print(f"    -> {len(files)} objects")
                    total_objects += len(files)
        elif p.is_dir():
            print(f"  Batch exporting: {p}/*")
            exporter = PBLBatchExporter(p, str(output))
            results = exporter.export_all()
            for pbl_path, files in results.items():
                exported_files.extend(files)
                total_objects += len(files)
            print(f"    -> {total_objects} objects from {len(results)} PBLs")
        else:
            print(f"  Error: not a PBL file or directory: {t}", file=sys.stderr)

    if total_objects == 0:
        print("\n  No objects exported. Nothing to snapshot.")
        sys.exit(0)

    print(f"  Exported {total_objects} object(s)")

    # --- Step 2: Diff with previous snapshot ---
    changelog_lines = []
    if do_diff:
        print(f"\n[2/4] Comparing with previous snapshot ...")
        changelog_lines = _diff_against_previous(
            output, snapshot_dir, args.verbose, args.json)

    # --- Step 3: Save snapshot metadata ---
    print(f"\n[3/4] Saving snapshot metadata ...")
    snapshot_meta = _save_snapshot_meta(
        snapshot_dir, output, total_objects, changelog_lines)

    # --- Step 4: Git commit ---
    if use_git:
        print(f"\n[4/4] Git commit ...")
        _git_commit(output, changelog_lines, snapshot_meta, args.message)
    else:
        print(f"\n[4/4] Git commit skipped (--no-git)")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Snapshot complete")
    print(f"  Objects:  {total_objects}")
    print(f"  Output:   {output.resolve()}")
    print(f"  Meta:     {snapshot_dir.resolve()}/latest.json")
    if changelog_lines:
        print(f"  Changes:  {sum(1 for l in changelog_lines if l.startswith('+'))} added, "
              f"{sum(1 for l in changelog_lines if l.startswith('-'))} removed, "
              f"{sum(1 for l in changelog_lines if l.startswith('~'))} modified")
    else:
        print(f"  Changes:  (first snapshot or no diff)")
    print(f"{'='*60}")


def _export_with_orca(pbl_path: Path, output_dir: str, args) -> list:
    """Export using PBORCA DLL."""
    from pb_devkit.pborca_engine import PBORCAEngine
    engine = PBORCAEngine(pb_version=args.pb_version)
    engine.session_open()
    try:
        exported = engine.export_all(str(pbl_path), output_dir,
                                     headers=True)
        return exported
    finally:
        engine.session_close()


def _diff_against_previous(output: Path, snapshot_dir: Path,
                           verbose: bool, json_output: bool) -> list:
    """Compare current output with previous snapshot, return changelog lines."""
    prev_dir = snapshot_dir / "previous"
    if not prev_dir.is_dir():
        print("    No previous snapshot found (first snapshot).")
        return []

    from pb_devkit.sr_parser import SRFileParser

    files_curr = {f.name: f for f in output.glob("**/*.sr*")}
    files_prev = {f.name: f for f in prev_dir.glob("**/*.sr*")}

    all_names = sorted(set(files_curr.keys()) | set(files_prev.keys()))

    added = []
    removed = []
    modified = []

    parser = SRFileParser()

    for name in all_names:
        if name not in files_prev:
            added.append(name)
        elif name not in files_curr:
            removed.append(name)
        else:
            t1 = files_prev[name].read_text(encoding="utf-8-sig", errors="replace")
            t2 = files_curr[name].read_text(encoding="utf-8-sig", errors="replace")
            if t1 != t2:
                try:
                    obj1 = parser.parse_file(files_prev[name])
                    obj2 = parser.parse_file(files_curr[name])
                    changes = _compare_objects(obj1, obj2)
                    modified.append({"name": name, "changes": changes})
                except Exception:
                    modified.append({"name": name, "changes": ["Content changed"]})

    # Build changelog
    lines = []
    for f in sorted(added):
        lines.append(f"+ {f}")
    for f in sorted(removed):
        lines.append(f"- {f}")
    for m in sorted(modified, key=lambda x: x["name"]):
        lines.append(f"~ {m['name']}")
        for c in m["changes"]:
            lines.append(f"    {c}")

    print(f"    Added: {len(added)}, Removed: {len(removed)}, "
          f"Modified: {len(modified)}, Unchanged: {len(all_names) - len(added) - len(removed) - len(modified)}")

    if verbose and lines:
        print()
        for line in lines:
            print(f"    {line}")

    if json_output:
        report = {
            "added": sorted(added),
            "removed": sorted(removed),
            "modified": sorted(modified, key=lambda x: x["name"]),
        }
        json_path = snapshot_dir / "diff-report.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        print(f"    JSON report: {json_path}")

    return lines


def _compare_objects(obj1, obj2) -> list:
    """Compare two parsed PB objects and return list of changes."""
    changes = []
    names1 = {r.name for r in obj1.routines}
    names2 = {r.name for r in obj2.routines}
    for name in sorted(names2 - names1):
        changes.append(f"Added routine: {name}")
    for name in sorted(names1 - names2):
        changes.append(f"Removed routine: {name}")
    for name in sorted(names1 & names2):
        r1 = next(r for r in obj1.routines if r.name == name)
        r2 = next(r for r in obj2.routines if r.name == name)
        if r1.script != r2.script:
            changes.append(f"Modified routine: {name}")
    vars1 = {v.name for v in obj1.variables}
    vars2 = {v.name for v in obj2.variables}
    for v in sorted(vars2 - vars1):
        changes.append(f"Added variable: {v}")
    for v in sorted(vars1 - vars2):
        changes.append(f"Removed variable: {v}")
    return changes


def _save_snapshot_meta(snapshot_dir: Path, output: Path,
                        total_objects: int, changelog: list) -> dict:
    """Save snapshot metadata and rotate previous snapshot."""
    import shutil

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Rotate: current -> previous
    prev_dir = snapshot_dir / "previous"
    if prev_dir.exists():
        shutil.rmtree(prev_dir)
    if output.exists():
        shutil.copytree(output, prev_dir)

    # Save metadata
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_objects": total_objects,
        "output_dir": str(output.resolve()),
        "changes_summary": {
            "added": sum(1 for l in changelog if l.startswith("+")),
            "removed": sum(1 for l in changelog if l.startswith("-")),
            "modified": sum(1 for l in changelog if l.startswith("~")),
        },
        "changelog": changelog,
    }

    meta_path = snapshot_dir / "latest.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    # Append to history
    history_path = snapshot_dir / "history.jsonl"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    return meta


def _git_commit(output: Path, changelog: list, meta: dict,
                custom_message: str | None):
    """Stage exported sources and commit with changelog."""
    import shutil

    # Check if git is available and we're in a repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("    Not a git repository. Skipping commit.")
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("    git not found. Skipping commit.")
        return

    # Stage exported sources
    try:
        subprocess.run(
            ["git", "add", "-f", str(output)],
            capture_output=True, text=True, timeout=30)

        # Also stage snapshot metadata
        snapshot_dir = Path(".pb-snapshots")
        if snapshot_dir.exists():
            subprocess.run(
                ["git", "add", "-f", str(snapshot_dir)],
                capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        print("    git add timed out.")
        return

    # Build commit message
    if custom_message:
        msg = custom_message
    else:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        summary = meta.get("changes_summary", {})
        msg = f"[pb snapshot] {ts}"
        if changelog:
            parts = []
            if summary.get("added"):
                parts.append(f"+{summary['added']}")
            if summary.get("removed"):
                parts.append(f"-{summary['removed']}")
            if summary.get("modified"):
                parts.append(f"~{summary['modified']}")
            msg += f" ({', '.join(parts)})"
        else:
            msg += " (initial snapshot)"
        # Append changelog details
        if changelog:
            msg += "\n\nChanges:\n" + "\n".join(changelog)

    # Commit
    try:
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # Extract short hash
            commit_line = result.stdout.strip().split("\n")[0]
            print(f"    Committed: {commit_line}")
        else:
            # Nothing to commit is fine
            if "nothing to commit" in result.stdout:
                print("    No changes to commit (sources unchanged).")
            else:
                print(f"    git commit: {result.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("    git commit timed out.")
