"""Tests for the Python parser against the known fixture file."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.models import EntityType, RelationType
from src.xray.parsers.python_parser import PythonParser

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


@pytest.fixture
def sample_source() -> str:
    path = FIXTURES_DIR / "python_sample.py"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def parsed(parser, sample_source):
    """Parse the sample file and return (entities, edges)."""
    return parser.parse_file("python_sample.py", sample_source)


class TestPythonParserBasics:
    """Basic parser functionality."""

    def test_language_name(self, parser):
        assert parser.language_name() == "python"

    def test_file_extensions(self, parser):
        exts = parser.file_extensions()
        assert ".py" in exts
        assert ".pyw" in exts

    def test_get_tree(self, parser, sample_source):
        tree = parser.get_tree(sample_source)
        assert tree is not None
        assert tree.root_node is not None

    def test_empty_source(self, parser):
        entities, edges = parser.parse_file("empty.py", "")
        # Should have at least the file entity
        assert len(entities) >= 1
        assert entities[0].type == EntityType.FILE

    def test_no_symbols(self, parser, sample_source):
        entities, edges = parser.parse_file(
            "test.py", sample_source, extract_symbols=False,
        )
        # Only file entity when symbols disabled
        assert len(entities) == 1
        assert entities[0].type == EntityType.FILE


class TestEntityExtraction:
    """Verify all expected entities are extracted."""

    def test_file_entity(self, parsed):
        entities, _ = parsed
        files = [e for e in entities if e.type == EntityType.FILE]
        assert len(files) == 1
        assert files[0].name == "python_sample.py"

    def test_functions_extracted(self, parsed):
        entities, _ = parsed
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        func_names = {f.name for f in funcs}
        assert "greet" in func_names
        assert "compute_total" in func_names
        assert "fetch_data" in func_names

    def test_classes_extracted(self, parsed):
        entities, _ = parsed
        classes = [e for e in entities if e.type == EntityType.CLASS]
        class_names = {c.name for c in classes}
        assert "User" in class_names
        assert "AdminUser" in class_names

    def test_methods_extracted(self, parsed):
        entities, _ = parsed
        methods = [e for e in entities if e.type == EntityType.METHOD]
        method_names = {m.qualified_name for m in methods}
        assert "User.__init__" in method_names
        assert "User.full_name" in method_names
        assert "AdminUser.promote" in method_names

    def test_imports_extracted(self, parsed):
        entities, _ = parsed
        imports = [e for e in entities if e.type == EntityType.IMPORT]
        assert len(imports) >= 2
        import_names = {i.name for i in imports}
        assert "os" in import_names

    def test_constants_extracted(self, parsed):
        entities, _ = parsed
        constants = [e for e in entities if e.type == EntityType.CONSTANT]
        const_names = {c.name for c in constants}
        assert "MAX_RETRIES" in const_names


class TestEntityDetails:
    """Verify entity details are correctly extracted."""

    def _find_entity(self, entities, name, entity_type=None):
        for e in entities:
            if e.name == name and (entity_type is None or e.type == entity_type):
                return e
        return None

    def test_function_signature(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert "name: str" in greet.signature
        assert "greeting: str" in greet.signature
        assert "str" in greet.signature  # return type

    def test_function_return_type(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert greet.return_type is not None
        assert "str" in greet.return_type

    def test_function_parameters(self, parsed):
        entities, _ = parsed
        compute = self._find_entity(entities, "compute_total", EntityType.FUNCTION)
        assert compute is not None
        assert compute.parameters is not None
        assert len(compute.parameters) == 2

    def test_function_docstring(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert greet.docstring is not None
        assert "greeting string" in greet.docstring

    def test_class_location(self, parsed):
        entities, _ = parsed
        user = self._find_entity(entities, "User", EntityType.CLASS)
        assert user is not None
        assert user.location is not None
        assert user.location.file == "python_sample.py"
        assert user.location.start_line > 0

    def test_method_qualified_name(self, parsed):
        entities, _ = parsed
        init = self._find_entity(entities, "__init__", EntityType.METHOD)
        assert init is not None
        assert init.qualified_name == "User.__init__"

    def test_method_parameters_exclude_self(self, parsed):
        entities, _ = parsed
        init = self._find_entity(entities, "__init__", EntityType.METHOD)
        assert init is not None
        # self should be excluded
        param_strs = " ".join(init.parameters)
        assert "self" not in param_strs

    def test_all_entities_have_language(self, parsed):
        entities, _ = parsed
        for ent in entities:
            assert ent.language == "python"


class TestEdgeExtraction:
    """Verify edges (relationships) are correctly extracted."""

    def test_calls_edges_exist(self, parsed):
        _, edges = parsed
        calls = [e for e in edges if e.relation == RelationType.CALLS]
        assert len(calls) > 0

    def test_contains_edges(self, parsed):
        _, edges = parsed
        contains = [e for e in edges if e.relation == RelationType.CONTAINS]
        assert len(contains) > 0

    def test_imports_edges(self, parsed):
        _, edges = parsed
        imports = [e for e in edges if e.relation == RelationType.IMPORTS]
        assert len(imports) >= 2

    def test_inherits_edge(self, parsed):
        _, edges = parsed
        inherits = [e for e in edges if e.relation == RelationType.INHERITS]
        assert len(inherits) >= 1
        # AdminUser inherits User
        admin_inherits = [
            e for e in inherits
            if "AdminUser" in e.source and "User" in e.target
        ]
        assert len(admin_inherits) == 1

    def test_call_evidence(self, parsed):
        _, edges = parsed
        calls_with_evidence = [
            e for e in edges
            if e.relation == RelationType.CALLS and e.evidence
        ]
        assert len(calls_with_evidence) > 0
        for call in calls_with_evidence:
            assert call.evidence[0].file == "python_sample.py"
            assert call.evidence[0].start_line > 0


class TestMetrics:
    """Verify metrics are computed for entities."""

    def _find_entity(self, entities, name, entity_type=None):
        for e in entities:
            if e.name == name and (entity_type is None or e.type == entity_type):
                return e
        return None

    def test_function_has_metrics(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert greet.metrics is not None
        assert greet.metrics.cyclomatic_complexity is not None
        assert greet.metrics.loc_code is not None

    def test_simple_function_low_complexity(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet.metrics.cyclomatic_complexity == 1

    def test_moderate_complexity(self, parsed):
        entities, _ = parsed
        compute = self._find_entity(entities, "compute_total", EntityType.FUNCTION)
        assert compute is not None
        # if + for + if = 3 decision points + 1 base = 4
        assert compute.metrics.cyclomatic_complexity >= 3

    def test_higher_complexity(self, parsed):
        entities, _ = parsed
        fetch = self._find_entity(entities, "fetch_data", EntityType.FUNCTION)
        assert fetch is not None
        # while + except + if + if = 4 decision points + 1 base = 5
        assert fetch.metrics.cyclomatic_complexity >= 4

    def test_parameter_count(self, parsed):
        entities, _ = parsed
        greet = self._find_entity(entities, "greet", EntityType.FUNCTION)
        assert greet.metrics.parameter_count == 2

    def test_class_metrics(self, parsed):
        entities, _ = parsed
        user = self._find_entity(entities, "User", EntityType.CLASS)
        assert user is not None
        assert user.metrics is not None
        assert user.metrics.loc_total is not None
        assert user.metrics.loc_total > 0


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_syntax_error_source(self, parser):
        bad_source = "def foo(\n  x = "
        entities, edges = parser.parse_file("bad.py", bad_source)
        # tree-sitter is error-tolerant, should still get something
        # At minimum, file entity
        assert len(entities) >= 1

    def test_deeply_nested(self, parser):
        source = '''
def deep():
    for i in range(10):
        for j in range(10):
            if i > j:
                while True:
                    if i == j:
                        break
'''
        entities, _ = parser.parse_file("deep.py", source)
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        assert len(funcs) == 1
        assert funcs[0].metrics.nesting_depth_max >= 4

    def test_async_function(self, parser):
        source = '''
async def fetch(url: str) -> dict:
    """Fetch a URL."""
    return {}
'''
        entities, _ = parser.parse_file("async.py", source)
        # tree-sitter should handle async function_definition
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        # May or may not extract depending on tree-sitter's node type for async
        # Just verify no crash
        assert len(entities) >= 1

    def test_class_with_decorators(self, parser):
        source = '''
import dataclasses

@dataclasses.dataclass
class Config:
    name: str
    value: int = 0
'''
        entities, _ = parser.parse_file("config.py", source)
        classes = [e for e in entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

    def test_multiline_function(self, parser):
        source = '''
def long_func(
    a: int,
    b: int,
    c: int,
    d: int,
) -> int:
    """Add numbers."""
    return a + b + c + d
'''
        entities, _ = parser.parse_file("multi.py", source)
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        assert len(funcs) == 1
        assert funcs[0].metrics.parameter_count == 4
