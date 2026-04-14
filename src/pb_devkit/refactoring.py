"""PowerBuilder source code auto-refactoring module.

Provides automated code fixes and improvement suggestions:
- RefactoringEngine: Apply safe transformations to PB source code
- Each rule is independent and can be toggled on/off
- Supports dry-run mode to preview changes before applying
"""
from __future__ import annotations
import logging, re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .sr_parser import SRFileParser, SRObjectType

logger = logging.getLogger(__name__)


class FixSeverity(Enum):
    SAFE = "safe"        # Always safe to apply
    LIKELY = "likely"    # Safe in most cases, review recommended
    MANUAL = "manual"    # Requires human review


@dataclass
class FixResult:
    """Result of a single refactoring fix."""
    rule_id: str
    description: str
    severity: FixSeverity
    file_name: str
    line_start: int = 0
    line_end: int = 0
    original: str = ""
    replacement: str = ""
    applied: bool = False


class RefactoringRule:
    """Base class for refactoring rules."""
    rule_id: str = "base"
    description: str = ""
    severity: FixSeverity = FixSeverity.SAFE

    def apply(self, text: str, filename: str = "") -> list[FixResult]:
        raise NotImplementedError


class FixEmptyCatchRule(RefactoringRule):
    """Add logging to empty CATCH blocks."""
    rule_id = "fix_empty_catch"
    description = "Add error logging to empty CATCH blocks"
    severity = FixSeverity.SAFE

    # Matches: catch(...) [optional comment] end try
    EMPTY_CATCH_RE = re.compile(
        r"(catch\s*\([^)]*\)\s*\n)"
        r"(\s*(?://[^\n]*)?\s*\n)*"
        r"(\s*end try)", re.I)

    def apply(self, text: str, filename: str = "") -> list[FixResult]:
        results = []
        lines = text.splitlines()
        i = 0
        new_lines = list(lines)

        while i < len(lines):
            sl = lines[i].strip().lower()
            if sl.startswith("catch") and "(" in sl:
                # Find matching end try
                j = i + 1
                body_lines = []
                has_content = False
                while j < len(lines):
                    if lines[j].strip().lower().startswith("end try"):
                        break
                    if lines[j].strip() and not lines[j].strip().startswith("//"):
                        has_content = True
                    body_lines.append(j)
                    j += 1

                if not has_content and j < len(lines):
                    # Found empty catch - add logging
                    indent = self._detect_indent(lines[i])
                    log_line = f"{indent}// TODO: log error - SQLCA.SQLErrText"
                    fix = FixResult(
                        rule_id=self.rule_id,
                        description=self.description,
                        severity=self.severity,
                        file_name=filename,
                        line_start=i + 1,
                        line_end=j + 1,
                        original="\n".join(lines[i:j + 1]),
                        replacement="\n".join(lines[i:j]) + "\n" + log_line + "\n" + lines[j],
                        applied=True)
                    results.append(fix)
                    new_lines.insert(j, log_line)
                    lines = new_lines  # Update reference
            i += 1

        # Apply changes to text
        final_text = "\n".join(new_lines)
        if results:
            for r in results:
                text = final_text
        return results, final_text

    def _detect_indent(self, line: str) -> str:
        m = re.match(r"^(\s+)", line)
        return m.group(1) if m else "\t"


class FixSelectStarRule(RefactoringRule):
    """Replace SELECT * with explicit column listing placeholder."""
    rule_id = "fix_select_star"
    description = "Replace SELECT * with explicit columns (placeholder)"
    severity = FixSeverity.MANUAL

    SELECT_STAR_RE = re.compile(
        r"\b(SELECT)\s+\*\s*\b(FROM\b)", re.I)

    def apply(self, text: str, filename: str = "") -> list[FixResult]:
        results = []
        new_text = text

        for m in self.SELECT_STAR_RE.finditer(text):
            # Only apply in DataWindow sources
            if not filename.lower().endswith(".srd"):
                continue
            fix = FixResult(
                rule_id=self.rule_id,
                description=self.description,
                severity=self.severity,
                file_name=filename,
                original=m.group(0),
                replacement=f"{m.group(1)} col1, col2 -- TODO: list all columns {m.group(2)}",
                applied=False)  # Manual review needed
            results.append(fix)

        return results, text  # Don't auto-apply


class FixMagicNumbersRule(RefactoringRule):
    """Extract magic numbers into constants."""
    rule_id = "fix_magic_numbers"
    description = "Extract magic numbers into named constants"
    severity = FixSeverity.LIKELY

    MAGIC_RE = re.compile(r"(?<![.\w])(\d{3,6})(?![.\w])")

    def apply(self, text: str, filename: str = "") -> list[FixResult]:
        results = []
        safe = {100, 256, 512, 1000, 1024, 2048, 8192, 32767, 65536}
        seen = set()
        lines = text.splitlines()

        for i, line in enumerate(lines):
            sl = line.strip()
            if sl.startswith("//") or sl.startswith("'"):
                continue
            for m in self.MAGIC_RE.finditer(line):
                num = int(m.group(1))
                if num in safe or num in seen:
                    continue
                seen.add(num)
                const_name = f"CONST_{num}"
                fix = FixResult(
                    rule_id=self.rule_id,
                    description=self.description,
                    severity=self.severity,
                    file_name=filename,
                    line_start=i + 1,
                    original=str(num),
                    replacement=const_name,
                    applied=False)
                results.append(fix)
                if len(results) >= 10:
                    return results, text

        return results, text


