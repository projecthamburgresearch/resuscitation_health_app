"""Manifest query engine.

Provides search and query capabilities over the Manifest index.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from src.manifest.schema import Manifest, ManifestEntity


def query_by_name(
    manifest: Manifest,
    name: str,
    *,
    exact: bool = False,
) -> List[ManifestEntity]:
    """Find entities by name.

    Args:
        manifest: The manifest to search.
        name: Name to search for.
        exact: If True, require exact match; otherwise substring match.

    Returns:
        List of matching entities.
    """
    name_lower = name.lower()
    if exact:
        return [e for e in manifest.entities if e.name.lower() == name_lower]
    return [e for e in manifest.entities if name_lower in e.name.lower()]


def query_by_type(
    manifest: Manifest,
    entity_type: str,
) -> List[ManifestEntity]:
    """Find all entities of a given type.

    Args:
        manifest: The manifest to search.
        entity_type: Type string (e.g., 'function', 'class').

    Returns:
        List of matching entities.
    """
    return [e for e in manifest.entities if e.type == entity_type]


def query_by_file(
    manifest: Manifest,
    file_path: str,
    *,
    exact: bool = False,
) -> List[ManifestEntity]:
    """Find entities in a specific file.

    Args:
        manifest: The manifest to search.
        file_path: File path to match.
        exact: If True, exact match; otherwise substring.

    Returns:
        List of matching entities.
    """
    if exact:
        return [e for e in manifest.entities if e.file == file_path]
    path_lower = file_path.lower()
    return [
        e for e in manifest.entities
        if e.file and path_lower in e.file.lower()
    ]


def query_by_tag(
    manifest: Manifest,
    tag: str,
) -> List[ManifestEntity]:
    """Find entities with a specific tag.

    Args:
        manifest: The manifest to search.
        tag: Tag to search for.

    Returns:
        List of matching entities.
    """
    tag_lower = tag.lower()
    return [
        e for e in manifest.entities
        if any(tag_lower in t.lower() for t in e.tags)
    ]


def query_callers(
    manifest: Manifest,
    entity_id: str,
) -> List[ManifestEntity]:
    """Find all entities that call the given entity.

    Args:
        manifest: The manifest to search.
        entity_id: ID of the target entity.

    Returns:
        List of calling entities.
    """
    caller_ids = manifest.get_callers(entity_id)
    return [
        manifest.get_entity(cid)
        for cid in caller_ids
        if manifest.get_entity(cid) is not None
    ]


def query_callees(
    manifest: Manifest,
    entity_id: str,
) -> List[ManifestEntity]:
    """Find all entities called by the given entity.

    Args:
        manifest: The manifest to search.
        entity_id: ID of the source entity.

    Returns:
        List of called entities.
    """
    ent = manifest.get_entity(entity_id)
    if not ent:
        return []
    return [
        manifest.get_entity(cid)
        for cid in ent.calls
        if manifest.get_entity(cid) is not None
    ]


def query_complexity_hotspots(
    manifest: Manifest,
    *,
    min_complexity: int = 5,
    limit: int = 20,
) -> List[ManifestEntity]:
    """Find entities with highest cyclomatic complexity.

    Args:
        manifest: The manifest to search.
        min_complexity: Minimum complexity to include.
        limit: Maximum results.

    Returns:
        Entities sorted by complexity descending.
    """
    hotspots = [
        e for e in manifest.entities
        if e.complexity is not None and e.complexity >= min_complexity
    ]
    hotspots.sort(key=lambda e: -(e.complexity or 0))
    return hotspots[:limit]


def query_large_entities(
    manifest: Manifest,
    *,
    min_loc: int = 50,
    limit: int = 20,
) -> List[ManifestEntity]:
    """Find largest entities by lines of code.

    Args:
        manifest: The manifest to search.
        min_loc: Minimum LOC to include.
        limit: Maximum results.

    Returns:
        Entities sorted by LOC descending.
    """
    large = [
        e for e in manifest.entities
        if e.loc is not None and e.loc >= min_loc
    ]
    large.sort(key=lambda e: -(e.loc or 0))
    return large[:limit]


def query_orphans(
    manifest: Manifest,
) -> List[ManifestEntity]:
    """Find entities with no callers and no callees.

    Returns:
        List of orphan entities.
    """
    return [
        e for e in manifest.entities
        if not e.calls and not e.called_by
        and e.type not in ("file", "import", "export", "variable", "constant")
    ]


def search(
    manifest: Manifest,
    predicate: Callable[[ManifestEntity], bool],
) -> List[ManifestEntity]:
    """Generic search with a predicate function.

    Args:
        manifest: The manifest to search.
        predicate: Function that takes a ManifestEntity and returns bool.

    Returns:
        List of matching entities.
    """
    return [e for e in manifest.entities if predicate(e)]
