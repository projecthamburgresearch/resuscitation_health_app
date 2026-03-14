"""Intra-run versioning system for snapshot workspaces.

Provides git-like version control WITHIN a snapshot during the intra-run
tuning phase. This is the safety net for autonomous/semi-autonomous tuning.

Key concepts:
- Checkpoint: A saved state of the snapshot's src/ at a point in time
- Change: A logged modification (code, config, or parameter)
- Revert: Restore to a previous checkpoint

This is NOT for fixing bugs (that happens in main src/).
This IS for safe experimentation during tuning.

Usage:
    from src.core.intra import IntraVersioning

    iv = IntraVersioning(snapshot_dir)

    # Before making changes, create a checkpoint
    iv.checkpoint("before-preset-change")

    # Log what you're changing
    iv.log_change(
        change_type="parameter",
        description="Changed preset from standard to deep",
        before={"preset": "standard"},
        after={"preset": "deep"},
    )

    # If things go wrong, revert
    iv.revert("before-preset-change")

    # See history
    history = iv.get_history()
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Checkpoint:
    """A saved state of the snapshot's src/."""
    checkpoint_id: str
    name: str
    created_at: str
    description: str = ""
    run_id: Optional[str] = None  # Which run triggered this checkpoint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "created_at": self.created_at,
            "description": self.description,
            "run_id": self.run_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            name=data["name"],
            created_at=data["created_at"],
            description=data.get("description", ""),
            run_id=data.get("run_id"),
        )


@dataclass
class Change:
    """A logged modification during intra-run tuning."""
    change_id: str
    timestamp: str
    change_type: str  # "code", "config", "parameter"
    description: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    checkpoint_ref: Optional[str] = None  # Checkpoint before this change
    run_id: Optional[str] = None  # Which run this affected
    outcome: Optional[str] = None  # Result of the change (filled in after run)
    files_affected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp,
            "change_type": self.change_type,
            "description": self.description,
            "before": self.before,
            "after": self.after,
            "checkpoint_ref": self.checkpoint_ref,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "files_affected": self.files_affected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Change":
        return cls(
            change_id=data["change_id"],
            timestamp=data["timestamp"],
            change_type=data["change_type"],
            description=data["description"],
            before=data.get("before", {}),
            after=data.get("after", {}),
            checkpoint_ref=data.get("checkpoint_ref"),
            run_id=data.get("run_id"),
            outcome=data.get("outcome"),
            files_affected=data.get("files_affected", []),
        )


@dataclass
class IntraLog:
    """The full intra-run versioning log."""
    snapshot_id: str
    created_at: str
    checkpoints: List[Checkpoint] = field(default_factory=list)
    changes: List[Change] = field(default_factory=list)
    current_checkpoint: Optional[str] = None  # HEAD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "changes": [c.to_dict() for c in self.changes],
            "current_checkpoint": self.current_checkpoint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntraLog":
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            checkpoints=[Checkpoint.from_dict(c) for c in data.get("checkpoints", [])],
            changes=[Change.from_dict(c) for c in data.get("changes", [])],
            current_checkpoint=data.get("current_checkpoint"),
        )


