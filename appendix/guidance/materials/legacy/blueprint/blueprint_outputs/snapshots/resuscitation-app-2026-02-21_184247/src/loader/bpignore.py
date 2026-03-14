"""Blueprint ignore file (.bpignore) parser.

Reads .bpignore files (gitignore-compatible syntax) from project roots
and merges them with Blueprint's built-in exclusion patterns.

Syntax:
- Lines starting with # are comments
- Empty lines are ignored
- Standard glob patterns (*, **, ?)
- Trailing / means directory only
- Leading ! negates (un-ignores) a pattern
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from src.core.io_utils import DEFAULT_EXCLUDE


BPIGNORE_FILENAME = ".bpignore"


def load_bpignore(project_root: Path) -> List[str]:
    """Load .bpignore patterns from a project root.

    Args:
        project_root: Path to the project being analyzed.

    Returns:
        List of glob patterns (may include ! negation prefixes).
        Returns empty list if no .bpignore exists.
    """
    bpignore_path = project_root / BPIGNORE_FILENAME
    if not bpignore_path.is_file():
        return []

    try:
        text = bpignore_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    return parse_bpignore(text)


def parse_bpignore(text: str) -> List[str]:
    """Parse .bpignore file content into glob patterns.

    Args:
        text: Raw text content of a .bpignore file.

    Returns:
        List of glob patterns.
    """
    patterns: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def split_patterns(patterns: List[str]) -> Tuple[List[str], List[str]]:
    """Split patterns into exclude and include (negated) lists.

    Negated patterns start with ! and mean "do NOT exclude this".

    Args:
        patterns: List of glob patterns, possibly with ! prefix.

    Returns:
        (exclude_patterns, include_patterns)
        - exclude_patterns: patterns to exclude (without !)
        - include_patterns: patterns to forcibly include (! removed)
    """
    excludes: List[str] = []
    includes: List[str] = []
    for pat in patterns:
        if pat.startswith("!"):
            # Negation -- force include
            includes.append(pat[1:].strip())
        else:
            excludes.append(pat)
    return excludes, includes


def normalize_pattern(pattern: str) -> str:
    """Normalize a .bpignore pattern into a glob suitable for path matching.

    Ensures patterns work consistently across platforms:
    - Directory patterns (trailing /) get ** prefix/suffix
    - File patterns (with extension) get ** prefix only
    - Bare names without extension get both file + directory treatment
    """
    pat = pattern.replace("\\", "/").strip("/")

    # If pattern ends with / it's explicitly a directory pattern
    if pattern.rstrip().endswith("/"):
        if not pat.startswith("**/"):
            pat = f"**/{pat}"
        if not pat.endswith("/**"):
            pat = f"{pat}/**"
        return pat

    # Check if this looks like a file (has a dot-extension in the last segment)
    last_segment = pat.rsplit("/", 1)[-1]
    has_extension = "." in last_segment and "*" not in last_segment

    if has_extension:
        # File pattern — match anywhere but don't add trailing /**
        # e.g., "package-lock.json" -> "**/package-lock.json"
        # e.g., ".env" -> "**/.env"
        if not pat.startswith("**/"):
            pat = f"**/{pat}"
        return pat

    # Bare name without extension and no wildcards — treat as directory
    # e.g., "node_modules" -> "**/node_modules/**"
    if "/" not in pat and "*" not in pat and "?" not in pat:
        return f"**/{pat}/**"

    # If no leading ** and no leading /, prefix with **/ for "anywhere" match
    if not pat.startswith("**/") and not pat.startswith("/"):
        pat = f"**/{pat}"

    return pat


def merge_patterns(
    bpignore_patterns: List[str],
    default_patterns: List[str] | None = None,
) -> List[str]:
    """Merge .bpignore patterns with Blueprint defaults.

    .bpignore patterns are additive -- they add to the default excludes.
    Negated patterns (!) remove from the merged set.

    Args:
        bpignore_patterns: Patterns from .bpignore file.
        default_patterns: Built-in defaults (uses DEFAULT_EXCLUDE if None).

    Returns:
        Final merged list of exclusion patterns.
    """
    defaults = list(default_patterns or DEFAULT_EXCLUDE)
    bp_excludes, bp_includes = split_patterns(bpignore_patterns)

    # Normalize bpignore patterns for consistent matching
    normalized_excludes = [normalize_pattern(p) for p in bp_excludes]

    # Start with defaults + bpignore excludes
    merged = defaults + normalized_excludes

    # Remove patterns that match any negation
    if bp_includes:
        negated_normalized = [normalize_pattern(p) for p in bp_includes]
        merged = [
            m for m in merged
            if not any(_patterns_match(m, neg) for neg in negated_normalized)
        ]

    # Deduplicate while preserving order
    seen: set = set()
    result: List[str] = []
    for pat in merged:
        if pat not in seen:
            seen.add(pat)
            result.append(pat)

    return result


def _patterns_match(pattern: str, negation: str) -> bool:
    """Check if a negation pattern should remove an exclude pattern.

    Simple substring/equality check -- a negation for "dist" should
    remove "**/dist/**" from the exclude list.
    """
    # Direct match
    if pattern == negation:
        return True

    # Strip ** wrappers for comparison
    stripped_pat = pattern.strip("*").strip("/")
    stripped_neg = negation.strip("*").strip("/")

    if stripped_pat and stripped_neg:
        return stripped_pat == stripped_neg

    return False
