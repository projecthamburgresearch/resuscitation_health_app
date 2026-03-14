"""Manifest schema — Master knowledge graph index.

The Manifest is a serializable representation of the entire codebase:
all entities, their relationships, execution sequences, and architecture
groupings. It serves as the single source of truth for LLMs to understand
a project's structure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ManifestEntity(BaseModel):
    """An entity entry in the manifest."""
    id: str
    type: str
    name: str
    qualified_name: Optional[str] = None
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    complexity: Optional[int] = None
    loc: Optional[int] = None
    calls: List[str] = Field(default_factory=list)       # IDs this entity calls
    called_by: List[str] = Field(default_factory=list)    # IDs that call this entity
    uses: List[str] = Field(default_factory=list)         # IDs this entity uses
    used_by: List[str] = Field(default_factory=list)      # IDs that use this entity
    tags: List[str] = Field(default_factory=list)         # User-defined tags
    meta: Dict[str, Any] = Field(default_factory=dict)


class ManifestRelationship(BaseModel):
    """A relationship entry in the manifest."""
    source: str
    target: str
    relation: str
    confidence: float = 1.0


class ExecutionSequence(BaseModel):
    """An ordered execution sequence (e.g., request flow)."""
    name: str
    description: str = ""
    steps: List[str] = Field(default_factory=list)  # Ordered entity IDs
    entry_point: Optional[str] = None
    exit_point: Optional[str] = None


class ArchitectureGroup(BaseModel):
    """A logical grouping of entities (layer, module, feature)."""
    name: str
    description: str = ""
    entity_ids: List[str] = Field(default_factory=list)
    group_type: str = "module"  # module, layer, feature, package


class Manifest(BaseModel):
    """The complete project manifest.

    This is the master index file that LLMs consume to understand
    a project's architecture, relationships, and hotspots.
    """
    version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=datetime.now)
    root_path: str = ""
    entities: List[ManifestEntity] = Field(default_factory=list)
    relationships: List[ManifestRelationship] = Field(default_factory=list)
    execution_sequences: List[ExecutionSequence] = Field(default_factory=list)
    architecture_groups: List[ArchitectureGroup] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)

    # Indexes (populated on load)
    _entity_index: Dict[str, ManifestEntity] = {}
    _called_by_index: Dict[str, List[str]] = {}
    _used_by_index: Dict[str, List[str]] = {}

    def model_post_init(self, __context: Any) -> None:
        """Build indexes after initialization."""
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build lookup indexes from entity data."""
        self._entity_index = {e.id: e for e in self.entities}
        self._called_by_index = {}
        self._used_by_index = {}
        for ent in self.entities:
            for call_id in ent.calls:
                self._called_by_index.setdefault(call_id, []).append(ent.id)
            for use_id in ent.uses:
                self._used_by_index.setdefault(use_id, []).append(ent.id)

    def get_entity(self, entity_id: str) -> Optional[ManifestEntity]:
        """Look up an entity by ID."""
        return self._entity_index.get(entity_id)

    def get_callers(self, entity_id: str) -> List[str]:
        """Get IDs of entities that call the given entity."""
        return self._called_by_index.get(entity_id, [])

    def get_users(self, entity_id: str) -> List[str]:
        """Get IDs of entities that use the given entity."""
        return self._used_by_index.get(entity_id, [])
