"""Pydantic models for Sonar quality findings."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FindingLevel(str, Enum):
    """Severity level of a quality finding."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCategory(str, Enum):
    """Category of a quality finding."""
    NAMING = "naming"
    COMPLEXITY = "complexity"
    DEAD_CODE = "dead_code"
    CONVENTION = "convention"
    STRUCTURE = "structure"


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single code quality finding."""
    finding_id: str
    category: FindingCategory
    level: FindingLevel
    message: str
    file_path: str
    line: Optional[int] = None
    entity_id: Optional[str] = None
    suggestion: Optional[str] = None


# ---------------------------------------------------------------------------
# SonarReport
# ---------------------------------------------------------------------------

class SonarReport(BaseModel):
    """Collection of quality findings produced by a Sonar scan."""
    findings: List[Finding] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)
    file_count: int = 0
    entity_count: int = 0
