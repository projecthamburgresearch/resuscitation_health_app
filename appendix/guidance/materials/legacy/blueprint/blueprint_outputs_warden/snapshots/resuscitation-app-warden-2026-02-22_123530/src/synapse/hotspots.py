"""Hotspot detection - find structurally significant entities in the call graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from src.core.models import Edge, Entity, EntityType, RelationType
from src.synapse.schema import Hotspot, HotspotType


def detect_hotspots(
    entities: List[Entity],
    edges: List[Edge],
    fan_in_threshold: int = 5,
    fan_out_threshold: int = 5,
) -> List[Hotspot]:
    """Detect structural hotspots in the call graph.

    Hotspot types:
    - HIGH_FAN_IN: Called by many others (central dependency)
    - HIGH_FAN_OUT: Calls many others (orchestrator/god function)
    - BOTTLENECK: High fan-in AND fan-out (risky single point of failure)
    - HUB: Sits at the intersection of many call chains
    - LEAF: Has callers but calls nothing (terminal function)
    - ORPHAN: No callers and no callees (potentially dead)

    Args:
        entities: All entities.
        edges: All edges.
        fan_in_threshold: Minimum callers for HIGH_FAN_IN.
        fan_out_threshold: Minimum callees for HIGH_FAN_OUT.

    Returns:
        List of Hotspot objects, sorted by severity then fan counts.
    """
    entity_map: Dict[str, Entity] = {e.id: e for e in entities}
    callers_of: Dict[str, Set[str]] = defaultdict(set)
    callees_of: Dict[str, Set[str]] = defaultdict(set)

    for edge in edges:
        if edge.relation == RelationType.CALLS:
            callees_of[edge.source].add(edge.target)
            callers_of[edge.target].add(edge.source)

    # Count chain participation
    chain_participation: Dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.relation == RelationType.CALLS:
            chain_participation[edge.source] += 1
            chain_participation[edge.target] += 1

    callable_types = {
        EntityType.FUNCTION, EntityType.METHOD,
    }

    hotspots: List[Hotspot] = []

    for entity in entities:
        if entity.type not in callable_types:
            continue

        fan_in = len(callers_of.get(entity.id, set()))
        fan_out = len(callees_of.get(entity.id, set()))
        chains = chain_participation.get(entity.id, 0)

        file_path = entity.location.file if entity.location else ""
        name = entity.qualified_name or entity.name

        # Classify
        if fan_in >= fan_in_threshold and fan_out >= fan_out_threshold:
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.BOTTLENECK,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="critical",
            ))
        elif fan_in >= fan_in_threshold:
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.HIGH_FAN_IN,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="warning",
            ))
        elif fan_out >= fan_out_threshold:
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.HIGH_FAN_OUT,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="warning",
            ))
        elif fan_in > 0 and fan_out == 0:
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.LEAF,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="info",
            ))
        elif fan_in == 0 and fan_out == 0:
            # Skip entry points and test functions
            name_lower = entity.name.lower()
            if name_lower in ("main", "__init__", "setup", "teardown"):
                continue
            if name_lower.startswith("test_"):
                continue
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.ORPHAN,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="info",
            ))
        elif chains >= (fan_in_threshold + fan_out_threshold):
            hotspots.append(Hotspot(
                entity_id=entity.id,
                entity_name=name,
                file_path=file_path,
                hotspot_type=HotspotType.HUB,
                fan_in=fan_in,
                fan_out=fan_out,
                chain_count=chains,
                severity="warning",
            ))

    # Sort: critical first, then warning, then info, then by fan counts
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    hotspots.sort(
        key=lambda h: (
            severity_order.get(h.severity, 3),
            -(h.fan_in + h.fan_out),
        ),
    )

    return hotspots
