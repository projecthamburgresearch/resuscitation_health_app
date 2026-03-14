"""Dead code detector for Sonar.

Analyses entities and edges from X-Ray results to identify code that
appears unreachable or unused:
- Functions/methods with zero callers that are not entry points
- Imports never referenced by any edge
- Classes with no methods and no inheritance edges
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Set

from src.core.models import Edge, Entity, EntityType, RelationType
from src.sonar.schema import Finding, FindingCategory, FindingLevel


# ---------------------------------------------------------------------------
# Entry-point heuristics
# ---------------------------------------------------------------------------

# Function / method names that are conventionally entry points or framework
# hooks and should not be flagged as dead code.
_ENTRY_POINT_NAMES: Set[str] = {
    "main",
    "__init__",
    "__main__",
    "__call__",
    "__enter__",
    "__exit__",
    "__new__",
    "setup",
    "teardown",
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "run",
    # Constructors (called implicitly on instantiation)
    "constructor",
    # React / UI frameworks — default-exported screen/page components
    "App",
}

# Name prefixes that typically indicate test or framework hooks
_ENTRY_POINT_PREFIXES = (
    "test_",
    "Test",
    "handle_",
    "on_",
    "signal_",
)

# Decorators that mark entry points (route handlers, CLI commands, etc.)
_ENTRY_POINT_DECORATORS: Set[str] = {
    "app.route",
    "app.get",
    "app.post",
    "app.put",
    "app.delete",
    "app.patch",
    "router.route",
    "router.get",
    "router.post",
    "router.put",
    "router.delete",
    "router.patch",
    "celery.task",
    "task",
    "click.command",
    "click.group",
    "property",
    "staticmethod",
    "classmethod",
    "abstractmethod",
    "override",
    "pytest.fixture",
    "fixture",
    "api_view",
    "login_required",
    "requires_auth",
}


def _make_id() -> str:
    """Generate a unique finding ID."""
    return f"dead_code-{uuid.uuid4().hex[:8]}"


def _is_entry_point(entity: Entity) -> bool:
    """Return True if *entity* looks like a framework/test entry point."""
    name = entity.name

    # Exact name match
    if name in _ENTRY_POINT_NAMES:
        return True

    # Prefix match
    for prefix in _ENTRY_POINT_PREFIXES:
        if name.startswith(prefix):
            return True

    # Decorator match
    if entity.decorators:
        for dec in entity.decorators:
            # Normalise: strip leading @ and trailing ()
            dec_clean = dec.lstrip("@").split("(")[0].strip()
            if dec_clean in _ENTRY_POINT_DECORATORS:
                return True

    # Dunder methods are implicitly called by Python runtime
    if name.startswith("__") and name.endswith("__"):
        return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_dead_code(
    entities: List[Entity],
    edges: List[Edge],
) -> List[Finding]:
    """Detect potentially dead code.

    Args:
        entities: All entities from the X-Ray analysis.
        edges: All edges (relationships) from the X-Ray analysis.

    Returns:
        List of info-level findings for suspected dead code.
    """
    findings: List[Finding] = []

    # Build lookup structures -----------------------------------------------
    entity_by_id: Dict[str, Entity] = {e.id: e for e in entities}

    # Set of entity IDs that are targets of "calls" or "called_by" edges
    called_ids: Set[str] = set()
    # Set of entity names that are called (for cross-file JSX resolution)
    called_names: Set[str] = set()
    # Set of entity IDs that are targets of "uses" / "used_by" edges
    used_ids: Set[str] = set()
    # Set of entity IDs that are part of inheritance edges
    inherited_ids: Set[str] = set()
    # Set of entity IDs referenced by any edge (either side)
    referenced_ids: Set[str] = set()
    # Set of entity IDs that have CONTAINS edges (class -> method)
    contains_targets: Set[str] = set()
    # Set of entity IDs that are exported (default export or named export)
    exported_ids: Set[str] = set()

    for edge in edges:
        referenced_ids.add(edge.source)
        referenced_ids.add(edge.target)

        if edge.relation in (RelationType.CALLS, RelationType.CALLED_BY):
            # For CALLS: target is the callee; for CALLED_BY: source is callee
            if edge.relation == RelationType.CALLS:
                called_ids.add(edge.target)
                # Extract the entity name from the target ID for cross-file
                # resolution (e.g., JSX <Component /> in file A calling
                # a component defined in file B).
                # ID format: "FUNC::filepath::name" or "METHOD::filepath::Class.method"
                parts = edge.target.split("::")
                if len(parts) >= 3:
                    called_names.add(parts[-1])
            else:
                called_ids.add(edge.source)
                parts = edge.source.split("::")
                if len(parts) >= 3:
                    called_names.add(parts[-1])

        elif edge.relation in (RelationType.USES, RelationType.USED_BY):
            if edge.relation == RelationType.USES:
                used_ids.add(edge.target)
            else:
                used_ids.add(edge.source)

        elif edge.relation in (
            RelationType.INHERITS,
            RelationType.INHERITED_BY,
            RelationType.IMPLEMENTS,
            RelationType.IMPLEMENTED_BY,
        ):
            inherited_ids.add(edge.source)
            inherited_ids.add(edge.target)

        elif edge.relation == RelationType.CONTAINS:
            contains_targets.add(edge.target)

        elif edge.relation in (
            RelationType.IMPORTS,
            RelationType.IMPORTED_BY,
        ):
            if edge.relation == RelationType.IMPORTS:
                used_ids.add(edge.target)
            else:
                used_ids.add(edge.source)

        elif edge.relation == RelationType.EXPORTS:
            # Exported entities are externally reachable — not dead code
            exported_ids.add(edge.target)

    # --- 1. Functions/methods with zero callers ----------------------------
    for entity in entities:
        if entity.type not in (EntityType.FUNCTION, EntityType.METHOD):
            continue

        # Skip entry points
        if _is_entry_point(entity):
            continue

        # Skip exported functions — they are externally reachable
        if entity.id in exported_ids:
            continue

        # Check fan_in metric first (computed by xray)
        fan_in = entity.metrics.fan_in if entity.metrics else None
        is_called = entity.id in called_ids

        # Cross-file name resolution: if a component/function is called
        # by name in another file (e.g., JSX <MainScreen />), the target
        # ID won't match because it includes the caller's file path.
        # Match by entity name as a fallback.
        is_called_by_name = entity.name in called_names

        if is_called or is_called_by_name:
            continue

        if fan_in is not None and fan_in > 0:
            continue

        file_path = entity.location.file if entity.location else ""
        line = entity.location.start_line if entity.location else None

        findings.append(Finding(
            finding_id=_make_id(),
            category=FindingCategory.DEAD_CODE,
            level=FindingLevel.INFO,
            message=(
                f"Function/method '{entity.name}' appears to have no callers."
            ),
            file_path=file_path,
            line=line,
            entity_id=entity.id,
            suggestion=(
                "Verify whether this function is still needed. If it is an "
                "entry point or callback, consider adding a decorator or "
                "comment to mark it as intentionally uncalled."
            ),
        ))

    # --- 2. Imports never referenced by any edge ---------------------------
    for entity in entities:
        if entity.type != EntityType.IMPORT:
            continue

        # An import is "alive" if it appears as source or target of any
        # USES, USED_BY, IMPORTS, or IMPORTED_BY edge that connects it
        # to a non-import entity, OR if the imported name appears in
        # referenced_ids via any edge type.
        if entity.id in referenced_ids:
            continue

        file_path = entity.location.file if entity.location else ""
        line = entity.location.start_line if entity.location else None

        findings.append(Finding(
            finding_id=_make_id(),
            category=FindingCategory.DEAD_CODE,
            level=FindingLevel.INFO,
            message=f"Import '{entity.name}' is never referenced.",
            file_path=file_path,
            line=line,
            entity_id=entity.id,
            suggestion="Remove unused imports to keep the module clean.",
        ))

    # --- 3. Empty classes with no inheritance ------------------------------
    # Collect entity IDs that are classes
    class_ids: Set[str] = {
        e.id for e in entities if e.type == EntityType.CLASS
    }

    # A class is "empty" if nothing is CONTAINED by it and it has no
    # inheritance relationships.
    for entity in entities:
        if entity.type != EntityType.CLASS:
            continue

        # Does this class contain any methods?
        has_members = any(
            edge.source == entity.id and edge.relation == RelationType.CONTAINS
            for edge in edges
        )
        if has_members:
            continue

        # Is this class part of any inheritance chain?
        if entity.id in inherited_ids:
            continue

        file_path = entity.location.file if entity.location else ""
        line = entity.location.start_line if entity.location else None

        findings.append(Finding(
            finding_id=_make_id(),
            category=FindingCategory.DEAD_CODE,
            level=FindingLevel.INFO,
            message=(
                f"Class '{entity.name}' has no methods and no inheritance "
                f"relationships."
            ),
            file_path=file_path,
            line=line,
            entity_id=entity.id,
            suggestion=(
                "This class may be a data container — consider using a "
                "dataclass or named tuple instead. If it is intentionally "
                "empty (e.g. a marker class), consider adding a docstring "
                "explaining its purpose."
            ),
        ))

    return findings
