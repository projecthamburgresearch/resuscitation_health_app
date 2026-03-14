"""Tests for the Synapse domain: chains, sequences, hotspots, engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import (
    AnalysisResult, Edge, Entity, EntityType, Location, Metrics, RelationType,
)
from src.synapse.chains import (
    build_adjacency, trace_chain, build_call_graph, build_all_call_graphs,
)
from src.synapse.sequences import (
    detect_entry_points, trace_execution_sequence, trace_all_sequences,
)
from src.synapse.hotspots import detect_hotspots
from src.synapse.schema import ChainDirection, HotspotType
from src.synapse.engine import SynapseEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def chain_entities():
    """Entities forming a call chain: A -> B -> C -> D."""
    return [
        Entity(id="FUNC::a.py::fn_a", type=EntityType.FUNCTION,
               name="fn_a", location=Location(file="a.py", start_line=1),
               language="python"),
        Entity(id="FUNC::b.py::fn_b", type=EntityType.FUNCTION,
               name="fn_b", location=Location(file="b.py", start_line=1),
               language="python"),
        Entity(id="FUNC::c.py::fn_c", type=EntityType.FUNCTION,
               name="fn_c", location=Location(file="c.py", start_line=1),
               language="python"),
        Entity(id="FUNC::d.py::fn_d", type=EntityType.FUNCTION,
               name="fn_d", location=Location(file="d.py", start_line=1),
               language="python"),
    ]


@pytest.fixture
def chain_edges():
    """Edges for A -> B -> C -> D chain."""
    return [
        Edge(source="FUNC::a.py::fn_a", target="FUNC::b.py::fn_b",
             relation=RelationType.CALLS),
        Edge(source="FUNC::b.py::fn_b", target="FUNC::c.py::fn_c",
             relation=RelationType.CALLS),
        Edge(source="FUNC::c.py::fn_c", target="FUNC::d.py::fn_d",
             relation=RelationType.CALLS),
    ]


@pytest.fixture
def fan_entities():
    """Entities for fan-in/fan-out testing.

    hub is called by caller1, caller2, caller3, caller4, caller5
    hub calls callee1, callee2, callee3, callee4, callee5
    """
    entities = [
        Entity(id="FUNC::hub.py::hub", type=EntityType.FUNCTION,
               name="hub", location=Location(file="hub.py", start_line=1),
               language="python"),
    ]
    for i in range(1, 6):
        entities.append(Entity(
            id=f"FUNC::caller{i}.py::caller{i}", type=EntityType.FUNCTION,
            name=f"caller{i}", location=Location(file=f"caller{i}.py", start_line=1),
            language="python",
        ))
        entities.append(Entity(
            id=f"FUNC::callee{i}.py::callee{i}", type=EntityType.FUNCTION,
            name=f"callee{i}", location=Location(file=f"callee{i}.py", start_line=1),
            language="python",
        ))
    return entities


@pytest.fixture
def fan_edges():
    """Edges for fan-in/fan-out testing."""
    edges = []
    for i in range(1, 6):
        edges.append(Edge(
            source=f"FUNC::caller{i}.py::caller{i}",
            target="FUNC::hub.py::hub",
            relation=RelationType.CALLS,
        ))
        edges.append(Edge(
            source="FUNC::hub.py::hub",
            target=f"FUNC::callee{i}.py::callee{i}",
            relation=RelationType.CALLS,
        ))
    return edges


@pytest.fixture
def entry_point_entities():
    """Entities for entry point detection."""
    return [
        Entity(id="FUNC::a.py::main", type=EntityType.FUNCTION,
               name="main", location=Location(file="a.py", start_line=1),
               language="python"),
        Entity(id="FUNC::a.py::test_login", type=EntityType.FUNCTION,
               name="test_login", location=Location(file="a.py", start_line=10),
               language="python"),
        Entity(id="FUNC::a.py::handle_request", type=EntityType.FUNCTION,
               name="handle_request", location=Location(file="a.py", start_line=20),
               language="python",
               decorators=["@app.route('/api')"]),
        Entity(id="FUNC::a.py::helper", type=EntityType.FUNCTION,
               name="helper", location=Location(file="a.py", start_line=30),
               language="python"),
        Entity(id="CLASS::a.py::MyClass", type=EntityType.CLASS,
               name="MyClass", location=Location(file="a.py", start_line=40),
               language="python"),
        Entity(id="FUNC::a.py::setup", type=EntityType.FUNCTION,
               name="setup", location=Location(file="a.py", start_line=50),
               language="python"),
    ]


@pytest.fixture
def sample_xray(chain_entities, chain_edges):
    """A basic X-Ray result for engine tests."""
    return AnalysisResult(
        domain="xray", version="2.0.0", root_path=".",
        entities=chain_entities, edges=chain_edges,
    )


# ------------------------------------------------------------------
# Adjacency / chains
# ------------------------------------------------------------------

class TestAdjacency:
    def test_build_adjacency_maps(self, chain_entities, chain_edges):
        callees_of, callers_of, entity_map = build_adjacency(
            chain_entities, chain_edges,
        )
        assert "FUNC::b.py::fn_b" in callees_of["FUNC::a.py::fn_a"]
        assert "FUNC::a.py::fn_a" in callers_of["FUNC::b.py::fn_b"]
        assert len(entity_map) == 4

    def test_adjacency_empty(self):
        callees_of, callers_of, entity_map = build_adjacency([], [])
        assert callees_of == {}
        assert callers_of == {}
        assert entity_map == {}

    def test_non_calls_edges_ignored(self, chain_entities):
        edges = [
            Edge(source="FUNC::a.py::fn_a", target="FUNC::b.py::fn_b",
                 relation=RelationType.USES),
        ]
        callees_of, callers_of, _ = build_adjacency(chain_entities, edges)
        assert len(callees_of) == 0
        assert len(callers_of) == 0


class TestChains:
    def test_downstream_chain(self, chain_entities, chain_edges):
        callees_of, _, entity_map = build_adjacency(chain_entities, chain_edges)
        chains = trace_chain(
            "FUNC::a.py::fn_a", callees_of, entity_map,
            ChainDirection.DOWNSTREAM, max_depth=10,
        )
        assert len(chains) >= 1
        # The longest chain should reach fn_d
        longest = max(chains, key=lambda c: c.depth)
        assert "FUNC::d.py::fn_d" in longest.chain

    def test_upstream_chain(self, chain_entities, chain_edges):
        _, callers_of, entity_map = build_adjacency(chain_entities, chain_edges)
        chains = trace_chain(
            "FUNC::d.py::fn_d", callers_of, entity_map,
            ChainDirection.UPSTREAM, max_depth=10,
        )
        assert len(chains) >= 1
        longest = max(chains, key=lambda c: c.depth)
        assert "FUNC::a.py::fn_a" in longest.chain

    def test_chain_depth_limit(self, chain_entities, chain_edges):
        callees_of, _, entity_map = build_adjacency(chain_entities, chain_edges)
        chains = trace_chain(
            "FUNC::a.py::fn_a", callees_of, entity_map,
            ChainDirection.DOWNSTREAM, max_depth=1,
        )
        # All chains should have depth <= 1
        assert all(c.depth <= 1 for c in chains)

    def test_chain_names_populated(self, chain_entities, chain_edges):
        callees_of, _, entity_map = build_adjacency(chain_entities, chain_edges)
        chains = trace_chain(
            "FUNC::a.py::fn_a", callees_of, entity_map,
            ChainDirection.DOWNSTREAM, max_depth=10,
        )
        for chain in chains:
            assert len(chain.names) == len(chain.chain)
            assert len(chain.files) == len(chain.chain)

    def test_chain_nonexistent_entity(self, chain_entities, chain_edges):
        callees_of, _, entity_map = build_adjacency(chain_entities, chain_edges)
        chains = trace_chain(
            "FUNC::z.py::nonexistent", callees_of, entity_map,
            ChainDirection.DOWNSTREAM,
        )
        assert chains == []


class TestCallGraph:
    def test_build_call_graph(self, chain_entities, chain_edges):
        graph = build_call_graph(
            "FUNC::b.py::fn_b", chain_entities, chain_edges,
        )
        assert graph.entity_id == "FUNC::b.py::fn_b"
        assert graph.entity_name == "fn_b"
        assert graph.upstream_depth >= 1  # A calls B
        assert graph.downstream_depth >= 1  # B calls C
        assert graph.total_callers >= 1
        assert graph.total_callees >= 1

    def test_build_all_call_graphs(self, chain_entities, chain_edges):
        graphs = build_all_call_graphs(chain_entities, chain_edges)
        # At least some entities should have graphs
        assert len(graphs) >= 1
        # Should be sorted by total connections descending
        if len(graphs) > 1:
            connections = [g.total_callers + g.total_callees for g in graphs]
            assert connections == sorted(connections, reverse=True)

    def test_graph_for_nonexistent_entity(self, chain_entities, chain_edges):
        graph = build_call_graph("nonexistent", chain_entities, chain_edges)
        assert graph.entity_id == "nonexistent"
        assert graph.total_callers == 0
        assert graph.total_callees == 0


# ------------------------------------------------------------------
# Entry points / sequences
# ------------------------------------------------------------------

class TestEntryPoints:
    def test_detect_main(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "FUNC::a.py::main" in ids

    def test_detect_test_function(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "FUNC::a.py::test_login" in ids

    def test_detect_decorated_handler(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "FUNC::a.py::handle_request" in ids

    def test_detect_setup(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "FUNC::a.py::setup" in ids

    def test_helper_not_entry_point(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "FUNC::a.py::helper" not in ids

    def test_class_not_entry_point(self, entry_point_entities):
        eps = detect_entry_points(entry_point_entities)
        ids = {e.id for e in eps}
        assert "CLASS::a.py::MyClass" not in ids

    def test_empty_entities(self):
        eps = detect_entry_points([])
        assert eps == []


class TestSequences:
    def test_trace_execution_sequence(self, chain_entities, chain_edges):
        seq = trace_execution_sequence(
            "FUNC::a.py::fn_a", chain_entities, chain_edges,
        )
        assert seq.entry_point_id == "FUNC::a.py::fn_a"
        assert len(seq.steps) == 4  # A, B, C, D
        # Steps should be in order
        for i, step in enumerate(seq.steps):
            assert step.order == i + 1

    def test_trace_sequence_with_branching(self):
        """Test that branching is counted correctly."""
        entities = [
            Entity(id="FUNC::a.py::root", type=EntityType.FUNCTION,
                   name="root", location=Location(file="a.py", start_line=1),
                   language="python"),
            Entity(id="FUNC::a.py::left", type=EntityType.FUNCTION,
                   name="left", location=Location(file="a.py", start_line=10),
                   language="python"),
            Entity(id="FUNC::a.py::right", type=EntityType.FUNCTION,
                   name="right", location=Location(file="a.py", start_line=20),
                   language="python"),
        ]
        edges = [
            Edge(source="FUNC::a.py::root", target="FUNC::a.py::left",
                 relation=RelationType.CALLS),
            Edge(source="FUNC::a.py::root", target="FUNC::a.py::right",
                 relation=RelationType.CALLS),
        ]
        seq = trace_execution_sequence("FUNC::a.py::root", entities, edges)
        assert seq.branches >= 1  # root has 2 callees -> 1 branch
        assert len(seq.steps) == 3

    def test_trace_nonexistent_entry_point(self, chain_entities, chain_edges):
        seq = trace_execution_sequence(
            "nonexistent", chain_entities, chain_edges,
        )
        assert seq.entry_point_id == "nonexistent"
        assert len(seq.steps) == 0

    def test_trace_all_sequences(self, chain_entities, chain_edges):
        # Add a "main" entity as entry point
        main_entity = Entity(
            id="FUNC::main.py::main", type=EntityType.FUNCTION,
            name="main", location=Location(file="main.py", start_line=1),
            language="python",
        )
        main_edge = Edge(
            source="FUNC::main.py::main", target="FUNC::a.py::fn_a",
            relation=RelationType.CALLS,
        )
        entities = chain_entities + [main_entity]
        edges = chain_edges + [main_edge]

        sequences = trace_all_sequences(entities, edges)
        # main should generate a sequence with steps
        assert len(sequences) >= 1
        # Should be sorted by step count descending
        if len(sequences) > 1:
            step_counts = [len(s.steps) for s in sequences]
            assert step_counts == sorted(step_counts, reverse=True)

    def test_cycle_detection(self):
        """Test that cycles don't cause infinite loops."""
        entities = [
            Entity(id="FUNC::a.py::fn_a", type=EntityType.FUNCTION,
                   name="fn_a", location=Location(file="a.py", start_line=1),
                   language="python"),
            Entity(id="FUNC::b.py::fn_b", type=EntityType.FUNCTION,
                   name="fn_b", location=Location(file="b.py", start_line=1),
                   language="python"),
        ]
        edges = [
            Edge(source="FUNC::a.py::fn_a", target="FUNC::b.py::fn_b",
                 relation=RelationType.CALLS),
            Edge(source="FUNC::b.py::fn_b", target="FUNC::a.py::fn_a",
                 relation=RelationType.CALLS),
        ]
        # This should not hang
        seq = trace_execution_sequence(
            "FUNC::a.py::fn_a", entities, edges, max_depth=10,
        )
        assert seq.loops >= 1


