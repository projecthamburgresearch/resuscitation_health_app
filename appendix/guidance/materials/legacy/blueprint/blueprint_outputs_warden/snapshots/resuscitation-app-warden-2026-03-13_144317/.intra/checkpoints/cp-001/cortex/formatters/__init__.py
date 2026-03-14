"""Cortex comment formatters for different language comment syntaxes."""

from __future__ import annotations

from typing import Dict, Optional, Type

from src.cortex.formatters.base import CommentFormatter

FORMATTER_REGISTRY: Dict[str, Type[CommentFormatter]] = {}


def register_formatter(formatter_class: Type[CommentFormatter]) -> Type[CommentFormatter]:
    """Register a formatter class for its declared file extensions."""
    instance = formatter_class()
    for ext in instance.file_extensions():
        FORMATTER_REGISTRY[ext] = formatter_class
    return formatter_class


def get_formatter_for_file(file_path: str) -> Optional[CommentFormatter]:
    """Get the appropriate comment formatter for a file."""
    _auto_register()
    from pathlib import Path
    ext = Path(file_path).suffix.lower()
    fmt_cls = FORMATTER_REGISTRY.get(ext)
    return fmt_cls() if fmt_cls else None


def _auto_register():
    """Import all formatter modules to trigger registration."""
    if FORMATTER_REGISTRY:
        return  # Already registered
    try:
        from src.cortex.formatters import hash_fmt  # noqa: F401
    except ImportError:
        pass
    try:
        from src.cortex.formatters import slash_fmt  # noqa: F401
    except ImportError:
        pass
    try:
        from src.cortex.formatters import block_fmt  # noqa: F401
    except ImportError:
        pass
    try:
        from src.cortex.formatters import html_fmt  # noqa: F401
    except ImportError:
        pass
