"""Pydantic models for the Registry domain.

The Registry is the master index and reconciliation layer for Blueprint.
These models define the project profile, zone partitioning, registry entries,
and the top-level master index.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Project Profile
# ---------------------------------------------------------------------------

class ProjectProfile(BaseModel):
    """Scope detection results for a project.

    Captures high-level statistics about the project's size, language
    distribution, and estimated complexity.
    """

    total_files: int = 0
    total_size_bytes: int = 0
    language_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of language name to file count.",
    )
    largest_files: List[Tuple[str, int]] = Field(
        default_factory=list,
        description="List of (relative_path, size_bytes) for the largest files.",
    )
    estimated_entities: int = 0
    directory_count: int = 0


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------

class Zone(BaseModel):
    """A partition of the project for parallel/incremental processing.

    Each zone groups a set of files that can be analyzed independently.
    Zones are typically aligned with top-level directory boundaries.
    """

    zone_id: str
    name: str
    root_path: str
    file_paths: List[str] = Field(default_factory=list)
    file_count: int = 0
    language: Optional[str] = Field(
        default=None,
        description="Dominant language in this zone.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Zone IDs that this zone depends on.",
    )


# ---------------------------------------------------------------------------
# Registry Entry
# ---------------------------------------------------------------------------

class RegistryEntry(BaseModel):
    """Metadata for one entity in the master index.

    Tracks an entity across multiple analysis runs, recording when it was
    first and last seen, how many times it changed, and its caller/callee
    relationships.
    """

    entity_id: str
    entity_type: str
    name: str
    qualified_name: Optional[str] = None
    file_path: str
    zone_id: str
    line: int
    language: str
    signature: Optional[str] = None
    callers: List[str] = Field(
        default_factory=list,
        description="Entity IDs that call this entity.",
    )
    callees: List[str] = Field(
        default_factory=list,
        description="Entity IDs that this entity calls.",
    )
    last_seen_run: str
    first_seen_run: str
    change_count: int = 0


# ---------------------------------------------------------------------------
# Master Index
# ---------------------------------------------------------------------------

class MasterIndex(BaseModel):
    """The top-level registry: the master index of all entities.

    Holds the project profile, zone partitioning, and a dictionary of
    every entity ever seen, along with run history and aggregate stats.
    """

    project_name: str
    project_root: str
    version: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    profile: ProjectProfile = Field(default_factory=ProjectProfile)
    zones: List[Zone] = Field(default_factory=list)
    entries: Dict[str, RegistryEntry] = Field(
        default_factory=dict,
        description="Mapping of entity_id to RegistryEntry.",
    )
    run_history: List[str] = Field(
        default_factory=list,
        description="Ordered list of run IDs.",
    )
    stats: Dict[str, Any] = Field(default_factory=dict)
