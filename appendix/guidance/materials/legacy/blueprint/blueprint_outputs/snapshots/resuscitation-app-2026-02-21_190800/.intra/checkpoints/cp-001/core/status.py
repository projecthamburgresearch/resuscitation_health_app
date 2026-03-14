"""Status reporting system for Blueprint observability.

Captures execution details, errors, anomalies, and decisions for every run.
Designed for consumption by both humans and autonomous agents that may
need to diagnose and fix issues.

Architecture:
- StatusReporter: Central collector that all domains report to
- RunStatus: Complete execution record for a single run
- Structured logs optimized for machine parsing and agent consumption
"""

from __future__ import annotations

import json
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class StatusLevel(str, Enum):
    """Log levels for status entries."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    RED_FLAG = "red_flag"  # Anomalies that need attention


class StatusCategory(str, Enum):
    """Categories of status entries for filtering."""
    EXECUTION = "execution"      # What ran, timing, order
    PARSER = "parser"            # Parser-level stats and issues
    DOMAIN = "domain"            # Domain execution details
    FILE = "file"                # Per-file processing info
    DECISION = "decision"        # What was skipped and why
    ANOMALY = "anomaly"          # Red flags, unexpected behavior
    ERROR = "error"              # Errors with context


@dataclass
class StatusEntry:
    """A single status log entry."""
    timestamp: str
    level: StatusLevel
    category: StatusCategory
    component: str          # e.g., "xray", "typescript_parser", "bpignore"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "category": self.category.value,
            "component": self.component,
            "message": self.message,
        }
        if self.details:
            d["details"] = self.details
        if self.file_path:
            d["file_path"] = self.file_path
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        return d


@dataclass
class ParserStats:
    """Statistics for a single parser's execution."""
    parser_name: str
    language: str
    files_attempted: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    files_empty: int = 0           # Parsed but returned 0 entities
    total_entities: int = 0
    total_edges: int = 0
    total_duration_ms: float = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parser_name": self.parser_name,
            "language": self.language,
            "files_attempted": self.files_attempted,
            "files_succeeded": self.files_succeeded,
            "files_failed": self.files_failed,
            "files_empty": self.files_empty,
            "total_entities": self.total_entities,
            "total_edges": self.total_edges,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "success_rate": round(self.files_succeeded / max(1, self.files_attempted) * 100, 1),
            "errors": self.errors,
        }


@dataclass
class DomainStats:
    """Statistics for a single domain's execution."""
    domain_name: str
    version: str
    started_at: str
    ended_at: Optional[str] = None
    duration_ms: float = 0
    status: str = "running"  # running, success, failed, skipped
    entities_produced: int = 0
    edges_produced: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_name": self.domain_name,
            "version": self.version,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "entities_produced": self.entities_produced,
            "edges_produced": self.edges_produced,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class Anomaly:
    """A detected anomaly that may need attention."""
    anomaly_id: str
    severity: str           # low, medium, high, critical
    rule: str               # Which detection rule triggered this
    message: str
    evidence: Dict[str, Any]
    suggested_action: str   # What an agent might do to fix this

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
        }