# ------------------------------------------------------------------
# Hotspots
# ------------------------------------------------------------------

class TestHotspots:
    def test_bottleneck_detection(self, fan_entities, fan_edges):
        hotspots = detect_hotspots(fan_entities, fan_edges)
        bottlenecks = [h for h in hotspots
                       if h.entity_id == "FUNC::hub.py::hub"
                       and h.hotspot_type == HotspotType.BOTTLENECK]
        assert len(bottlenecks) == 1
        assert bottlenecks[0].severity == "critical"
        assert bottlenecks[0].fan_in == 5
        assert bottlenecks[0].fan_out == 5

    def test_leaf_detection(self, chain_entities, chain_edges):
        # Use high fan_in_threshold so fn_d (fan_in=1) is classified as LEAF
        # rather than HIGH_FAN_IN
        hotspots = detect_hotspots(chain_entities, chain_edges,
                                   fan_in_threshold=5, fan_out_threshold=5)
        leaves = [h for h in hotspots
                  if h.hotspot_type == HotspotType.LEAF]
        # fn_d has callers but no callees -> leaf
        leaf_ids = {h.entity_id for h in leaves}
        assert "FUNC::d.py::fn_d" in leaf_ids

    def test_orphan_detection(self):
        """Isolated function with no callers or callees."""
        entities = [
            Entity(id="FUNC::z.py::orphan", type=EntityType.FUNCTION,
                   name="orphan", location=Location(file="z.py", start_line=1),
                   language="python"),
        ]
        hotspots = detect_hotspots(entities, [])
        orphans = [h for h in hotspots
                   if h.hotspot_type == HotspotType.ORPHAN]
        assert len(orphans) == 1
        assert orphans[0].severity == "info"

    def test_entry_points_not_orphaned(self):
        """main, test_ etc should not be marked as orphans."""
        entities = [
            Entity(id="FUNC::a.py::main", type=EntityType.FUNCTION,
                   name="main", location=Location(file="a.py", start_line=1),
                   language="python"),
            Entity(id="FUNC::a.py::test_foo", type=EntityType.FUNCTION,
                   name="test_foo", location=Location(file="a.py", start_line=10),
                   language="python"),
        ]
        hotspots = detect_hotspots(entities, [])
        orphans = [h for h in hotspots
                   if h.hotspot_type == HotspotType.ORPHAN]
        assert len(orphans) == 0

    def test_high_fan_in(self):
        """Entity called by many but calling few."""
        entities = [
            Entity(id="FUNC::util.py::helper", type=EntityType.FUNCTION,
                   name="helper", location=Location(file="util.py", start_line=1),
                   language="python"),
        ]
        for i in range(6):
            entities.append(Entity(
                id=f"FUNC::caller{i}.py::c{i}", type=EntityType.FUNCTION,
                name=f"c{i}", location=Location(file=f"caller{i}.py", start_line=1),
                language="python",
            ))
        edges = [
            Edge(source=f"FUNC::caller{i}.py::c{i}",
                 target="FUNC::util.py::helper",
                 relation=RelationType.CALLS)
            for i in range(6)
        ]
        hotspots = detect_hotspots(entities, edges, fan_in_threshold=5)
        hi = [h for h in hotspots
              if h.entity_id == "FUNC::util.py::helper"
              and h.hotspot_type == HotspotType.HIGH_FAN_IN]
        assert len(hi) == 1

    def test_high_fan_out(self):
        """Entity calling many but called by few."""
        entities = [
            Entity(id="FUNC::orch.py::orchestrator", type=EntityType.FUNCTION,
                   name="orchestrator",
                   location=Location(file="orch.py", start_line=1),
                   language="python"),
        ]
        for i in range(6):
            entities.append(Entity(
                id=f"FUNC::dep{i}.py::d{i}", type=EntityType.FUNCTION,
                name=f"d{i}", location=Location(file=f"dep{i}.py", start_line=1),
                language="python",
            ))
        edges = [
            Edge(source="FUNC::orch.py::orchestrator",
                 target=f"FUNC::dep{i}.py::d{i}",
                 relation=RelationType.CALLS)
            for i in range(6)
        ]
        hotspots = detect_hotspots(entities, edges, fan_out_threshold=5)
        ho = [h for h in hotspots
              if h.entity_id == "FUNC::orch.py::orchestrator"
              and h.hotspot_type == HotspotType.HIGH_FAN_OUT]
        assert len(ho) == 1

    def test_sorted_by_severity(self, fan_entities, fan_edges):
        hotspots = detect_hotspots(fan_entities, fan_edges)
        if len(hotspots) > 1:
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            severities = [severity_order.get(h.severity, 3) for h in hotspots]
            assert severities == sorted(severities)

    def test_empty_inputs(self):
        hotspots = detect_hotspots([], [])
        assert hotspots == []

    def test_classes_ignored(self):
        """Only FUNCTION/METHOD entities are analyzed."""
        entities = [
            Entity(id="CLASS::a.py::Foo", type=EntityType.CLASS,
                   name="Foo", location=Location(file="a.py", start_line=1),
                   language="python"),
        ]
        hotspots = detect_hotspots(entities, [])
        assert hotspots == []


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------

