"""Cortex injector — Insert/update @blueprint:cortex blocks in source files.

Default mode: dry-run (never modify files without explicit opt-in).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import Entity, EntityType
from src.cortex.formatters import get_formatter_for_file
from src.cortex.schema import CortexBlock


class InjectionResult:
    """Result of an injection operation on a single file."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.blocks_inserted = 0
        self.blocks_updated = 0
        self.blocks_skipped = 0
        self.new_source: Optional[str] = None  # Only set if changes were made

    @property
    def total_changes(self) -> int:
        return self.blocks_inserted + self.blocks_updated

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0


def inject_cortex_blocks(
    file_path: str,
    source: str,
    entities: List[Entity],
    calls_map: Dict[str, List[str]],
    uses_map: Dict[str, List[str]],
    *,
    dry_run: bool = True,
    overwrite: bool = False,
) -> InjectionResult:
    """Inject @blueprint:cortex blocks above entities in a source file.

    Args:
        file_path: Relative file path.
        source: Current source code.
        entities: Entities in this file (functions, classes, methods).
        calls_map: Mapping entity_id -> [callee_ids].
        uses_map: Mapping entity_id -> [use_ids].
        dry_run: If True, compute changes but don't modify source.
        overwrite: If True, overwrite existing cortex blocks.

    Returns:
        InjectionResult with details and optionally new source.
    """
    result = InjectionResult(file_path)

    formatter = get_formatter_for_file(file_path)
    if not formatter:
        return result

    # Get entities that should have cortex blocks (functions, classes, methods)
    injectable = [
        e for e in entities
        if e.type in (EntityType.FUNCTION, EntityType.CLASS, EntityType.METHOD)
        and e.location
    ]

    if not injectable:
        return result

    # Sort by line number descending so we can insert without shifting later lines
    injectable.sort(key=lambda e: -(e.location.start_line if e.location else 0))

    lines = source.splitlines(keepends=True)

    # Find existing cortex blocks
    existing_blocks = _find_existing_blocks(lines, formatter.comment_prefix())

    for entity in injectable:
        if not entity.location:
            continue

        insert_line = entity.location.start_line - 1  # 0-indexed

        # Check if there's already a cortex block above this entity
        existing = existing_blocks.get(insert_line)
        if existing and not overwrite:
            # Update last_visited timestamp only
            result.blocks_skipped += 1
            continue

        # Build CortexBlock
        block = CortexBlock(
            id=entity.id,
            entity_type=entity.type.value,
            calls=calls_map.get(entity.id, []),
            uses=uses_map.get(entity.id, []),
            complexity=entity.metrics.cyclomatic_complexity if entity.metrics else None,
            loc=entity.metrics.loc_code if entity.metrics else None,
        )

        # Preserve created timestamp from existing block
        if existing:
            block.created = existing.created
            result.blocks_updated += 1
        else:
            result.blocks_inserted += 1

        # Format the block
        comment = formatter.format_block(block)

        if not dry_run:
            # Remove existing block if overwriting
            if existing:
                lines = _remove_block_at(lines, insert_line, formatter.comment_prefix())

            # Insert new block
            indent = _get_indent(lines, insert_line)
            indented_comment = _indent_comment(comment, indent)
            lines.insert(insert_line, indented_comment + "\n")

    if result.has_changes:
        result.new_source = "".join(lines)

    return result


def _find_existing_blocks(
    lines: List[str],
    prefix: str,
) -> Dict[int, CortexBlock]:
    """Find existing @blueprint:cortex blocks and the line they precede.

    Returns:
        Dict mapping the line number AFTER the block -> CortexBlock.
    """
    import json

    blocks: Dict[int, CortexBlock] = {}
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if "@blueprint:cortex" in stripped:
            start = i
            comment_lines: List[str] = []
            i += 1
            while i < len(lines):
                stripped = lines[i].strip()
                if "@end:cortex" in stripped:
                    i += 1
                    break
                content = stripped
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
                comment_lines.append(content)
                i += 1

            # The entity starts at the line after the block
            entity_line = i
            try:
                json_str = "\n".join(comment_lines)
                data = json.loads(json_str)
                block = CortexBlock.from_comment_dict(data)
                blocks[entity_line] = block
            except Exception:
                pass
        else:
            i += 1

    return blocks


def _remove_block_at(
    lines: List[str],
    entity_line: int,
    prefix: str,
) -> List[str]:
    """Remove a cortex block that precedes the given entity line."""
    # Search backwards from entity_line for @end:cortex, then @blueprint:cortex
    end_line = entity_line - 1
    if end_line < 0:
        return lines

    # Find the end marker
    while end_line >= 0:
        if "@end:cortex" in lines[end_line]:
            break
        end_line -= 1

    if end_line < 0:
        return lines

    # Find the start marker
    start_line = end_line
    while start_line >= 0:
        if "@blueprint:cortex" in lines[start_line]:
            break
        start_line -= 1

    if start_line < 0:
        return lines

    # Remove the block
    return lines[:start_line] + lines[end_line + 1:]


def _get_indent(lines: List[str], line_idx: int) -> str:
    """Get the indentation of a specific line."""
    if line_idx < len(lines):
        line = lines[line_idx]
        return line[: len(line) - len(line.lstrip())]
    return ""


def _indent_comment(comment: str, indent: str) -> str:
    """Add indentation to each line of a comment."""
    return "\n".join(indent + line for line in comment.splitlines())
