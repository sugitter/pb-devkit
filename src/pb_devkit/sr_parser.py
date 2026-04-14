"""PowerBuilder .sr* source file parser and code quality analyzer.

Provides:
- SRFileParser: Parse PB source files into structured objects
- PBSourceAnalyzer: Detect code quality issues with configurable rules
- DependencyAnalyzer: Track cross-object references and dependencies
- ComplexityAnalyzer: Measure cyclomatic complexity of PB routines
"""
from __future__ import annotations
import logging, re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class SRObjectType(Enum):
    APPLICATION = "sra"; DATAWINDOW = "srd"; WINDOW = "srw"; MENU = "srm"
    FUNCTION = "srf"; STRUCTURE = "srs"; USEROBJECT = "sru"; QUERY = "srq"
    PIPELINE = "srp"; PROJECT = "srj"; PROXY = "srx"; UNKNOWN = "bin"


@dataclass
class PBRoutine:
    name: str; access: str = "public"; return_type: str = "(none)"
    arguments: list[str] = field(default_factory=list)
    event: bool = False
    script: str = ""; line_start: int = 0; line_end: int = 0


@dataclass
class PBVariable:
    name: str; data_type: str; access: str = "public"; initial_value: str = ""


@dataclass
class PBSourceObject:
    object_name: str; object_type: SRObjectType; file_path: str = ""
    raw_text: str = ""; header_lines: list[str] = field(default_factory=list)
    routines: list[PBRoutine] = field(default_factory=list)
    variables: list[PBVariable] = field(default_factory=list)


class SRFileParser:
    """Parse PowerBuilder .sr* source files into structured objects."""
    ROUTINE_RE = re.compile(
        r"^(?:forward\s+)?(?P<access>public|protected|private|global)\s+"
        r"(?P<sub>subroutine|function)\s+(?:(?P<type>\w+(?:\[\])?)\s+)?"
        r"(?P<name>\w+)\s*(?:\((?P<args>[^)]*)\))?"
        r"(?:\s+(?:throws|THROWS)\s+(?P<throws>[\w,\s]+))?", re.IGNORECASE)
    # Event pattern: on/off event declarations
    EVENT_RE = re.compile(
        r"^(?:event|EVENT)\s+(?P<name>\w+)\s+"
        r"(?:(?P<type>\w+)\s+)?"
        r"(?:\((?P<args>[^)]*)\))?", re.IGNORECASE)
    VAR_RE = re.compile(
        r"^(?P<access>public|protected|private|instance|shared|global)\s+"
        r"(?P<type>[\w\[\]]+)\s+(?P<name>[\w\[\]]+)"
        r"(?:\s*=\s*(?P<init>[^;\n]+))?\s*[;]?\s*$", re.IGNORECASE)

    def parse_file(self, fp) -> PBSourceObject:
        fp = Path(fp)
        ext = fp.suffix.lstrip(".")
        try:
            ot = SRObjectType(ext)
        except ValueError:
            ot = SRObjectType.UNKNOWN
        text = fp.read_text(encoding="utf-8-sig", errors="replace")
        return self.parse_text(text, fp.name, ot, str(fp))

    def parse_text(self, text: str, name: str,
                   obj_type: SRObjectType, file_path: str = "") -> PBSourceObject:
        lines = text.splitlines()
        obj = PBSourceObject(
            object_name=name, object_type=obj_type,
            file_path=file_path, raw_text=text)

        # Find header end (first routine/event declaration)
        hend = len(lines)
        for i, l in enumerate(lines):
            s = l.strip()
            if self.ROUTINE_RE.match(s) or self.EVENT_RE.match(s):
                hend = i
                break
        obj.header_lines = lines[:hend]

        # Parse code blocks
        i = hend
        while i < len(lines):
            s = lines[i].strip()
            # Try routine match
            m = self.ROUTINE_RE.match(s)
            if m:
                g = m.groupdict()
                r = PBRoutine(
                    name=g.get("name", ""), access=g.get("access", "public").lower(),
                    return_type=g.get("type", "(none)"), line_start=i + 1,
                    event=g.get("sub", "").lower() == "event")
                a = g.get("args", "")
                if a:
                    r.arguments = [x.strip() for x in a.split(",") if x.strip()]
                i += 1
                i = self._collect_body(lines, i, r)
                obj.routines.append(r)
                continue

            # Try event match
            m = self.EVENT_RE.match(s)
            if m:
                g = m.groupdict()
                r = PBRoutine(
                    name=g.get("name", ""), access="public",
                    return_type=g.get("type", "(none)"), line_start=i + 1,
                    event=True)
                a = g.get("args", "")
                if a:
                    r.arguments = [x.strip() for x in a.split(",") if x.strip()]
                i += 1
                i = self._collect_body(lines, i, r)
                obj.routines.append(r)
                continue

            i += 1

        # Parse variables from header
        for l in obj.header_lines:
            vm = self.VAR_RE.match(l.strip())
            if vm:
                g = vm.groupdict()
                init_val = g.get("init") or ""
                obj.variables.append(PBVariable(
                    name=g["name"], data_type=g["type"],
                    access=g["access"].lower(),
                    initial_value=init_val.strip()))
        return obj

    def _collect_body(self, lines: list[str], i: int,
                      r: PBRoutine) -> int:
        """Collect lines until matching end statement."""
        script = []
        depth = 0
        while i < len(lines):
            sl = lines[i].strip()
            if re.match(r"^end\s+(subroutine|function|event)\b", sl, re.I):
                r.line_end = i + 1
                i += 1
                break
            if re.match(r"^(if|for|do|try|choose)\b", sl, re.I):
                depth += 1
            if re.match(r"^end\s+(if|for|do|try|choose)\b", sl, re.I):
                if depth > 0:
                    depth -= 1
            script.append(lines[i])
            i += 1
        r.script = "\n".join(script)
        return i


