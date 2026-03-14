"""Git analysis for Blueprint X-Ray.

Uses subprocess to call git commands for blame, churn, change frequency,
and last-modified information. All operations are non-blocking and
failures are silently handled (git is always optional).
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import Entity, GitInfo


def is_git_repo(root: Path) -> bool:
    """Check if the given path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_last_modified(root: Path, file_path: str) -> Optional[GitInfo]:
    """Get git info for a specific file.

    Args:
        root: Repository root directory.
        file_path: Relative file path.

    Returns:
        GitInfo with last_modified, last_author, change_count.
    """
    try:
        # Last commit info
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%aI|%an", "--", file_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if log_result.returncode != 0 or not log_result.stdout.strip():
            return None

        parts = log_result.stdout.strip().split("|", 1)
        date_str = parts[0]
        author = parts[1] if len(parts) > 1 else "unknown"

        try:
            last_modified = datetime.fromisoformat(date_str)
        except ValueError:
            last_modified = None

        # Change count (number of commits touching this file)
        count_result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD", "--", file_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        change_count = 0
        if count_result.returncode == 0:
            try:
                change_count = int(count_result.stdout.strip())
            except ValueError:
                pass

        return GitInfo(
            last_modified=last_modified,
            last_author=author,
            change_count=change_count,
        )
    except Exception:
        return None


def get_file_churn(root: Path, file_path: str, max_commits: int = 100) -> int:
    """Get the total lines changed (added + deleted) for a file.

    Args:
        root: Repository root.
        file_path: Relative file path.
        max_commits: Maximum commits to scan.

    Returns:
        Total churn (lines added + deleted).
    """
    try:
        result = subprocess.run(
            [
                "git", "log", f"-{max_commits}",
                "--numstat", "--format=", "--", file_path,
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return 0

        churn = 0
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != "-" else 0
                    deleted = int(parts[1]) if parts[1] != "-" else 0
                    churn += added + deleted
                except ValueError:
                    continue
        return churn
    except Exception:
        return 0


def get_blame_summary(
    root: Path,
    file_path: str,
    start_line: int = 1,
    end_line: int = 0,
) -> Dict[str, int]:
    """Get author contribution summary from git blame.

    Args:
        root: Repository root.
        file_path: Relative file path.
        start_line: Start line (1-based).
        end_line: End line (0 = end of file).

    Returns:
        Dict mapping author -> line count.
    """
    try:
        cmd = ["git", "blame", "--porcelain"]
        if end_line > 0:
            cmd.extend([f"-L{start_line},{end_line}"])
        cmd.extend(["--", file_path])

        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}

        authors: Dict[str, int] = {}
        for line in result.stdout.splitlines():
            if line.startswith("author "):
                author = line[7:].strip()
                authors[author] = authors.get(author, 0) + 1
        return authors
    except Exception:
        return {}


def get_change_frequency(
    root: Path,
    days: int = 90,
    max_files: int = 100,
) -> List[Tuple[str, int]]:
    """Get most frequently changed files in the last N days.

    Args:
        root: Repository root.
        days: Number of days to look back.
        max_files: Max files to return.

    Returns:
        List of (file_path, change_count) tuples, sorted by frequency.
    """
    try:
        result = subprocess.run(
            [
                "git", "log", f"--since={days} days ago",
                "--name-only", "--format=",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        file_counts: Dict[str, int] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                file_counts[line] = file_counts.get(line, 0) + 1

        sorted_files = sorted(
            file_counts.items(),
            key=lambda x: -x[1],
        )
        return sorted_files[:max_files]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Integration with X-Ray engine
# ---------------------------------------------------------------------------

def enrich_with_git(
    root: Path,
    entities: List[Entity],
) -> None:
    """Enrich entities with git information.

    Modifies entities in-place, adding git_info where available.

    Args:
        root: Repository root directory.
        entities: List of entities to enrich.
    """
    if not is_git_repo(root):
        return

    # Cache per-file git info to avoid repeated calls
    file_cache: Dict[str, Optional[GitInfo]] = {}

    for entity in entities:
        if not entity.location:
            continue

        file_path = entity.location.file
        if file_path not in file_cache:
            file_cache[file_path] = get_last_modified(root, file_path)

        git_info = file_cache.get(file_path)
        if git_info:
            entity.git_info = git_info
