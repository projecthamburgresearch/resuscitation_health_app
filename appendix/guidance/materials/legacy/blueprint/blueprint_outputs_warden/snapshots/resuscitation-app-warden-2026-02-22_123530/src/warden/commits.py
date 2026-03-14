"""Warden local commit tracking.

Provides a local version control layer for tracking changes made
by the warden. This allows reverting to previous states without
affecting the actual git repository.

Each commit records:
- What changed
- When it changed
- Why it changed (linked to decision)
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Change:
    """A single file change."""
    file: str
    type: str  # add, modify, delete
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"file": self.file, "type": self.type}
        if self.before_hash:
            d["before_hash"] = self.before_hash
        if self.after_hash:
            d["after_hash"] = self.after_hash
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Change":
        return cls(
            file=data["file"],
            type=data["type"],
            before_hash=data.get("before_hash"),
            after_hash=data.get("after_hash"),
        )


@dataclass
class Commit:
    """A local commit record."""
    id: str
    timestamp: str
    message: str
    changes: List[Change] = field(default_factory=list)
    decision_id: Optional[str] = None
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "message": self.message,
            "changes": [c.to_dict() for c in self.changes],
            "decision_id": self.decision_id,
            "parent_id": self.parent_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Commit":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            message=data["message"],
            changes=[Change.from_dict(c) for c in data.get("changes", [])],
            decision_id=data.get("decision_id"),
            parent_id=data.get("parent_id"),
            tags=data.get("tags", []),
        )


class CommitManager:
    """Manages local commits for the warden.

    Usage:
        manager = CommitManager(warden_dir)
        manager.load()

        # Create a commit
        commit_id = manager.create_commit(
            message="Fixed TypeScript parser",
            changes=[
                {"file": "src/xray/parser.py", "type": "modify"},
            ],
        )

        # Revert to a previous commit
        manager.revert_to(commit_id)

        # Get commit history
        commits = manager.get_commits()

        manager.save()
    """

    def __init__(self, warden_dir: Path):
        self.warden_dir = Path(warden_dir)
        self.commits_dir = self.warden_dir / "commits"
        self.log_file = self.commits_dir / "commits.json"
        self.snapshots_dir = self.commits_dir / "snapshots"
        self.commits: List[Commit] = []
        self.head: Optional[str] = None

    def load(self) -> None:
        """Load commits from disk."""
        if not self.log_file.exists():
            return

        try:
            data = json.loads(self.log_file.read_text())
            self.commits = [Commit.from_dict(c) for c in data.get("commits", [])]
            self.head = data.get("head")
        except (json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        """Save commits to disk."""
        self.commits_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "saved_at": datetime.now().isoformat(),
            "head": self.head,
            "commit_count": len(self.commits),
            "commits": [c.to_dict() for c in self.commits],
        }

        self.log_file.write_text(json.dumps(data, indent=2))

    def create_commit(
        self,
        message: str,
        changes: List[Dict[str, Any]],
        decision_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new commit.

        Args:
            message: Commit message.
            changes: List of changes [{file, type, ...}].
            decision_id: Optional linked decision.
            tags: Optional tags for this commit.

        Returns:
            Commit ID.
        """
        commit_id = f"wc-{uuid.uuid4().hex[:8]}"

        commit = Commit(
            id=commit_id,
            timestamp=datetime.now().isoformat(),
            message=message,
            changes=[
                Change(
                    file=c.get("file", ""),
                    type=c.get("type", "modify"),
                    before_hash=c.get("before_hash"),
                    after_hash=c.get("after_hash"),
                )
                for c in changes
            ],
            decision_id=decision_id,
            parent_id=self.head,
            tags=tags or [],
        )

        self.commits.append(commit)
        self.head = commit_id

        return commit_id

    def get_commits(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get commit history.

        Args:
            limit: Maximum number to return.

        Returns:
            Commits as dictionaries, newest first.
        """
        commits = list(reversed(self.commits))
        if limit:
            commits = commits[:limit]
        return [c.to_dict() for c in commits]

    def get_commit(self, commit_id: str) -> Optional[Commit]:
        """Get a specific commit by ID.

        Args:
            commit_id: The commit ID.

        Returns:
            The commit or None.
        """
        for commit in self.commits:
            if commit.id == commit_id:
                return commit
        return None

    def revert_to(self, commit_id: str) -> bool:
        """Revert to a previous commit.

        Creates a new revert commit and updates head.

        Args:
            commit_id: ID of commit to revert to.

        Returns:
            True if revert succeeded.
        """
        target = self.get_commit(commit_id)
        if not target:
            return False

        # Find all commits after target
        target_idx = None
        for i, c in enumerate(self.commits):
            if c.id == commit_id:
                target_idx = i
                break

        if target_idx is None:
            return False

        # Create revert commit
        reverted_commits = self.commits[target_idx + 1:]
        revert_message = f"Revert to {target.message} (reverted {len(reverted_commits)} commits)"

        self.create_commit(
            message=revert_message,
            changes=[],
            tags=["revert", f"revert-to:{commit_id}"],
        )

        return True

    def get_by_tag(self, tag: str) -> List[Commit]:
        """Get commits with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            Matching commits.
        """
        return [c for c in self.commits if tag in c.tags]

    def get_by_decision(self, decision_id: str) -> List[Commit]:
        """Get commits linked to a specific decision.

        Args:
            decision_id: Decision ID.

        Returns:
            Matching commits.
        """
        return [c for c in self.commits if c.decision_id == decision_id]

    def tag_commit(self, commit_id: str, tag: str) -> bool:
        """Add a tag to a commit.

        Args:
            commit_id: Commit to tag.
            tag: Tag to add.

        Returns:
            True if commit was found and tagged.
        """
        commit = self.get_commit(commit_id)
        if commit and tag not in commit.tags:
            commit.tags.append(tag)
            return True
        return False

    def get_diff(self, from_id: str, to_id: str) -> List[Change]:
        """Get changes between two commits.

        Args:
            from_id: Starting commit.
            to_id: Ending commit.

        Returns:
            List of changes.
        """
        # Find commit indices
        from_idx = to_idx = None
        for i, c in enumerate(self.commits):
            if c.id == from_id:
                from_idx = i
            if c.id == to_id:
                to_idx = i

        if from_idx is None or to_idx is None:
            return []

        # Collect all changes between commits
        changes = []
        start = min(from_idx, to_idx)
        end = max(from_idx, to_idx)

        for commit in self.commits[start + 1:end + 1]:
            changes.extend(commit.changes)

        return changes

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        tags: Dict[str, int] = {}
        for commit in self.commits:
            for tag in commit.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "total_commits": len(self.commits),
            "head": self.head,
            "tags": tags,
            "reverts": len(self.get_by_tag("revert")),
        }
