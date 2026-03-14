"""Central Pydantic data models for Blueprint.

All domains communicate through these models. Entity and Edge are the
fundamental units; AnalysisResult is the exchange format between domains.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """Types of code entities Blueprint can identify."""
    FILE = "file"
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    EXPORT = "export"
    ENDPOINT = "endpoint"
    NETWORK_REQUEST = "network_request"
    TABLE = "table"
    DATASET = "dataset"
    COLUMN = "column"
    CHUNK = "chunk"
    INTERFACE = "interface"
    ENUM = "enum"
    TYPE_ALIAS = "type_alias"
    DECORATOR = "decorator"
    STRUCT = "struct"
    TRAIT = "trait"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    DEFINES = "defines"
    CALLS = "calls"
    CALLED_BY = "called_by"
    USES = "uses"
    USED_BY = "used_by"
    IMPORTS = "imports"
    IMPORTED_BY = "imported_by"
    EXPORTS = "exports"
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    INHERITS = "inherits"
    INHERITED_BY = "inherited_by"
    IMPLEMENTS = "implements"
    IMPLEMENTED_BY = "implemented_by"
    DECLARES_ENDPOINT = "declares_endpoint"
    CONTAINS_REQUEST = "contains_request"
    MATCHES_ENDPOINT = "matches_endpoint"
    TOUCHES_TABLE = "touches_table"
    LINKS_TO_FILE = "links_to_file"
    MENTIONS = "mentions"
    HAS_COLUMN = "has_column"
    HAS_CHUNK = "has_chunk"
    DECLARES_DATASET = "declares_dataset"
    ORPHAN_OF = "orphan_of"


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class Location(BaseModel):
    """Source code location of an entity."""
    file: str
    start_line: int
    start_col: int = 0
    end_line: int = 0
    end_col: int = 0

    def __str__(self) -> str:
        return f"{self.file}:{self.start_line}"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class Metrics(BaseModel):
    """Code quality metrics for an entity."""
    cyclomatic_complexity: Optional[int] = None
    cognitive_complexity: Optional[int] = None
    loc_total: Optional[int] = None
    loc_code: Optional[int] = None
    loc_comment: Optional[int] = None
    loc_blank: Optional[int] = None
    nesting_depth_max: Optional[int] = None
    nesting_depth_avg: Optional[float] = None
    fan_in: Optional[int] = None
    fan_out: Optional[int] = None
    parameter_count: Optional[int] = None
    statement_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Git info
# ---------------------------------------------------------------------------

class GitInfo(BaseModel):
    """Git-derived metadata for an entity or file."""
    last_modified: Optional[datetime] = None
    last_author: Optional[str] = None
    change_count: Optional[int] = None
    churn: Optional[int] = None


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    """Source code evidence supporting a relationship."""
    file: str
    start_line: int
    end_line: int
    snippet: str = ""


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    """A code entity: function, class, method, file, variable, etc."""
    id: str  # Unique key: "TYPE::filepath::name"
    type: EntityType
    name: str
    qualified_name: Optional[str] = None
    location: Optional[Location] = None
    language: Optional[str] = None
    signature: Optional[str] = None
    return_type: Optional[str] = None
    parameters: Optional[List[str]] = None
    decorators: Optional[List[str]] = None
    docstring: Optional[str] = None
    metrics: Optional[Metrics] = None
    git_info: Optional[GitInfo] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Entity):
            return self.id == other.id
        return False


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

class Edge(BaseModel):
    """A directed relationship between two entities."""
    source: str  # Entity ID
    target: str  # Entity ID
    relation: RelationType
    confidence: float = 1.0
    evidence: Optional[List[Evidence]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analysis Result (domain exchange format)
# ---------------------------------------------------------------------------

class AnalysisResult(BaseModel):
    """Output of a single domain run. The universal exchange format."""
    domain: str  # "xray", "cortex", "manifest"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    root_path: str
    entities: List[Entity] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    def entity_count(self) -> int:
        return len(self.entities)

    def edge_count(self) -> int:
        return len(self.edges)

    def entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        return [e for e in self.entities if e.type == entity_type]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None