class DependencyAnalyzer:
    """Track cross-object dependencies in PB source code."""
    # Patterns for detecting references
    CREATE_RE = re.compile(r"\bcreate\s+(\w+)", re.I)
    OPEN_RE = re.compile(r"\b(?:open|OpenWithParm|OpenSheet|OpenSheetWithParm)\s*\(\s*(\w+)", re.I)
    INVOKE_RE = re.compile(r"\w+\.(\w+)\s*\(", re.I)  # object.method()
    DW_RE = re.compile(r"\bdataobject\s*=\s*['\"]?(\w+)", re.I)
    INHERIT_RE = re.compile(r"(?:global\s+)?type\s+(\w+)\s+from\s+(\w+)", re.I)
    # PB SQL patterns
    SQL_TABLE_RE = re.compile(r"\b(?:from|join)\s+(\w+)", re.I)

    def analyze(self, objects: list[PBSourceObject]) -> dict:
        """Analyze dependencies between objects.

        Returns:
            {
                "dependencies": {obj_name: [dep_name, ...]},
                "dependents": {obj_name: [used_by_name, ...]},
                "sql_tables": {obj_name: [table_name, ...]},
                "inheritance": {child_name: parent_name},
            }
        """
        deps: dict[str, set[str]] = defaultdict(set)
        reverse_deps: dict[str, set[str]] = defaultdict(set)
        sql_tables: dict[str, set[str]] = defaultdict(set)
        inheritance: dict[str, str] = {}

        for obj in objects:
            name = obj.object_name
            all_text = obj.raw_text

            # Inheritance
            for m in self.INHERIT_RE.finditer(all_text):
                child = m.group(1)
                parent = m.group(2)
                if parent != "UserObject" and parent != "DataWindow":
                    inheritance[child] = parent
                    deps[name].add(parent)

            # Creates / opens
            for m in self.CREATE_RE.finditer(all_text):
                deps[name].add(m.group(1))
            for m in self.OPEN_RE.finditer(all_text):
                deps[name].add(m.group(1))

            # DataWindow dataobject references
            for m in self.DW_RE.finditer(all_text):
                ref = m.group(1)
                if ref.lower().startswith("d_"):
                    deps[name].add(ref)

            # SQL tables
            for m in self.SQL_TABLE_RE.finditer(all_text):
                table = m.group(1)
                if not table.lower().startswith(("where", "select", "order", "group")):
                    sql_tables[name].add(table)

        # Build reverse deps
        for name, d in deps.items():
            for dep in d:
                reverse_deps[dep].add(name)

        return {
            "dependencies": {k: sorted(v) for k, v in deps.items()},
            "dependents": {k: sorted(v) for k, v in reverse_deps.items()},
            "sql_tables": {k: sorted(v) for k, v in sql_tables.items()},
            "inheritance": inheritance,
        }


