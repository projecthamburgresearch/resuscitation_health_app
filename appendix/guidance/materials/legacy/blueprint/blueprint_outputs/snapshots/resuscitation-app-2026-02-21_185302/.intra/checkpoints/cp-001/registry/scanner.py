"""Project scope detection for the Registry domain.

Walks the filesystem to build a ProjectProfile capturing file counts,
language distribution, largest files, estimated entity counts, and
directory structure.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.core.config import BlueprintConfig
from src.core.io_utils import iter_files, normalize_path, TEXT_EXTS
from src.registry.schema import ProjectProfile


# ---------------------------------------------------------------------------
# Extension-to-language mapping
# ---------------------------------------------------------------------------

_EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".hh": "cpp",
    ".cxx": "cpp",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".env": "config",
    ".ini": "config",
    ".cfg": "config",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".css": "css",
    ".scss": "scss",
    ".sass": "scss",
    ".less": "less",
    ".sql": "sql",
    ".csv": "csv",
    ".md": "markdown",
    ".txt": "text",
    ".rst": "rst",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
}

# Extensions considered "code" files (higher entity estimate)
_CODE_EXTS: Set[str] = {
    ".py", ".pyw", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".cs", ".rb", ".php", ".swift",
    ".kt", ".kts", ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx",
}

# Extensions considered "config" files (lower entity estimate)
_CONFIG_EXTS: Set[str] = {
    ".yml", ".yaml", ".json", ".toml", ".env", ".ini", ".cfg",
    ".xml", ".sql",
}

# Entities-per-file heuristics
_ENTITIES_PER_CODE_FILE = 10
_ENTITIES_PER_CONFIG_FILE = 3
_TOP_LARGEST_FILES = 20


def _language_for_ext(ext: str) -> str:
    """Map a file extension to a language name."""
    return _EXT_TO_LANGUAGE.get(ext.lower(), "unknown")


def scan_project_profile(root: Path, config: BlueprintConfig) -> ProjectProfile:
    """Walk the filesystem and build a ProjectProfile.

    Uses ``io_utils.iter_files`` to discover scannable files, then
    aggregates statistics about file counts, sizes, language distribution,
    largest files, estimated entity counts, and directory count.

    Args:
        root: The project root directory.
        config: Blueprint configuration (controls filters and limits).

    Returns:
        A fully-populated ProjectProfile.
    """
    files = iter_files(
        root=root,
        focus=config.focus_path,
        include_patterns=config.include_patterns,
        exclude_patterns=config.exclude_patterns,
        max_files=config.max_files,
        max_file_size=config.max_file_size,
    )

    total_files = 0
    total_size_bytes = 0
    language_counter: Counter[str] = Counter()
    file_sizes: List[Tuple[str, int]] = []
    directories: Set[str] = set()
    estimated_entities = 0

    for file_path in files:
        total_files += 1
        rel = normalize_path(file_path, root)
        ext = file_path.suffix.lower()

        # File size
        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
        total_size_bytes += size
        file_sizes.append((rel, size))

        # Language distribution
        lang = _language_for_ext(ext)
        language_counter[lang] += 1

        # Entity estimate heuristic
        if ext in _CODE_EXTS:
            estimated_entities += _ENTITIES_PER_CODE_FILE
        elif ext in _CONFIG_EXTS:
            estimated_entities += _ENTITIES_PER_CONFIG_FILE
        else:
            # Documentation, text, etc. -- minimal entities
            estimated_entities += 1

        # Track parent directories
        parent = normalize_path(file_path.parent, root)
        if parent and parent != ".":
            directories.add(parent)
            # Also add ancestor directories
            parts = parent.split("/")
            for i in range(1, len(parts)):
                directories.add("/".join(parts[:i]))

    # Sort by size descending, keep top N
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    largest_files = file_sizes[:_TOP_LARGEST_FILES]

    # Convert Counter to plain dict sorted by count descending
    language_distribution: Dict[str, int] = dict(
        language_counter.most_common()
    )

    return ProjectProfile(
        total_files=total_files,
        total_size_bytes=total_size_bytes,
        language_distribution=language_distribution,
        largest_files=largest_files,
        estimated_entities=estimated_entities,
        directory_count=len(directories),
    )
