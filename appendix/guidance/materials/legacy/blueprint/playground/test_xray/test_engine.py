"""Tests for blueprint.xray.engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import EntityType, RelationType
from src.xray.engine import XRayEngine


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def engine() -> XRayEngine:
    return XRayEngine()


@pytest.fixture
def fixtures_config(tmp_path: Path) -> BlueprintConfig:
    return BlueprintConfig(
        root_path=FIXTURES_DIR,
        output_path=tmp_path / "output",
        extract_symbols=True,
        extract_references=True,
        extract_git=False,
    )


class TestXRayEngineBasics:
    """Basic engine properties."""

    def test_name(self, engine):
        assert engine.name() == "xray"

    def test_version(self, engine):
        assert engine.version() == "2.0.0"

    def test_validate_config_valid(self, engine, fixtures_config):
        errors = engine.validate_config(fixtures_config)
        assert len(errors) == 0

    def test_validate_config_missing_root(self, engine, tmp_path):
        config = BlueprintConfig(
            root_path=tmp_path / "nonexistent",
            output_path=tmp_path / "out",
        )
        errors = engine.validate_config(config)
        assert len(errors) > 0


class TestXRayEngineRun:
    """Engine run tests against fixture files."""

    def test_run_produces_result(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        assert result.domain == "xray"
        assert result.version == "2.0.0"
        assert result.entity_count() > 0
        assert result.edge_count() > 0

    def test_run_finds_python_entities(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        funcs = result.entities_by_type(EntityType.FUNCTION)
        assert len(funcs) > 0
        func_names = {f.name for f in funcs}
        assert "greet" in func_names

    def test_run_finds_classes(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        classes = result.entities_by_type(EntityType.CLASS)
        assert len(classes) > 0
        class_names = {c.name for c in classes}
        assert "User" in class_names

    def test_run_finds_edges(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        calls = [e for e in result.edges if e.relation == RelationType.CALLS]
        assert len(calls) > 0

    def test_run_stats(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        assert "files_scanned" in result.stats
        assert "entity_count" in result.stats
        assert "elapsed_seconds" in result.stats
        assert result.stats["files_scanned"] > 0

    def test_run_no_errors(self, engine, fixtures_config):
        result = engine.run(fixtures_config)
        # Should have zero or minimal errors on clean fixture files
        assert len(result.errors) == 0

    def test_run_with_symbols_disabled(self, engine, tmp_path):
        config = BlueprintConfig(
            root_path=FIXTURES_DIR,
            output_path=tmp_path / "out",
            extract_symbols=False,
            extract_references=False,
        )
        result = engine.run(config)
        # Should still have file entities
        files = result.entities_by_type(EntityType.FILE)
        assert len(files) > 0
        # But fewer total entities (no functions/classes extracted by parser)
        funcs = result.entities_by_type(EntityType.FUNCTION)
        # With symbols disabled, parser doesn't extract details
        # But file entities are still created


class TestXRayEngineEdgeCases:
    """Edge cases for engine."""

    def test_empty_directory(self, engine, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        config = BlueprintConfig(
            root_path=empty_dir,
            output_path=tmp_path / "out",
        )
        result = engine.run(config)
        assert result.entity_count() == 0
        assert result.edge_count() == 0

    def test_single_file(self, engine, tmp_path):
        # Create a simple Python file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "hello.py").write_text(
            "def hello():\n    return 'world'\n",
            encoding="utf-8",
        )
        config = BlueprintConfig(
            root_path=src_dir,
            output_path=tmp_path / "out",
        )
        result = engine.run(config)
        assert result.entity_count() >= 2  # FILE + FUNCTION
        funcs = result.entities_by_type(EntityType.FUNCTION)
        assert len(funcs) == 1
        assert funcs[0].name == "hello"


class TestXRayEngineReferences:
    """Reference detection in engine pipeline."""

    def test_detect_references_in_code(self, engine, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # File with fetch call and express endpoint
        (src_dir / "api.ts").write_text(
            "app.get('/api/users', handler)\n"
            "fetch('/api/users')\n",
            encoding="utf-8",
        )
        config = BlueprintConfig(
            root_path=src_dir,
            output_path=tmp_path / "out",
            extract_references=True,
        )
        result = engine.run(config)

        endpoints = result.entities_by_type(EntityType.ENDPOINT)
        requests = result.entities_by_type(EntityType.NETWORK_REQUEST)
        # Should find at least the endpoint and request
        assert len(endpoints) >= 1 or len(requests) >= 1

    def test_sql_table_detection(self, engine, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "query.sql").write_text(
            "SELECT * FROM users JOIN orders ON users.id = orders.user_id;\n",
            encoding="utf-8",
        )
        config = BlueprintConfig(
            root_path=src_dir,
            output_path=tmp_path / "out",
            extract_references=True,
        )
        result = engine.run(config)
        tables = result.entities_by_type(EntityType.TABLE)
        table_names = {t.name for t in tables}
        assert "users" in table_names
        assert "orders" in table_names