class StatusReporter:
    """Central status collector for a Blueprint run.

    Usage:
        reporter = StatusReporter(run_id, project_name)
        reporter.start_run(config)

        # During execution:
        reporter.log_info("xray", "Starting analysis")
        reporter.start_domain("xray", "0.2.0")
        reporter.record_parser_file("typescript", "src/app.ts", entities=15, edges=20)
        reporter.end_domain("xray", entities=100, edges=200)

        # On error:
        reporter.log_error("xray", "Parse failed", exception=exc, file_path="bad.ts")

        # End run:
        reporter.end_run()
        reporter.save(workspace_path)
    """

    def __init__(self, run_id: str, project_name: str):
        self.run_id = run_id
        self.project_name = project_name
        self.started_at: Optional[str] = None
        self.ended_at: Optional[str] = None
        self.config: Dict[str, Any] = {}

        self.entries: List[StatusEntry] = []
        self.parser_stats: Dict[str, ParserStats] = {}
        self.domain_stats: Dict[str, DomainStats] = {}
        self.anomalies: List[Anomaly] = []
        self.decisions: List[Dict[str, Any]] = []  # Skipped files, excluded paths, etc.

        # Tracking for anomaly detection
        self._files_by_extension: Dict[str, int] = {}
        self._entities_by_extension: Dict[str, int] = {}

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _make_entry(
        self,
        level: StatusLevel,
        category: StatusCategory,
        component: str,
        message: str,
        **kwargs,
    ) -> StatusEntry:
        return StatusEntry(
            timestamp=self._now(),
            level=level,
            category=category,
            component=component,
            message=message,
            **kwargs,
        )

    # --- Run lifecycle ---

    def start_run(self, config: Dict[str, Any]) -> None:
        """Mark the start of a run."""
        self.started_at = self._now()
        self.config = config
        self.entries.append(self._make_entry(
            StatusLevel.INFO,
            StatusCategory.EXECUTION,
            "runner",
            f"Run started for project: {self.project_name}",
            details={"run_id": self.run_id, "config": config},
        ))

    def end_run(self, success: bool = True) -> None:
        """Mark the end of a run and trigger anomaly detection."""
        self.ended_at = self._now()

        # Run anomaly detection
        self._detect_anomalies()

        status = "success" if success else "failed"
        error_count = sum(1 for e in self.entries if e.level == StatusLevel.ERROR)
        anomaly_count = len(self.anomalies)

        self.entries.append(self._make_entry(
            StatusLevel.INFO,
            StatusCategory.EXECUTION,
            "runner",
            f"Run completed: {status}",
            details={
                "run_id": self.run_id,
                "error_count": error_count,
                "anomaly_count": anomaly_count,
                "domains_run": list(self.domain_stats.keys()),
            },
        ))

    # --- Logging methods ---

    def log_debug(self, component: str, message: str, **kwargs) -> None:
        self.entries.append(self._make_entry(
            StatusLevel.DEBUG, StatusCategory.EXECUTION, component, message, **kwargs
        ))

    def log_info(self, component: str, message: str, **kwargs) -> None:
        self.entries.append(self._make_entry(
            StatusLevel.INFO, StatusCategory.EXECUTION, component, message, **kwargs
        ))

    def log_warn(self, component: str, message: str, **kwargs) -> None:
        self.entries.append(self._make_entry(
            StatusLevel.WARN, StatusCategory.EXECUTION, component, message, **kwargs
        ))

    def log_error(
        self,
        component: str,
        message: str,
        exception: Optional[Exception] = None,
        file_path: Optional[str] = None,
        **kwargs,
    ) -> None:
        details = kwargs.pop("details", {})
        if exception:
            details["exception_type"] = type(exception).__name__
            details["exception_message"] = str(exception)
            details["traceback"] = traceback.format_exc()

        self.entries.append(self._make_entry(
            StatusLevel.ERROR,
            StatusCategory.ERROR,
            component,
            message,
            details=details,
            file_path=file_path,
            **kwargs,
        ))

    # --- Domain tracking ---

    def start_domain(self, domain_name: str, version: str) -> None:
        """Record that a domain started execution."""
        self.domain_stats[domain_name] = DomainStats(
            domain_name=domain_name,
            version=version,
            started_at=self._now(),
        )
        self.entries.append(self._make_entry(
            StatusLevel.INFO,
            StatusCategory.DOMAIN,
            domain_name,
            f"Domain started: {domain_name} v{version}",
        ))

    def end_domain(
        self,
        domain_name: str,
        entities: int = 0,
        edges: int = 0,
        success: bool = True,
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Record that a domain finished execution."""
        if domain_name not in self.domain_stats:
            return

        stats = self.domain_stats[domain_name]
        stats.ended_at = self._now()
        stats.status = "success" if success else "failed"
        stats.entities_produced = entities
        stats.edges_produced = edges
        if errors:
            stats.errors = errors

        # Calculate duration
        start = datetime.fromisoformat(stats.started_at)
        end = datetime.fromisoformat(stats.ended_at)
        stats.duration_ms = (end - start).total_seconds() * 1000

        self.entries.append(self._make_entry(
            StatusLevel.INFO,
            StatusCategory.DOMAIN,
            domain_name,
            f"Domain completed: {domain_name} ({stats.status})",
            details={
                "entities": entities,
                "edges": edges,
                "duration_ms": stats.duration_ms,
            },
            duration_ms=stats.duration_ms,
        ))

    # --- Parser tracking ---

    def record_parser_file(
        self,
        parser_name: str,
        language: str,
        file_path: str,
        entities: int,
        edges: int,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record stats for a single file parsed."""
        if parser_name not in self.parser_stats:
            self.parser_stats[parser_name] = ParserStats(
                parser_name=parser_name,
                language=language,
            )

        stats = self.parser_stats[parser_name]
        stats.files_attempted += 1
        stats.total_duration_ms += duration_ms

        # Track by extension for anomaly detection
        ext = Path(file_path).suffix.lower()
        self._files_by_extension[ext] = self._files_by_extension.get(ext, 0) + 1

        if success:
            stats.files_succeeded += 1
            stats.total_entities += entities
            stats.total_edges += edges
            self._entities_by_extension[ext] = self._entities_by_extension.get(ext, 0) + entities

            if entities == 0:
                stats.files_empty += 1
                self.entries.append(self._make_entry(
                    StatusLevel.DEBUG,
                    StatusCategory.PARSER,
                    parser_name,
                    f"File parsed but returned 0 entities",
                    file_path=file_path,
                    duration_ms=duration_ms,
                ))
        else:
            stats.files_failed += 1
            stats.errors.append({
                "file_path": file_path,
                "error": error,
            })
            self.entries.append(self._make_entry(
                StatusLevel.ERROR,
                StatusCategory.PARSER,
                parser_name,
                f"Parse failed: {error}",
                file_path=file_path,
                duration_ms=duration_ms,
            ))

    # --- Decision tracking ---

    def record_decision(
        self,
        decision_type: str,
        subject: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a decision made during processing (skip, exclude, etc.)."""
        self.decisions.append({
            "timestamp": self._now(),
            "type": decision_type,
            "subject": subject,
            "reason": reason,
            "details": details or {},
        })
        self.entries.append(self._make_entry(
            StatusLevel.DEBUG,
            StatusCategory.DECISION,
            "runner",
            f"Decision: {decision_type} - {subject}",
            details={"reason": reason, **(details or {})},
        ))

    # --- Anomaly detection ---

    def _detect_anomalies(self) -> None:
        """Run anomaly detection rules after the run completes."""
        # Rule 1: Parser returned 0 entities for many files of same extension
        for ext, file_count in self._files_by_extension.items():
            entity_count = self._entities_by_extension.get(ext, 0)
            if file_count >= 5 and entity_count == 0:
                self.anomalies.append(Anomaly(
                    anomaly_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                    severity="high",
                    rule="zero_entities_for_extension",
                    message=f"Parser returned 0 entities for all {file_count} {ext} files",
                    evidence={
                        "extension": ext,
                        "file_count": file_count,
                        "entity_count": entity_count,
                    },
                    suggested_action=f"Check if the {ext} parser is correctly configured or if these files are empty/invalid",
                ))

        # Rule 2: High error rate for a parser
        for parser_name, stats in self.parser_stats.items():
            if stats.files_attempted >= 5:
                error_rate = stats.files_failed / stats.files_attempted
                if error_rate > 0.5:
                    self.anomalies.append(Anomaly(
                        anomaly_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                        severity="critical",
                        rule="high_parser_error_rate",
                        message=f"Parser '{parser_name}' failed on {stats.files_failed}/{stats.files_attempted} files ({error_rate*100:.0f}%)",
                        evidence={
                            "parser_name": parser_name,
                            "files_attempted": stats.files_attempted,
                            "files_failed": stats.files_failed,
                            "error_rate": round(error_rate, 2),
                            "sample_errors": stats.errors[:3],
                        },
                        suggested_action=f"Review parser '{parser_name}' implementation or check if files use unsupported syntax",
                    ))

        # Rule 3: Domain produced entities but no edges
        for domain_name, stats in self.domain_stats.items():
            if stats.entities_produced > 50 and stats.edges_produced == 0:
                self.anomalies.append(Anomaly(
                    anomaly_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                    severity="medium",
                    rule="entities_without_edges",
                    message=f"Domain '{domain_name}' produced {stats.entities_produced} entities but 0 edges",
                    evidence={
                        "domain_name": domain_name,
                        "entities": stats.entities_produced,
                        "edges": stats.edges_produced,
                    },
                    suggested_action="Check if edge extraction is working correctly for this codebase",
                ))

        # Rule 4: Very slow parser (>1s per file average)
        for parser_name, stats in self.parser_stats.items():
            if stats.files_succeeded > 0:
                avg_ms = stats.total_duration_ms / stats.files_succeeded
                if avg_ms > 1000:
                    self.anomalies.append(Anomaly(
                        anomaly_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                        severity="low",
                        rule="slow_parser",
                        message=f"Parser '{parser_name}' averaging {avg_ms:.0f}ms per file",
                        evidence={
                            "parser_name": parser_name,
                            "avg_ms_per_file": round(avg_ms, 2),
                            "files_processed": stats.files_succeeded,
                            "total_ms": round(stats.total_duration_ms, 2),
                        },
                        suggested_action="Consider optimizing parser or investigating if files are unusually large",
                    ))

        # Rule 5: Many files skipped by bpignore
        skipped_count = sum(1 for d in self.decisions if d["type"] == "skip_file")
        total_considered = skipped_count + sum(s.files_attempted for s in self.parser_stats.values())
        if total_considered > 0 and skipped_count / total_considered > 0.9:
            self.anomalies.append(Anomaly(
                anomaly_id=f"anomaly-{uuid.uuid4().hex[:8]}",
                severity="medium",
                rule="excessive_exclusions",
                message=f"{skipped_count}/{total_considered} files ({skipped_count/total_considered*100:.0f}%) were excluded",
                evidence={
                    "skipped_count": skipped_count,
                    "total_considered": total_considered,
                },
                suggested_action="Review .bpignore patterns - may be too aggressive",
            ))

    # --- Serialization ---

    def to_dict(self) -> Dict[str, Any]:
        """Convert the full status to a dictionary."""
        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "config": self.config,
            "summary": {
                "domains_run": len(self.domain_stats),
                "total_errors": sum(1 for e in self.entries if e.level == StatusLevel.ERROR),
                "total_warnings": sum(1 for e in self.entries if e.level == StatusLevel.WARN),
                "anomaly_count": len(self.anomalies),
                "decisions_count": len(self.decisions),
            },
            "domain_stats": {k: v.to_dict() for k, v in self.domain_stats.items()},
            "parser_stats": {k: v.to_dict() for k, v in self.parser_stats.items()},
            "anomalies": [a.to_dict() for a in self.anomalies],
            "decisions": self.decisions,
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self, workspace_path: Path) -> Path:
        """Save the status report to workspace/status/runs/<run_id>/."""
        status_dir = workspace_path / "status" / "runs" / self.run_id
        status_dir.mkdir(parents=True, exist_ok=True)

        full_data = self.to_dict()

        # Save the complete status
        with open(status_dir / "status.json", "w") as f:
            json.dump(full_data, f, indent=2)

        # Save individual components for easier access
        with open(status_dir / "execution.json", "w") as f:
            json.dump({
                "run_id": self.run_id,
                "project_name": self.project_name,
                "started_at": self.started_at,
                "ended_at": self.ended_at,
                "config": self.config,
                "summary": full_data["summary"],
            }, f, indent=2)

        with open(status_dir / "parsers.json", "w") as f:
            json.dump(full_data["parser_stats"], f, indent=2)

        with open(status_dir / "domains.json", "w") as f:
            json.dump(full_data["domain_stats"], f, indent=2)

        with open(status_dir / "anomalies.json", "w") as f:
            json.dump(full_data["anomalies"], f, indent=2)

        with open(status_dir / "decisions.json", "w") as f:
            json.dump(full_data["decisions"], f, indent=2)

        with open(status_dir / "errors.json", "w") as f:
            errors = [e.to_dict() for e in self.entries if e.level == StatusLevel.ERROR]
            json.dump(errors, f, indent=2)

        # Update the global health.json
        self._update_health(workspace_path)

        # Update history.json
        self._update_history(workspace_path)

        return status_dir

    def _update_health(self, workspace_path: Path) -> None:
        """Update workspace/status/health.json with latest run info."""
        health_path = workspace_path / "status" / "health.json"

        health = {
            "last_run_id": self.run_id,
            "last_run_at": self.ended_at,
            "last_project": self.project_name,
            "last_status": "success" if all(
                s.status == "success" for s in self.domain_stats.values()
            ) else "failed",
            "recent_anomalies": len(self.anomalies),
            "recent_errors": sum(1 for e in self.entries if e.level == StatusLevel.ERROR),
        }

        with open(health_path, "w") as f:
            json.dump(health, f, indent=2)

    def _update_history(self, workspace_path: Path) -> None:
        """Append to workspace/status/history.json (rolling log)."""
        history_path = workspace_path / "status" / "history.json"

        # Load existing history
        history = []
        if history_path.exists():
            try:
                with open(history_path) as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        # Add this run
        history.append({
            "run_id": self.run_id,
            "project_name": self.project_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "domains": list(self.domain_stats.keys()),
            "error_count": sum(1 for e in self.entries if e.level == StatusLevel.ERROR),
            "anomaly_count": len(self.anomalies),
        })

        # Keep only last 100 runs
        history = history[-100:]

        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_status_reporter(project_name: str) -> StatusReporter:
    """Create a new StatusReporter with a unique run ID."""
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    return StatusReporter(run_id, project_name)
