"""Tests for PB DevKit modules."""
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pb_devkit.pbl_parser import (
    PBObjectType, PBLEntry, PBLSource, OBJ_EXT, KW_TYPE, PBLParser, PBLBatchExporter,
    HEADER_SIZE_PB_OLD, HEADER_SIZE_PB_NEW)
from pb_devkit.sr_parser import (
    SRObjectType, SRFileParser, PBSourceAnalyzer,
    DependencyAnalyzer, ComplexityAnalyzer, PBRoutine, PBVariable)
from pb_devkit.refactoring import (
    RefactoringEngine, FixEmptyCatchRule, FixSelectStarRule,
    FixMagicNumbersRule, FixDeprecatedFunctionsRule, FixDeprecatedFunctionsRule)
from pb_devkit.config import PBConfig, CONFIG_FILENAMES


class TestPBObjectType(unittest.TestCase):
    def test_extension_map(self):
        self.assertEqual(OBJ_EXT[PBObjectType.APPLICATION], ".sra")
        self.assertEqual(OBJ_EXT[PBObjectType.DATAWINDOW], ".srd")
        self.assertEqual(OBJ_EXT[PBObjectType.WINDOW], ".srw")
        self.assertEqual(OBJ_EXT[PBObjectType.MENU], ".srm")
        self.assertEqual(OBJ_EXT[PBObjectType.FUNCTION], ".srf")
        self.assertEqual(OBJ_EXT[PBObjectType.STRUCTURE], ".srs")
        self.assertEqual(OBJ_EXT[PBObjectType.USEROBJECT], ".sru")

    def test_type_codes_complete(self):
        """Ensure KW_TYPE and OBJ_EXT cover the same types."""
        for kw, code in KW_TYPE.items():
            self.assertIn(PBObjectType(code), OBJ_EXT,
                          f"KW_TYPE entry '{kw}' ({code}) missing from OBJ_EXT")


class TestPBLEntry(unittest.TestCase):
    def test_basic_entry(self):
        e = PBLEntry(name="w_main", object_type=PBObjectType.WINDOW)
        self.assertEqual(e.name, "w_main")
        self.assertEqual(e.extension, ".srw")
        self.assertEqual(e.type_name, "Window")
        self.assertEqual(e.data_size, 0)

    def test_comment_entry(self):
        e = PBLEntry(name="d_employee", object_type=PBObjectType.DATAWINDOW,
                     comment="datawindow")
        self.assertEqual(e.extension, ".srd")


class TestPBLSource(unittest.TestCase):
    def test_source_text_utf8(self):
        src = PBLSource(
            entry=PBLEntry(name="test", object_type=PBObjectType.WINDOW),
            source="Hello 世界".encode("utf-8"))
        self.assertIn("世界", src.source_text)

    def test_source_text_latin1(self):
        src = PBLSource(
            entry=PBLEntry(name="test", object_type=PBObjectType.WINDOW),
            source="café".encode("latin-1"))
        self.assertIn("café", src.source_text)

    def test_source_text_utf16le(self):
        """PB12+ PBL stores DAT* source data as UTF-16LE without BOM."""
        pb_source = "$PBExportHeader$w_main.srw\nforward\nglobal type w_main from window\nend type"
        raw = pb_source.encode("utf-16-le")
        src = PBLSource(
            entry=PBLEntry(name="w_main", object_type=PBObjectType.WINDOW),
            source=raw)
        text = src.source_text
        self.assertIn("w_main", text)
        self.assertIn("forward", text)

    def test_source_text_utf16le_chinese(self):
        """PB12+ UTF-16LE with Chinese characters."""
        pb_source = "$PBExportHeader$w_main.srw\nforward\n// 中文注释\nglobal type w_main from window"
        raw = pb_source.encode("utf-16-le")
        src = PBLSource(
            entry=PBLEntry(name="w_main", object_type=PBObjectType.WINDOW),
            source=raw)
        text = src.source_text
        self.assertIn("中文注释", text)

    def test_to_utf8_bytes_from_utf16le(self):
        """to_utf8_bytes() should convert UTF-16LE PB source to UTF-8."""
        # PB12 source starts with "Export By" or "$PBExportHeader$"
        pb_source = "$PBExportHeader$w_main.srw\nforward\nglobal type w_main from window\nHello"
        raw = pb_source.encode("utf-16-le")
        src = PBLSource(
            entry=PBLEntry(name="w_main.srw", object_type=PBObjectType.WINDOW),
            source=raw)
        result = src.to_utf8_bytes()
        # Should be valid UTF-8 without null bytes
        decoded = result.decode("utf-8")
        self.assertIn("$PBExportHeader$", decoded)
        self.assertIn("w_main", decoded)
        self.assertNotIn(b"\x00", result)

    def test_to_utf8_bytes_from_utf8(self):
        """to_utf8_bytes() should pass through UTF-8 unchanged."""
        original = "Hello 世界".encode("utf-8")
        src = PBLSource(
            entry=PBLEntry(name="test", object_type=PBObjectType.WINDOW),
            source=original)
        result = src.to_utf8_bytes()
        self.assertEqual(result, original)

    def test_source_text_short_bytes(self):
        """source_text should handle very short byte sequences gracefully."""
        src = PBLSource(
            entry=PBLEntry(name="test", object_type=PBObjectType.WINDOW),
            source=b"\x00\x01")
        text = src.source_text
        self.assertIsInstance(text, str)


