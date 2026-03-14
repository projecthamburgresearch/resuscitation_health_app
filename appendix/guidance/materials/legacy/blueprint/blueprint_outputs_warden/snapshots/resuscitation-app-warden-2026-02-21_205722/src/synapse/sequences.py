"""Execution sequence tracing - determine order of operations from entry points."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set

from src.core.models import Edge, Entity, EntityType, RelationType
from src.synapse.schema import ExecutionSequence, SequenceStep


# Entity names/patterns that indicate entry points
ENTRY_POINT_PATTERNS = {
    "main", "__main__", "app", "index", "server", "handler",
    "cli", "run", "start", "init", "setup", "bootstrap",
}

ENTRY_POINT_DECORATORS = {
    "app.route", "app.get", "app.post", "app.put", "app.delete",
    "router.get", "router.post", "click.command", "click.group",
    "pytest.fixture", "test_",
}


def detect_entry_points(entities: List[Entity]) -> List[Entity]:
    """Find likely entry points in the codebase.

    Entry points are functions/methods that serve as starting points
    for execution: main functions, route handlers, CLI commands,
    test functions, etc.

    Args:
        entities: All entities from X-Ray analysis.

    Returns:
        List of entities identified as entry points.
    """
    entry_points: List[Entity] = []

    for entity in entities:
        if entity.type not in (EntityType.FUNCTION, EntityType.METHOD):
            continue

        name_lower = entity.name.lower()

        # Check name patterns
        if name_lower in ENTRY_POINT_PATTERNS:
            entry_points.append(entity)
            continue

        # Check if name starts with test_
        if name_lower.startswith("test_"):
            entry_points.append(entity)
            continue

        # Check decorators
        if entity.decorators:
            for dec in entity.decorators:
                dec_lower = dec.lower()
                for pattern in ENTRY_POINT_DECORATORS:
                    if pattern in dec_lower:
                        entry_points.append(entity)
                        break
            else:
                continue
            continue  # Already added via decorator match

        # Check if signature contains route-like patterns
        if entity.signature:
            sig_lower = entity.signature.lower()
            if any(p in sig_lower for p in ("@app.", "@router.", "def main")):
                entry_points.append(entity)
                continue

    return entry_points


def trace_execution_sequence(
    entry_point_id: str,
    entities: List[Entity],
    edges: List[Edge],
    max_depth: int = 50,
) -> ExecutionSequence:
    """Trace the execution sequence from an entry point.

    Performs a DFS traversal of CALLS edges to determine the
    order of function/method invocations.

    Args:
        entry_point_id: Entity ID of the entry point.
        entities: All entities.
        edges: All edges.
        max_depth: Maximum traversal depth.

    Returns:
        ExecutionSequence with ordered steps.
    """
    entity_map: Dict[str, Entity] = {e.id: e for e in entities}
    callees_of: Dict[str, List[str]] = defaultdict(list)

    for edge in edges:
        if edge.relation == RelationType.CALLS:
            callees_of[edge.source].append(edge.target)

    entry = entity_map.get(entry_point_id)
    if not entry:
        return ExecutionSequence(
            entry_point_id=entry_point_id,
            entry_point_name=entry_point_id.split("::")[-1],
        )

    steps: List[SequenceStep] = []
    visited: Set[str] = set()
    branches = 0
    loops = 0
    order_counter = 0

    def _dfs(current_id: str, depth: int) -> None:
        nonlocal order_counter, branches, loops

        if depth > max_depth:
            return
        if current_id in visited:
            loops += 1
            return

        visited.add(current_id)
        ent = entity_map.get(current_id)

        order_counter += 1
        steps.append(SequenceStep(
            order=order_counter,
            entity_id=current_id,
            entity_name=ent.qualified_name or ent.name if ent else current_id.split("::")[-1],
            file_path=ent.location.file if ent and ent.location else "",
            call_type="direct",
        ))

        callees = callees_of.get(current_id, [])
        if len(callees) > 1:
            branches += len(callees) - 1

        for callee_id in callees:
            _dfs(callee_id, depth + 1)

        visited.discard(current_id)

    _dfs(entry_point_id, 0)

    return ExecutionSequence(
        entry_point_id=entry_point_id,
        entry_point_name=entry.qualified_name or entry.name,
        steps=steps,
        branches=branches,
        loops=loops,
        max_depth=max(s.order for s in steps) if steps else 0,
    )


def trace_all_sequences(
    entities: List[Entity],
    edges: List[Edge],
    max_depth: int = 50,
    entry_points: Optional[List[Entity]] = None,
) -> List[ExecutionSequence]:
    """Trace execution sequences from all detected entry points.

    Args:
        entities: All entities.
        edges: All edges.
        max_depth: Max traversal depth.
        entry_points: Override entry point detection.

    Returns:
        List of ExecutionSequence objects, sorted by step count descending.
    """
    if entry_points is None:
        entry_points = detect_entry_points(entities)

    sequences = []
    for ep in entry_points:
        seq = trace_execution_sequence(ep.id, entities, edges, max_depth)
        if len(seq.steps) > 1:  # Only include sequences with actual calls
            sequences.append(seq)

    sequences.sort(key=lambda s: len(s.steps), reverse=True)
    return sequences
