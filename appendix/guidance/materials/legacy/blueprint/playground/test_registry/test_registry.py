"""Tests for the Registry domain: scanner, partitioner, index, engine."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import (
    AnalysisResult, Edge, Entity, EntityType, Location, RelationType,
)
from src.registry.schema import MasterIndex, ProjectProfile, Zone
from src.registry.scanner import scan_project_profile
from src.registry.partitioner import partition_into_zones, detect_zone_dependencies
from src.registry.index import (
    build_master_index, update_master_index, merge_zone_results,
    save_master_index, load_master_index,
)
from src.registry.engine import RegistryEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def sample_entities():
    return [
        Entity(id="FUNC::src/a.py::foo", type=EntityType.FUNCTION,
               name="foo", location=Location(file="src/a.py", start_line=10),
               language="python"),
        Entity(id="FUNC::src/b.py::bar", type=EntityType.FUNCTION,
               name="bar", location=Location(file="src/b.py", start_line=20),
               language="python"),
        Entity(id="CLASS::lib/c.py::Baz", type=EntityType.CLASS,
               name="Baz", location=Location(file="lib/c.py", start_line=1),
               language="python"),
    ]


@pytest.fixture
def sample_edges():
    return [
        Edge(source="FUNC::src/a.py::foo",
             target="FUNC::src/b.py::bar",
             relation=RelationType.CALLS),
    ]


@pytest.fixture
def sample_xray(sample_entities, sample_edges):
    return AnalysisResult(
        domain="xray", version="2.0.0", root_path=".",
        entities=sample_entities, edges=sample_edges,
    )


@pytest.fixture
def sample_profile():
    return ProjectProfile(
        total_files=100,
        total_size_bytes=500000,
        language_distribution={"python": 60, "typescript": 30, "config": 10},
        largest_files=[("big.py", 50000), ("huge.ts", 40000)],
        estimated_entities=800,
        directory_count=15,
    )


@pytest.fixture
def sample_zones():
    return [
        Zone(zone_id="zone_src", name="src", root_path="src",
             file_paths=["src/a.py", "src/b.py"], file_count=2,
             language="python"),
        Zone(zone_id="zone_lib", name="lib", root_path="lib",
             file_paths=["lib/c.py"], file_count=1,
             language="python"),
    ]


# ------------------------------------------------------------------
# Scanner
# ------------------------------------------------------------------

class TestScanner:
    def test_scan_project_profile(self):
        root = Path(__file__).parent.parent.parent
        config = BlueprintConfig(root_path=root, max_files=50)
        profile = scan_project_profile(root, config)
        assert profile.total_files > 0
        assert profile.total_size_bytes > 0
        assert profile.directory_count > 0
        assert len(profile.language_distribution) > 0

    def test_estimated_entities_positive(self):
        root = Path(__file__).parent.parent.parent
        config = BlueprintConfig(root_path=root, max_files=50)
        profile = scan_project_profile(root, config)
        assert profile.estimated_entities > 0


# ------------------------------------------------------------------
# Partitioner
# ------------------------------------------------------------------

class TestPartitioner:
    def test_partition_creates_zones(self):
        root = Path(__file__).parent.parent.parent
        config = BlueprintConfig(root_path=root, max_files=50)
        profile = scan_project_profile(root, config)
        zones = partition_into_zones(root, profile, config)
        assert len(zones) > 0
        assert all(z.file_count > 0 for z in zones)

    def test_all_files_in_zones(self):
        root = Path(__file__).parent.parent.parent
        config = BlueprintConfig(root_path=root, max_files=50)
        profile = scan_project_profile(root, config)
        zones = partition_into_zones(root, profile, config)
        total_zone_files = sum(z.file_count for z in zones)
        assert total_zone_files == profile.total_files

    def test_detect_zone_dependencies(self, sample_zones, sample_edges):
        updated = detect_zone_dependencies(sample_zones, sample_edges)
        # src/a.py calls src/b.py -> same zone, no cross-zone dep
        # No cross-zone edges in this sample
        assert isinstance(updated, list)


# ------------------------------------------------------------------
# Index
# ------------------------------------------------------------------

class TestIndex:
    def test_build_master_index(self, sample_xray, sample_profile, sample_zones):
        idx = build_master_index(
            "test_project", Path("."), sample_profile,
            sample_zones, sample_xray, "run001",
        )
        assert len(idx.entries) >= 2
        assert idx.project_name == "test_project"
        assert "run001" in idx.run_history

    def test_caller_callee_populated(self, sample_xray, sample_profile, sample_zones):
        idx = build_master_index(
            "test", Path("."), sample_profile,
            sample_zones, sample_xray, "run001",
        )
        foo = idx.entries.get("FUNC::src/a.py::foo")
        bar = idx.entries.get("FUNC::src/b.py::bar")
        assert foo is not None
        assert "FUNC::src/b.py::bar" in foo.callees
        assert bar is not None
        assert "FUNC::src/a.py::foo" in bar.callers

    def test_update_master_index(self, sample_xray, sample_profile, sample_zones):
        idx = build_master_index(
            "test", Path("."), sample_profile,
            sample_zones, sample_xray, "run001",
        )
        new_entities = sample_xray.entities + [
            Entity(id="FUNC::src/d.py::qux", type=EntityType.FUNCTION,
                   name="qux", location=Location(file="src/d.py", start_line=5),
                   language="python"),
        ]
        xray2 = AnalysisResult(
            domain="xray", version="2.0.0", root_path=".",
            entities=new_entities, edges=sample_xray.edges,
        )
        idx2 = update_master_index(idx, xray2, "run002")
        assert len(idx2.entries) >= 3
        assert "run002" in idx2.run_history

    def test_save_load_roundtrip(self, sample_xray, sample_profile, sample_zones):
        idx = build_master_index(
            "test", Path("."), sample_profile,
            sample_zones, sample_xray, "run001",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            save_master_index(idx, path)
            loaded = load_master_index(path)
            assert len(loaded.entries) == len(idx.entries)
            assert loaded.project_name == idx.project_name

    def test_merge_zone_results(self, sample_xray):
        xray2 = AnalysisResult(
            domain="xray", version="2.0.0", root_path=".",
            entities=[
                Entity(id="FUNC::src/a.py::foo", type=EntityType.FUNCTION,
                       name="foo", location=Location(file="src/a.py", start_line=10),
                       language="python"),
                Entity(id="FUNC::new.py::new_func", type=EntityType.FUNCTION,
                       name="new_func", location=Location(file="new.py", start_line=1),
                       language="python"),
            ],
            edges=[],
        )
        merged = merge_zone_results([sample_xray, xray2])
        ids = {e.id for e in merged.entities}
        assert "FUNC::src/a.py::foo" in ids
        assert "FUNC::new.py::new_func" in ids
        # foo should not be duplicated
        foo_count = sum(1 for e in merged.entities if e.id == "FUNC::src/a.py::foo")
        assert foo_count == 1


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------

class TestRegistryEngine:
    def test_engine_name_version(self):
        engine = RegistryEngine()
        assert engine.name() == "registry"
        assert engine.version() == "0.2.0"

    def test_engine_run_without_xray(self):
        engine = RegistryEngine()
        config = BlueprintConfig(root_path=Path(__file__).parent.parent.parent)
        result = engine.run(config)
        assert result.domain == "registry"
        assert "profile" in result.stats

    def test_engine_run_with_xray(self, sample_xray):
        engine = RegistryEngine()
        config = BlueprintConfig(
            root_path=Path(__file__).parent.parent.parent,
            output_path=Path(tempfile.mkdtemp()),
        )
        result = engine.run(config, prior_results=[sample_xray])
        assert result.domain == "registry"
        assert result.stats["zones"]["count"] > 0
