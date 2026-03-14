"""Naming convention analyzer for Sonar.

Checks entity names against language-specific naming conventions and
flags violations such as wrong casing, single-character names, overly
long names, and use of reserved words as identifiers.
"""

from __future__ import annotations

import re
import uuid
from typing import List, Set

from src.core.models import Entity, EntityType
from src.sonar.schema import Finding, FindingCategory, FindingLevel


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")


def _is_snake_case(name: str) -> bool:
    """Return True if *name* is valid snake_case."""
    return bool(_SNAKE_RE.match(name))


def _is_pascal_case(name: str) -> bool:
    """Return True if *name* is valid PascalCase."""
    return bool(_PASCAL_RE.match(name))


def _is_camel_case(name: str) -> bool:
    """Return True if *name* is valid camelCase."""
    return bool(_CAMEL_RE.match(name))


def _is_upper_snake(name: str) -> bool:
    """Return True if *name* is valid UPPER_SNAKE_CASE."""
    return bool(_UPPER_SNAKE_RE.match(name))


# ---------------------------------------------------------------------------
# Single-character / length / reserved-word checks
# ---------------------------------------------------------------------------

_LOOP_VARS: Set[str] = {"i", "j", "k", "x", "y", "z"}

# Language reserved words commonly misused as identifiers
_RESERVED: Set[str] = {
    # Python
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
    # Java / C#
    "abstract", "boolean", "byte", "case", "catch", "char", "const",
    "default", "do", "double", "enum", "extends", "final", "float",
    "goto", "implements", "instanceof", "int", "interface", "long",
    "native", "new", "null", "package", "private", "protected", "public",
    "short", "static", "strictfp", "super", "switch", "synchronized",
    "this", "throw", "throws", "transient", "void", "volatile",
    # Go
    "chan", "defer", "fallthrough", "func", "go", "map", "range",
    "select", "struct", "type", "var",
    # JavaScript / TypeScript
    "arguments", "debugger", "delete", "eval", "export", "function",
    "let", "typeof", "undefined", "window",
}

_MAX_NAME_LENGTH = 50


def _make_id() -> str:
    """Generate a unique finding ID."""
    return f"naming-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_naming_conventions(entities: List[Entity]) -> List[Finding]:
    """Check naming conventions across all entities.

    Rules applied per language:
    - Python: functions/methods snake_case, classes PascalCase, constants UPPER_SNAKE
    - Go: exported (capitalised) vs unexported checks
    - Java / C#: classes PascalCase, methods camelCase
    - General: single-char names, names > 50 chars, reserved word identifiers
    """
    findings: List[Finding] = []

    for entity in entities:
        name = entity.name
        lang = (entity.language or "").lower()
        etype = entity.type
        file_path = entity.location.file if entity.location else ""
        line = entity.location.start_line if entity.location else None

        # Skip file / module level entities — their "name" is a path
        if etype in (EntityType.FILE, EntityType.MODULE, EntityType.IMPORT, EntityType.EXPORT):
            continue

        # Skip entities from JSON/config files — keys like "private",
        # "extends", "dependencies" are not code identifiers
        if file_path.endswith((".json", ".yaml", ".yml", ".toml")):
            continue

        # --- General checks ------------------------------------------------

        # Single-character names (except common loop variables)
        if len(name) == 1 and name not in _LOOP_VARS:
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Single-character name '{name}' is not descriptive.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Use a more descriptive name that conveys intent.",
            ))

        # Overly long names
        if len(name) > _MAX_NAME_LENGTH:
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Name '{name[:40]}...' exceeds {_MAX_NAME_LENGTH} characters ({len(name)}).",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Consider a shorter, equally descriptive name.",
            ))

        # Reserved word used as identifier
        if name in _RESERVED:
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.ERROR,
                message=f"Name '{name}' is a language reserved word used as an identifier.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Rename to avoid conflicts with language keywords.",
            ))

        # --- Language-specific checks --------------------------------------

        if lang == "python":
            _check_python_naming(entity, name, etype, file_path, line, findings)
        elif lang == "go":
            _check_go_naming(entity, name, etype, file_path, line, findings)
        elif lang in ("java", "c_sharp", "csharp", "kotlin"):
            _check_java_csharp_naming(entity, name, etype, file_path, line, findings)

    return findings


# ---------------------------------------------------------------------------
# Language-specific checkers
# ---------------------------------------------------------------------------

