"""Slash-style comment formatter (//) for TS, JS, Go, Rust, Java, etc."""

from __future__ import annotations

from typing import List

from src.cortex.formatters.base import CommentFormatter
from src.cortex.formatters import register_formatter


class SlashFormatter(CommentFormatter):
    """Formatter for // comment languages."""

    def comment_prefix(self) -> str:
        return "//"

    def file_extensions(self) -> List[str]:
        return [
            ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
            ".go", ".rs", ".java", ".cs", ".swift", ".kt", ".kts",
            ".c", ".h", ".cpp", ".hpp", ".cc",
        ]


register_formatter(SlashFormatter)
