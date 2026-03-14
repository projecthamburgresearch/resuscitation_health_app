"""Tests for the Sonar domain: naming, complexity, dead code, engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import (
    AnalysisResult, Edge, Entity, EntityType, Location, Metrics, RelationType,
)
from src.sonar.naming import (
    check_naming_conventions, _is_snake_case, _is_pascal_case,
    _is_camel_case, _is_upper_snake,
)
from src.sonar.complexity import check_complexity, DEFAULT_THRESHOLDS
from src.sonar.dead_code import check_dead_code
from src.sonar.schema import FindingCategory, FindingLevel
from src.sonar.engine import SonarEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def python_entities():
    """Entities with Python naming conventions -- some good, some bad."""
    return [
        Entity(id="CLASS::a.py::MyClass", type=EntityType.CLASS,
               name="MyClass", location=Location(file="a.py", start_line=1),
               language="python"),
        Entity(id="CLASS::a.py::bad_class", type=EntityType.CLASS,
               name="bad_class", location=Location(file="a.py", start_line=10),
               language="python"),
        Entity(id="FUNC::a.py::good_func", type=EntityType.FUNCTION,
               name="good_func", location=Location(file="a.py", start_line=20),
               language="python"),
        Entity(id="FUNC::a.py::BadFunc", type=EntityType.FUNCTION,
               name="BadFunc", location=Location(file="a.py", start_line=30),
               language="python"),
        Entity(id="METHOD::a.py::__init__", type=EntityType.METHOD,
               name="__init__", location=Location(file="a.py", start_line=40),
               language="python"),
        Entity(id="CONST::a.py::MAX_SIZE", type=EntityType.CONSTANT,
               name="MAX_SIZE", location=Location(file="a.py", start_line=50),
               language="python"),
        Entity(id="CONST::a.py::badConst", type=EntityType.CONSTANT,
               name="badConst", location=Location(file="a.py", start_line=55),
               language="python"),
    ]


@pytest.fixture
def java_entities():
    """Entities with Java naming conventions."""
    return [
        Entity(id="CLASS::A.java::MyService", type=EntityType.CLASS,
               name="MyService", location=Location(file="A.java", start_line=1),
               language="java"),
        Entity(id="CLASS::A.java::bad_service", type=EntityType.CLASS,
               name="bad_service", location=Location(file="A.java", start_line=10),
               language="java"),
        Entity(id="METHOD::A.java::processData", type=EntityType.METHOD,
               name="processData", location=Location(file="A.java", start_line=20),
               language="java"),
        Entity(id="METHOD::A.java::ProcessData", type=EntityType.METHOD,
               name="ProcessData", location=Location(file="A.java", start_line=30),
               language="java"),
    ]


@pytest.fixture
def complex_entities():
    """Entities with various complexity metrics."""
    return [
        # High cyclomatic complexity (error)
        Entity(id="FUNC::x.py::complex_fn", type=EntityType.FUNCTION,
               name="complex_fn", location=Location(file="x.py", start_line=1),
               language="python",
               metrics=Metrics(cyclomatic_complexity=25, loc_total=100)),
        # Medium cyclomatic complexity (warning)
        Entity(id="FUNC::x.py::moderate_fn", type=EntityType.FUNCTION,
               name="moderate_fn", location=Location(file="x.py", start_line=50),
               language="python",
               metrics=Metrics(cyclomatic_complexity=15, loc_total=40)),
        # Low complexity - no finding
        Entity(id="FUNC::x.py::simple_fn", type=EntityType.FUNCTION,
               name="simple_fn", location=Location(file="x.py", start_line=100),
               language="python",
               metrics=Metrics(cyclomatic_complexity=3, loc_total=10)),
        # High LOC (error)
        Entity(id="FUNC::x.py::huge_fn", type=EntityType.FUNCTION,
               name="huge_fn", location=Location(file="x.py", start_line=200),
               language="python",
               metrics=Metrics(cyclomatic_complexity=5, loc_total=250)),
        # High nesting (warning)
        Entity(id="FUNC::x.py::nested_fn", type=EntityType.FUNCTION,
               name="nested_fn", location=Location(file="x.py", start_line=300),
               language="python",
               metrics=Metrics(nesting_depth_max=5)),
        # Many parameters (error)
        Entity(id="FUNC::x.py::many_params", type=EntityType.FUNCTION,
               name="many_params", location=Location(file="x.py", start_line=400),
               language="python",
               metrics=Metrics(parameter_count=10)),
        # High fan-out (warning)
        Entity(id="FUNC::x.py::wide_fn", type=EntityType.FUNCTION,
               name="wide_fn", location=Location(file="x.py", start_line=500),
               language="python",
               metrics=Metrics(fan_out=15)),
        # No metrics - should produce no finding
        Entity(id="FUNC::x.py::no_metrics", type=EntityType.FUNCTION,
               name="no_metrics", location=Location(file="x.py", start_line=600),
               language="python"),
    ]


@pytest.fixture
def dead_code_entities():
    """Entities for dead code detection."""
    return [
        # Called function - alive
        Entity(id="FUNC::a.py::called_fn", type=EntityType.FUNCTION,
               name="called_fn", location=Location(file="a.py", start_line=1),
               language="python"),
        # Uncalled function - dead
        Entity(id="FUNC::a.py::orphan_fn", type=EntityType.FUNCTION,
               name="orphan_fn", location=Location(file="a.py", start_line=10),
               language="python"),
        # Entry point - not dead
        Entity(id="FUNC::a.py::main", type=EntityType.FUNCTION,
               name="main", location=Location(file="a.py", start_line=20),
               language="python"),
        # Test function - not dead
        Entity(id="FUNC::a.py::test_something", type=EntityType.FUNCTION,
               name="test_something", location=Location(file="a.py", start_line=30),
               language="python"),
        # Dunder - not dead
        Entity(id="METHOD::a.py::__str__", type=EntityType.METHOD,
               name="__str__", location=Location(file="a.py", start_line=40),
               language="python"),
        # Empty class - dead
        Entity(id="CLASS::a.py::EmptyClass", type=EntityType.CLASS,
               name="EmptyClass", location=Location(file="a.py", start_line=50),
               language="python"),
        # Class with members - alive
        Entity(id="CLASS::a.py::GoodClass", type=EntityType.CLASS,
               name="GoodClass", location=Location(file="a.py", start_line=60),
               language="python"),
        Entity(id="METHOD::a.py::GoodClass.method", type=EntityType.METHOD,
               name="method", location=Location(file="a.py", start_line=65),
               language="python"),
        # Unreferenced import
        Entity(id="IMPORT::a.py::os", type=EntityType.IMPORT,
               name="os", location=Location(file="a.py", start_line=1),
               language="python"),
        # Referenced import
        Entity(id="IMPORT::a.py::sys", type=EntityType.IMPORT,
               name="sys", location=Location(file="a.py", start_line=2),
               language="python"),
    ]


@pytest.fixture
def dead_code_edges():
    """Edges for dead code detection."""
    return [
        # main calls called_fn
        Edge(source="FUNC::a.py::main",
             target="FUNC::a.py::called_fn",
             relation=RelationType.CALLS),
        # GoodClass contains method
        Edge(source="CLASS::a.py::GoodClass",
             target="METHOD::a.py::GoodClass.method",
             relation=RelationType.CONTAINS),
        # sys is imported by something
        Edge(source="FILE::a.py",
             target="IMPORT::a.py::sys",
             relation=RelationType.IMPORTS),
    ]


@pytest.fixture
def sample_xray():
    """A basic X-Ray result for the engine tests."""
    entities = [
        Entity(id="FUNC::a.py::foo", type=EntityType.FUNCTION,
               name="foo", location=Location(file="a.py", start_line=1),
               language="python",
               metrics=Metrics(cyclomatic_complexity=5)),
        Entity(id="FUNC::a.py::bar", type=EntityType.FUNCTION,
               name="bar", location=Location(file="a.py", start_line=20),
               language="python",
               metrics=Metrics(cyclomatic_complexity=15)),
        Entity(id="CLASS::a.py::MyClass", type=EntityType.CLASS,
               name="MyClass", location=Location(file="a.py", start_line=40),
               language="python"),
    ]
    edges = [
        Edge(source="FUNC::a.py::foo",
             target="FUNC::a.py::bar",
             relation=RelationType.CALLS),
    ]
    return AnalysisResult(
        domain="xray", version="2.0.0", root_path=".",
        entities=entities, edges=edges,
    )


# ------------------------------------------------------------------
# Naming helpers
# ------------------------------------------------------------------

class TestNamingHelpers:
    def test_snake_case_valid(self):
        assert _is_snake_case("foo_bar")
        assert _is_snake_case("x")
        assert _is_snake_case("my_func")

    def test_snake_case_invalid(self):
        assert not _is_snake_case("FooBar")
        assert not _is_snake_case("fooBar")
        assert not _is_snake_case("FOO_BAR")
        assert not _is_snake_case("_leading")

    def test_pascal_case_valid(self):
        assert _is_pascal_case("FooBar")
        assert _is_pascal_case("MyClass")
        assert _is_pascal_case("X")

    def test_pascal_case_invalid(self):
        assert not _is_pascal_case("fooBar")
        assert not _is_pascal_case("foo_bar")
        assert not _is_pascal_case("FOO_BAR")

    def test_camel_case_valid(self):
        assert _is_camel_case("fooBar")
        assert _is_camel_case("myFunc")
        assert _is_camel_case("x")

    def test_camel_case_invalid(self):
        assert not _is_camel_case("FooBar")
        assert not _is_camel_case("foo_bar")

    def test_upper_snake_valid(self):
        assert _is_upper_snake("FOO_BAR")
        assert _is_upper_snake("MAX_SIZE")
        assert _is_upper_snake("X")

    def test_upper_snake_invalid(self):
        assert not _is_upper_snake("foo_bar")
        assert not _is_upper_snake("FooBar")


# ------------------------------------------------------------------
# Naming conventions
# ------------------------------------------------------------------

class TestNamingConventions:
    def test_python_class_pascal_ok(self, python_entities):
        findings = check_naming_conventions(python_entities)
        # MyClass is PascalCase - should not appear
        messages = [f.message for f in findings]
        assert not any("MyClass" in m and "PascalCase" in m for m in messages)

    def test_python_class_bad_casing(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert any("bad_class" in f.message and "PascalCase" in f.message
                    for f in findings)

    def test_python_func_snake_ok(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert not any("good_func" in f.message for f in findings)

    def test_python_func_bad_casing(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert any("BadFunc" in f.message and "snake_case" in f.message
                    for f in findings)

    def test_dunder_not_flagged(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert not any("__init__" in f.message for f in findings)

    def test_python_constant_upper_snake_ok(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert not any("MAX_SIZE" in f.message for f in findings)

    def test_python_constant_bad_casing(self, python_entities):
        findings = check_naming_conventions(python_entities)
        assert any("badConst" in f.message for f in findings)

    def test_java_class_bad_casing(self, java_entities):
        findings = check_naming_conventions(java_entities)
        assert any("bad_service" in f.message and "PascalCase" in f.message
                    for f in findings)

    def test_java_method_camel_ok(self, java_entities):
        findings = check_naming_conventions(java_entities)
        assert not any("processData" in f.message for f in findings)

    def test_java_method_bad_casing(self, java_entities):
        findings = check_naming_conventions(java_entities)
        assert any("ProcessData" in f.message and "camelCase" in f.message
                    for f in findings)

    def test_single_char_name_flagged(self):
        entities = [
            Entity(id="FUNC::a.py::a", type=EntityType.FUNCTION,
                   name="a", location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        findings = check_naming_conventions(entities)
        assert any("Single-character" in f.message for f in findings)

    def test_loop_var_not_flagged(self):
        entities = [
            Entity(id="VAR::a.py::i", type=EntityType.VARIABLE,
                   name="i", location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        findings = check_naming_conventions(entities)
        assert not any("Single-character" in f.message for f in findings)

    def test_reserved_word_flagged(self):
        entities = [
            Entity(id="FUNC::a.py::class", type=EntityType.FUNCTION,
                   name="class", location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        findings = check_naming_conventions(entities)
        assert any("reserved word" in f.message for f in findings)
        assert any(f.level == FindingLevel.ERROR for f in findings)

    def test_long_name_flagged(self):
        long_name = "a" * 55
        entities = [
            Entity(id=f"FUNC::a.py::{long_name}", type=EntityType.FUNCTION,
                   name=long_name, location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        findings = check_naming_conventions(entities)
        assert any("exceeds" in f.message for f in findings)

    def test_file_entities_skipped(self):
        entities = [
            Entity(id="FILE::a.py", type=EntityType.FILE,
                   name="a.py", location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        findings = check_naming_conventions(entities)
        assert len(findings) == 0

    def test_empty_entities_no_crash(self):
        findings = check_naming_conventions([])
        assert findings == []


# ------------------------------------------------------------------
# Complexity
# ------------------------------------------------------------------

class TestComplexity:
    def test_high_cc_error(self, complex_entities):
        findings = check_complexity(complex_entities)
        errors = [f for f in findings
                  if f.entity_id == "FUNC::x.py::complex_fn"
                  and f.level == FindingLevel.ERROR]
        assert len(errors) >= 1

    def test_medium_cc_warning(self, complex_entities):
        findings = check_complexity(complex_entities)
        warnings = [f for f in findings
                    if f.entity_id == "FUNC::x.py::moderate_fn"
                    and f.level == FindingLevel.WARNING
                    and "complexity" in f.message.lower()]
        assert len(warnings) >= 1

    def test_low_cc_no_finding(self, complex_entities):
        findings = check_complexity(complex_entities)
        simple = [f for f in findings
                  if f.entity_id == "FUNC::x.py::simple_fn"
                  and "complexity" in f.message.lower()]
        assert len(simple) == 0

    def test_high_loc_error(self, complex_entities):
        findings = check_complexity(complex_entities)
        loc_errs = [f for f in findings
                    if f.entity_id == "FUNC::x.py::huge_fn"
                    and f.level == FindingLevel.ERROR
                    and "lines" in f.message.lower()]
        assert len(loc_errs) >= 1

    def test_high_nesting_warning(self, complex_entities):
        findings = check_complexity(complex_entities)
        nesting = [f for f in findings
                   if f.entity_id == "FUNC::x.py::nested_fn"
                   and "nesting" in f.message.lower()]
        assert len(nesting) >= 1

    def test_many_params_error(self, complex_entities):
        findings = check_complexity(complex_entities)
        params = [f for f in findings
                  if f.entity_id == "FUNC::x.py::many_params"
                  and "parameter" in f.message.lower()
                  and f.level == FindingLevel.ERROR]
        assert len(params) >= 1

    def test_high_fan_out_warning(self, complex_entities):
        findings = check_complexity(complex_entities)
        fo = [f for f in findings
              if f.entity_id == "FUNC::x.py::wide_fn"
              and "fan-out" in f.message.lower()]
        assert len(fo) >= 1

    def test_no_metrics_skipped(self, complex_entities):
        findings = check_complexity(complex_entities)
        no_m = [f for f in findings
                if f.entity_id == "FUNC::x.py::no_metrics"]
        assert len(no_m) == 0

    def test_custom_thresholds(self):
        entities = [
            Entity(id="FUNC::x.py::fn", type=EntityType.FUNCTION,
                   name="fn", location=Location(file="x.py", start_line=1),
                   language="python",
                   metrics=Metrics(cyclomatic_complexity=6)),
        ]
        # Default threshold warning=10 -- no finding
        default_findings = check_complexity(entities)
        assert len([f for f in default_findings
                    if "complexity" in f.message.lower()]) == 0

        # Lower threshold to 5 -- should produce warning
        custom = {"cyclomatic_complexity": {"warning": 5, "error": 15}}
        custom_findings = check_complexity(entities, thresholds=custom)
        assert len([f for f in custom_findings
                    if "complexity" in f.message.lower()]) >= 1

    def test_empty_entities_no_crash(self):
        findings = check_complexity([])
        assert findings == []


# ------------------------------------------------------------------
# Dead code
# ------------------------------------------------------------------

class TestDeadCode:
    def test_uncalled_function_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        orphan = [f for f in findings
                  if f.entity_id == "FUNC::a.py::orphan_fn"
                  and f.category == FindingCategory.DEAD_CODE]
        assert len(orphan) == 1

    def test_called_function_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        called = [f for f in findings
                  if f.entity_id == "FUNC::a.py::called_fn"]
        assert len(called) == 0

    def test_entry_point_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        main = [f for f in findings
                if f.entity_id == "FUNC::a.py::main"]
        assert len(main) == 0

    def test_test_function_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        test = [f for f in findings
                if f.entity_id == "FUNC::a.py::test_something"]
        assert len(test) == 0

    def test_dunder_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        dunder = [f for f in findings
                  if f.entity_id == "METHOD::a.py::__str__"]
        assert len(dunder) == 0

    def test_empty_class_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        empty = [f for f in findings
                 if f.entity_id == "CLASS::a.py::EmptyClass"
                 and f.category == FindingCategory.DEAD_CODE]
        assert len(empty) == 1

    def test_class_with_members_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        good = [f for f in findings
                if f.entity_id == "CLASS::a.py::GoodClass"]
        assert len(good) == 0

    def test_unreferenced_import_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        unused = [f for f in findings
                  if f.entity_id == "IMPORT::a.py::os"
                  and f.category == FindingCategory.DEAD_CODE]
        assert len(unused) == 1

    def test_referenced_import_not_flagged(self, dead_code_entities, dead_code_edges):
        findings = check_dead_code(dead_code_entities, dead_code_edges)
        used = [f for f in findings
                if f.entity_id == "IMPORT::a.py::sys"]
        assert len(used) == 0

    def test_decorator_entry_point(self):
        entities = [
            Entity(id="FUNC::a.py::get_users", type=EntityType.FUNCTION,
                   name="get_users", location=Location(file="a.py", start_line=1),
                   language="python",
                   decorators=["@app.route('/users')"]),
        ]
        findings = check_dead_code(entities, [])
        assert not any(f.entity_id == "FUNC::a.py::get_users" for f in findings)

    def test_empty_inputs_no_crash(self):
        findings = check_dead_code([], [])
        assert findings == []


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------

class TestSonarEngine:
    def test_engine_name_version(self):
        engine = SonarEngine()
        assert engine.name() == "sonar"
        assert engine.version() == "0.2.0"

    def test_engine_without_xray(self):
        engine = SonarEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config)
        assert result.domain == "sonar"
        assert len(result.errors) > 0

    def test_engine_with_xray(self, sample_xray):
        engine = SonarEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        assert result.domain == "sonar"
        assert "total_findings" in result.stats
        assert "findings" in result.stats
        assert isinstance(result.stats["findings"], list)

    def test_engine_findings_are_json_safe(self, sample_xray):
        engine = SonarEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        # All findings should be dicts (JSON-safe)
        for f in result.stats.get("findings", []):
            assert isinstance(f, dict)
            assert "finding_id" in f
            assert "category" in f
            assert isinstance(f["category"], str)  # Not enum

    def test_engine_category_counts(self, sample_xray):
        engine = SonarEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        by_cat = result.stats.get("findings_by_category", {})
        assert isinstance(by_cat, dict)

    def test_engine_level_counts(self, sample_xray):
        engine = SonarEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        by_level = result.stats.get("findings_by_level", {})
        assert isinstance(by_level, dict)
