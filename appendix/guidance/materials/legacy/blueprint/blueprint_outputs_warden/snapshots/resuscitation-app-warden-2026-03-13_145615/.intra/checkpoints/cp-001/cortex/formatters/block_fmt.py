"""Block-style comment formatter (/* */) for CSS, SCSS."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.cortex.formatters.base import CommentFormatter
from src.cortex.formatters import register_formatter
from src.cortex.schema import CortexBlock


class BlockFormatter(CommentFormatter):
    """Formatter for /* */ comment languages (CSS, SCSS, etc.)."""

    def comment_prefix(self) -> str:
        return " *"

    def file_extensions(self) -> List[str]:
        return [".css", ".scss", ".sass", ".less"]

    def format_block(self, block: CortexBlock) -> str:
        """Format as a /* ... */ block comment."""
        import json
        data = block.to_comment_dict()
        json_str = json.dumps(data, indent=2, default=str)

        lines = ["/* @blueprint:cortex"]
        for line in json_str.splitlines():
            lines.append(f" * {line}")
        lines.append(" * @end:cortex")
        lines.append(" */")

        return "\n".join(lines)

    def extract_blocks_from_source(self, source: str) -> List[CortexBlock]:
        """Extract CortexBlocks from CSS-style block comments."""
        blocks: List[CortexBlock] = []
        lines = source.splitlines()

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if "@blueprint:cortex" in stripped:
                comment_lines: List[str] = []
                i += 1
                while i < len(lines):
                    stripped = lines[i].strip()
                    if "@end:cortex" in stripped:
                        break
                    content = stripped
                    if content.startswith("*"):
                        content = content[1:].strip()
                    elif content.startswith("/*"):
                        content = content[2:].strip()
                    comment_lines.append(content)
                    i += 1

                block = self.parse_block(comment_lines)
                if block:
                    blocks.append(block)
            i += 1

        return blocks


register_formatter(BlockFormatter)
