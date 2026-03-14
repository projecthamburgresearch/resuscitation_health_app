"""Cortex metadata schema.

Defines the CortexBlock — the structured metadata that gets injected
into source code comments to provide LLMs with context about each entity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CortexBlock(BaseModel):
    """Structured metadata block for a code entity.

    This data is serialized into native comment syntax and placed
    above each function/class/method in the source code.

    Format: @blueprint:cortex { ... }
    """
    # Identity
    id: str
    entity_type: str

    # Timestamps
    created: datetime = Field(default_factory=datetime.now)
    last_visited: datetime = Field(default_factory=datetime.now)
    last_reviewed: Optional[datetime] = None

    # Relationships (bounded — only outgoing calls)
    calls: List[str] = Field(default_factory=list)
    uses: List[str] = Field(default_factory=list)

    # Execution context
    execution_order: Optional[int] = None
    control_flow: Optional[str] = None  # "sequential", "branching", "looping"

    # Metrics
    complexity: Optional[int] = None
    loc: Optional[int] = None

    # Tags
    tags: List[str] = Field(default_factory=list)

    def to_comment_dict(self) -> Dict[str, Any]:
        """Convert to a dict suitable for embedding in comments.

        Excludes None values and formats timestamps as ISO strings.
        """
        data: Dict[str, Any] = {
            "id": self.id,
            "type": self.entity_type,
            "created": self.created.isoformat(),
            "last_visited": self.last_visited.isoformat(),
        }
        if self.last_reviewed:
            data["last_reviewed"] = self.last_reviewed.isoformat()
        if self.calls:
            data["calls"] = self.calls
        if self.uses:
            data["uses"] = self.uses
        if self.execution_order is not None:
            data["exec_order"] = self.execution_order
        if self.control_flow:
            data["control_flow"] = self.control_flow
        if self.complexity is not None:
            data["complexity"] = self.complexity
        if self.loc is not None:
            data["loc"] = self.loc
        if self.tags:
            data["tags"] = self.tags
        return data

    @classmethod
    def from_comment_dict(cls, data: Dict[str, Any]) -> CortexBlock:
        """Parse a CortexBlock from a comment dictionary."""
        return cls(
            id=data.get("id", ""),
            entity_type=data.get("type", ""),
            created=datetime.fromisoformat(data["created"]) if "created" in data else datetime.now(),
            last_visited=datetime.fromisoformat(data["last_visited"]) if "last_visited" in data else datetime.now(),
            last_reviewed=datetime.fromisoformat(data["last_reviewed"]) if "last_reviewed" in data else None,
            calls=data.get("calls", []),
            uses=data.get("uses", []),
            execution_order=data.get("exec_order"),
            control_flow=data.get("control_flow"),
            complexity=data.get("complexity"),
            loc=data.get("loc"),
            tags=data.get("tags", []),
        )
