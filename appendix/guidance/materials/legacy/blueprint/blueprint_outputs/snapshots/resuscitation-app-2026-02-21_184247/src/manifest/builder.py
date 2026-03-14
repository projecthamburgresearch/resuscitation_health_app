"""Manifest builder — Transforms AnalysisResult into a Manifest.

Takes the output of X-Ray (and optionally other domains) and produces
a complete Manifest with entities, relationships, and indexes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from src.core.io_utils import ensure_dir
from src.core.models import AnalysisResult, EntityType, RelationType
from src.manifest.schema import (
    ArchitectureGroup,
    Manifest,
    ManifestEntity,
    ManifestRelationship,
)


def build_manifest(
    result: AnalysisResult,
    *,
    include_types: Optional[Set[str]] = None,
) -> Manifest:
    """Build a Manifest from an AnalysisResult.

    Args:
        result: X-Ray or combined analysis result.
        include_types: If set, only include entities of these types.

    Returns:
        A populated Manifest.
    """
    # Build relationship lookup
    calls_map: Dict[str, List[str]] = {}      # entity -> [callees]
    called_by_map: Dict[str, List[str]] = {}  # entity -> [callers]
    uses_map: Dict[str, List[str]] = {}       # entity -> [uses]
    used_by_map: Dict[str, List[str]] = {}    # entity -> [used_by]

    for edge in result.edges:
        if edge.relation == RelationType.CALLS:
            calls_map.setdefault(edge.source, []).append(edge.target)
            called_by_map.setdefault(edge.target, []).append(edge.source)
        elif edge.relation == RelationType.USES:
            uses_map.setdefault(edge.source, []).append(edge.target)
            used_by_map.setdefault(edge.target, []).append(edge.source)

    # Build manifest entities
    manifest_entities: List[ManifestEntity] = []

    for ent in result.entities:
        if include_types and ent.type.value not in include_types:
            continue

        me = ManifestEntity(
            id=ent.id,
            type=ent.type.value,
            name=ent.name,
            qualified_name=ent.qualified_name,
            file=ent.location.file if ent.location else None,
            start_line=ent.location.start_line if ent.location else None,
            end_line=ent.location.end_line if ent.location else None,
            language=ent.language,
            signature=ent.signature,
            docstring=ent.docstring,
            complexity=ent.metrics.cyclomatic_complexity if ent.metrics else None,
            loc=ent.metrics.loc_code if ent.metrics else None,
            calls=_dedup(calls_map.get(ent.id, [])),
            called_by=_dedup(called_by_map.get(ent.id, [])),
            uses=_dedup(uses_map.get(ent.id, [])),
            used_by=_dedup(used_by_map.get(ent.id, [])),
            meta=ent.meta,
        )
        manifest_entities.append(me)

    # Build relationships
    relationships: List[ManifestRelationship] = []
    for edge in result.edges:
        relationships.append(ManifestRelationship(
            source=edge.source,
            target=edge.target,
            relation=edge.relation.value,
            confidence=edge.confidence,
        ))

    # Auto-detect architecture groups by file directory
    groups = _build_architecture_groups(manifest_entities)

    # Stats
    type_counts: Dict[str, int] = {}
    for ent in manifest_entities:
        type_counts[ent.type] = type_counts.get(ent.type, 0) + 1

    stats = {
        "entity_count": len(manifest_entities),
        "relationship_count": len(relationships),
        "entity_types": type_counts,
        "files_indexed": len({e.file for e in manifest_entities if e.file}),
        "source_domain": result.domain,
        "source_version": result.version,
    }

    return Manifest(
        root_path=result.root_path,
        entities=manifest_entities,
        relationships=relationships,
        architecture_groups=groups,
        stats=stats,
    )


def save_manifest(
    manifest: Manifest,
    output_path: Path,
    fmt: str = "yaml",
) -> Path:
    """Save a Manifest to disk.

    Args:
        manifest: The Manifest to save.
        output_path: Output directory.
        fmt: Format — 'yaml' or 'json'.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)

    data = manifest.model_dump(exclude_none=True, mode="json")

    if fmt == "yaml":
        out_file = output_path / "manifest.yaml"
        out_file.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        out_file = output_path / "manifest.json"
        out_file.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    return out_file


def load_manifest(path: Path) -> Manifest:
    """Load a Manifest from a file.

    Args:
        path: Path to manifest.yaml or manifest.json.

    Returns:
        Parsed Manifest.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yml", ".yaml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return Manifest.model_validate(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dedup(items: List[str]) -> List[str]:
    """Deduplicate while preserving order."""
    seen: set = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _build_architecture_groups(
    entities: List[ManifestEntity],
) -> List[ArchitectureGroup]:
    """Auto-detect architecture groups from file paths."""
    dir_entities: Dict[str, List[str]] = {}

    for ent in entities:
        if ent.file:
            parts = ent.file.split("/")
            if len(parts) > 1:
                dir_name = parts[0]
            else:
                dir_name = "root"
            dir_entities.setdefault(dir_name, []).append(ent.id)

    groups = []
    for dir_name, entity_ids in sorted(dir_entities.items()):
        if len(entity_ids) < 2:
            continue
        groups.append(ArchitectureGroup(
            name=dir_name,
            entity_ids=entity_ids,
            group_type="package",
        ))

    return groups