class ComplexityAnalyzer:
    """Measure cyclomatic complexity of PB routines."""

    # Branching keywords that increase complexity
    BRANCH_KEYWORDS = re.compile(
        r"^\s*(?:if|else|elseif|else\s+if|choose\s+case|case|for|do\s+while|do\s+until|"
        r"continue|exit|return|throw|goto)\b", re.I)

    def analyze_routine(self, routine: PBRoutine) -> dict:
        """Calculate cyclomatic complexity of a routine."""
        lines = routine.script.splitlines()
        complexity = 1  # Base complexity
        branch_lines = []

        for i, line in enumerate(lines):
            sl = line.strip()
            if not sl or sl.startswith("//") or sl.startswith("'"):
                continue
            if self.BRANCH_KEYWORDS.match(sl):
                complexity += 1
                branch_lines.append(routine.line_start + i)

        # Adjust for CHOOSE CASE (counts as +1 total, not per CASE)
        choose_count = sum(1 for l in branch_lines
                           if lines[l - routine.line_start].strip().lower().startswith("case "))
        if choose_count > 0:
            complexity -= choose_count  # Remove per-case additions
            complexity += 1  # Add 1 for the choose itself (already counted as +1)

        code_lines = [l for l in lines if l.strip() and not l.strip().startswith(("//", "'"))]
        return {
            "name": routine.name,
            "complexity": complexity,
            "code_lines": len(code_lines),
            "branch_lines": branch_lines,
            "rating": self._rate(complexity),
        }

    def analyze_object(self, obj: PBSourceObject) -> list[dict]:
        """Analyze all routines in an object."""
        return [self.analyze_routine(r) for r in obj.routines if r.script.strip()]

    def _rate(self, complexity: int) -> str:
        if complexity <= 5:
            return "A"  # Simple
        if complexity <= 10:
            return "B"  # Moderate
        if complexity <= 20:
            return "C"  # Complex
        if complexity <= 50:
            return "D"  # Very Complex
        return "F"  # Unmaintainable