def _check_python_naming(
    entity: Entity,
    name: str,
    etype: EntityType,
    file_path: str,
    line: int | None,
    findings: List[Finding],
) -> None:
    """Apply Python naming conventions."""
    # Classes should be PascalCase
    if etype == EntityType.CLASS:
        if not _is_pascal_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Python class '{name}' should be PascalCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{_to_pascal(name)}'.",
            ))

    # Functions / methods should be snake_case
    elif etype in (EntityType.FUNCTION, EntityType.METHOD):
        # Dunder methods are allowed (e.g. __init__)
        if name.startswith("__") and name.endswith("__"):
            return
        if not _is_snake_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Python function/method '{name}' should be snake_case.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{_to_snake(name)}'.",
            ))

    # Constants should be UPPER_SNAKE_CASE
    elif etype == EntityType.CONSTANT:
        if not _is_upper_snake(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.INFO,
                message=f"Python constant '{name}' should be UPPER_SNAKE_CASE.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{name.upper()}'.",
            ))


def _check_go_naming(
    entity: Entity,
    name: str,
    etype: EntityType,
    file_path: str,
    line: int | None,
    findings: List[Finding],
) -> None:
    """Apply Go naming conventions (exported vs unexported)."""
    if not name:
        return

    is_exported = name[0].isupper()

    # Struct / interface types should be PascalCase if exported
    if etype in (EntityType.CLASS, EntityType.STRUCT, EntityType.INTERFACE):
        if is_exported and not _is_pascal_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Go exported type '{name}' should be PascalCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Use PascalCase for exported type names.",
            ))

    # Functions: exported should be PascalCase, unexported should be camelCase
    if etype in (EntityType.FUNCTION, EntityType.METHOD):
        if is_exported and not _is_pascal_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Go exported function '{name}' should be PascalCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Use PascalCase for exported function names.",
            ))
        elif not is_exported and not _is_camel_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.INFO,
                message=f"Go unexported function '{name}' is typically camelCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Use camelCase for unexported function names.",
            ))

    # Constants: Go conventionally uses PascalCase (exported) or camelCase
    if etype == EntityType.CONSTANT:
        if is_exported and not _is_pascal_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.INFO,
                message=f"Go exported constant '{name}' is typically PascalCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion="Use PascalCase for exported constants in Go.",
            ))


def _check_java_csharp_naming(
    entity: Entity,
    name: str,
    etype: EntityType,
    file_path: str,
    line: int | None,
    findings: List[Finding],
) -> None:
    """Apply Java / C# naming conventions."""
    # Classes / interfaces should be PascalCase
    if etype in (EntityType.CLASS, EntityType.INTERFACE, EntityType.ENUM):
        if not _is_pascal_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Class/interface '{name}' should be PascalCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{_to_pascal(name)}'.",
            ))

    # Methods should be camelCase
    elif etype in (EntityType.FUNCTION, EntityType.METHOD):
        if not _is_camel_case(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.WARNING,
                message=f"Method '{name}' should be camelCase.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{_to_camel(name)}'.",
            ))

    # Constants typically UPPER_SNAKE in Java, PascalCase in C#
    elif etype == EntityType.CONSTANT:
        lang = (entity.language or "").lower()
        if lang == "java" and not _is_upper_snake(name):
            findings.append(Finding(
                finding_id=_make_id(),
                category=FindingCategory.NAMING,
                level=FindingLevel.INFO,
                message=f"Java constant '{name}' should be UPPER_SNAKE_CASE.",
                file_path=file_path,
                line=line,
                entity_id=entity.id,
                suggestion=f"Rename to '{name.upper()}'.",
            ))


# ---------------------------------------------------------------------------
# Name transformation helpers
# ---------------------------------------------------------------------------

def _to_snake(name: str) -> str:
    """Convert a name to snake_case (best-effort)."""
    # Insert underscores before uppercase letters
    s = re.sub(r"([A-Z]+)", r"_\1", name).strip("_").lower()
    # Collapse double underscores
    return re.sub(r"_+", "_", s)


def _to_pascal(name: str) -> str:
    """Convert a name to PascalCase (best-effort)."""
    parts = re.split(r"[_\s-]+", name)
    return "".join(p.capitalize() for p in parts if p)


def _to_camel(name: str) -> str:
    """Convert a name to camelCase (best-effort)."""
    pascal = _to_pascal(name)
    if not pascal:
        return name
    return pascal[0].lower() + pascal[1:]