class FixDeprecatedFunctionsRule(RefactoringRule):
    """Replace deprecated PB function calls."""
    rule_id = "fix_deprecated"
    description = "Replace deprecated PowerBuilder functions"
    severity = FixSeverity.LIKELY

    DEPRECATED = [
        (re.compile(r"\bSetPointer\s*\(\s*(\w+)\s*\)", re.I),
         r"SetPointer(\1)  // TODO: use Pointer property instead"),
        (re.compile(r"\bYield\s*\(\s*\)", re.I),
         r"// Yield() removed - use Timer(0.1) for async if needed"),
    ]

    def apply(self, text: str, filename: str = "") -> list[FixResult]:
        results = []
        for pattern, replacement in self.DEPRECATED:
            for m in pattern.finditer(text):
                fix = FixResult(
                    rule_id=self.rule_id,
                    description=self.description,
                    severity=self.severity,
                    file_name=filename,
                    original=m.group(0),
                    replacement=replacement,
                    applied=False)
                results.append(fix)
        return results, text


class FixLongRoutineRule(RefactoringRule):
    """Suggest splitting long routines."""
    rule_id = "fix_long_routine"
    description = "Routine exceeds recommended length - consider splitting"
    severity = FixSeverity.MANUAL

    def apply(self, text: str, filename: str = "", max_lines: int = 200) -> tuple:
        from .sr_parser import SRFileParser
        obj = SRFileParser().parse_text(text, filename, SRObjectType.UNKNOWN)
        results = []
        for r in obj.routines:
            code_lines = [l for l in r.script.splitlines()
                          if l.strip() and not l.strip().startswith(("//", "'"))]
            if len(code_lines) > max_lines:
                results.append(FixResult(
                    rule_id=self.rule_id,
                    description=f"'{r.name}' has {len(code_lines)} lines "
                                f"(recommend <{max_lines})",
                    severity=self.severity,
                    file_name=filename,
                    line_start=r.line_start,
                    line_end=r.line_end,
                    applied=False))
        return results, text


class RefactoringEngine:
    """Apply refactoring rules to PB source files.

    Usage:
        engine = RefactoringEngine()

        # With config from .pbdevkit.json
        from pb_devkit.config import PBConfig
        config = PBConfig.load()
        engine = RefactoringEngine(config=config)

        # Dry run - preview changes
        results = engine.run(source_dir, dry_run=True)

        # Apply changes
        results = engine.run(source_dir, dry_run=False)
    """

    def __init__(self, config=None):
        self.rules: list[RefactoringRule] = []
        self._config = config
        self._register_defaults()
        self._apply_config_filter()

    def _register_defaults(self):
        self.register(FixEmptyCatchRule())
        self.register(FixSelectStarRule())
        self.register(FixMagicNumbersRule())
        self.register(FixDeprecatedFunctionsRule())
        self.register(FixLongRoutineRule())

    def _apply_config_filter(self):
        """Filter rules based on .pbdevkit.json config."""
        if not self._config:
            return
        enabled = self._config.enabled_rules  # None = all
        disabled = self._config.disabled_rules
        if enabled is not None:
            self.rules = [r for r in self.rules if r.rule_id in enabled]
        if disabled:
            self.rules = [r for r in self.rules if r.rule_id not in disabled]

    def register(self, rule: RefactoringRule):
        self.rules.append(rule)

    def run(self, source_path: Path, dry_run: bool = True,
            rule_filter: Optional[list[str]] = None) -> dict:
        """Run refactoring on a file or directory.

        Args:
            source_path: Path to .sr* file or directory.
            dry_run: If True, only report suggested changes without modifying files.
            rule_filter: Only run rules with these IDs. None = all rules.

        Returns:
            {
                "total_fixes": int,
                "by_severity": {"safe": N, "likely": N, "manual": N},
                "files_modified": [str, ...],
                "details": [FixResult, ...],
            }
        """
        source_path = Path(source_path)
        rules = self._filter_rules(rule_filter)
        all_results: list[FixResult] = []
        files_modified = []

        files = [source_path] if source_path.is_file() else sorted(source_path.glob("*.sr*"))

        for f in files:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8-sig")
            original_text = text
            file_results = []

            for rule in rules:
                try:
                    result = rule.apply(text, f.name)
                    if isinstance(result, tuple):
                        fixes, text = result
                        file_results.extend(fixes)
                    elif isinstance(result, list):
                        file_results.extend(result)
                except Exception as e:
                    logger.warning("Rule %s failed on %s: %s", rule.rule_id, f.name, e)

            all_results.extend(file_results)

            if not dry_run and text != original_text:
                # Backup and write
                backup = f.with_suffix(f.suffix + ".bak")
                backup.write_text(original_text, encoding="utf-8")
                f.write_text(text, encoding="utf-8")
                files_modified.append(str(f))

        by_severity = {"safe": 0, "likely": 0, "manual": 0}
        for r in all_results:
            by_severity[r.severity.value] += 1

        return {
            "total_fixes": len(all_results),
            "by_severity": by_severity,
            "files_modified": files_modified,
            "details": all_results,
        }

    def _filter_rules(self, rule_filter: Optional[list[str]]) -> list[RefactoringRule]:
        if not rule_filter:
            return list(self.rules)
        return [r for r in self.rules if r.rule_id in rule_filter]
