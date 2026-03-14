"""Hash-style comment formatter (#) for Python, Ruby, Bash."""

from __future__ import annotations

from typing import List

from src.cortex.formatters.base import CommentFormatter
from src.cortex.formatters import register_formatter


class HashFormatter(CommentFormatter):
    """Formatter for # comment languages (Python, Ruby, Bash, etc.)."""

    def comment_prefix(self) -> str:
        return "#"

    def file_extensions(self) -> List[str]:
        return [".py", ".pyw", ".rb", ".sh", ".bash", ".zsh", ".yml", ".yaml"]


register_formatter(HashFormatter)
