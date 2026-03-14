"""Tests for the Manifest domain (schema, builder, query, differ)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import (
    AnalysisResult,
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    Metrics,
    RelationType,
)
from src.manifest.schema import (
    Manifest,
    ManifestEntity,
    ManifestRelationship,
    ExecutionSequence,
    ArchitectureGroup,
)
from src.manifest.builder import build_manifest, save_manifest, load_manifest
from src.manifest.query import (
    query_by_name,
    query_by_type,
    query_by_file,
    query_callers,
    query_callees,
    query_complexity_hotspots,
    query_orphans,
    search,
)
from src.manifest.differ import diff_manifests


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_result() -> AnalysisResult:
    """Create a sample AnalysisResult for testing."""
    entities = [
        Entity(
            id="FILE::app.py",
            type=EntityType.FILE,
            name="app.py",
            qualified_name="app.py",
            language="python",
        ),
        Entity(
            id="FUNC::app.py::main",
            type=EntityType.FUNCTION,
            name="main",
            qualified_name="main",
            location=Location(file="app.py", start_line=1, end_line=10),
            language="python",
            signature="def main() -> None",
            metrics=Metrics(cyclomatic_complexity=3, loc_code=10),
        ),
        Entity(
            id="FUNC::app.py::helper",
            type=EntityType.FUNCTION,
            name="helper",
            qualified_name="helper",
            location=Location(file="app.py", start_line=12, end_line=20),
            language="python",
            signature="def helper(x: int) -> str",
            metrics=Metrics(cyclomatic_complexity=1, loc_code=5),
        ),
        Entity(
            id="CLASS::models.py::User",
            type=EntityType.CLASS,
            name="User",
            qualified_name="User",
            location=Location(file="models.py", start_line=1, end_line=30),
            language="python",
            metrics=Metrics(cyclomatic_complexity=8, loc_code=25),
        ),
        Entity(
            id="FUNC::utils.py::orphan_func",
            type=EntityType.FUNCTION,
            name="orphan_func",
            qualified_name="orphan_func",
            location=Location(file="utils.py", start_line=1, end_line=5),
            language="python",
            metrics=Metrics(cyclomatic_complexity=1, loc_code=3),
        ),
    ]
    edges = [
        Edge(
            source="FUNC::app.py::main",
            target="FUNC::app.py::helper",
            relation=RelationType.CALLS,
        ),
        Edge(
            source="FUNC::app.py::main",
            target="CLASS::models.py::User",
            relation=RelationType.USES,
        ),
        Edge(
            source="FILE::app.py",
            target="FUNC::app.py::main",
            relation=RelationType.CONTAINS,
        ),
        Edge(
            source="FILE::app.py",
            target="FUNC::app.py::helper",
            relation=RelationType.CONTAINS,
        ),
    ]
    return AnalysisResult(
        domain="xray",
        version="2.0.0",
        root_path="/project",
        entities=entities,
        edges=edges,
        stats={"files_scanned": 3},
    )


@pytest.fixture
def manifest(sample_result) -> Manifest:
    """Build a manifest from the sample result."""
    return build_manifest(sample_result)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestManifestSchema:
    def test_manifest_entity(self):
        me = ManifestEntity(
            id="FUNC::a.py::foo",
            type="function",
            name="foo",
            calls=["FUNC::a.py::bar"],
        )
        assert me.id == "FUNC::a.py::foo"
        assert len(me.calls) == 1

    def test_manifest_defaults(self):
        m = Manifest(root_path="/test")
        assert m.version == "1.0.0"
        assert len(m.entities) == 0

    def test_manifest_get_entity(self, manifest):
        ent = manifest.get_entity("FUNC::app.py::main")
        assert ent is not None
        assert ent.name == "main"

    def test_manifest_get_callers(self, manifest):
        callers = manifest.get_callers("FUNC::app.py::helper")
        assert "FUNC::app.py::main" in callers


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------

class TestBuilder:
    def test_build_creates_entities(self, manifest):
        assert len(manifest.entities) > 0

    def test_build_creates_relationships(self, manifest):
        assert len(manifest.relationships) > 0

    def test_build_calls_populated(self, manifest):
        main = manifest.get_entity("FUNC::app.py::main")
        assert main is not None
        assert "FUNC::app.py::helper" in main.calls

    def test_build_called_by_populated(self, manifest):
        helper = manifest.get_entity("FUNC::app.py::helper")
        assert helper is not None
        assert "FUNC::app.py::main" in helper.called_by

    def test_build_uses_populated(self, manifest):
        main = manifest.get_entity("FUNC::app.py::main")
        assert main is not None
        assert "CLASS::models.py::User" in main.uses

    def test_build_stats(self, manifest):
        assert "entity_count" in manifest.stats
        assert manifest.stats["entity_count"] == len(manifest.entities)

    def test_build_architecture_groups(self, manifest):
        # Should auto-detect groups from file paths
        # (app.py entities grouped together, etc.)
        assert isinstance(manifest.architecture_groups, list)

    def test_save_yaml(self, manifest, tmp_path):
        path = save_manifest(manifest, tmp_path, fmt="yaml")
        assert path.exists()
        assert path.suffix == ".yaml"

    def test_save_json(self, manifest, tmp_path):
        path = save_manifest(manifest, tmp_path, fmt="json")
        assert path.exists()
        assert path.suffix == ".json"

    def test_save_load_roundtrip_yaml(self, manifest, tmp_path):
        path = save_manifest(manifest, tmp_path, fmt="yaml")
        loaded = load_manifest(path)
        assert len(loaded.entities) == len(manifest.entities)
        assert loaded.root_path == manifest.root_path

    def test_save_load_roundtrip_json(self, manifest, tmp_path):
        path = save_manifest(manifest, tmp_path, fmt="json")
        loaded = load_manifest(path)
        assert len(loaded.entities) == len(manifest.entities)


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------

class TestQuery:
    def test_query_by_name_exact(self, manifest):
        results = query_by_name(manifest, "main", exact=True)
        assert len(results) == 1
        assert results[0].name == "main"

    def test_query_by_name_substring(self, manifest):
        results = query_by_name(manifest, "help")
        assert len(results) >= 1

    def test_query_by_type(self, manifest):
        funcs = query_by_type(manifest, "function")
        assert len(funcs) >= 2

    def test_query_by_file(self, manifest):
        results = query_by_file(manifest, "app.py")
        assert len(results) >= 2

    def test_query_callers(self, manifest):
        callers = query_callers(manifest, "FUNC::app.py::helper")
        assert len(callers) >= 1
        assert callers[0].name == "main"

    def test_query_callees(self, manifest):
        callees = query_callees(manifest, "FUNC::app.py::main")
        assert len(callees) >= 1

    def test_complexity_hotspots(self, manifest):
        hotspots = query_complexity_hotspots(manifest, min_complexity=2)
        assert len(hotspots) >= 1
        # Should be sorted by complexity desc
        for i in range(len(hotspots) - 1):
            assert hotspots[i].complexity >= hotspots[i + 1].complexity

    def test_query_orphans(self, manifest):
        orphans = query_orphans(manifest)
        orphan_names = {o.name for o in orphans}
        assert "orphan_func" in orphan_names

    def test_search_generic(self, manifest):
        results = search(manifest, lambda e: e.language == "python")
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Differ tests
# ---------------------------------------------------------------------------

class TestDiffer:
    def test_no_changes(self, manifest):
        diff = diff_manifests(manifest, manifest)
        assert not diff.has_changes

    def test_added_entity(self, manifest):
        new_manifest = Manifest(
            root_path=manifest.root_path,
            entities=list(manifest.entities) + [
                ManifestEntity(
                    id="FUNC::new.py::new_func",
                    type="function",
                    name="new_func",
                    file="new.py",
                )
            ],
            relationships=list(manifest.relationships),
        )
        diff = diff_manifests(manifest, new_manifest)
        assert len(diff.added) == 1
        assert diff.added[0].entity_name == "new_func"

    def test_removed_entity(self, manifest):
        fewer = Manifest(
            root_path=manifest.root_path,
            entities=manifest.entities[:-1],
            relationships=list(manifest.relationships),
        )
        diff = diff_manifests(manifest, fewer)
        assert len(diff.removed) == 1

    def test_modified_entity(self, manifest):
        # Clone and modify complexity
        modified_entities = []
        for e in manifest.entities:
            if e.name == "main":
                modified = e.model_copy()
                modified.complexity = 99
                modified_entities.append(modified)
            else:
                modified_entities.append(e)

        new_manifest = Manifest(
            root_path=manifest.root_path,
            entities=modified_entities,
            relationships=list(manifest.relationships),
        )
        diff = diff_manifests(manifest, new_manifest)
        assert len(diff.modified) >= 1

    def test_diff_summary(self, manifest):
        diff = diff_manifests(manifest, manifest)
        summary = diff.summary()
        assert summary["total"] == 0
