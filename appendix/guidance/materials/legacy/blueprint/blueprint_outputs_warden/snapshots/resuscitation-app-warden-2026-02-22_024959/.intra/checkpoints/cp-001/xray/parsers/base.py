"""Abstract base class for all language parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import Edge, Entity, Metrics


class LanguageParser(ABC):
    """Base class for tree-sitter-based language parsers.

    Each subclass handles one or more file extensions and extracts
    entities (functions, classes, etc.) and edges (calls, imports, etc.)
    from source code using tree-sitter ASTs.
    """

    @abstractmethod
    def language_name(self) -> str:
        """Return the language identifier (e.g., 'python', 'typescript')."""
        ...

    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this parser handles (e.g., ['.py'])."""
        ...

    @abstractmethod
    def parse_file(
        self,
        file_path: str,
        source: str,
        *,
        extract_symbols: bool = True,
    ) -> Tuple[List[Entity], List[Edge]]:
        """Parse source code and extract entities and edges.

        Args:
            file_path: Relative path to the file (used in entity IDs).
            source: The source code text.
            extract_symbols: Whether to extract detailed symbol info.

        Returns:
            Tuple of (entities, edges).
        """
        ...

    def get_tree(self, source: str) -> Optional[Any]:
        """Parse source into a tree-sitter Tree. Returns None on failure."""
        try:
            parser = self._get_parser()
            if parser is None:
                return None
            return parser.parse(source.encode("utf-8"))
        except Exception:
            return None

    def _get_parser(self) -> Optional[Any]:
        """Get or create the tree-sitter parser for this language.

        Lazy-initialized and cached on the class.
        """
        cache_attr = f"_ts_parser_{self.language_name()}"
        cached = getattr(self.__class__, cache_attr, None)
        if cached is not None:
            return cached

        try:
            import tree_sitter_language_pack as tslp
            parser = tslp.get_parser(self.language_name())
            setattr(self.__class__, cache_attr, parser)
            return parser
        except Exception:
            return None

    def _get_language(self) -> Optional[Any]:
        """Get the tree-sitter Language object for this language."""
        cache_attr = f"_ts_language_{self.language_name()}"
        cached = getattr(self.__class__, cache_attr, None)
        if cached is not None:
            return cached

        try:
            import tree_sitter_language_pack as tslp
            language = tslp.get_language(self.language_name())
            setattr(self.__class__, cache_attr, language)
            return language
        except Exception:
            return None

    # ---------------------------------------------------------------
    # Helper: Entity ID generation
    # ---------------------------------------------------------------

    @staticmethod
    def make_entity_id(entity_type: str, file_path: str, name: str) -> str:
        """Generate a unique entity ID.

        Format: TYPE::filepath::name
        Examples:
            FUNC::src/auth.py::login
            CLASS::src/models.py::User
            METHOD::src/models.py::User.save
        """
        return f"{entity_type.upper()}::{file_path}::{name}"

    @staticmethod
    def make_file_entity_id(file_path: str) -> str:
        """Generate entity ID for a file."""
        return f"FILE::{file_path}"

    # ---------------------------------------------------------------
    # Helper: Extract text from tree-sitter node
    # ---------------------------------------------------------------

    @staticmethod
    def node_text(node: Any, source_bytes: bytes) -> str:
        """Extract the text of a tree-sitter node."""
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def node_line(node: Any) -> int:
        """Get 1-based start line of a node."""
        return node.start_point[0] + 1

    @staticmethod
    def node_end_line(node: Any) -> int:
        """Get 1-based end line of a node."""
        return node.end_point[0] + 1

    # ---------------------------------------------------------------
    # Helper: Walk children of a given type
    # ---------------------------------------------------------------

    @staticmethod
    def find_children(node: Any, *types: str) -> List[Any]:
        """Find all direct children of the given type(s)."""
        return [c for c in node.children if c.type in types]

    @staticmethod
    def find_descendants(node: Any, *types: str) -> List[Any]:
        """Recursively find all descendants of the given type(s)."""
        results: List[Any] = []
        stack = list(node.children)
        while stack:
            child = stack.pop()
            if child.type in types:
                results.append(child)
            stack.extend(child.children)
        return results
