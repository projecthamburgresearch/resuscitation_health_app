"""Tests for the TypeScript parser against the known fixture file."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.models import EntityType, RelationType
from src.xray.parsers.typescript_parser import TypeScriptParser

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def parser() -> TypeScriptParser:
    return TypeScriptParser()


@pytest.fixture
def sample_source() -> str:
    path = FIXTURES_DIR / "typescript_sample.ts"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def parsed(parser, sample_source):
    """Parse the TS fixture and return (entities, edges)."""
    return parser.parse_file("typescript_sample.ts", sample_source)


class TestTypeScriptParserBasics:
    """Basic parser functionality."""

    def test_language_name(self, parser):
        assert parser.language_name() == "typescript"

    def test_file_extensions(self, parser):
        exts = parser.file_extensions()
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".js" in exts
        assert ".jsx" in exts

    def test_empty_source(self, parser):
        entities, edges = parser.parse_file("empty.ts", "")
        assert len(entities) >= 1
        assert entities[0].type == EntityType.FILE

    def test_no_symbols(self, parser, sample_source):
        entities, edges = parser.parse_file(
            "test.ts", sample_source, extract_symbols=False,
        )
        assert len(entities) == 1
        assert entities[0].type == EntityType.FILE


class TestEntityExtraction:
    """Verify all expected entities are extracted."""

    def test_file_entity(self, parsed):
        entities, _ = parsed
        files = [e for e in entities if e.type == EntityType.FILE]
        assert len(files) == 1

    def test_functions_extracted(self, parsed):
        entities, _ = parsed
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        func_names = {f.name for f in funcs}
        assert "greet" in func_names
        assert "calculateTotal" in func_names

    def test_class_extracted(self, parsed):
        entities, _ = parsed
        classes = [e for e in entities if e.type == EntityType.CLASS]
        class_names = {c.name for c in classes}
        assert "UserService" in class_names

    def test_methods_extracted(self, parsed):
        entities, _ = parsed
        methods = [e for e in entities if e.type == EntityType.METHOD]
        method_names = {m.name for m in methods}
        assert "getUser" in method_names
        assert "createUser" in method_names
        assert "listUsers" in method_names

    def test_interface_extracted(self, parsed):
        entities, _ = parsed
        interfaces = [e for e in entities if e.type == EntityType.INTERFACE]
        names = {i.name for i in interfaces}
        assert "User" in names

    def test_enum_extracted(self, parsed):
        entities, _ = parsed
        enums = [e for e in entities if e.type == EntityType.ENUM]
        names = {e.name for e in enums}
        assert "Role" in names

    def test_imports_extracted(self, parsed):
        entities, _ = parsed
        imports = [e for e in entities if e.type == EntityType.IMPORT]
        assert len(imports) >= 1


class TestEntityDetails:
    """Verify entity details are correct."""

    def _find(self, entities, name, etype=None):
        for e in entities:
            if e.name == name and (etype is None or e.type == etype):
                return e
        return None

    def test_function_signature(self, parsed):
        entities, _ = parsed
        greet = self._find(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert greet.signature is not None
        assert "greet" in greet.signature

    def test_arrow_function_marked(self, parsed):
        entities, _ = parsed
        calc = self._find(entities, "calculateTotal", EntityType.FUNCTION)
        assert calc is not None
        assert calc.meta.get("arrow") is True

    def test_method_qualified_name(self, parsed):
        entities, _ = parsed
        get_user = self._find(entities, "getUser", EntityType.METHOD)
        assert get_user is not None
        assert get_user.qualified_name == "UserService.getUser"

    def test_all_entities_have_language(self, parsed):
        entities, _ = parsed
        for ent in entities:
            assert ent.language == "typescript"

    def test_function_has_metrics(self, parsed):
        entities, _ = parsed
        greet = self._find(entities, "greet", EntityType.FUNCTION)
        assert greet is not None
        assert greet.metrics is not None
        assert greet.metrics.cyclomatic_complexity is not None


class TestEdgeExtraction:
    """Verify edges are correctly extracted."""

    def test_calls_edges(self, parsed):
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
        assert len(imports) >= 1


class TestEdgeCases:
    """Edge cases."""

    def test_jsx_file(self, parser):
        source = '''
import React from 'react';

function App(): JSX.Element {
  return <div>Hello</div>;
}

export default App;
'''
        entities, edges = parser.parse_file("App.tsx", source)
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        assert any(f.name == "App" for f in funcs)

    def test_async_function(self, parser):
        source = '''
async function fetchData(url: string): Promise<Response> {
  return await fetch(url);
}
'''
        entities, edges = parser.parse_file("async.ts", source)
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        assert len(funcs) >= 1

    def test_generic_function(self, parser):
        source = '''
function identity<T>(arg: T): T {
  return arg;
}
'''
        entities, edges = parser.parse_file("generic.ts", source)
        funcs = [e for e in entities if e.type == EntityType.FUNCTION]
        assert len(funcs) >= 1
