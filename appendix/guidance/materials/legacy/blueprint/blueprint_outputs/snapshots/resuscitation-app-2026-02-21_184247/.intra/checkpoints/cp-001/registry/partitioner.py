"""Zone partitioning for the Registry domain.

Partitions a project's files into zones (groups) based on directory
structure.  Each top-level directory becomes a zone; oversized zones
are split further by subdirectory.  Cross-zone dependencies are
detected from edges that span zone boundaries.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

from src.core.config import BlueprintConfig
from src.core.io_utils import iter_files, normalize_path
from src.core.models import Edge
from src.registry.schema import ProjectProfile, Zone
from src.registry.scanner import _language_for_ext


def _zone_id_for(name: str) -> str:
    """Generate a deterministic zone ID from a zone name."""
    return f"zone::{name}"


def _dominant_language(file_paths: List[str]) -> str | None:
    """Determine the most common language among a list of file paths."""
    if not file_paths:
        return None
    counter: Counter[str] = Counter()
    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        lang = _language_for_ext(ext)
        if lang != "unknown":
            counter[lang] += 1
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def _split_zone_by_subdir(
    zone_name: str,
    root_path: str,
    file_paths: List[str],
    max_zone_files: int,
) -> List[Zone]:
    """Split an oversized zone into sub-zones by next-level subdirectory.

    If a sub-zone is still too large, it is returned as-is (one level of
    splitting only, to keep the algorithm predictable).
    """
    subdir_groups: Dict[str, List[str]] = defaultdict(list)

    for fp in file_paths:
        # fp is relative to the project root and uses forward slashes.
        # The top-level dir is already the zone_name.  We split by the
        # *next* directory component inside that top-level dir.
        parts = fp.split("/")
        if len(parts) <= 2:
            # File is directly inside the top-level dir (e.g., "src/main.py")
            subdir_groups[zone_name] = subdir_groups.get(zone_name, [])
            subdir_groups[zone_name].append(fp)
        else:
            # e.g., "src/utils/helpers.py" -> subdir = "src/utils"
            subdir_key = f"{parts[0]}/{parts[1]}"
            subdir_groups[subdir_key].append(fp)

    zones: List[Zone] = []
    for sub_name, sub_files in sorted(subdir_groups.items()):
        zid = _zone_id_for(sub_name)
        zones.append(Zone(
            zone_id=zid,
            name=sub_name,
            root_path=root_path,
            file_paths=sorted(sub_files),
            file_count=len(sub_files),
            language=_dominant_language(sub_files),
        ))

    return zones


def partition_into_zones(
    root: Path,
    profile: ProjectProfile,
    config: BlueprintConfig,
    max_zone_files: int = 500,
) -> List[Zone]:
    """Partition project files into zones based on directory structure.

    Each top-level directory becomes a zone.  If a zone exceeds
    *max_zone_files*, it is split further by its immediate subdirectories.
    Files that live directly in the project root (no subdirectory) are
    collected into a special ``root`` zone.

    Args:
        root: The project root directory.
        profile: The previously-computed ProjectProfile (used for context).
        config: Blueprint configuration (controls file discovery filters).
        max_zone_files: Maximum number of files per zone before splitting.

    Returns:
        A list of Zone objects covering all discovered files.
    """
    files = iter_files(
        root=root,
        focus=config.focus_path,
        include_patterns=config.include_patterns,
        exclude_patterns=config.exclude_patterns,
        max_files=config.max_files,
        max_file_size=config.max_file_size,
    )

    root_str = normalize_path(root, root) or "."

    # Group files by top-level directory
    toplevel_groups: Dict[str, List[str]] = defaultdict(list)

    for file_path in files:
        rel = normalize_path(file_path, root)
        parts = rel.split("/")
        if len(parts) == 1:
            # File is directly in the project root
            toplevel_groups["root"].append(rel)
        else:
            toplevel_groups[parts[0]].append(rel)

    # Build zones
    zones: List[Zone] = []
    for top_name in sorted(toplevel_groups.keys()):
        group_files = toplevel_groups[top_name]

        if len(group_files) > max_zone_files:
            # Split oversized zone by subdirectory
            sub_zones = _split_zone_by_subdir(
                zone_name=top_name,
                root_path=root_str,
                file_paths=group_files,
                max_zone_files=max_zone_files,
            )
            zones.extend(sub_zones)
        else:
            zid = _zone_id_for(top_name)
            zones.append(Zone(
                zone_id=zid,
                name=top_name,
                root_path=root_str,
                file_paths=sorted(group_files),
                file_count=len(group_files),
                language=_dominant_language(group_files),
            ))

    return zones


def _build_file_to_zone_map(zones: List[Zone]) -> Dict[str, str]:
    """Build a mapping from file path to zone ID."""
    mapping: Dict[str, str] = {}
    for zone in zones:
        for fp in zone.file_paths:
            mapping[fp] = zone.zone_id
    return mapping


def _entity_id_to_file(entity_id: str) -> str | None:
    """Extract the file path from a standard entity ID.

    Entity IDs follow the format ``TYPE::filepath::name``.
    """
    parts = entity_id.split("::")
    if len(parts) >= 3:
        return parts[1]
    return None


def detect_zone_dependencies(
    zones: List[Zone],
    edges: List[Edge],
) -> List[Zone]:
    """Detect cross-zone dependencies from edges and fill in each zone's
    dependency list.

    An edge whose source entity belongs to zone A and whose target entity
    belongs to zone B (A != B) creates a dependency from A to B.

    Args:
        zones: The list of zones to update in-place.
        edges: All edges from the analysis result.

    Returns:
        The same list of zones with ``dependencies`` populated.
    """
    file_to_zone = _build_file_to_zone_map(zones)
    zone_map: Dict[str, Zone] = {z.zone_id: z for z in zones}

    # Collect dependencies per zone
    zone_deps: Dict[str, Set[str]] = defaultdict(set)

    for edge in edges:
        src_file = _entity_id_to_file(edge.source)
        tgt_file = _entity_id_to_file(edge.target)

        if src_file is None or tgt_file is None:
            continue

        src_zone = file_to_zone.get(src_file)
        tgt_zone = file_to_zone.get(tgt_file)

        if src_zone and tgt_zone and src_zone != tgt_zone:
            zone_deps[src_zone].add(tgt_zone)

    # Update zones
    for zone in zones:
        deps = sorted(zone_deps.get(zone.zone_id, set()))
        zone.dependencies = deps

    return zones
