"""X-Ray parser registry and language-specific parsers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Type

from src.xray.parsers.base import LanguageParser

# Registry mapping file extensions to parser classes
PARSER_REGISTRY: Dict[str, Type[LanguageParser]] = {}


def register_parser(parser_class: Type[LanguageParser]) -> Type[LanguageParser]:
    """Register a parser class for its declared file extensions."""
    instance = parser_class()
    for ext in instance.file_extensions():
        PARSER_REGISTRY[ext] = parser_class
    return parser_class


def get_parser_for_file(file_path: str) -> Optional[LanguageParser]:
    """Get the appropriate parser for a file based on its extension."""
    ext = Path(file_path).suffix.lower()
    parser_cls = PARSER_REGISTRY.get(ext)
    return parser_cls() if parser_cls else None


def get_supported_extensions() -> list[str]:
    """Return list of all supported file extensions."""
    return sorted(PARSER_REGISTRY.keys())


def _auto_register():
    """Import all parser modules to trigger registration."""
    # Each parser module calls register_parser() at module level
    try:
        from src.xray.parsers import python_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import typescript_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import go_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import rust_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import java_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import csharp_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import ruby_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import php_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import swift_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import kotlin_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import c_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import config_parser  # noqa: F401
    except ImportError:
        pass
    try:
        from src.xray.parsers import web_parser  # noqa: F401
    except ImportError:
        pass


_auto_register()
