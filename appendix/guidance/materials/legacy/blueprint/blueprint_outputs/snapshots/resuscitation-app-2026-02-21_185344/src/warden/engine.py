"""Warden engine - core logic for the LLM operator.

The WardenEngine is the central component that coordinates:
- Configuration management
- Memory persistence
- Decision making and logging
- Error recovery
- Context management
- Integration with certificate and intra-versioning systems
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.warden.config import WardenConfig, load_warden_config, save_warden_config
from src.warden.memory import WardenMemory
from src.warden.decisions import DecisionLog
from src.warden.commits import CommitManager


class WardenEngine:
    """Core engine for the Warden LLM operator.

    The Warden operates Blueprint with guardrails, managing:
    - What domains to run (tool levers)
    - How to handle errors (recovery strategies)
    - What to remember across sessions
    - What decisions were made and why

    Usage:
        warden = WardenEngine(workspace_path)
        warden.load()

        # Check if ready to operate
        can_boot, reason = warden.check_can_boot()

        # Make and log decisions
        warden.decide("analyze", "src/api/", "Critical path", confidence=0.9)

        # Handle errors
        warden.record_error("parser", "SyntaxError", "...", "file.ts")

        # Get recovery suggestions
        suggestions = warden.suggest_recovery()

        # Checkpoint before risky operations
        warden.checkpoint_before_operation("refactor", snapshot_dir)

        warden.save()
    """

    def __init__(
        self,
        workspace_path: Path,
        blueprint_root: Optional[Path] = None,
    ):
        self.workspace_path = Path(workspace_path)
        self.blueprint_root = Path(blueprint_root) if blueprint_root else None
        self.warden_dir = self.workspace_path / "warden"

        # Components
        self.config: Optional[WardenConfig] = None
        self.memory: Optional[WardenMemory] = None
        self.decisions: Optional[DecisionLog] = None
        self.commits: Optional[CommitManager] = None

        # Error tracking
        self._errors: List[Dict[str, Any]] = []

    def load(self) -> None:
        """Load all warden state from disk."""
        self.warden_dir.mkdir(parents=True, exist_ok=True)

        self.config = load_warden_config(self.warden_dir)

        self.memory = WardenMemory(self.warden_dir)
        self.memory.load()

        self.decisions = DecisionLog(self.warden_dir)
        self.decisions.load()

        self.commits = CommitManager(self.warden_dir)
        self.commits.load()

        # Load recent errors
        self._load_errors()

    def save(self) -> None:
        """Save all warden state to disk."""
        self.warden_dir.mkdir(parents=True, exist_ok=True)

        if self.config:
            save_warden_config(self.config, self.warden_dir)

        if self.memory:
            self.memory.save()

        if self.decisions:
            self.decisions.save()

        if self.commits:
            self.commits.save()

        self._save_errors()

    # --- Boot Gating ---

    def check_can_boot(self) -> Tuple[bool, str]:
        """Check if the warden can proceed with operations.

        Verifies certificate status if blueprint_root is set.

        Returns:
            Tuple of (can_proceed, reason).
        """
        if self.blueprint_root is None:
            return True, "No blueprint root set, proceeding without certificate check"

        try:
            from src.core.certificate import check_boot_certificate
            return check_boot_certificate(self.blueprint_root)
        except ImportError:
            return True, "Certificate system not available"

    # --- Decision Making ---

    def decide(
        self,
        action: str,
        target: str,
        reason: str,
        confidence: float = 1.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Make and log a decision.

        Args:
            action: What action to take.
            target: What to act on.
            reason: Why this decision.
            confidence: Confidence level 0-1.
            context: Additional context.

        Returns:
            Decision ID.
        """
        if self.decisions is None:
            self.decisions = DecisionLog(self.warden_dir)

        return self.decisions.record(
            action=action,
            target=target,
            reason=reason,
            confidence=confidence,
            context=context,
        )

    def record_decision_outcome(
        self,
        decision_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record the outcome of a decision."""
        if self.decisions:
            self.decisions.record_outcome(decision_id, success, result, error)

    # --- Error Handling ---

    def record_error(
        self,
        component: str,
        error_type: str,
        message: str,
        file_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an error for learning.

        Args:
            component: What component failed.
            error_type: Type of error.
            message: Error message.
            file_path: File that caused error.
            context: Additional context.

        Returns:
            Error ID.
        """
        error_id = f"err-{datetime.now().strftime('%H%M%S')}-{len(self._errors)}"

        error = {
            "id": error_id,
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error_type": error_type,
            "message": message,
            "file_path": file_path,
            "context": context or {},
        }

        self._errors.append(error)

        # Also remember in memory for pattern learning
        if self.memory:
            self.memory.remember(
                key=f"error_{component}_{error_type}",
                value=error,
                category="errors",
            )

        return error_id

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self._errors[-limit:]

    def suggest_recovery(self) -> List[Dict[str, Any]]:
        """Suggest recovery actions based on error patterns.

        Returns:
            List of suggestions with action and confidence.
        """
        suggestions = []

        if not self._errors:
            return suggestions

        # Pattern: Multiple JSX errors
        jsx_errors = [
            e for e in self._errors
            if "jsx" in e["message"].lower() or "tsx" in str(e.get("file_path", "")).lower()
        ]
        if len(jsx_errors) >= 2:
            suggestions.append({
                "action": "enable_jsx",
                "description": "Enable JSX parsing for TypeScript files",
                "confidence": 0.8,
                "evidence": f"{len(jsx_errors)} JSX-related errors detected",
            })

        # Pattern: Syntax errors in same file type
        by_extension: Dict[str, int] = {}
        for e in self._errors:
            if e.get("file_path"):
                ext = Path(e["file_path"]).suffix
                by_extension[ext] = by_extension.get(ext, 0) + 1

        for ext, count in by_extension.items():
            if count >= 3:
                suggestions.append({
                    "action": "review_parser",
                    "description": f"Review parser configuration for {ext} files",
                    "confidence": 0.7,
                    "evidence": f"{count} errors in {ext} files",
                })

        # Pattern: Repeated timeout/memory errors
        timeout_errors = [
            e for e in self._errors
            if "timeout" in e["message"].lower() or "memory" in e["message"].lower()
        ]
        if len(timeout_errors) >= 2:
            suggestions.append({
                "action": "reduce_scope",
                "description": "Reduce analysis scope or increase limits",
                "confidence": 0.6,
                "evidence": f"{len(timeout_errors)} resource-related errors",
            })

        return suggestions

    def _load_errors(self) -> None:
        """Load errors from disk."""
        errors_file = self.warden_dir / "errors.json"
        if errors_file.exists():
            try:
                data = json.loads(errors_file.read_text())
                self._errors = data.get("errors", [])
            except (json.JSONDecodeError, OSError):
                pass

    def _save_errors(self) -> None:
        """Save errors to disk."""
        errors_file = self.warden_dir / "errors.json"
        data = {
            "saved_at": datetime.now().isoformat(),
            "errors": self._errors[-100:],  # Keep last 100
        }
        errors_file.write_text(json.dumps(data, indent=2))

    # --- Checkpoint Integration ---

    def checkpoint_before_operation(
        self,
        operation: str,
        snapshot_dir: Path,
    ) -> Optional[str]:
        """Create a checkpoint before a risky operation.

        Args:
            operation: Name of the operation.
            snapshot_dir: Snapshot directory to checkpoint.

        Returns:
            Checkpoint ID or None if checkpointing disabled.
        """
        if self.config and not self.config.checkpoint_before_changes:
            return None

        try:
            from src.core.intra import IntraVersioning

            intra = IntraVersioning(snapshot_dir)
            checkpoint_id = intra.checkpoint(
                name=f"pre_{operation}",
                description=f"Checkpoint before {operation}",
            )

            # Record as a commit
            if self.commits:
                self.commits.create_commit(
                    message=f"Checkpoint: pre-{operation}",
                    changes=[],
                    tags=["checkpoint", f"pre-{operation}"],
                )

            return checkpoint_id

        except (ImportError, Exception):
            return None

    # --- Context Management ---

    def summarize_for_context(
        self,
        data: Dict[str, Any],
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Summarize large data to fit in context window.

        Args:
            data: Data to summarize.
            max_tokens: Maximum tokens in summary.

        Returns:
            Summarized data.
        """
        summary = {}

        # Handle entities
        if "entities" in data:
            entities = data["entities"]
            summary["entity_count"] = len(entities)
            if len(entities) > 10:
                # Include first and last few
                summary["entities_sample"] = entities[:5] + entities[-5:]
            else:
                summary["entities"] = entities

        # Handle edges
        if "edges" in data:
            edges = data["edges"]
            summary["edge_count"] = len(edges)
            if len(edges) > 10:
                summary["edges_sample"] = edges[:5]
            else:
                summary["edges"] = edges

        # Handle other keys
        for key, value in data.items():
            if key in ("entities", "edges"):
                continue

            if isinstance(value, list) and len(value) > 20:
                summary[f"{key}_count"] = len(value)
                summary[f"{key}_sample"] = value[:5]
            elif isinstance(value, dict) and len(str(value)) > 1000:
                summary[key] = f"<{len(value)} items>"
            else:
                summary[key] = value

        return summary

    def prioritize_context(
        self,
        items: List[Dict[str, Any]],
        max_items: int = 10,
    ) -> List[Dict[str, Any]]:
        """Prioritize context items by importance.

        Args:
            items: Items with "priority" field.
            max_items: Maximum items to return.

        Returns:
            Highest priority items.
        """
        sorted_items = sorted(
            items,
            key=lambda x: x.get("priority", 0),
            reverse=True,
        )
        return sorted_items[:max_items]

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of warden state for context.

        Returns compact info suitable for including in prompts.
        """
        summary = {
            "purpose": self.config.purpose if self.config else "",
            "enabled_domains": [
                k for k, v in (self.config.tool_levers if self.config else {}).items()
                if v
            ],
        }

        if self.memory:
            memory_summary = self.memory.get_summary()
            summary["memory"] = {
                "items": memory_summary["total_items"],
                "categories": list(memory_summary["categories"].keys()),
            }

        if self.decisions:
            decision_summary = self.decisions.get_summary()
            summary["decisions"] = {
                "total": decision_summary["total_decisions"],
                "recent_failures": len(self.decisions.get_failed()[-5:]),
            }

        if self._errors:
            summary["recent_errors"] = len(self._errors[-10:])

        return summary

    # --- Memory Shortcuts ---

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "learnings",
    ) -> None:
        """Shortcut to remember something."""
        if self.memory:
            self.memory.remember(key, value, category)

    def recall(self, key: str) -> Optional[Any]:
        """Shortcut to recall something."""
        if self.memory:
            return self.memory.recall(key)
        return None