class IntraVersioning:
    """Version control system for intra-run tuning within a snapshot."""

    def __init__(self, snapshot_dir: Path):
        """Initialize intra-run versioning for a snapshot.

        Args:
            snapshot_dir: Path to the snapshot directory.
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.src_dir = self.snapshot_dir / "src"
        self.intra_dir = self.snapshot_dir / ".intra"
        self.checkpoints_dir = self.intra_dir / "checkpoints"
        self.log_path = self.intra_dir / "intra-log.json"

        # Initialize if needed
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Ensure the intra versioning system is initialized."""
        if not self.intra_dir.exists():
            self.intra_dir.mkdir(parents=True)
            self.checkpoints_dir.mkdir()

            # Create initial log
            log = IntraLog(
                snapshot_id=self.snapshot_dir.name,
                created_at=datetime.now().isoformat(),
            )
            self._save_log(log)

            # Create initial checkpoint (the boot state)
            self.checkpoint("initial", description="Original boot state from src/")

    def _load_log(self) -> IntraLog:
        """Load the intra-run log."""
        if self.log_path.exists():
            data = json.loads(self.log_path.read_text(encoding="utf-8"))
            return IntraLog.from_dict(data)
        return IntraLog(
            snapshot_id=self.snapshot_dir.name,
            created_at=datetime.now().isoformat(),
        )

    def _save_log(self, log: IntraLog) -> None:
        """Save the intra-run log."""
        self.log_path.write_text(
            json.dumps(log.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix."""
        log = self._load_log()
        if prefix == "cp":
            num = len(log.checkpoints) + 1
        else:
            num = len(log.changes) + 1
        return f"{prefix}-{num:03d}"

    def checkpoint(
        self,
        name: str,
        description: str = "",
        run_id: Optional[str] = None,
    ) -> str:
        """Create a checkpoint of the current src/ state.

        Args:
            name: Short name for this checkpoint (e.g., "before-preset-change").
            description: Longer description of why this checkpoint was created.
            run_id: Optional run ID that triggered this checkpoint.

        Returns:
            The checkpoint ID.
        """
        log = self._load_log()

        # Generate checkpoint ID
        checkpoint_id = self._generate_id("cp")

        # Create checkpoint directory
        checkpoint_path = self.checkpoints_dir / checkpoint_id

        # Copy src/ to checkpoint (excluding __pycache__)
        if self.src_dir.exists():
            shutil.copytree(
                self.src_dir,
                checkpoint_path,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )

        # Record checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            name=name,
            created_at=datetime.now().isoformat(),
            description=description,
            run_id=run_id,
        )
        log.checkpoints.append(checkpoint)
        log.current_checkpoint = checkpoint_id

        self._save_log(log)
        return checkpoint_id

    def log_change(
        self,
        change_type: str,
        description: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        files_affected: Optional[List[str]] = None,
        run_id: Optional[str] = None,
        auto_checkpoint: bool = True,
    ) -> str:
        """Log a change made during intra-run tuning.

        Args:
            change_type: Type of change ("code", "config", "parameter").
            description: What was changed and why.
            before: State before the change.
            after: State after the change.
            files_affected: List of files modified.
            run_id: Which run this change is for.
            auto_checkpoint: If True, create a checkpoint before the change.

        Returns:
            The change ID.
        """
        log = self._load_log()

        # Auto-checkpoint before change
        checkpoint_ref = log.current_checkpoint
        if auto_checkpoint:
            checkpoint_ref = self.checkpoint(
                name=f"before-{change_type}",
                description=f"Auto-checkpoint before: {description}",
                run_id=run_id,
            )
            log = self._load_log()  # Reload after checkpoint

        # Generate change ID
        change_id = self._generate_id("ch")

        # Record change
        change = Change(
            change_id=change_id,
            timestamp=datetime.now().isoformat(),
            change_type=change_type,
            description=description,
            before=before or {},
            after=after or {},
            checkpoint_ref=checkpoint_ref,
            run_id=run_id,
            files_affected=files_affected or [],
        )
        log.changes.append(change)

        self._save_log(log)
        return change_id

    def record_outcome(
        self,
        change_id: str,
        outcome: str,
        run_id: Optional[str] = None,
    ) -> None:
        """Record the outcome of a change after running.

        Args:
            change_id: The change ID to update.
            outcome: Description of the outcome (e.g., "entities increased from 164 to 210").
            run_id: The run ID that produced this outcome.
        """
        log = self._load_log()

        for change in log.changes:
            if change.change_id == change_id:
                change.outcome = outcome
                if run_id:
                    change.run_id = run_id
                break

        self._save_log(log)

    def revert(self, checkpoint_id: str) -> bool:
        """Revert src/ to a previous checkpoint.

        Args:
            checkpoint_id: The checkpoint ID to revert to.

        Returns:
            True if successful, False otherwise.
        """
        log = self._load_log()

        # Find the checkpoint
        checkpoint = None
        for cp in log.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break

        if checkpoint is None:
            return False

        checkpoint_path = self.checkpoints_dir / checkpoint_id
        if not checkpoint_path.exists():
            return False

        # Log the revert as a change
        self.log_change(
            change_type="revert",
            description=f"Reverted to checkpoint: {checkpoint.name}",
            before={"checkpoint": log.current_checkpoint},
            after={"checkpoint": checkpoint_id},
            auto_checkpoint=True,  # Save current state before reverting
        )

        # Remove current src/
        if self.src_dir.exists():
            shutil.rmtree(self.src_dir)

        # Copy checkpoint to src/
        shutil.copytree(checkpoint_path, self.src_dir)

        # Update current checkpoint
        log = self._load_log()  # Reload
        log.current_checkpoint = checkpoint_id
        self._save_log(log)

        return True

    def get_checkpoints(self) -> List[Checkpoint]:
        """Get all checkpoints."""
        log = self._load_log()
        return log.checkpoints

    def get_changes(self) -> List[Change]:
        """Get all logged changes."""
        log = self._load_log()
        return log.changes

    def get_history(self) -> Dict[str, Any]:
        """Get the full intra-run history.

        Returns a summary of all checkpoints and changes.
        """
        log = self._load_log()

        return {
            "snapshot_id": log.snapshot_id,
            "created_at": log.created_at,
            "current_checkpoint": log.current_checkpoint,
            "total_checkpoints": len(log.checkpoints),
            "total_changes": len(log.changes),
            "checkpoints": [cp.to_dict() for cp in log.checkpoints],
            "changes": [ch.to_dict() for ch in log.changes],
            "changes_by_type": self._group_changes_by_type(log.changes),
        }

    def _group_changes_by_type(self, changes: List[Change]) -> Dict[str, int]:
        """Group changes by type."""
        by_type: Dict[str, int] = {}
        for change in changes:
            by_type[change.change_type] = by_type.get(change.change_type, 0) + 1
        return by_type

    def get_diff_summary(
        self,
        from_checkpoint: str,
        to_checkpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a summary of changes between two checkpoints.

        Args:
            from_checkpoint: Starting checkpoint ID.
            to_checkpoint: Ending checkpoint ID. If None, uses current state.

        Returns:
            Summary of changes between the checkpoints.
        """
        log = self._load_log()

        # Find checkpoint indices
        from_idx = -1
        to_idx = len(log.checkpoints)

        for i, cp in enumerate(log.checkpoints):
            if cp.checkpoint_id == from_checkpoint:
                from_idx = i
            if to_checkpoint and cp.checkpoint_id == to_checkpoint:
                to_idx = i

        if from_idx == -1:
            return {"error": f"Checkpoint {from_checkpoint} not found"}

        # Get changes between checkpoints
        changes_between = []
        for change in log.changes:
            # Find when this change was made relative to checkpoints
            for i, cp in enumerate(log.checkpoints):
                if change.checkpoint_ref == cp.checkpoint_id:
                    if from_idx <= i < to_idx:
                        changes_between.append(change)
                    break

        return {
            "from_checkpoint": from_checkpoint,
            "to_checkpoint": to_checkpoint or "current",
            "changes": [ch.to_dict() for ch in changes_between],
            "total_changes": len(changes_between),
        }

    def can_revert(self) -> bool:
        """Check if there are any checkpoints to revert to."""
        log = self._load_log()
        return len(log.checkpoints) > 1  # More than just initial


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def init_intra_versioning(snapshot_dir: Path) -> IntraVersioning:
    """Initialize intra-run versioning for a snapshot.

    This is called automatically when a snapshot is booted.
    """
    return IntraVersioning(snapshot_dir)


def load_intra_log(snapshot_dir: Path) -> Optional[IntraLog]:
    """Load the intra-run log for a snapshot."""
    log_path = snapshot_dir / ".intra" / "intra-log.json"
    if log_path.exists():
        data = json.loads(log_path.read_text(encoding="utf-8"))
        return IntraLog.from_dict(data)
    return None