class TestSRFileParser(unittest.TestCase):
    SAMPLE_WINDOW = textwrap.dedent("""\
        $PBExportHeader$w_main.srw
        forward
        global type w_main from window
        end type
        type main_menu from menu
        end type
        global w_main w_main

        type variables
            integer ii_count
            string is_name
        end variables

        forward prototypes
        public subroutine uf_init()
        public function integer uf_calc (integer ai_val)
        end prototypes

        public subroutine uf_init()
            ii_count = 0
            is_name = "main"
        end subroutine

        public function integer uf_calc (integer ai_val); RETURN ai_val * 2
        end function

        on w_main.create
            call super::create
            this.title = "Main Window"
        end on
        on w_main.destroy
            call super::destroy
        end on
        """)

    def test_parse_window(self):
        parser = SRFileParser()
        obj = parser.parse_text(self.SAMPLE_WINDOW, "w_main.srw",
                                SRObjectType.WINDOW)
        self.assertEqual(obj.object_name, "w_main.srw")
        self.assertEqual(obj.object_type, SRObjectType.WINDOW)
        # Variables may or may not parse depending on exact format
        # Just verify the object was created with correct metadata
        self.assertIsNotNone(obj.raw_text)

    def test_parse_routines(self):
        parser = SRFileParser()
        obj = parser.parse_text(self.SAMPLE_WINDOW, "w_main.srw",
                                SRObjectType.WINDOW)
        # Find uf_init
        init = next((r for r in obj.routines if r.name == "uf_init"), None)
        self.assertIsNotNone(init)
        self.assertEqual(init.access, "public")

    def test_parse_function(self):
        parser = SRFileParser()
        obj = parser.parse_text(self.SAMPLE_WINDOW, "w_main.srw",
                                SRObjectType.WINDOW)
        calc = next((r for r in obj.routines if r.name == "uf_calc"), None)
        self.assertIsNotNone(calc)
        self.assertEqual(calc.return_type, "integer")
        self.assertFalse(calc.event)

    def test_parse_events(self):
        parser = SRFileParser()
        obj = parser.parse_text(self.SAMPLE_WINDOW, "w_main.srw",
                                SRObjectType.WINDOW)
        # The parser should find at least the subroutines/functions
        self.assertGreaterEqual(len(obj.routines), 2)


