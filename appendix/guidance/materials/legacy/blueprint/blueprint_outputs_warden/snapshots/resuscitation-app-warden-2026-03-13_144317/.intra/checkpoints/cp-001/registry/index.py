"""Master index management for the Registry domain.

Builds, updates, merges, saves and loads the MasterIndex -- the central
catalog of every entity Blueprint has ever seen across all analysis runs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from src.core.io_utils import ensure_dir, normalize_path
from src.core.models import AnalysisResult, Edge, Entity, RelationType
from src.registry.schema import (
    MasterIndex,
    ProjectProfile,
    RegistryEntry,
    Zone,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entity_id_to_file(entity_id: str) -> str | None:
    """Extract the file path component from a standard entity ID.

    Entity IDs follow the format ``TYPE::filepath::name``.
    """
    parts = entity_id.split("::")
    if len(parts) >= 3:
        return parts[1]
    return None


def _build_file_to_zone(zones: List[Zone]) -> Dict[str, str]:
    """Map each file path to its zone_id."""
    mapping: Dict[str, str] = {}
    for zone in zones:
        for fp in zone.file_paths:
            mapping[fp] = zone.zone_id
    return mapping


def _build_caller_callee_maps(
    edges: List[Edge],
) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Build caller and callee maps from CALLS edges.

    Returns:
        (callers_map, callees_map) where each maps entity_id -> list of
        related entity_ids.
    """
    callers: Dict[str, List[str]] = defaultdict(list)
    callees: Dict[str, List[str]] = defaultdict(list)

    for edge in edges:
        if edge.relation == RelationType.CALLS:
            # source CALLS target  =>  target has caller=source,
            #                          source has callee=target
            callers[edge.target].append(edge.source)
            callees[edge.source].append(edge.target)

    return dict(callers), dict(callees)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_master_index(
    project_name: str,
    root: Path,
    profile: ProjectProfile,
    zones: List[Zone],
    result: AnalysisResult,
    run_id: str,
) -> MasterIndex:
    """Build a MasterIndex from scratch using an AnalysisResult.

    Populates each RegistryEntry with caller/callee information derived
    from the CALLS edges in the result.

    Args:
        project_name: Human-readable project name.
        root: The project root path.
        profile: The previously-computed ProjectProfile.
        zones: The zone partitioning.
        result: The AnalysisResult (typically from xray).
        run_id: Unique identifier for this analysis run.

    Returns:
        A fully-populated MasterIndex.
    """
    file_to_zone = _build_file_to_zone(zones)
    callers_map, callees_map = _build_caller_callee_maps(result.edges)

    entries: Dict[str, RegistryEntry] = {}
    now = datetime.now()

    for entity in result.entities:
        file_path = ""
        line = 0
        if entity.location:
            file_path = entity.location.file
            line = entity.location.start_line
        elif "::" in entity.id:
            # Fall back to parsing the entity ID
            extracted = _entity_id_to_file(entity.id)
            if extracted:
                file_path = extracted

        zone_id = file_to_zone.get(file_path, "zone::root")

        entry = RegistryEntry(
            entity_id=entity.id,
            entity_type=entity.type.value,
            name=entity.name,
            qualified_name=entity.qualified_name,
            file_path=file_path,
            zone_id=zone_id,
            line=line,
            language=entity.language or "unknown",
            signature=entity.signature,
            callers=callers_map.get(entity.id, []),
            callees=callees_map.get(entity.id, []),
            last_seen_run=run_id,
            first_seen_run=run_id,
            change_count=0,
        )
        entries[entity.id] = entry

    root_str = normalize_path(root, root) or str(root).replace("\\", "/")

    return MasterIndex(
        project_name=project_name,
        project_root=root_str,
        version="0.2.0",
        created_at=now,
        updated_at=now,
        profile=profile,
        zones=zones,
        entries=entries,
        run_history=[run_id],
        stats={
            "total_entries": len(entries),
            "total_zones": len(zones),
            "total_edges": len(result.edges),
            "total_errors": len(result.errors),
        },
    )


# ---------------------------------------------------------------------------
# Incremental Update
# ---------------------------------------------------------------------------

