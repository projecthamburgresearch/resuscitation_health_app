"""Knowledge graph operations wrapping NetworkX."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from src.core.models import Edge, Entity, RelationType


class KnowledgeGraph:
    """Typed wrapper around NetworkX DiGraph for code intelligence.

    Stores Entity objects as node data and Edge objects as edge data,
    providing typed query methods for common code analysis patterns.
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._entities: Dict[str, Entity] = {}

    # -------------------------------------------------------------------
    # Mutation
    # -------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self._entities[entity.id] = entity
        self._graph.add_node(
            entity.id,
            type=entity.type.value,
            name=entity.name,
            language=entity.language,
        )

    def add_edge(self, edge: Edge) -> None:
        """Add a relationship edge to the graph."""
        # Ensure source and target nodes exist
        if edge.source not in self._graph:
            self._graph.add_node(edge.source)
        if edge.target not in self._graph:
            self._graph.add_node(edge.target)
        self._graph.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation.value,
            confidence=edge.confidence,
            meta=edge.meta,
        )

    def merge(self, other: KnowledgeGraph) -> None:
        """Merge another graph into this one."""
        for entity in other._entities.values():
            self.add_entity(entity)
        for u, v, data in other._graph.edges(data=True):
            self._graph.add_edge(u, v, **data)

    # -------------------------------------------------------------------
    # Entity queries
    # -------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self._entities.get(entity_id)

    def get_all_entities(self) -> List[Entity]:
        """Get all entities in the graph."""
        return list(self._entities.values())

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a given type."""
        return [e for e in self._entities.values() if e.type.value == entity_type]

    def get_entities_by_file(self, file_path: str) -> List[Entity]:
        """Get all entities in a specific file."""
        return [
            e for e in self._entities.values()
            if e.location and e.location.file == file_path
        ]

    # -------------------------------------------------------------------
    # Relationship queries
    # -------------------------------------------------------------------

    def get_callers(self, entity_id: str) -> List[Entity]:
        """Get entities that call the given entity (predecessors with CALLS relation)."""
        callers = []
        for pred in self._graph.predecessors(entity_id):
            edge_data = self._graph.edges[pred, entity_id]
            if edge_data.get("relation") == RelationType.CALLS.value:
                ent = self._entities.get(pred)
                if ent:
                    callers.append(ent)
        return callers

    def get_callees(self, entity_id: str) -> List[Entity]:
        """Get entities that the given entity calls (successors with CALLS relation)."""
        callees = []
        for succ in self._graph.successors(entity_id):
            edge_data = self._graph.edges[entity_id, succ]
            if edge_data.get("relation") == RelationType.CALLS.value:
                ent = self._entities.get(succ)
                if ent:
                    callees.append(ent)
        return callees

    def get_dependencies(self, entity_id: str, depth: int = 1) -> List[Entity]:
        """Get entities this entity depends on (outgoing edges), up to given depth."""
        visited: Set[str] = set()
        result: List[Entity] = []
        queue = [(entity_id, 0)]

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue
            for succ in self._graph.successors(current):
                if succ not in visited:
                    visited.add(succ)
                    ent = self._entities.get(succ)
                    if ent:
                        result.append(ent)
                    queue.append((succ, d + 1))

        return result

    def get_dependents(self, entity_id: str, depth: int = 1) -> List[Entity]:
        """Get entities that depend on this entity (incoming edges), up to given depth."""
        visited: Set[str] = set()
        result: List[Entity] = []
        queue = [(entity_id, 0)]

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue
            for pred in self._graph.predecessors(current):
                if pred not in visited:
                    visited.add(pred)
                    ent = self._entities.get(pred)
                    if ent:
                        result.append(ent)
                    queue.append((pred, d + 1))

        return result

    # -------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------

    def compute_fan_in_out(self) -> Dict[str, Tuple[int, int]]:
        """Compute fan-in (callers) and fan-out (callees) for all entities.

        Returns:
            Dict mapping entity_id -> (fan_in, fan_out)
        """
        result = {}
        for node_id in self._graph.nodes():
            fan_in = sum(
                1 for pred in self._graph.predecessors(node_id)
                if self._graph.edges[pred, node_id].get("relation") == RelationType.CALLS.value
            )
            fan_out = sum(
                1 for succ in self._graph.successors(node_id)
                if self._graph.edges[node_id, succ].get("relation") == RelationType.CALLS.value
            )
            result[node_id] = (fan_in, fan_out)
        return result

    def find_orphans(self) -> List[Entity]:
        """Find entities with no incoming or outgoing edges."""
        orphans = []
        for node_id in self._graph.nodes():
            if self._graph.degree(node_id) == 0:
                ent = self._entities.get(node_id)
                if ent:
                    orphans.append(ent)
        return orphans

    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the call graph."""
        try:
            return list(nx.simple_cycles(self._graph))
        except nx.NetworkXError:
            return []

    # -------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def to_dict(self) -> Dict[str, Any]:
        """Export graph as a JSON-serializable dictionary."""
        nodes = []
        for entity in self._entities.values():
            nodes.append(entity.model_dump(exclude_none=True))

        edges = []
        for u, v, data in self._graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                **data,
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": self.node_count,
                "edge_count": self.edge_count,
            },
        }

    @classmethod
    def from_entities_and_edges(
        cls, entities: List[Entity], edges: List[Edge]
    ) -> KnowledgeGraph:
        """Build a KnowledgeGraph from lists of entities and edges."""
        graph = cls()
        for entity in entities:
            graph.add_entity(entity)
        for edge in edges:
            graph.add_edge(edge)
        return graph
