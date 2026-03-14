"""Observer module for anomaly detection and red flag identification.

Provides extensible rules for detecting issues during Blueprint runs.
Rules are designed to produce actionable feedback for both humans
and autonomous agents.

Each rule produces:
- A clear description of the problem
- Evidence (data that triggered the rule)
- A suggested action (what an agent might do to fix it)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.status import StatusReporter


@dataclass
class AnomalyRule:
    """Definition of an anomaly detection rule."""
    rule_id: str
    name: str
    description: str
    severity: str  # low, medium, high, critical
    category: str  # parser, domain, performance, coverage, config

    def __hash__(self):
        return hash(self.rule_id)


@dataclass
class AnomalyResult:
    """Result of an anomaly rule check."""
    rule: AnomalyRule
    triggered: bool
    message: str
    evidence: Dict[str, Any]
    suggested_action: str


class AnomalyDetector(ABC):
    """Base class for anomaly detectors."""

    @property
    @abstractmethod
    def rule(self) -> AnomalyRule:
        """Return the rule this detector implements."""
        ...

    @abstractmethod
    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        """Check for the anomaly. Return None if not triggered."""
        ...


# ---------------------------------------------------------------------------
# Built-in Anomaly Detectors
# ---------------------------------------------------------------------------

class ZeroEntitiesForExtensionDetector(AnomalyDetector):
    """Detects when a parser returns 0 entities for all files of an extension."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="zero_entities_for_extension",
            name="Zero Entities for File Extension",
            description="Parser returned 0 entities for all files of a specific extension",
            severity="high",
            category="parser",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        for ext, file_count in reporter._files_by_extension.items():
            entity_count = reporter._entities_by_extension.get(ext, 0)
            if file_count >= 5 and entity_count == 0:
                return AnomalyResult(
                    rule=self.rule,
                    triggered=True,
                    message=f"Parser returned 0 entities for all {file_count} {ext} files",
                    evidence={
                        "extension": ext,
                        "file_count": file_count,
                        "entity_count": entity_count,
                    },
                    suggested_action=f"Check if the {ext} parser is correctly configured or if these files are empty/invalid",
                )
        return None


class HighParserErrorRateDetector(AnomalyDetector):
    """Detects when a parser has a high failure rate."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="high_parser_error_rate",
            name="High Parser Error Rate",
            description="Parser failed on more than 50% of files",
            severity="critical",
            category="parser",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        for parser_name, stats in reporter.parser_stats.items():
            if stats.files_attempted >= 5:
                error_rate = stats.files_failed / stats.files_attempted
                if error_rate > 0.5:
                    return AnomalyResult(
                        rule=self.rule,
                        triggered=True,
                        message=f"Parser '{parser_name}' failed on {stats.files_failed}/{stats.files_attempted} files ({error_rate*100:.0f}%)",
                        evidence={
                            "parser_name": parser_name,
                            "files_attempted": stats.files_attempted,
                            "files_failed": stats.files_failed,
                            "error_rate": round(error_rate, 2),
                            "sample_errors": stats.errors[:3],
                        },
                        suggested_action=f"Review parser '{parser_name}' implementation or check if files use unsupported syntax",
                    )
        return None


class EntitiesWithoutEdgesDetector(AnomalyDetector):
    """Detects when a domain produces entities but no edges."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="entities_without_edges",
            name="Entities Without Edges",
            description="Domain produced many entities but zero edges",
            severity="medium",
            category="domain",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        for domain_name, stats in reporter.domain_stats.items():
            if stats.entities_produced > 50 and stats.edges_produced == 0:
                return AnomalyResult(
                    rule=self.rule,
                    triggered=True,
                    message=f"Domain '{domain_name}' produced {stats.entities_produced} entities but 0 edges",
                    evidence={
                        "domain_name": domain_name,
                        "entities": stats.entities_produced,
                        "edges": stats.edges_produced,
                    },
                    suggested_action="Check if edge extraction is working correctly for this codebase",
                )
        return None


