"""Cortex reader — Scan files for existing @blueprint:cortex blocks."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from src.cortex.formatters import get_formatter_for_file
from src.cortex.schema import CortexBlock


def read_cortex_blocks(
    file_path: str,
    source: str,
) -> List[CortexBlock]:
    """Read all @blueprint:cortex blocks from a source file.

    Args:
        file_path: File path (used to select formatter).
        source: Source code text.

    Returns:
        List of CortexBlocks found in the file.
    """
    formatter = get_formatter_for_file(file_path)
    if not formatter:
        return []

    return formatter.extract_blocks_from_source(source)


def scan_directory(
    root: Path,
    *,
    extensions: Optional[set] = None,
) -> Dict[str, List[CortexBlock]]:
    """Scan a directory for all @blueprint:cortex blocks.

    Args:
        root: Directory to scan.
        extensions: File extensions to scan (default: all supported).

    Returns:
        Dict mapping file_path -> list of CortexBlocks.
    """
    from src.core.io_utils import iter_files, normalize_path

    results: Dict[str, List[CortexBlock]] = {}

    files = iter_files(root, extensions=extensions)
    for file_path in files:
        rel_path = normalize_path(file_path, root)
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            blocks = read_cortex_blocks(rel_path, source)
            if blocks:
                results[rel_path] = blocks
        except Exception:
            continue

    return results
