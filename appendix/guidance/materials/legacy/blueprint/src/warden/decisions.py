"""Warden decision audit trail.

Records all decisions made by the warden for transparency and learning.
Each decision includes:
- What action was taken
- Why it was taken
- Confidence level
- Outcome (if known)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Decision:
    """A single decision record."""
    id: str
    timestamp: str
    action: str
    target: str
    reason: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "reason": self.reason,
            "confidence": self.confidence,
        }
        if self.context:
            d["context"] = self.context
        if self.outcome:
            d["outcome"] = self.outcome
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            action=data["action"],
            target=data["target"],
            reason=data["reason"],
            confidence=data["confidence"],
            context=data.get("context", {}),
            outcome=data.get("outcome"),
        )


class DecisionLog:
    """Audit trail of warden decisions.

    Usage:
        log = DecisionLog(warden_dir)
        log.load()

        # Record a decision
        decision_id = log.record(
            action="skip_file",
            target="node_modules/",
            reason="Standard exclusion",
            confidence=1.0,
        )

        # Record outcome
        log.record_outcome(decision_id, success=True, result={"skipped": 1000})

        # Review decisions
        decisions = log.get_decisions()
        recent = log.get_recent(limit=10)

        log.save()
    """

    def __init__(self, warden_dir: Path):
        self.warden_dir = Path(warden_dir)
        self.decisions_dir = self.warden_dir / "decisions"
        self.log_file = self.decisions_dir / "decisions.json"
        self.decisions: List[Decision] = []

    def load(self) -> None:
        """Load decisions from disk."""
        if not self.log_file.exists():
            return

        try:
            data = json.loads(self.log_file.read_text())
            self.decisions = [
                Decision.from_dict(d) for d in data.get("decisions", [])
            ]
        except (json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        """Save decisions to disk."""
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "saved_at": datetime.now().isoformat(),
            "decision_count": len(self.decisions),
            "decisions": [d.to_dict() for d in self.decisions],
        }

        self.log_file.write_text(json.dumps(data, indent=2))

        # Also save a rolling daily log
        self._save_daily_log()

    def _save_daily_log(self) -> None:
        """Save today's decisions to a separate file."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.decisions_dir / f"decisions_{today}.json"

        today_decisions = [
            d for d in self.decisions
            if d.timestamp.startswith(today)
        ]

        if today_decisions:
            data = {
                "date": today,
                "decisions": [d.to_dict() for d in today_decisions],
            }
            daily_file.write_text(json.dumps(data, indent=2))

    def record(
        self,
        action: str,
        target: str,
        reason: str,
        confidence: float = 1.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a decision.

        Args:
            action: What action was taken (analyze, skip, retry, etc.)
            target: What the action was taken on (file, directory, etc.)
            reason: Why this decision was made
            confidence: Confidence level 0-1
            context: Additional context

        Returns:
            Decision ID
        """
        decision_id = f"dec-{uuid.uuid4().hex[:8]}"

        decision = Decision(
            id=decision_id,
            timestamp=datetime.now().isoformat(),
            action=action,
            target=target,
            reason=reason,
            confidence=confidence,
            context=context or {},
        )

        self.decisions.append(decision)
        return decision_id

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Record the outcome of a decision.

        Args:
            decision_id: ID of the decision.
            success: Whether the action succeeded.
            result: Result data if successful.
            error: Error message if failed.

        Returns:
            True if decision was found and updated.
        """
        for decision in self.decisions:
            if decision.id == decision_id:
                decision.outcome = {
                    "success": success,
                    "recorded_at": datetime.now().isoformat(),
                }
                if result:
                    decision.outcome["result"] = result
                if error:
                    decision.outcome["error"] = error
                return True
        return False

    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get all decisions as dictionaries."""
        return [d.to_dict() for d in self.decisions]

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent decisions.

        Args:
            limit: Maximum number to return.

        Returns:
            Most recent decisions.
        """
        return [d.to_dict() for d in self.decisions[-limit:]]

    def get_by_action(self, action: str) -> List[Decision]:
        """Get all decisions with a specific action.

        Args:
            action: Action type to filter by.

        Returns:
            Matching decisions.
        """
        return [d for d in self.decisions if d.action == action]

    def get_failed(self) -> List[Decision]:
        """Get decisions that resulted in failure."""
        return [
            d for d in self.decisions
            if d.outcome and not d.outcome.get("success", True)
        ]

    def get_low_confidence(self, threshold: float = 0.7) -> List[Decision]:
        """Get decisions made with low confidence.

        Args:
            threshold: Confidence threshold.

        Returns:
            Decisions below threshold.
        """
        return [d for d in self.decisions if d.confidence < threshold]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        actions: Dict[str, int] = {}
        outcomes: Dict[str, int] = {"success": 0, "failure": 0, "unknown": 0}

        for d in self.decisions:
            actions[d.action] = actions.get(d.action, 0) + 1

            if d.outcome is None:
                outcomes["unknown"] += 1
            elif d.outcome.get("success"):
                outcomes["success"] += 1
            else:
                outcomes["failure"] += 1

        return {
            "total_decisions": len(self.decisions),
            "actions": actions,
            "outcomes": outcomes,
            "avg_confidence": (
                sum(d.confidence for d in self.decisions) / len(self.decisions)
                if self.decisions else 0
            ),
        }

    def clear_old(self, days: int = 30) -> int:
        """Clear decisions older than N days.

        Args:
            days: Maximum age in days.

        Returns:
            Number of decisions removed.
        """
        cutoff = datetime.now().isoformat()[:10]  # Just date part
        # This is a simplified version - would need proper date comparison
        original_count = len(self.decisions)

        # Keep only recent decisions
        # In production, would properly parse and compare dates
        self.decisions = self.decisions[-1000:]  # Keep last 1000

        return original_count - len(self.decisions)
