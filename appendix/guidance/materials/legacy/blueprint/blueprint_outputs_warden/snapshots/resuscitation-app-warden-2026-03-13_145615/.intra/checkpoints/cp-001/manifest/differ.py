"""Manifest differ — Compare two manifests to find changes.

Detects added, removed, and modified entities between manifest versions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from src.manifest.schema import Manifest, ManifestEntity


class EntityDiff(BaseModel):
    """Represents a change to a single entity."""
    entity_id: str
    entity_name: str
    entity_type: str
    change_type: str  # "added", "removed", "modified"
    file: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    # changes maps field_name -> {"old": ..., "new": ...}


class ManifestDiff(BaseModel):
    """Complete diff between two manifest versions."""
    old_root: str = ""
    new_root: str = ""
    added: List[EntityDiff] = Field(default_factory=list)
    removed: List[EntityDiff] = Field(default_factory=list)
    modified: List[EntityDiff] = Field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.removed) + len(self.modified)

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0

    def summary(self) -> Dict[str, int]:
        """Return a summary of changes by type."""
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "modified": len(self.modified),
            "total": self.total_changes,
        }


def diff_manifests(
    old: Manifest,
    new: Manifest,
    *,
    compare_fields: Optional[List[str]] = None,
) -> ManifestDiff:
    """Compare two manifests and return the differences.

    Args:
        old: The baseline manifest.
        new: The updated manifest.
        compare_fields: Fields to compare for modifications.
            Defaults to signature, complexity, loc, calls, called_by.

    Returns:
        ManifestDiff with added, removed, and modified entities.
    """
    if compare_fields is None:
        compare_fields = [
            "signature", "complexity", "loc",
            "calls", "called_by", "file",
            "start_line", "end_line",
        ]

    old_index: Dict[str, ManifestEntity] = {e.id: e for e in old.entities}
    new_index: Dict[str, ManifestEntity] = {e.id: e for e in new.entities}

    old_ids = set(old_index.keys())
    new_ids = set(new_index.keys())

    result = ManifestDiff(
        old_root=old.root_path,
        new_root=new.root_path,
    )

    # Added entities
    for eid in sorted(new_ids - old_ids):
        ent = new_index[eid]
        result.added.append(EntityDiff(
            entity_id=eid,
            entity_name=ent.name,
            entity_type=ent.type,
            change_type="added",
            file=ent.file,
        ))

    # Removed entities
    for eid in sorted(old_ids - new_ids):
        ent = old_index[eid]
        result.removed.append(EntityDiff(
            entity_id=eid,
            entity_name=ent.name,
            entity_type=ent.type,
            change_type="removed",
            file=ent.file,
        ))

    # Modified entities
    for eid in sorted(old_ids & new_ids):
        old_ent = old_index[eid]
        new_ent = new_index[eid]
        changes = _compare_entities(old_ent, new_ent, compare_fields)
        if changes:
            result.modified.append(EntityDiff(
                entity_id=eid,
                entity_name=new_ent.name,
                entity_type=new_ent.type,
                change_type="modified",
                file=new_ent.file,
                changes=changes,
            ))

    return result


def _compare_entities(
    old: ManifestEntity,
    new: ManifestEntity,
    fields: List[str],
) -> Dict[str, Any]:
    """Compare two entities on the given fields.

    Returns:
        Dict of changed fields mapping to {"old": ..., "new": ...}.
    """
    changes: Dict[str, Any] = {}

    for field in fields:
        old_val = getattr(old, field, None)
        new_val = getattr(new, field, None)

        # Normalize lists for comparison
        if isinstance(old_val, list) and isinstance(new_val, list):
            if sorted(old_val) != sorted(new_val):
                changes[field] = {"old": old_val, "new": new_val}
        elif old_val != new_val:
            changes[field] = {"old": old_val, "new": new_val}

    return changes
