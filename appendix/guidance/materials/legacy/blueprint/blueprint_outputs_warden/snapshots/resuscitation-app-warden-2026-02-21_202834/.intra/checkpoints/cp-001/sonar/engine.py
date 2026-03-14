"""Sonar Engine -- Code quality scanning domain.

Reads entities and edges produced by X-Ray, runs all quality analyzers
(naming, complexity, dead-code), and produces an AnalysisResult whose
stats contain the complete list of findings.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.core.config import BlueprintConfig
from src.core.domain import Domain
from src.core.models import AnalysisResult
from src.sonar.complexity import check_complexity
from src.sonar.dead_code import check_dead_code
from src.sonar.naming import check_naming_conventions
from src.sonar.schema import Finding, FindingCategory, FindingLevel, SonarReport


class SonarEngine(Domain):
    """Sonar v0.2.0 -- Code quality scanning domain.

    Pipeline:
    1. Retrieve X-Ray analysis result from *prior_results*
    2. Run naming convention checks
    3. Run complexity checks
    4. Run dead-code detection
    5. Aggregate findings into a :class:`SonarReport`
    6. Return an :class:`AnalysisResult` with stats
    """

    def name(self) -> str:
        return "sonar"

    def version(self) -> str:
        return "0.2.0"

    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        """Execute the Sonar quality scanning pipeline.

        Requires a prior ``xray`` result.  If none is found the engine
        returns an empty result with an error entry.
        """
        t0 = time.time()
        errors: List[Dict[str, Any]] = []

        # --- Locate the X-Ray result --------------------------------------
        xray_result = self.find_prior_result("xray", prior_results)
        if xray_result is None:
            errors.append({
                "error": "No prior X-Ray result found. Sonar requires X-Ray to run first.",
                "phase": "init",
            })
            return AnalysisResult(
                domain=self.name(),
                version=self.version(),
                root_path=str(config.root_path),
                entities=[],
                edges=[],
                stats={"findings": [], "error_count": 1},
                errors=errors,
            )

        entities = xray_result.entities
        edges = xray_result.edges

        # --- Run analyzers -------------------------------------------------
        all_findings: List[Finding] = []

        try:
            naming_findings = check_naming_conventions(entities)
            all_findings.extend(naming_findings)
        except Exception as exc:
            errors.append({
                "error": f"Naming analyzer error: {exc}",
                "phase": "naming",
            })

        try:
            complexity_findings = check_complexity(entities)
            all_findings.extend(complexity_findings)
        except Exception as exc:
            errors.append({
                "error": f"Complexity analyzer error: {exc}",
                "phase": "complexity",
            })

        try:
            dead_code_findings = check_dead_code(entities, edges)
            all_findings.extend(dead_code_findings)
        except Exception as exc:
            errors.append({
                "error": f"Dead-code analyzer error: {exc}",
                "phase": "dead_code",
            })

        # --- Build report --------------------------------------------------
        report = _build_report(all_findings, entities)

        elapsed = round(time.time() - t0, 3)

        # Findings by category
        by_category: Dict[str, int] = {}
        for f in all_findings:
            key = f.category.value
            by_category[key] = by_category.get(key, 0) + 1

        # Findings by level
        by_level: Dict[str, int] = {}
        for f in all_findings:
            key = f.level.value
            by_level[key] = by_level.get(key, 0) + 1

        stats: Dict[str, Any] = {
            "total_findings": len(all_findings),
            "findings_by_category": by_category,
            "findings_by_level": by_level,
            "file_count": report.file_count,
            "entity_count": report.entity_count,
            "elapsed_seconds": elapsed,
            "error_count": len(errors),
            # Store the full findings list as serialisable dicts
            "findings": [f.model_dump(mode="json") for f in all_findings],
        }

        # Sonar does not produce its own entities or edges
        return AnalysisResult(
            domain=self.name(),
            version=self.version(),
            root_path=str(config.root_path),
            entities=[],
            edges=[],
            stats=stats,
            errors=errors,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_report(findings: List[Finding], entities: list) -> SonarReport:
    """Assemble a :class:`SonarReport` from raw findings."""
    summary: Dict[str, int] = {}
    for f in findings:
        key = f.category.value
        summary[key] = summary.get(key, 0) + 1

    # Count unique files and entities referenced by findings
    files_seen: set = set()
    entities_seen: set = set()
    for f in findings:
        if f.file_path:
            files_seen.add(f.file_path)
        if f.entity_id:
            entities_seen.add(f.entity_id)

    return SonarReport(
        findings=findings,
        summary=summary,
        file_count=len(files_seen),
        entity_count=len(entities_seen),
    )