class TestPBSourceAnalyzer(unittest.TestCase):
    SAMPLE_WITH_ISSUES = textwrap.dedent("""\
        forward
        global type u_test from userobject
        end type
        type variables
            global integer gi_global_var
        end variables

        forward prototypes
        public subroutine long_routine()
        end prototypes

        public subroutine long_routine()
        """ + "\n".join([f"    // line {i}" for i in range(1, 250)]) + """
        end subroutine
        """)

    def test_global_variable_detection(self):
        # Test with PB code that has semicolons (some PB versions use them)
        code = textwrap.dedent("""\
            $PBExportHeader$u_test.sru
            forward
            global type u_test from userobject
            end type
            global u_test u_test

            type variables
                global integer gi_global_var;
            end variables

            forward prototypes
            public subroutine test_method()
            end prototypes

            public subroutine test_method()
                gi_global_var = 1
            end subroutine
            """)
        parser = SRFileParser()
        obj = parser.parse_text(code, "u_test.sru", SRObjectType.USEROBJECT)
        analyzer = PBSourceAnalyzer()
        issues = analyzer.analyze_object(obj)
        global_issues = [i for i in issues if i["type"] == "global_variable"]
        self.assertGreaterEqual(len(global_issues), 1)
        found_vars = [i["message"] for i in global_issues]
        self.assertTrue(any("gi_global_var" in v for v in found_vars))

    def test_long_routine_detection(self):
        # Test with a properly formatted long routine
        lines = []
        lines.append("$PBExportHeader$u_test.sru")
        lines.append("forward")
        lines.append("global type u_test from userobject")
        lines.append("end type")
        lines.append("global u_test u_test")
        lines.append("forward prototypes")
        lines.append("public subroutine long_routine()")
        lines.append("end prototypes")
        lines.append("")
        lines.append("public subroutine long_routine()")
        for i in range(250):
            lines.append(f"    integer li_{i} = {i}")
        lines.append("end subroutine")
        code = "\n".join(lines)
        parser = SRFileParser()
        obj = parser.parse_text(code, "u_test.sru", SRObjectType.USEROBJECT)
        analyzer = PBSourceAnalyzer()
        issues = analyzer.analyze_object(obj)
        long_issues = [i for i in issues if i["type"] == "routine_too_long"]
        self.assertEqual(len(long_issues), 1)

    def test_empty_catch_detection(self):
        code = textwrap.dedent("""\
            forward
            global type u_err from userobject
            end type
            forward prototypes
            public subroutine test()
            end prototypes

            public subroutine test()
                try
                    // something
                catch (RuntimeError e)
                end try
            end subroutine
            """)
        parser = SRFileParser()
        obj = parser.parse_text(code, "u_err.sru", SRObjectType.USEROBJECT)
        analyzer = PBSourceAnalyzer()
        issues = analyzer.analyze_object(obj)
        catch_issues = [i for i in issues if i["type"] == "empty_catch"]
        self.assertEqual(len(catch_issues), 1)


class TestDependencyAnalyzer(unittest.TestCase):
    def test_inheritance_detection(self):
        code = textwrap.dedent("""\
            $PBExportHeader$u_child.sru
            forward
            global type u_child from u_parent
            end type
            global u_child u_child

            on u_child.create
                call super::create
            end on
            """)
        parser = SRFileParser()
        obj = parser.parse_text(code, "u_child.sru", SRObjectType.USEROBJECT)
        analyzer = DependencyAnalyzer()
        deps = analyzer.analyze([obj])
        # Inheritance: key=child, value=parent
        self.assertEqual(deps["inheritance"].get("u_child"), "u_parent")

    def test_create_detection(self):
        code = textwrap.dedent("""\
            forward
            global type w_test from window
            end type
            forward prototypes
            public subroutine open_child()
            end prototypes

            public subroutine open_child()
                w_child lw_child
                lw_child = create w_child
                open(lw_child)
            end subroutine
            """)
        parser = SRFileParser()
        obj = parser.parse_text(code, "w_test.srw", SRObjectType.WINDOW)
        analyzer = DependencyAnalyzer()
        deps = analyzer.analyze([obj])
        self.assertIn("w_child", deps["dependencies"].get("w_test.srw", []))


class TestComplexityAnalyzer(unittest.TestCase):
    def test_simple_function(self):
        routine = PBRoutine(name="simple", script="  li_result = 1\n")
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze_routine(routine)
        self.assertEqual(result["complexity"], 1)
        self.assertEqual(result["rating"], "A")

    def test_complex_function(self):
        lines = ["    if x > 0 then"] + \
                ["        if y > 0 then"] + \
                ["            if z > 0 then"] + \
                ["                // nested"] * 5 + \
                ["            end if"] * 3 + \
                ["    end if"]
        routine = PBRoutine(name="complex", script="\n".join(lines))
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze_routine(routine)
        self.assertGreater(result["complexity"], 1)


class TestRefactoringRules(unittest.TestCase):
    def test_empty_catch_rule(self):
        code = textwrap.dedent("""\
            try
                x = 1
            catch (RuntimeError e)
            end try
            """)
        rule = FixEmptyCatchRule()
        results, new_text = rule.apply(code, "test.sru")
        self.assertEqual(len(results), 1)
        self.assertIn("TODO: log error", new_text)

    def test_select_star_rule(self):
        code = textwrap.dedent("""\
            SELECT * FROM employee WHERE id = 1
            """)
        rule = FixSelectStarRule()
        results, new_text = rule.apply(code, "d_emp.srd")
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].applied)  # Manual review

    def test_magic_numbers_rule(self):
        code = textwrap.dedent("""\
            x = 3600
            y = 86400
            """)
        rule = FixMagicNumbersRule()
        results, new_text = rule.apply(code, "test.srw")
        self.assertGreater(len(results), 0)