class TestSynapseEngine:
    def test_engine_name_version(self):
        engine = SynapseEngine()
        assert engine.name() == "synapse"
        assert engine.version() == "0.2.0"

    def test_engine_without_xray(self):
        engine = SynapseEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config)
        assert result.domain == "synapse"
        assert len(result.errors) > 0

    def test_engine_with_xray(self, sample_xray):
        engine = SynapseEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        assert result.domain == "synapse"
        assert "call_graphs_count" in result.stats
        assert "entry_points_count" in result.stats
        assert "sequences_count" in result.stats
        assert "hotspots_count" in result.stats

    def test_engine_stats_structure(self, sample_xray):
        engine = SynapseEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        stats = result.stats
        assert "hotspots_by_type" in stats
        assert "hotspots_by_severity" in stats
        assert "max_upstream_depth" in stats
        assert "max_downstream_depth" in stats
        assert "max_sequence_length" in stats

    def test_engine_call_graphs_serialized(self, sample_xray):
        engine = SynapseEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[sample_xray])
        # call_graphs should be serialized dicts
        graphs = result.stats.get("call_graphs", [])
        for g in graphs:
            assert isinstance(g, dict)

    def test_engine_with_rich_xray(self):
        """Test engine with a richer X-Ray result that has entry points."""
        entities = [
            Entity(id="FUNC::main.py::main", type=EntityType.FUNCTION,
                   name="main", location=Location(file="main.py", start_line=1),
                   language="python"),
            Entity(id="FUNC::a.py::process", type=EntityType.FUNCTION,
                   name="process", location=Location(file="a.py", start_line=10),
                   language="python"),
            Entity(id="FUNC::b.py::validate", type=EntityType.FUNCTION,
                   name="validate", location=Location(file="b.py", start_line=1),
                   language="python"),
            Entity(id="FUNC::c.py::save", type=EntityType.FUNCTION,
                   name="save", location=Location(file="c.py", start_line=1),
                   language="python"),
        ]
        edges = [
            Edge(source="FUNC::main.py::main",
                 target="FUNC::a.py::process",
                 relation=RelationType.CALLS),
            Edge(source="FUNC::a.py::process",
                 target="FUNC::b.py::validate",
                 relation=RelationType.CALLS),
            Edge(source="FUNC::a.py::process",
                 target="FUNC::c.py::save",
                 relation=RelationType.CALLS),
        ]
        xray = AnalysisResult(
            domain="xray", version="2.0.0", root_path=".",
            entities=entities, edges=edges,
        )
        engine = SynapseEngine()
        config = BlueprintConfig(root_path=Path("."))
        result = engine.run(config, prior_results=[xray])
        assert result.stats["entry_points_count"] >= 1
        assert result.stats["call_graphs_count"] >= 1
