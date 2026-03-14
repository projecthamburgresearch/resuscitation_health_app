"""Tests for blueprint.core.models."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.core.models import (
    AnalysisResult,
    Edge,
    Entity,
    EntityType,
    Evidence,
    GitInfo,
    Location,
    Metrics,
    RelationType,
)


class TestEntityType:
    """EntityType enum tests."""

    def test_all_types_are_strings(self):
        for et in EntityType:
            assert isinstance(et.value, str)

    def test_function_type(self):
        assert EntityType.FUNCTION.value == "function"

    def test_class_type(self):
        assert EntityType.CLASS.value == "class"


class TestRelationType:
    """RelationType enum tests."""

    def test_calls_relation(self):
        assert RelationType.CALLS.value == "calls"

    def test_imports_relation(self):
        assert RelationType.IMPORTS.value == "imports"


class TestLocation:
    """Location model tests."""

    def test_basic_location(self):
        loc = Location(file="src/main.py", start_line=10)
        assert loc.file == "src/main.py"
        assert loc.start_line == 10
        assert loc.start_col == 0  # default
        assert loc.end_line == 0    # default

    def test_str_representation(self):
        loc = Location(file="src/main.py", start_line=10)
        assert str(loc) == "src/main.py:10"

    def test_full_location(self):
        loc = Location(file="app.py", start_line=5, start_col=4, end_line=15, end_col=0)
        assert loc.start_col == 4
        assert loc.end_line == 15


class TestMetrics:
    """Metrics model tests."""

    def test_default_metrics(self):
        m = Metrics()
        assert m.cyclomatic_complexity is None
        assert m.fan_in is None

    def test_partial_metrics(self):
        m = Metrics(cyclomatic_complexity=5, loc_code=15)
        assert m.cyclomatic_complexity == 5
        assert m.loc_code == 15
        assert m.cognitive_complexity is None

    def test_full_metrics(self):
        m = Metrics(
            cyclomatic_complexity=5,
            cognitive_complexity=8,
            loc_total=30,
            loc_code=20,
            loc_comment=5,
            loc_blank=5,
            nesting_depth_max=3,
            nesting_depth_avg=1.5,
            fan_in=2,
            fan_out=4,
            parameter_count=3,
            statement_count=12,
        )
        assert m.nesting_depth_avg == 1.5
        assert m.statement_count == 12


class TestGitInfo:
    """GitInfo model tests."""

    def test_git_info(self):
        gi = GitInfo(last_author="alice", change_count=10)
        assert gi.last_author == "alice"
        assert gi.change_count == 10
        assert gi.last_modified is None


class TestEvidence:
    """Evidence model tests."""

    def test_evidence(self):
        ev = Evidence(file="main.py", start_line=10, end_line=10, snippet="x = foo()")
        assert ev.snippet == "x = foo()"

    def test_evidence_default_snippet(self):
        ev = Evidence(file="main.py", start_line=1, end_line=1)
        assert ev.snippet == ""


class TestEntity:
    """Entity model tests."""

    def test_basic_entity(self):
        ent = Entity(
            id="FUNC::app.py::main",
            type=EntityType.FUNCTION,
            name="main",
        )
        assert ent.id == "FUNC::app.py::main"
        assert ent.type == EntityType.FUNCTION
        assert ent.name == "main"
        assert ent.language is None

    def test_entity_equality(self):
        e1 = Entity(id="FUNC::a.py::foo", type=EntityType.FUNCTION, name="foo")
        e2 = Entity(id="FUNC::a.py::foo", type=EntityType.FUNCTION, name="foo")
        e3 = Entity(id="FUNC::a.py::bar", type=EntityType.FUNCTION, name="bar")
        assert e1 == e2
        assert e1 != e3

    def test_entity_hash(self):
        e1 = Entity(id="FUNC::a.py::foo", type=EntityType.FUNCTION, name="foo")
        e2 = Entity(id="FUNC::a.py::foo", type=EntityType.FUNCTION, name="foo")
        assert hash(e1) == hash(e2)
        assert len({e1, e2}) == 1  # Same in a set

    def test_entity_with_all_fields(self):
        ent = Entity(
            id="METHOD::app.py::User.save",
            type=EntityType.METHOD,
            name="save",
            qualified_name="User.save",
            location=Location(file="app.py", start_line=20, end_line=30),
            language="python",
            signature="def save(self) -> None",
            return_type="None",
            parameters=[],
            decorators=["staticmethod"],
            docstring="Save user to db.",
            metrics=Metrics(cyclomatic_complexity=3),
            meta={"async": False},
        )
        assert ent.qualified_name == "User.save"
        assert ent.decorators == ["staticmethod"]
        assert ent.metrics.cyclomatic_complexity == 3


class TestEdge:
    """Edge model tests."""

    def test_basic_edge(self):
        edge = Edge(
            source="FUNC::a.py::foo",
            target="FUNC::a.py::bar",
            relation=RelationType.CALLS,
        )
        assert edge.confidence == 1.0
        assert edge.evidence is None

    def test_edge_with_evidence(self):
        edge = Edge(
            source="FUNC::a.py::foo",
            target="FUNC::b.py::baz",
            relation=RelationType.CALLS,
            confidence=0.8,
            evidence=[Evidence(file="a.py", start_line=10, end_line=10, snippet="baz()")],
        )
        assert len(edge.evidence) == 1
        assert edge.confidence == 0.8


class TestAnalysisResult:
    """AnalysisResult model tests."""

    def test_empty_result(self):
        result = AnalysisResult(domain="xray", version="2.0.0", root_path="/project")
        assert result.entity_count() == 0
        assert result.edge_count() == 0
        assert result.domain == "xray"

    def test_result_with_entities(self, sample_entity, sample_edge):
        result = AnalysisResult(
            domain="xray",
            version="2.0.0",
            root_path="/project",
            entities=[sample_entity],
            edges=[sample_edge],
            stats={"files_scanned": 1},
        )
        assert result.entity_count() == 1
        assert result.edge_count() == 1

    def test_entities_by_type(self, sample_entity):
        result = AnalysisResult(
            domain="xray",
            version="2.0.0",
            root_path="/project",
            entities=[sample_entity],
        )
        funcs = result.entities_by_type(EntityType.FUNCTION)
        assert len(funcs) == 1
        classes = result.entities_by_type(EntityType.CLASS)
        assert len(classes) == 0

    def test_get_entity(self, sample_entity):
        result = AnalysisResult(
            domain="xray",
            version="2.0.0",
            root_path="/project",
            entities=[sample_entity],
        )
        found = result.get_entity(sample_entity.id)
        assert found is not None
        assert found.name == "login"

        missing = result.get_entity("nonexistent")
        assert missing is None

    def test_timestamp_auto_set(self):
        result = AnalysisResult(domain="test", version="1.0", root_path="/")
        assert isinstance(result.timestamp, datetime)

    def test_serialization_roundtrip(self, sample_entity, sample_edge):
        result = AnalysisResult(
            domain="xray",
            version="2.0.0",
            root_path="/project",
            entities=[sample_entity],
            edges=[sample_edge],
        )
        data = result.model_dump()
        restored = AnalysisResult.model_validate(data)
        assert restored.entity_count() == 1
        assert restored.edges[0].relation == RelationType.CALLS