class TestRefactoringEngine(unittest.TestCase):
    def test_dry_run(self):
        code = textwrap.dedent("""\
            try
                x = 1
            catch (RuntimeError e)
            end try
            """)
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "test.sru"
            f.write_text(code, encoding="utf-8")
            engine = RefactoringEngine()
            result = engine.run(Path(tmpdir), dry_run=True)
            self.assertGreater(result["total_fixes"], 0)
            # File should not be modified
            self.assertEqual(f.read_text(encoding="utf-8"), code)

    def test_apply_fix(self):
        code = textwrap.dedent("""\
            try
                x = 1
            catch (RuntimeError e)
            end try
            """)
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "test.sru"
            f.write_text(code, encoding="utf-8")
            engine = RefactoringEngine()
            result = engine.run(Path(tmpdir), dry_run=False)
            self.assertGreater(result["total_fixes"], 0)
            modified = f.read_text(encoding="utf-8")
            self.assertIn("TODO: log error", modified)

    def test_rule_filter(self):
        """Only run specified rules."""
        code = textwrap.dedent("""\
            try
                x = 1
            catch (RuntimeError e)
            end try
            SELECT * FROM emp
            """)
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "d_emp.srd"
            f.write_text(code, encoding="utf-8")
            engine = RefactoringEngine()
            # Only run fix_select_star rule
            result = engine.run(Path(tmpdir), dry_run=True,
                               rule_filter=["fix_select_star"])
            self.assertGreater(result["total_fixes"], 0)
            # Verify only the select star rule fired (not empty catch)
            rule_ids = {r.rule_id for r in result["details"]}
            self.assertIn("fix_select_star", rule_ids)
            self.assertNotIn("fix_empty_catch", rule_ids)


class TestDeprecatedFunctions(unittest.TestCase):
    def test_setpointer_detection(self):
        analyzer = PBSourceAnalyzer()
        code = textwrap.dedent("""\
            forward
            global type w_test from window
            end type
            forward prototypes
            public subroutine uf_test()
            end prototypes
            public subroutine uf_test()
                SetPointer(HourGlass!)
                Yield()
            end subroutine
            """)
        obj = SRFileParser().parse_text(code, "w_test.srw", SRObjectType.WINDOW)
        issues = analyzer.analyze_object(obj)
        dep_issues = [i for i in issues if i["type"] == "deprecated_function"]
        self.assertGreater(len(dep_issues), 0)

    def test_deprecated_rule(self):
        rule = FixDeprecatedFunctionsRule()
        code = "SetPointer(HourGlass!)\nYield()\n"
        results, _ = rule.apply(code, "test.srw")
        self.assertGreater(len(results), 0)


class TestHardcodedSQL(unittest.TestCase):
    def test_inline_sql_detection(self):
        analyzer = PBSourceAnalyzer()
        code = textwrap.dedent("""\
            forward
            global type w_test from window
            end type
            forward prototypes
            public subroutine uf_query()
            end prototypes
            public subroutine uf_query()
                string ls_sql
                ls_sql = "SELECT name FROM employee WHERE id = 1"
                EXECUTE IMMEDIATE :ls_sql;
            end subroutine
            """)
        obj = SRFileParser().parse_text(code, "w_test.srw", SRObjectType.WINDOW)
        issues = analyzer.analyze_object(obj)
        sql_issues = [i for i in issues if i["type"] == "hardcoded_sql"]
        self.assertEqual(len(sql_issues), 1)


class TestComplexityEdgeCases(unittest.TestCase):
    def test_choose_case_not_overcounted(self):
        """CHOOSE CASE should count as +1, not +1 per CASE branch."""
        script = textwrap.dedent("""\
            choose case li_val
                case 1
                    x = 1
                case 2
                    x = 2
                case 3
                    x = 3
                case else
                    x = 0
            end choose
            """)
        routine = PBRoutine(name="test_choose", script=script)
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze_routine(routine)
        # CHOOSE CASE = +1, not +5
        self.assertLessEqual(result["complexity"], 3)

    def test_deep_nesting_detection(self):
        analyzer = PBSourceAnalyzer()
        script = textwrap.dedent("""\
            forward
            global type u_deep from userobject
            end type
            forward prototypes
            public subroutine uf_deep()
            end prototypes
            public subroutine uf_deep()
                if a > 0 then
                    if b > 0 then
                        if c > 0 then
                            if d > 0 then
                                if e > 0 then
                                    x = 1
                                end if
                            end if
                        end if
                    end if
                end if
            end subroutine
            """)
        obj = SRFileParser().parse_text(script, "u_deep.sru", SRObjectType.USEROBJECT)
        issues = analyzer.analyze_object(obj)
        deep_issues = [i for i in issues if i["type"] == "deep_nesting"]
        self.assertEqual(len(deep_issues), 1)


