"""Chronicle — Run history, milestones, delta tracking, and persistence.

Tracks Blueprint analysis runs over time: when they happened, what changed,
and named milestone snapshots. Persists as chronicle.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.io_utils import ensure_dir
from src.core.models import AnalysisResult


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RunRecord(BaseModel):
    """Record of a single Blueprint scan run."""
    id: str  # UUID or timestamp-based
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    domains_run: List[str] = Field(default_factory=list)
    root_path: str = ""
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    entity_count: int = 0
    edge_count: int = 0
    error_count: int = 0

    @property
    def is_complete(self) -> bool:
        return self.finished_at is not None


class DeltaRecord(BaseModel):
    """Record of changes between two runs."""
    from_run: str  # Run ID
    to_run: str    # Run ID
    entities_added: int = 0
    entities_removed: int = 0
    entities_modified: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class Milestone(BaseModel):
    """A named milestone (snapshot) in the project's analysis history."""
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    run_id: str = ""  # Associated run
    tags: List[str] = Field(default_factory=list)
    checklist: List[Dict[str, Any]] = Field(default_factory=list)
    # checklist items: {"task": "...", "done": True/False}


class Chronicle(BaseModel):
    """Complete analysis history for a project."""
    project_root: str = ""
    runs: List[RunRecord] = Field(default_factory=list)
    deltas: List[DeltaRecord] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)

    @property
    def latest_run(self) -> Optional[RunRecord]:
        return self.runs[-1] if self.runs else None

    @property
    def run_count(self) -> int:
        return len(self.runs)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        for r in self.runs:
            if r.id == run_id:
                return r
        return None

    def get_milestone(self, name: str) -> Optional[Milestone]:
        for m in self.milestones:
            if m.name == name:
                return m
        return None


# ---------------------------------------------------------------------------
# Tracker — run tracking and milestone management
# ---------------------------------------------------------------------------

def start_run(
    chronicle: Chronicle,
    root_path: str,
    domains: List[str],
    config: Optional[Dict[str, Any]] = None,
) -> RunRecord:
    """Start tracking a new analysis run.

    Args:
        chronicle: The chronicle to add the run to.
        root_path: Project root path.
        domains: List of domain names being run.
        config: Optional config snapshot.

    Returns:
        The new RunRecord (in-progress).
    """
    run = RunRecord(
        id=str(uuid.uuid4())[:8],
        started_at=datetime.now(),
        domains_run=domains,
        root_path=root_path,
        config_snapshot=config or {},
    )
    chronicle.runs.append(run)
    return run


def end_run(
    run: RunRecord,
    results: List[AnalysisResult],
) -> None:
    """Mark a run as complete with its results.

    Args:
        run: The RunRecord to complete.
        results: Results from all domains.
    """
    run.finished_at = datetime.now()
    run.duration_seconds = (
        run.finished_at - run.started_at
    ).total_seconds()

    total_entities = 0
    total_edges = 0
    total_errors = 0
    combined_stats: Dict[str, Any] = {}

    for result in results:
        total_entities += result.entity_count()
        total_edges += result.edge_count()
        total_errors += len(result.errors)
        combined_stats[result.domain] = result.stats

    run.entity_count = total_entities
    run.edge_count = total_edges
    run.error_count = total_errors
    run.stats = combined_stats


def record_delta(
    chronicle: Chronicle,
    from_run_id: str,
    to_run_id: str,
    added: int = 0,
    removed: int = 0,
    modified: int = 0,
) -> DeltaRecord:
    """Record changes between two runs.

    Args:
        chronicle: The chronicle.
        from_run_id: Previous run ID.
        to_run_id: Current run ID.
        added: Entities added.
        removed: Entities removed.
        modified: Entities modified.

    Returns:
        The new DeltaRecord.
    """
    delta = DeltaRecord(
        from_run=from_run_id,
        to_run=to_run_id,
        entities_added=added,
        entities_removed=removed,
        entities_modified=modified,
    )
    chronicle.deltas.append(delta)
    return delta


def create_milestone(
    chronicle: Chronicle,
    name: str,
    description: str = "",
    run_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    checklist: Optional[List[Dict[str, Any]]] = None,
) -> Milestone:
    """Create a named milestone.

    Args:
        chronicle: The chronicle.
        name: Milestone name.
        description: Description.
        run_id: Associated run ID (defaults to latest run).
        tags: Optional tags.
        checklist: Optional checklist items.

    Returns:
        The new Milestone.
    """
    if run_id is None and chronicle.latest_run:
        run_id = chronicle.latest_run.id

    milestone = Milestone(
        name=name,
        description=description,
        run_id=run_id or "",
        tags=tags or [],
        checklist=checklist or [],
    )
    chronicle.milestones.append(milestone)
    return milestone


# ---------------------------------------------------------------------------
# Storage — save/load chronicle as JSON
# ---------------------------------------------------------------------------

def save_chronicle(
    chronicle: Chronicle,
    output_path: Path,
) -> Path:
    """Save a Chronicle to disk as JSON.

    Args:
        chronicle: The chronicle to save.
        output_path: Output directory.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)
    out_file = output_path / "chronicle.json"
    data = chronicle.model_dump(mode="json")
    out_file.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )
    return out_file


def load_chronicle(path: Path) -> Chronicle:
    """Load a Chronicle from disk.

    Args:
        path: Path to chronicle.json.

    Returns:
        Parsed Chronicle.
    """
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return Chronicle.model_validate(data)


def get_or_create_chronicle(output_path: Path) -> Chronicle:
    """Load existing chronicle or create a new one.

    Args:
        output_path: Directory where chronicle.json lives.

    Returns:
        Chronicle instance.
    """
    chronicle_file = output_path / "chronicle.json"
    if chronicle_file.exists():
        try:
            return load_chronicle(chronicle_file)
        except Exception:
            pass
    return Chronicle()