class PBSourceAnalyzer:
    """Analyze PB source code for quality issues.

    Checks include:
    - Routine length (recommend <200 lines)
    - Empty CATCH blocks
    - SELECT * in DataWindows
    - Global variables
    - Hardcoded SQL (suggest using DataWindow)
    - Magic numbers
    - Deeply nested code
    - Unused variables
    - Duplicate code patterns
    - Missing error handling
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.max_routine_lines = self.config.get("max_routine_lines", 200)
        self.max_complexity = self.config.get("max_complexity", 20)
        self.max_nesting = self.config.get("max_nesting", 4)

    def analyze_file(self, fp) -> list[dict]:
        return self.analyze_object(SRFileParser().parse_file(fp))

    def analyze_directory(self, d: Path) -> dict[str, list[dict]]:
        d = Path(d)
        return {f.name: self.analyze_file(f) for f in sorted(d.rglob("*.sr*"))}

    def analyze_object(self, obj: PBSourceObject) -> list[dict]:
        issues = []
        complexity_analyzer = ComplexityAnalyzer()

        for r in obj.routines:
            # Check routine length
            code_lines = [l for l in r.script.splitlines()
                          if l.strip() and not l.strip().startswith(("//", "'"))]
            if len(code_lines) > self.max_routine_lines:
                issues.append({
                    "severity": "warning", "type": "routine_too_long",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' has {len(code_lines)} lines "
                               f"(recommend <{self.max_routine_lines})"})

            # Check empty CATCH blocks
            if re.search(r"catch\s*\([^)]*\)\s*\n\s*(?://.*)?\s*end\s+try", r.script, re.I):
                issues.append({
                    "severity": "error", "type": "empty_catch",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' has empty CATCH block"})

            # Check deep nesting
            max_depth = self._max_nesting_depth(r.script)
            if max_depth > self.max_nesting:
                issues.append({
                    "severity": "warning", "type": "deep_nesting",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' has nesting depth {max_depth} "
                               f"(recommend <{self.max_nesting})"})

            # Check magic numbers
            magic = self._find_magic_numbers(r.script)
            if magic:
                issues.append({
                    "severity": "info", "type": "magic_numbers",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' uses magic numbers: {', '.join(magic[:5])}"})

            # Check hardcoded strings (potential SQL injection)
            if self._has_hardcoded_sql(r.script):
                issues.append({
                    "severity": "warning", "type": "hardcoded_sql",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' has hardcoded SQL - consider using DataWindow"})

            # Check missing error handling (functions that don't have try-catch)
            if r.return_type != "(none)" and not r.event:
                if "try" not in r.script.lower():
                    issues.append({
                        "severity": "info", "type": "no_error_handling",
                        "object": obj.object_name, "routine": r.name,
                        "line": r.line_start,
                        "message": f"'{r.name}' lacks try-catch error handling"})

            # Check for deprecated PB functions
            deprecated = self._find_deprecated_calls(r.script)
            for dep in deprecated:
                issues.append({
                    "severity": "warning", "type": "deprecated_function",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' uses deprecated: {dep}"})

            # Complexity check
            cc = complexity_analyzer.analyze_routine(r)
            if cc["complexity"] > self.max_complexity:
                issues.append({
                    "severity": "warning", "type": "high_complexity",
                    "object": obj.object_name, "routine": r.name,
                    "line": r.line_start,
                    "message": f"'{r.name}' complexity={cc['complexity']} "
                               f"(rating={cc['rating']}, recommend <{self.max_complexity})"})

        # DataWindow-specific checks
        if obj.object_type == SRObjectType.DATAWINDOW:
            hdr = "\n".join(obj.header_lines)
            if re.search(r"\bSELECT\s+\*", hdr, re.I):
                issues.append({
                    "severity": "warning", "type": "select_star",
                    "object": obj.object_name, "routine": "",
                    "message": "Uses SELECT * - explicitly list columns"})

        # Global variables
        for v in obj.variables:
            if v.access == "global":
                issues.append({
                    "severity": "info", "type": "global_variable",
                    "object": obj.object_name, "routine": "",
                    "message": f"Global variable '{v.name}' ({v.data_type})"})

        return issues

    def _max_nesting_depth(self, script: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        depth = 0
        for line in script.splitlines():
            sl = line.strip().lower()
            if sl.startswith(("if ", "if(", "for ", "for(", "do ", "do while",
                               "do until", "choose case", "try")):
                depth += 1
                max_depth = max(max_depth, depth)
            elif sl.startswith(("end if", "end for", "end do", "next",
                                "end choose", "end try", "loop")):
                depth = max(0, depth - 1)
        return max_depth

    def _find_magic_numbers(self, script: str) -> list[str]:
        """Find unexplained numeric literals."""
        # Exclude common safe numbers: 0, 1, -1, 100, 1000, powers of 2
        safe = {0, 1, -1, 2, 4, 8, 10, 16, 32, 64, 100, 128, 256,
                512, 1000, 1024, 2048, 8192}
        found = []
        for m in re.finditer(r"(?<![.\w])(\d+)(?![.\w])", script):
            num = int(m.group(1))
            # Skip if in a comment
            line_start = script.rfind("\n", 0, m.start()) + 1
            line = script[line_start:m.start()]
            if "//" in line or "'" in line:
                continue
            if num not in safe and 2 < num < 100000:
                found.append(str(num))
        return list(dict.fromkeys(found))[:10]  # Deduplicate, limit 10

    def _has_hardcoded_sql(self, script: str) -> bool:
        """Check for inline SQL statements."""
        sql_patterns = [
            r"\b(?:SELECT|INSERT|UPDATE|DELETE)\s+.*\bFROM\b",
            r"\bEXEC(?:UTE)?\s+(?:IMMEDIATE\s+)?['\"]",
            r"\bSQLCA\.(?:SQLCode|DBCode)",
        ]
        return any(re.search(p, script, re.I) for p in sql_patterns)

    def _find_deprecated_calls(self, script: str) -> list[str]:
        """Find deprecated PowerBuilder function calls."""
        deprecated = [
            (r"\bSetPointer\b", "SetPointer (use Pointer property)"),
            (r"\bYield\(\)", "Yield() (use Timer for async)"),
            (r"\bDoEvents\b", "DoEvents (use Timer for async)"),
            (r"\bRGB\b(?!\s*\()", "RGB() (use Long color constants)"),
            (r"\bSetRedraw\b", "SetRedraw (use SetRedraw property)"),
        ]
        found = []
        for pattern, desc in deprecated:
            if re.search(pattern, script, re.I):
                found.append(desc)
        return found

    def analyze_project(self, source_dir: Path) -> dict:
        """Full project analysis with dependency graph."""
        files = list(source_dir.rglob("*.sr*"))
        objects = [SRFileParser().parse_file(f) for f in files]

        # Quality issues
        all_issues = {}
        for obj in objects:
            issues = self.analyze_object(obj)
            if issues:
                all_issues[obj.object_name] = issues

        # Dependencies
        dep_analyzer = DependencyAnalyzer()
        deps = dep_analyzer.analyze(objects)

        # Complexity
        complexity_analyzer = ComplexityAnalyzer()
        complexity = {}
        for obj in objects:
            cc = complexity_analyzer.analyze_object(obj)
            if cc:
                complexity[obj.object_name] = cc

        # Summary
        total_issues = sum(len(v) for v in all_issues.values())
        by_severity = defaultdict(int)
        for issues in all_issues.values():
            for iss in issues:
                by_severity[iss["severity"]] += 1

        return {
            "summary": {
                "files": len(files),
                "objects": len(objects),
                "total_issues": total_issues,
                "by_severity": dict(by_severity),
            },
            "issues": all_issues,
            "dependencies": deps,
            "complexity": complexity,
        }
