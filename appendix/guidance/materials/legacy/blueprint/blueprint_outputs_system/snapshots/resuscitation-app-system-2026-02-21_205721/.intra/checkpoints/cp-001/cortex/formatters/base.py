"""Base class for comment formatters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.cortex.schema import CortexBlock


class CommentFormatter(ABC):
    """Base class for language-specific comment formatters.

    Each formatter knows how to:
    1. Format a CortexBlock into native comment syntax
    2. Parse an existing @blueprint:cortex comment back into a CortexBlock
    """

    @abstractmethod
    def comment_prefix(self) -> str:
        """Return the comment prefix (e.g., '#', '//')."""
        ...

    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return supported file extensions."""
        ...

    def format_block(self, block: CortexBlock) -> str:
        """Format a CortexBlock as a native comment.

        Returns multi-line comment string.
        """
        import json
        data = block.to_comment_dict()
        json_str = json.dumps(data, indent=2, default=str)

        prefix = self.comment_prefix()
        lines = [f"{prefix} @blueprint:cortex"]
        for line in json_str.splitlines():
            lines.append(f"{prefix} {line}")
        lines.append(f"{prefix} @end:cortex")

        return "\n".join(lines)

    def parse_block(self, comment_lines: List[str]) -> Optional[CortexBlock]:
        """Parse a CortexBlock from comment lines.

        Args:
            comment_lines: Lines between @blueprint:cortex and @end:cortex,
                          with comment prefix stripped.

        Returns:
            CortexBlock or None if parsing fails.
        """
        import json
        try:
            # Join lines and parse as JSON
            json_str = "\n".join(comment_lines)
            data = json.loads(json_str)
            return CortexBlock.from_comment_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def extract_blocks_from_source(self, source: str) -> List[CortexBlock]:
        """Extract all CortexBlocks from a source file.

        Args:
            source: Full source code text.

        Returns:
            List of parsed CortexBlocks.
        """
        blocks: List[CortexBlock] = []
        lines = source.splitlines()
        prefix = self.comment_prefix()

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith(prefix) and "@blueprint:cortex" in stripped:
                # Found start marker — collect lines until @end:cortex
                comment_lines: List[str] = []
                i += 1
                while i < len(lines):
                    stripped = lines[i].strip()
                    if "@end:cortex" in stripped:
                        break
                    # Remove comment prefix
                    content = stripped
                    if content.startswith(prefix):
                        content = content[len(prefix):].strip()
                    comment_lines.append(content)
                    i += 1

                block = self.parse_block(comment_lines)
                if block:
                    blocks.append(block)
            i += 1

        return blocks