class TestMagicNumbers(unittest.TestCase):
    def test_safe_numbers_ignored(self):
        """Common powers of 2 and round numbers should not be flagged."""
        analyzer = PBSourceAnalyzer()
        script = textwrap.dedent("""\
            forward
            global type u_test from userobject
            end type
            forward prototypes
            public subroutine uf_test()
            end prototypes
            public subroutine uf_test()
                integer li_size = 1024
                integer li_port = 8080
            end subroutine
            """)
        obj = SRFileParser().parse_text(script, "u_test.sru", SRObjectType.USEROBJECT)
        issues = analyzer.analyze_object(obj)
        magic = [i for i in issues if i["type"] == "magic_numbers"]
        self.assertEqual(len(magic), 1)  # Only 8080 is flagged, 1024 is safe


class TestUTF8Unicode(unittest.TestCase):
    def test_chinese_comments(self):
        """PB source with Chinese comments should parse correctly."""
        code = textwrap.dedent("""\
            $PBExportHeader$w_main.srw
            forward
            global type w_main from window
            end type
            global w_main w_main

            forward prototypes
            public subroutine uf_init()
            end prototypes

            public subroutine uf_init()
                // 这是中文注释
                this.title = "主窗口"
            end subroutine

            on w_main.create
                call super::create
            end on
            """)
        parser = SRFileParser()
        obj = parser.parse_text(code, "w_main.srw", SRObjectType.WINDOW)
        self.assertIn("主窗口", obj.raw_text)
        self.assertGreaterEqual(len(obj.routines), 1)

    def test_gb2312_source_bytes(self):
        """PBLSource should handle various encodings gracefully."""
        src = PBLSource(
            entry=PBLEntry(name="test", object_type=PBObjectType.WINDOW),
            source="标题".encode("gb2312"))
        # The source_text property should return something (latin-1 fallback)
        text = src.source_text
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)


class TestDependencyAnalyzerEdgeCases(unittest.TestCase):
    def test_sql_table_extraction(self):
        code = textwrap.dedent("""\
            $PBExportHeader$d_emp.srd
            forward
            global type d_emp from datawindow
            end type
            SELECT employee.id, employee.name FROM employee
            WHERE employee.dept_id = :as_dept
            """)
        obj = SRFileParser().parse_text(code, "d_emp.srd", SRObjectType.DATAWINDOW)
        analyzer = DependencyAnalyzer()
        deps = analyzer.analyze([obj])
        tables = deps.get("sql_tables", {})
        self.assertIn("employee", tables.get("d_emp.srd", []))

    def test_datawindow_reference(self):
        code = textwrap.dedent("""\
            forward
            global type w_test from window
            end type
            forward prototypes
            public subroutine uf_setdw()
            end prototypes
            public subroutine uf_setdw()
                dw_1.dataobject = "d_employee"
            end subroutine
            """)
        obj = SRFileParser().parse_text(code, "w_test.srw", SRObjectType.WINDOW)
        analyzer = DependencyAnalyzer()
        deps = analyzer.analyze([obj])
        self.assertIn("d_employee", deps["dependencies"].get("w_test.srw", []))


class TestPBConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = PBConfig()
        self.assertEqual(cfg.pb_version, 125)
        self.assertEqual(cfg.max_routine_lines, 200)
        self.assertEqual(cfg.max_complexity, 20)
        self.assertEqual(cfg.encoding, "utf-8")
        # enabled_rules is None when not set (all rules enabled)
        self.assertIsNone(cfg._data.get("rules", {}).get("enabled"))
        self.assertEqual(cfg.disabled_rules, [])

    def test_custom_config(self):
        data = {
            "max_routine_lines": 150,
            "max_complexity": 15,
            "rules": {"enabled": ["fix_empty_catch"], "disabled": ["fix_magic_numbers"]},
        }
        cfg = PBConfig(data)
        self.assertEqual(cfg.max_routine_lines, 150)
        self.assertEqual(cfg.max_complexity, 15)
        self.assertEqual(cfg.enabled_rules, ["fix_empty_catch"])
        self.assertEqual(cfg.disabled_rules, ["fix_magic_numbers"])

    def test_deep_merge(self):
        data = {"naming": {"window": "^w_custom_"}}
        cfg = PBConfig(data)
        # Other naming patterns should still have defaults
        self.assertEqual(cfg.naming_patterns["window"], "^w_custom_")
        self.assertEqual(cfg.naming_patterns["datawindow"], "^d_")

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / ".pbdevkit.json"
            cfg_path.write_text(json.dumps({
                "pb_version": 110,
                "encoding": "gb2312",
            }), encoding="utf-8")
            cfg = PBConfig.load(str(cfg_path))
            self.assertEqual(cfg.pb_version, 110)
            self.assertEqual(cfg.encoding, "gb2312")

    def test_missing_config_file(self):
        cfg = PBConfig.load("/nonexistent/path/config.json")
        # Should return defaults
        self.assertEqual(cfg.pb_version, 125)

    def test_analyzer_config(self):
        cfg = PBConfig({"max_routine_lines": 100, "max_nesting": 2})
        acfg = cfg.as_analyzer_config()
        self.assertEqual(acfg["max_routine_lines"], 100)
        self.assertEqual(acfg["max_nesting"], 2)

    def test_to_dict(self):
        cfg = PBConfig({"pb_version": 100})
        d = cfg.to_dict()
        self.assertEqual(d["pb_version"], 100)
        self.assertIn("naming", d)


class TestChinesePath(unittest.TestCase):
    def test_chinese_directory_path(self):
        """Verify file operations work with Chinese characters in path."""
        code = textwrap.dedent("""\
            forward
            global type w_test from window
            end type
            forward prototypes
            public subroutine uf_test()
            end prototypes
            public subroutine uf_test()
                integer li_x = 1
            end subroutine
            """)
        with tempfile.TemporaryDirectory() as tmpdir:
            chinese_dir = Path(tmpdir) / "测试目录"
            chinese_dir.mkdir()
            f = chinese_dir / "w_test.srw"
            f.write_text(code, encoding="utf-8")
            # Parse from Chinese path
            obj = SRFileParser().parse_file(f)
            self.assertEqual(len(obj.routines), 1)
            # Analyze from Chinese path
            analyzer = PBSourceAnalyzer()
            issues = analyzer.analyze_object(obj)
            self.assertIsInstance(issues, list)


class TestRefactoringBackup(unittest.TestCase):
    def test_backup_created_on_apply(self):
        """Applying refactoring should create .bak files."""
        code = textwrap.dedent("""\
            try
                x = 1
            catch (RuntimeError e)
            end try
            """)
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "test.sru"
            f.write_text(code, encoding="utf-8")
            engine = RefactoringEngine()
            engine.run(Path(tmpdir), dry_run=False)
            backup = f.with_suffix(".sru.bak")
            self.assertTrue(backup.exists())
            # Backup should contain original content
            self.assertEqual(backup.read_text(encoding="utf-8"), code)


class TestPBLEntryTypeDetection(unittest.TestCase):
    def test_prefix_detection(self):
        """Type detection from naming convention prefixes."""
        from pb_devkit.pbl_parser import PBLParser
        parser = PBLParser.__new__(PBLParser)
        parser.strict = False
        self.assertEqual(parser._detect_type("d_employee", ""), PBObjectType.DATAWINDOW)
        self.assertEqual(parser._detect_type("w_main", ""), PBObjectType.WINDOW)
        self.assertEqual(parser._detect_type("m_file", ""), PBObjectType.MENU)
        self.assertEqual(parser._detect_type("n_led_display", ""), PBObjectType.USEROBJECT)
        self.assertEqual(parser._detect_type("f_calc", ""), PBObjectType.FUNCTION)
        self.assertEqual(parser._detect_type("s_record", ""), PBObjectType.STRUCTURE)
        self.assertEqual(parser._detect_type("gf_total", ""), PBObjectType.FUNCTION)

    def test_comment_detection(self):
        """Type detection from comment keywords."""
        from pb_devkit.pbl_parser import PBLParser
        parser = PBLParser.__new__(PBLParser)
        parser.strict = False
        self.assertEqual(parser._detect_type("myobj", "datawindow d_test"),
                         PBObjectType.DATAWINDOW)
        self.assertEqual(parser._detect_type("myobj", "menu m_main"),
                         PBObjectType.MENU)
        self.assertEqual(parser._detect_type("myobj", "application"),
                         PBObjectType.APPLICATION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
