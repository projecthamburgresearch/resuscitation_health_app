"""HTML-style comment formatter (<!-- -->) for HTML, XML."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.cortex.formatters.base import CommentFormatter
from src.cortex.formatters import register_formatter
from src.cortex.schema import CortexBlock


class HTMLFormatter(CommentFormatter):
    """Formatter for <!-- --> comment languages (HTML, XML)."""

    def comment_prefix(self) -> str:
        return "  "

    def file_extensions(self) -> List[str]:
        return [".html", ".htm", ".xml", ".svg"]

    def format_block(self, block: CortexBlock) -> str:
        """Format as an HTML comment."""
        import json
        data = block.to_comment_dict()
        json_str = json.dumps(data, indent=2, default=str)

        lines = ["<!-- @blueprint:cortex"]
        for line in json_str.splitlines():
            lines.append(f"  {line}")
        lines.append("  @end:cortex")
        lines.append("-->")

        return "\n".join(lines)

    def extract_blocks_from_source(self, source: str) -> List[CortexBlock]:
        """Extract CortexBlocks from HTML comments."""
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
                    if content.startswith("<!--"):
                        content = content[4:].strip()
                    if content.endswith("-->"):
                        content = content[:-3].strip()
                    comment_lines.append(content)
                    i += 1

                block = self.parse_block(comment_lines)
                if block:
                    blocks.append(block)
            i += 1

        return blocks


register_formatter(HTMLFormatter)
