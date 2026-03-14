"""Call chain analysis - trace caller/callee paths through the codebase."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from src.core.models import Edge, Entity, EntityType, RelationType
from src.synapse.schema import (
    CallChain,
    CallGraph,
    ChainDirection,
)


def build_adjacency(
    entities: List[Entity],
    edges: List[Edge],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, Entity]]:
    """Build caller->callee and callee->caller adjacency maps.

    Returns:
        (callees_of, callers_of, entity_map)
        - callees_of[entity_id] = list of entity IDs it calls
        - callers_of[entity_id] = list of entity IDs that call it
        - entity_map[entity_id] = Entity object
    """
    callees_of: Dict[str, List[str]] = defaultdict(list)
    callers_of: Dict[str, List[str]] = defaultdict(list)
    entity_map: Dict[str, Entity] = {e.id: e for e in entities}

    for edge in edges:
        if edge.relation == RelationType.CALLS:
            callees_of[edge.source].append(edge.target)
            callers_of[edge.target].append(edge.source)

    return dict(callees_of), dict(callers_of), entity_map


def trace_chain(
    start_id: str,
    adjacency: Dict[str, List[str]],
    entity_map: Dict[str, Entity],
    direction: ChainDirection,
    max_depth: int = 20,
) -> List[CallChain]:
    """Trace all chains from a starting entity in a given direction.

    Args:
        start_id: Entity ID to start from.
        adjacency: callers_of (upstream) or callees_of (downstream).
        entity_map: ID -> Entity lookup.
        direction: upstream or downstream.
        max_depth: Maximum chain depth to prevent infinite loops.

    Returns:
        List of CallChain objects, one per unique path.
    """
    chains: List[CallChain] = []
    start = entity_map.get(start_id)
    if not start:
        return chains

    start_name = start.qualified_name or start.name

    # BFS to find all paths (with cycle detection per path)
    # Each queue item: (current_id, path_so_far)
    queue: List[Tuple[str, List[str]]] = [(start_id, [start_id])]

    while queue:
        current_id, path = queue.pop(0)

        if len(path) > max_depth:
            continue

        neighbors = adjacency.get(current_id, [])
        if not neighbors or len(path) > 1 and not neighbors:
            # End of chain - record if it has depth > 1
            if len(path) > 1:
                names = []
                files = []
                for eid in path:
                    ent = entity_map.get(eid)
                    if ent:
                        names.append(ent.qualified_name or ent.name)
                        files.append(ent.location.file if ent.location else "")
                    else:
                        names.append(eid.split("::")[-1])
                        files.append("")

                chains.append(CallChain(
                    root_entity_id=start_id,
                    root_name=start_name,
                    direction=direction,
                    depth=len(path) - 1,
                    chain=path,
                    names=names,
                    files=files,
                ))

        extended = False
        for neighbor_id in neighbors:
            if neighbor_id in path:
                continue  # Cycle detection
            queue.append((neighbor_id, path + [neighbor_id]))
            extended = True

        # If we couldn't extend and path has depth, still record
        if not extended and len(path) > 1:
            # Check if already recorded
            path_key = tuple(path)
            already = any(tuple(c.chain) == path_key for c in chains)
            if not already:
                names = []
                files = []
                for eid in path:
                    ent = entity_map.get(eid)
                    if ent:
                        names.append(ent.qualified_name or ent.name)
                        files.append(ent.location.file if ent.location else "")
                    else:
                        names.append(eid.split("::")[-1])
                        files.append("")

                chains.append(CallChain(
                    root_entity_id=start_id,
                    root_name=start_name,
                    direction=direction,
                    depth=len(path) - 1,
                    chain=path,
                    names=names,
                    files=files,
                ))

    return chains


def build_call_graph(
    entity_id: str,
    entities: List[Entity],
    edges: List[Edge],
    max_depth: int = 10,
) -> CallGraph:
    """Build complete call graph for a single entity.

    Args:
        entity_id: The entity to analyze.
        entities: All entities.
        edges: All edges.
        max_depth: Max chain traversal depth.

    Returns:
        CallGraph with upstream and downstream chains.
    """
    callees_of, callers_of, entity_map = build_adjacency(entities, edges)

    entity = entity_map.get(entity_id)
    if not entity:
        return CallGraph(
            entity_id=entity_id,
            entity_name=entity_id.split("::")[-1],
            file_path="",
        )

    upstream = trace_chain(
        entity_id, callers_of, entity_map,
        ChainDirection.UPSTREAM, max_depth,
    )
    downstream = trace_chain(
        entity_id, callees_of, entity_map,
        ChainDirection.DOWNSTREAM, max_depth,
    )

    # Collect unique callers/callees
    unique_callers: Set[str] = set()
    for chain in upstream:
        for eid in chain.chain:
            if eid != entity_id:
                unique_callers.add(eid)

    unique_callees: Set[str] = set()
    for chain in downstream:
        for eid in chain.chain:
            if eid != entity_id:
                unique_callees.add(eid)

    return CallGraph(
        entity_id=entity_id,
        entity_name=entity.qualified_name or entity.name,
        file_path=entity.location.file if entity.location else "",
        upstream_chains=upstream,
        downstream_chains=downstream,
        upstream_depth=max((c.depth for c in upstream), default=0),
        downstream_depth=max((c.depth for c in downstream), default=0),
        total_callers=len(unique_callers),
        total_callees=len(unique_callees),
    )


def build_all_call_graphs(
    entities: List[Entity],
    edges: List[Edge],
    max_depth: int = 10,
    entity_types: Optional[List[EntityType]] = None,
) -> List[CallGraph]:
    """Build call graphs for all callable entities.

    Args:
        entities: All entities.
        edges: All edges.
        max_depth: Max chain depth.
        entity_types: Filter to these types (default: FUNCTION, METHOD).

    Returns:
        List of CallGraph objects, sorted by total connections descending.
    """
    types = entity_types or [EntityType.FUNCTION, EntityType.METHOD]
    target_entities = [e for e in entities if e.type in types]

    graphs = []
    for entity in target_entities:
        graph = build_call_graph(entity.id, entities, edges, max_depth)
        if graph.total_callers > 0 or graph.total_callees > 0:
            graphs.append(graph)

    graphs.sort(
        key=lambda g: g.total_callers + g.total_callees,
        reverse=True,
    )
    return graphs
