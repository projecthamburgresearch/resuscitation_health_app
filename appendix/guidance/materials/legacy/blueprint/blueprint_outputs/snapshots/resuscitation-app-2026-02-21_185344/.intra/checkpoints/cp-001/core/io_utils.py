"""File I/O utilities for Blueprint."""

from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path
from typing import List, Tuple


# Default patterns to exclude from scanning
DEFAULT_EXCLUDE = [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/__pycache__/**",
    "**/.next/**",
    "**/.venv/**",
    "**/venv/**",
    "**/*.pyc",
    "**/.history/**",
    "**/.specstory/**",
]

# File extensions Blueprint can process
TEXT_EXTS = {
    # Code
    ".py", ".pyw",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt", ".kts",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx",
    # Config
    ".yml", ".yaml", ".json", ".toml", ".env", ".ini", ".cfg",
    # Web
    ".html", ".htm", ".xml", ".css", ".scss", ".sass", ".less",
    # Data
    ".sql", ".csv",
    # Docs
    ".md", ".txt", ".rst",
    # Shell
    ".sh", ".bash", ".zsh",
}


def sha1_bytes(b: bytes) -> str:
    """Compute SHA1 hex digest of bytes."""
    return hashlib.sha1(b).hexdigest()


def safe_read_text(path: Path, max_bytes: int = 1_500_000) -> Tuple[str, bytes]:
    """Read a file safely, truncating if too large. Returns (text, raw_bytes)."""
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace"), raw


def normalize_path(p: Path, root: Path) -> str:
    """Get path relative to root, normalized with forward slashes."""
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def ensure_dir(p: Path) -> None:
    """Create directory and parents if they don't exist."""
    p.mkdir(parents=True, exist_ok=True)


def glob_match(path_str: str, patterns: List[str]) -> bool:
    """Check if path matches any of the given glob patterns."""
    if not patterns:
        return True
    return any(fnmatch.fnmatch(path_str, pat) for pat in patterns)


def _match_double_star(path_str: str, pattern: str) -> bool:
    """Match a path against a pattern that may contain ** globs.

    Handles **/ (match any number of directories) correctly,
    unlike fnmatch which treats * as single-segment only.

    Examples:
        **/.git/** matches .git/objects/abc and sub/.git/config
        **/node_modules/** matches node_modules/foo and a/node_modules/b
        **/*.pyc matches foo/bar.pyc and bar.pyc
        **/package-lock.json matches package-lock.json and sub/package-lock.json
    """
    # Fast path: no ** in pattern, use fnmatch directly
    if "**" not in pattern:
        return fnmatch.fnmatch(path_str, pattern)

    parts = path_str.split("/")

    if pattern.startswith("**/") and pattern.endswith("/**"):
        # Middle match: e.g. **/.git/** — path contains this segment
        middle = pattern[3:-3]  # strip **/ and /**
        if "/" in middle:
            # Multi-segment middle: e.g. **/foo/bar/**
            return (f"/{middle}/" in f"/{path_str}/"
                    or path_str.startswith(f"{middle}/")
                    or path_str.endswith(f"/{middle}"))
        # Single segment: check if any path segment matches
        return middle in parts

    if pattern.startswith("**/"):
        # Suffix match: e.g. **/*.pyc or **/package-lock.json
        suffix_pattern = pattern[3:]
        # Try matching the full path and every path suffix
        if fnmatch.fnmatch(path_str, suffix_pattern):
            return True
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            if fnmatch.fnmatch(suffix, suffix_pattern):
                return True
        return False

    if pattern.endswith("/**"):
        # Prefix match: e.g. dist/**
        prefix_pattern = pattern[:-3]
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            if fnmatch.fnmatch(prefix, prefix_pattern):
                return True
        return False

    # Fallback: try fnmatch
    return fnmatch.fnmatch(path_str, pattern)


def glob_excluded(path_str: str, patterns: List[str]) -> bool:
    """Check if path is excluded by any of the given glob patterns."""
    if not patterns:
        return False
    return any(_match_double_star(path_str, pat) for pat in patterns)


def take_snippet(lines: List[str], start_line: int, end_line: int,
                 max_lines: int = 12) -> str:
    """Extract a code snippet from lines, bounded by max_lines."""
    start = max(0, start_line - 1)
    end = min(len(lines), end_line)
    chunk = lines[start:end]
    if len(chunk) > max_lines:
        chunk = chunk[:max_lines] + ["...\n"]
    return "".join(chunk)


def pos_to_line(lines: List[str], pos: int) -> int:
    """Convert a byte/char position to a 1-based line number."""
    total = 0
    for i, ln in enumerate(lines, start=1):
        total += len(ln)
        if total >= pos:
            return i
    return max(1, len(lines))


def iter_files(
    root: Path,
    focus: Path | None = None,
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    max_files: int = 0,
    max_file_size: int = 1_500_000,
    extensions: set[str] | None = None,
    respect_bpignore: bool = True,
) -> List[Path]:
    """Discover files to analyze, respecting filters.

    Args:
        root: Project root directory.
        focus: Optional subdirectory to focus on.
        include_patterns: Only include files matching these globs.
        exclude_patterns: Exclude files matching these globs.
        max_files: Maximum files to return (0 = unlimited).
        max_file_size: Skip files larger than this (bytes).
        extensions: Allowed file extensions (default: TEXT_EXTS).
        respect_bpignore: If True, load .bpignore from root and merge
            its patterns into the exclude list.

    Returns:
        Sorted list of Path objects.
    """
    scan_dir = focus if focus and focus.exists() else root
    exts = extensions or TEXT_EXTS
    excl = list(exclude_patterns or DEFAULT_EXCLUDE)

    # Merge .bpignore patterns if present
    if respect_bpignore:
        bpignore_file = root / ".bpignore"
        if bpignore_file.is_file():
            try:
                from src.loader.bpignore import load_bpignore, merge_patterns
                bp_patterns = load_bpignore(root)
                if bp_patterns:
                    excl = merge_patterns(bp_patterns, excl)
            except ImportError:
                pass  # workspace module not available
    incl = include_patterns or []

    paths: List[Path] = []
    for p in scan_dir.rglob("*"):
        if not p.is_file():
            continue

        rel = normalize_path(p, root)
        ext = p.suffix.lower()

        # Extension filter
        if ext and ext not in exts:
            continue

        # Exclude filter
        if glob_excluded(rel, excl):
            continue

        # Include filter (if specified, file must match)
        if incl and not glob_match(rel, incl):
            continue

        # Size filter
        try:
            if p.stat().st_size > max_file_size:
                continue
        except OSError:
            continue

        paths.append(p)

    # Sort for deterministic output
    paths.sort(key=lambda x: normalize_path(x, root))

    # Cap
    if max_files > 0 and len(paths) > max_files:
        paths = paths[:max_files]

    return paths
