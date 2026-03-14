"""Complexity analyzer for Sonar.

Examines entity metrics (cyclomatic complexity, LOC, nesting depth,
parameter count, fan-out) and produces findings when thresholds are
exceeded.  All thresholds are configurable via an optional dict.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from src.core.models import Entity, EntityType
from src.sonar.schema import Finding, FindingCategory, FindingLevel


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "cyclomatic_complexity": {
        "warning": 10,
        "error": 20,
    },
    "loc_function": {
        "warning": 50,
        "error": 200,
    },
    "nesting_depth": {
        "warning": 4,
        "error": 6,
    },
    "parameter_count": {
        "warning": 5,
        "error": 8,
    },
    "fan_out": {
        "warning": 10,
    },
}


def _make_id() -> str:
    """Generate a unique finding ID."""
    return f"complexity-{uuid.uuid4().hex[:8]}"


def _get(thresholds: Dict[str, Any], metric: str, level: str, default: Any) -> Any:
    """Safely retrieve a threshold value, falling back to *default*."""
    metric_dict = thresholds.get(metric, {})
    if isinstance(metric_dict, dict):
        return metric_dict.get(level, default)
    return default


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_complexity(
    entities: List[Entity],
    thresholds: Optional[Dict[str, Any]] = None,
) -> List[Finding]:
    """Check complexity metrics for all entities.

    Args:
        entities: Entities (typically from an X-Ray result).
        thresholds: Optional dict overriding :data:`DEFAULT_THRESHOLDS`.
            Keys are metric names, values are dicts with ``"warning"``
            and/or ``"error"`` numeric limits.

    Returns:
        List of :class:`Finding` objects for any threshold violations.
    """
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        for key, val in thresholds.items():
            if key in t and isinstance(val, dict):
                t[key] = {**t[key], **val}
            else:
                t[key] = val

    findings: List[Finding] = []

    for entity in entities:
        metrics = entity.metrics
        if metrics is None:
            continue

        etype = entity.type
        file_path = entity.location.file if entity.location else ""
        line = entity.location.start_line if entity.location else None

        # --- Cyclomatic complexity -----------------------------------------
        cc = metrics.cyclomatic_complexity
        if cc is not None:
            cc_err = _get(t, "cyclomatic_complexity", "error", 20)
            cc_warn = _get(t, "cyclomatic_complexity", "warning", 10)
            if cc > cc_err:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.ERROR,
                    message=(
                        f"Cyclomatic complexity of '{entity.name}' is {cc} "
                        f"(threshold: {cc_err})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Refactor into smaller functions. Extract conditional "
                        "branches into helper methods or use a strategy pattern."
                    ),
                ))
            elif cc > cc_warn:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.WARNING,
                    message=(
                        f"Cyclomatic complexity of '{entity.name}' is {cc} "
                        f"(threshold: {cc_warn})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Consider breaking this function into smaller, "
                        "single-responsibility helpers."
                    ),
                ))

        # --- Lines of code (functions / methods only) ----------------------
        loc = metrics.loc_total
        if loc is not None and etype in (
            EntityType.FUNCTION,
            EntityType.METHOD,
        ):
            loc_err = _get(t, "loc_function", "error", 200)
            loc_warn = _get(t, "loc_function", "warning", 50)
            if loc > loc_err:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.ERROR,
                    message=(
                        f"Function '{entity.name}' has {loc} lines "
                        f"(threshold: {loc_err})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Split this function into smaller, focused functions. "
                        "Long functions are hard to test and maintain."
                    ),
                ))
            elif loc > loc_warn:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.WARNING,
                    message=(
                        f"Function '{entity.name}' has {loc} lines "
                        f"(threshold: {loc_warn})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Consider extracting logical sections into separate "
                        "helper functions for better readability."
                    ),
                ))

        # --- Nesting depth -------------------------------------------------
        nd = metrics.nesting_depth_max
        if nd is not None:
            nd_err = _get(t, "nesting_depth", "error", 6)
            nd_warn = _get(t, "nesting_depth", "warning", 4)
            if nd > nd_err:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.ERROR,
                    message=(
                        f"Max nesting depth of '{entity.name}' is {nd} "
                        f"(threshold: {nd_err})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Reduce nesting by using early returns (guard clauses), "
                        "extracting inner blocks into functions, or flattening "
                        "conditional logic."
                    ),
                ))
            elif nd > nd_warn:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.WARNING,
                    message=(
                        f"Max nesting depth of '{entity.name}' is {nd} "
                        f"(threshold: {nd_warn})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Consider using guard clauses or extracting deeply "
                        "nested blocks into helper functions."
                    ),
                ))

        # --- Parameter count -----------------------------------------------
        pc = metrics.parameter_count
        if pc is not None:
            pc_err = _get(t, "parameter_count", "error", 8)
            pc_warn = _get(t, "parameter_count", "warning", 5)
            if pc > pc_err:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.ERROR,
                    message=(
                        f"Function '{entity.name}' has {pc} parameters "
                        f"(threshold: {pc_err})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Group related parameters into a configuration object "
                        "or data class. Too many parameters make the API hard "
                        "to use and test."
                    ),
                ))
            elif pc > pc_warn:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.WARNING,
                    message=(
                        f"Function '{entity.name}' has {pc} parameters "
                        f"(threshold: {pc_warn})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "Consider grouping parameters into a data class or "
                        "using keyword arguments with sensible defaults."
                    ),
                ))

        # --- Fan-out -------------------------------------------------------
        fo = metrics.fan_out
        if fo is not None:
            fo_warn = _get(t, "fan_out", "warning", 10)
            if fo > fo_warn:
                findings.append(Finding(
                    finding_id=_make_id(),
                    category=FindingCategory.COMPLEXITY,
                    level=FindingLevel.WARNING,
                    message=(
                        f"Function '{entity.name}' depends on {fo} other "
                        f"entities (fan-out threshold: {fo_warn})."
                    ),
                    file_path=file_path,
                    line=line,
                    entity_id=entity.id,
                    suggestion=(
                        "High fan-out indicates excessive coupling. Consider "
                        "introducing an intermediary layer or breaking the "
                        "function into smaller units with fewer dependencies."
                    ),
                ))

    return findings