def update_master_index(
    index: MasterIndex,
    result: AnalysisResult,
    run_id: str,
) -> MasterIndex:
    """Incrementally update a MasterIndex with a new AnalysisResult.

    - New entities are added.
    - Existing entities are updated: ``change_count`` is incremented and
      ``last_seen_run`` is set to *run_id*.
    - Entities that were in the index but are **not** in the new result
      are removed (they no longer exist in the codebase).

    Args:
        index: The existing MasterIndex to update.
        result: The new AnalysisResult.
        run_id: Unique identifier for this analysis run.

    Returns:
        The updated MasterIndex (mutated in-place and returned).
    """
    callers_map, callees_map = _build_caller_callee_maps(result.edges)

    # Collect the set of entity IDs present in the new result
    new_entity_ids: Set[str] = set()
    file_to_zone = _build_file_to_zone(index.zones)

    for entity in result.entities:
        new_entity_ids.add(entity.id)

        file_path = ""
        line = 0
        if entity.location:
            file_path = entity.location.file
            line = entity.location.start_line
        elif "::" in entity.id:
            extracted = _entity_id_to_file(entity.id)
            if extracted:
                file_path = extracted

        zone_id = file_to_zone.get(file_path, "zone::root")

        if entity.id in index.entries:
            # Existing entity -- update
            existing = index.entries[entity.id]
            existing.change_count += 1
            existing.last_seen_run = run_id
            existing.callers = callers_map.get(entity.id, [])
            existing.callees = callees_map.get(entity.id, [])
            existing.line = line
            existing.signature = entity.signature
            existing.qualified_name = entity.qualified_name
            existing.language = entity.language or existing.language
        else:
            # New entity
            entry = RegistryEntry(
                entity_id=entity.id,
                entity_type=entity.type.value,
                name=entity.name,
                qualified_name=entity.qualified_name,
                file_path=file_path,
                zone_id=zone_id,
                line=line,
                language=entity.language or "unknown",
                signature=entity.signature,
                callers=callers_map.get(entity.id, []),
                callees=callees_map.get(entity.id, []),
                last_seen_run=run_id,
                first_seen_run=run_id,
                change_count=0,
            )
            index.entries[entity.id] = entry

    # Remove entities no longer present in the codebase
    stale_ids = [eid for eid in index.entries if eid not in new_entity_ids]
    for eid in stale_ids:
        del index.entries[eid]

    # Update run history and timestamp
    if run_id not in index.run_history:
        index.run_history.append(run_id)
    index.updated_at = datetime.now()

    # Refresh stats
    index.stats = {
        "total_entries": len(index.entries),
        "total_zones": len(index.zones),
        "total_runs": len(index.run_history),
    }

    return index


# ---------------------------------------------------------------------------
# Merge Zone Results
# ---------------------------------------------------------------------------

def merge_zone_results(zone_results: List[AnalysisResult]) -> AnalysisResult:
    """Combine results from independently-processed zones into one.

    Deduplicates entities by ID (first occurrence wins) and concatenates
    edges and errors.

    Args:
        zone_results: A list of AnalysisResult objects, one per zone.

    Returns:
        A single merged AnalysisResult.
    """
    if not zone_results:
        return AnalysisResult(
            domain="registry",
            version="0.2.0",
            root_path=".",
            entities=[],
            edges=[],
            stats={},
            errors=[],
        )

    seen_entity_ids: Set[str] = set()
    merged_entities: List[Entity] = []
    merged_edges: List[Edge] = []
    merged_errors: List[Dict[str, Any]] = []
    merged_stats: Dict[str, Any] = {
        "zone_count": len(zone_results),
        "total_entities": 0,
        "total_edges": 0,
    }

    # Use the first result's metadata as base
    base = zone_results[0]
    root_path = base.root_path
    domain = base.domain
    version = base.version

    for zr in zone_results:
        for entity in zr.entities:
            if entity.id not in seen_entity_ids:
                seen_entity_ids.add(entity.id)
                merged_entities.append(entity)
        merged_edges.extend(zr.edges)
        merged_errors.extend(zr.errors)

    merged_stats["total_entities"] = len(merged_entities)
    merged_stats["total_edges"] = len(merged_edges)
    merged_stats["total_errors"] = len(merged_errors)

    return AnalysisResult(
        domain=domain,
        version=version,
        root_path=root_path,
        entities=merged_entities,
        edges=merged_edges,
        stats=merged_stats,
        errors=merged_errors,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_master_index(index: MasterIndex, output_path: Path) -> Path:
    """Save a MasterIndex to a JSON file.

    Creates parent directories as needed.

    Args:
        index: The MasterIndex to save.
        output_path: Destination file path (should end with ``.json``).

    Returns:
        The path that was written to.
    """
    ensure_dir(output_path.parent)

    data = index.model_dump(mode="json")
    # Ensure datetime fields are ISO strings
    for key in ("created_at", "updated_at"):
        val = data.get(key)
        if isinstance(val, datetime):
            data[key] = val.isoformat()

    output_path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path


def load_master_index(path: Path) -> MasterIndex:
    """Load a MasterIndex from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        A MasterIndex instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return MasterIndex.model_validate(data)