class SlowParserDetector(AnomalyDetector):
    """Detects parsers that are unusually slow."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="slow_parser",
            name="Slow Parser",
            description="Parser averaging more than 1 second per file",
            severity="low",
            category="performance",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        for parser_name, stats in reporter.parser_stats.items():
            if stats.files_succeeded > 0:
                avg_ms = stats.total_duration_ms / stats.files_succeeded
                if avg_ms > 1000:
                    return AnomalyResult(
                        rule=self.rule,
                        triggered=True,
                        message=f"Parser '{parser_name}' averaging {avg_ms:.0f}ms per file",
                        evidence={
                            "parser_name": parser_name,
                            "avg_ms_per_file": round(avg_ms, 2),
                            "files_processed": stats.files_succeeded,
                            "total_ms": round(stats.total_duration_ms, 2),
                        },
                        suggested_action="Consider optimizing parser or investigating if files are unusually large",
                    )
        return None


class ExcessiveExclusionsDetector(AnomalyDetector):
    """Detects when too many files are being excluded."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="excessive_exclusions",
            name="Excessive File Exclusions",
            description="More than 90% of files were excluded by bpignore",
            severity="medium",
            category="config",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        skipped_count = sum(1 for d in reporter.decisions if d["type"] == "skip_file")
        total_considered = skipped_count + sum(
            s.files_attempted for s in reporter.parser_stats.values()
        )
        if total_considered > 10 and skipped_count / total_considered > 0.9:
            return AnomalyResult(
                rule=self.rule,
                triggered=True,
                message=f"{skipped_count}/{total_considered} files ({skipped_count/total_considered*100:.0f}%) were excluded",
                evidence={
                    "skipped_count": skipped_count,
                    "total_considered": total_considered,
                },
                suggested_action="Review .bpignore patterns - may be too aggressive",
            )
        return None


class NoDomainSuccessDetector(AnomalyDetector):
    """Detects when no domains completed successfully."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="no_domain_success",
            name="No Domains Succeeded",
            description="All requested domains failed to complete",
            severity="critical",
            category="domain",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        if not reporter.domain_stats:
            return None

        successes = sum(1 for s in reporter.domain_stats.values() if s.status == "success")
        if successes == 0:
            return AnomalyResult(
                rule=self.rule,
                triggered=True,
                message=f"All {len(reporter.domain_stats)} domains failed",
                evidence={
                    "domains": [
                        {"name": s.domain_name, "status": s.status}
                        for s in reporter.domain_stats.values()
                    ],
                },
                suggested_action="Check error logs for root cause - may be configuration or project structure issue",
            )
        return None


class LowEntityCountDetector(AnomalyDetector):
    """Detects when very few entities are extracted from a large codebase."""

    @property
    def rule(self) -> AnomalyRule:
        return AnomalyRule(
            rule_id="low_entity_count",
            name="Suspiciously Low Entity Count",
            description="Very few entities extracted relative to file count",
            severity="medium",
            category="coverage",
        )

    def check(self, reporter: StatusReporter) -> Optional[AnomalyResult]:
        total_files = sum(s.files_succeeded for s in reporter.parser_stats.values())
        total_entities = sum(s.total_entities for s in reporter.parser_stats.values())

        # If we have many files but very few entities, something might be wrong
        if total_files >= 20 and total_entities < total_files:
            return AnomalyResult(
                rule=self.rule,
                triggered=True,
                message=f"Only {total_entities} entities from {total_files} files (less than 1 per file)",
                evidence={
                    "total_files": total_files,
                    "total_entities": total_entities,
                    "entities_per_file": round(total_entities / max(1, total_files), 2),
                },
                suggested_action="Check if parsers are extracting entities correctly - most files should have at least 1 entity",
            )
        return None


# ---------------------------------------------------------------------------
# Observer Registry
# ---------------------------------------------------------------------------

# Default detectors
DEFAULT_DETECTORS: List[AnomalyDetector] = [
    ZeroEntitiesForExtensionDetector(),
    HighParserErrorRateDetector(),
    EntitiesWithoutEdgesDetector(),
    SlowParserDetector(),
    ExcessiveExclusionsDetector(),
    NoDomainSuccessDetector(),
    LowEntityCountDetector(),
]


def run_anomaly_detection(
    reporter: StatusReporter,
    detectors: Optional[List[AnomalyDetector]] = None,
) -> List[AnomalyResult]:
    """Run all anomaly detectors against a StatusReporter.

    Args:
        reporter: The StatusReporter with run data.
        detectors: Optional list of detectors. Uses DEFAULT_DETECTORS if None.

    Returns:
        List of AnomalyResults for triggered rules.
    """
    if detectors is None:
        detectors = DEFAULT_DETECTORS

    results = []
    for detector in detectors:
        try:
            result = detector.check(reporter)
            if result and result.triggered:
                results.append(result)
        except Exception:
            # Don't let a detector failure break the whole system
            pass

    return results


def get_anomaly_summary(results: List[AnomalyResult]) -> Dict[str, Any]:
    """Get a summary of anomaly detection results."""
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_category: Dict[str, int] = {}

    for r in results:
        by_severity[r.rule.severity] = by_severity.get(r.rule.severity, 0) + 1
        by_category[r.rule.category] = by_category.get(r.rule.category, 0) + 1

    return {
        "total": len(results),
        "by_severity": by_severity,
        "by_category": by_category,
        "has_critical": by_severity["critical"] > 0,
        "has_high": by_severity["high"] > 0,
    }
