"""Tests for blueprint.core.graph."""

from __future__ import annotations

import pytest

from src.core.graph import KnowledgeGraph
from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    Metrics,
    RelationType,
)


@pytest.fixture
def graph() -> KnowledgeGraph:
    """Create an empty knowledge graph."""
    return KnowledgeGraph()


@pytest.fixture
def populated_graph() -> KnowledgeGraph:
    """Create a graph with sample entities and edges."""
    g = KnowledgeGraph()

    # Entities
    func_a = Entity(
        id="FUNC::app.py::foo",
        type=EntityType.FUNCTION,
        name="foo",
        location=Location(file="app.py", start_line=1, end_line=10),
        language="python",
    )
    func_b = Entity(
        id="FUNC::app.py::bar",
        type=EntityType.FUNCTION,
        name="bar",
        location=Location(file="app.py", start_line=12, end_line=20),
        language="python",
    )
    func_c = Entity(
        id="FUNC::utils.py::baz",
        type=EntityType.FUNCTION,
        name="baz",
        location=Location(file="utils.py", start_line=1, end_line=5),
        language="python",
    )
    class_a = Entity(
        id="CLASS::models.py::User",
        type=EntityType.CLASS,
        name="User",
        location=Location(file="models.py", start_line=1, end_line=30),
        language="python",
    )
    orphan = Entity(
        id="FUNC::orphan.py::lonely",
        type=EntityType.FUNCTION,
        name="lonely",
        location=Location(file="orphan.py", start_line=1, end_line=3),
        language="python",
    )

    for ent in [func_a, func_b, func_c, class_a, orphan]:
        g.add_entity(ent)

    # Edges: foo -> bar -> baz
    g.add_edge(Edge(
        source="FUNC::app.py::foo",
        target="FUNC::app.py::bar",
        relation=RelationType.CALLS,
    ))
    g.add_edge(Edge(
        source="FUNC::app.py::bar",
        target="FUNC::utils.py::baz",
        relation=RelationType.CALLS,
    ))
    # foo also uses User
    g.add_edge(Edge(
        source="FUNC::app.py::foo",
        target="CLASS::models.py::User",
        relation=RelationType.USES,
    ))

    return g


class TestKnowledgeGraphBasics:
    """Basic graph operations."""

    def test_empty_graph(self, graph):
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_entity(self, graph):
        ent = Entity(
            id="FUNC::a.py::foo",
            type=EntityType.FUNCTION,
            name="foo",
            language="python",
        )
        graph.add_entity(ent)
        assert graph.node_count == 1
        assert graph.get_entity("FUNC::a.py::foo") is not None

    def test_add_edge(self, graph):
        graph.add_edge(Edge(
            source="A",
            target="B",
            relation=RelationType.CALLS,
        ))
        assert graph.edge_count == 1

    def test_get_entity_missing(self, graph):
        assert graph.get_entity("nonexistent") is None


class TestEntityQueries:
    """Entity query methods."""

    def test_get_all_entities(self, populated_graph):
        entities = populated_graph.get_all_entities()
        assert len(entities) == 5

    def test_get_entities_by_type(self, populated_graph):
        funcs = populated_graph.get_entities_by_type("function")
        assert len(funcs) == 4  # foo, bar, baz, lonely

        classes = populated_graph.get_entities_by_type("class")
        assert len(classes) == 1

    def test_get_entities_by_file(self, populated_graph):
        app_entities = populated_graph.get_entities_by_file("app.py")
        assert len(app_entities) == 2  # foo, bar

        utils_entities = populated_graph.get_entities_by_file("utils.py")
        assert len(utils_entities) == 1


class TestRelationshipQueries:
    """Relationship query methods."""

    def test_get_callers(self, populated_graph):
        callers = populated_graph.get_callers("FUNC::app.py::bar")
        assert len(callers) == 1
        assert callers[0].name == "foo"

    def test_get_callees(self, populated_graph):
        callees = populated_graph.get_callees("FUNC::app.py::foo")
        assert len(callees) == 1
        assert callees[0].name == "bar"

    def test_get_callers_none(self, populated_graph):
        callers = populated_graph.get_callers("FUNC::app.py::foo")
        assert len(callers) == 0

    def test_get_dependencies(self, populated_graph):
        deps = populated_graph.get_dependencies("FUNC::app.py::foo", depth=1)
        assert len(deps) == 2  # bar, User

    def test_get_dependencies_deep(self, populated_graph):
        deps = populated_graph.get_dependencies("FUNC::app.py::foo", depth=2)
        assert len(deps) == 3  # bar, User, baz

    def test_get_dependents(self, populated_graph):
        dependents = populated_graph.get_dependents("FUNC::utils.py::baz", depth=1)
        assert len(dependents) == 1
        assert dependents[0].name == "bar"


class TestAnalysis:
    """Graph analysis methods."""

    def test_find_orphans(self, populated_graph):
        orphans = populated_graph.find_orphans()
        assert len(orphans) == 1
        assert orphans[0].name == "lonely"

    def test_find_cycles_none(self, populated_graph):
        cycles = populated_graph.find_cycles()
        assert len(cycles) == 0

    def test_find_cycles_present(self, graph):
        # Create A -> B -> A cycle
        graph.add_entity(Entity(
            id="A", type=EntityType.FUNCTION, name="a", language="python",
        ))
        graph.add_entity(Entity(
            id="B", type=EntityType.FUNCTION, name="b", language="python",
        ))
        graph.add_edge(Edge(source="A", target="B", relation=RelationType.CALLS))
        graph.add_edge(Edge(source="B", target="A", relation=RelationType.CALLS))

        cycles = graph.find_cycles()
        assert len(cycles) >= 1

    def test_compute_fan_in_out(self, populated_graph):
        fan = populated_graph.compute_fan_in_out()
        foo_in, foo_out = fan["FUNC::app.py::foo"]
        assert foo_in == 0
        assert foo_out == 1  # calls bar

        bar_in, bar_out = fan["FUNC::app.py::bar"]
        assert bar_in == 1   # called by foo
        assert bar_out == 1  # calls baz


class TestSerialization:
    """Serialization and construction."""

    def test_to_dict(self, populated_graph):
        d = populated_graph.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "stats" in d
        assert d["stats"]["node_count"] == 5
        assert d["stats"]["edge_count"] == 3

    def test_from_entities_and_edges(self):
        entities = [
            Entity(id="A", type=EntityType.FUNCTION, name="a", language="python"),
            Entity(id="B", type=EntityType.FUNCTION, name="b", language="python"),
        ]
        edges = [
            Edge(source="A", target="B", relation=RelationType.CALLS),
        ]
        g = KnowledgeGraph.from_entities_and_edges(entities, edges)
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_merge(self, graph):
        g1 = KnowledgeGraph()
        g1.add_entity(Entity(id="A", type=EntityType.FUNCTION, name="a", language="python"))
        g2 = KnowledgeGraph()
        g2.add_entity(Entity(id="B", type=EntityType.FUNCTION, name="b", language="python"))
        g2.add_edge(Edge(source="A", target="B", relation=RelationType.CALLS))

        g1.merge(g2)
        assert g1.node_count == 2
        assert g1.edge_count == 1
