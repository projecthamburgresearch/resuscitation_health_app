"""Config-file parser for Blueprint X-Ray.

Extracts entities from configuration files (YAML, JSON, TOML, ENV, INI)
without using tree-sitter.  Each top-level key becomes a VARIABLE entity
(or CONSTANT for .env files), and nested structures are flattened into
dotted-path names (e.g. ``database.host``).
"""

from __future__ import annotations

import configparser
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Location,
    RelationType,
)
from src.xray.parsers.base import LanguageParser


class ConfigParser(LanguageParser):
    """Parser for configuration files (YAML, JSON, TOML, ENV, INI).

    This parser does **not** use tree-sitter.  Instead it relies on
    stdlib modules (``json``, ``tomllib``/``tomli``, ``configparser``)
    and PyYAML to extract entities from config files.
    """

    # ------------------------------------------------------------------
    # LanguageParser interface
    # ------------------------------------------------------------------

    def language_name(self) -> str:
        return "config"

    def file_extensions(self) -> List[str]:
        return [".json", ".yaml", ".yml", ".toml", ".env", ".ini"]

    # Override tree-sitter helpers to be explicit no-ops.
    def get_tree(self, source: str) -> Optional[Any]:  # type: ignore[override]
        """Config parser does not use tree-sitter."""
        return None

    def _get_parser(self) -> Optional[Any]:  # type: ignore[override]
        """Config parser does not use tree-sitter."""
        return None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def parse_file(
        self,
        file_path: str,
        source: str,
        *,
        extract_symbols: bool = True,
    ) -> Tuple[List[Entity], List[Edge]]:
        """Parse a config file and extract entities and edges."""
        entities: List[Entity] = []
        edges: List[Edge] = []

        # Determine total lines for the FILE entity.
        lines = source.splitlines()
        total_lines = len(lines) if lines else 1

        # Create FILE entity.
        file_entity = Entity(
            id=self.make_file_entity_id(file_path),
            type=EntityType.FILE,
            name=file_path.split("/")[-1].split("\\")[-1],
            qualified_name=file_path,
            location=Location(
                file=file_path,
                start_line=1,
                end_line=total_lines,
            ),
            language="config",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        # Dispatch to format-specific handler based on extension.
        p = Path(file_path)
        ext = p.suffix.lower()
        name = p.name.lower()
        try:
            if ext in (".yaml", ".yml"):
                self._parse_yaml(file_path, source, entities, edges)
            elif ext == ".json":
                self._parse_json(file_path, source, entities, edges)
            elif ext == ".toml":
                self._parse_toml(file_path, source, entities, edges)
            elif ext == ".env" or name.startswith(".env"):
                self._parse_env(file_path, source, entities, edges)
            elif ext == ".ini":
                self._parse_ini(file_path, source, entities, edges)
        except Exception:
            # If parsing fails we still return the FILE entity so the
            # file is represented in the graph.
            pass

        # Add CONTAINS edges from the file to every extracted entity.
        file_id = file_entity.id
        for ent in entities:
            if ent.type != EntityType.FILE:
                edges.append(Edge(
                    source=file_id,
                    target=ent.id,
                    relation=RelationType.CONTAINS,
                ))

        return entities, edges

    # ------------------------------------------------------------------
    # YAML
    # ------------------------------------------------------------------

    def _parse_yaml(
        self,
        file_path: str,
        source: str,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Parse YAML using PyYAML and extract entities."""
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(source)
        if not isinstance(data, dict):
            return
        self._extract_from_dict(data, file_path, entities, edges, prefix="")

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _parse_json(
        self,
        file_path: str,
        source: str,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Parse JSON using the stdlib ``json`` module."""
        data = json.loads(source)
        if not isinstance(data, dict):
            return
        self._extract_from_dict(data, file_path, entities, edges, prefix="")

    # ------------------------------------------------------------------
    # TOML
    # ------------------------------------------------------------------

    def _parse_toml(
        self,
        file_path: str,
        source: str,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Parse TOML using ``tomllib`` (3.11+) or ``tomli``."""
        if sys.version_info >= (3, 11):
            import tomllib  # type: ignore[import-not-found]
            data = tomllib.loads(source)
        else:
            try:
                import tomli  # type: ignore[import-untyped]
                data = tomli.loads(source)
            except ImportError:
                return

        if not isinstance(data, dict):
            return
        self._extract_from_dict(data, file_path, entities, edges, prefix="")

    # ------------------------------------------------------------------
    # ENV
    # ------------------------------------------------------------------

    _ENV_LINE_RE = re.compile(
        r"""
        ^\s*
        (?:export\s+)?          # optional 'export' prefix
        ([A-Za-z_][A-Za-z0-9_]*)  # key
        \s*=\s*                 # equals sign
        (.*)                    # value (may be quoted)
        $
        """,
        re.VERBOSE,
    )

    def _parse_env(
        self,
        file_path: str,
        source: str,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Parse a ``.env`` file (``KEY=VALUE`` lines).

        Each key is emitted as a CONSTANT entity.
        """
        for lineno, raw_line in enumerate(source.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = self._ENV_LINE_RE.match(line)
            if not match:
                continue

            key = match.group(1)
            value = match.group(2).strip()
            # Strip surrounding quotes from value.
            if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
                value = value[1:-1]

            entity_id = self.make_entity_id("CONST", file_path, key)
            entities.append(Entity(
                id=entity_id,
                type=EntityType.CONSTANT,
                name=key,
                qualified_name=key,
                location=Location(
                    file=file_path,
                    start_line=lineno,
                    end_line=lineno,
                ),
                language="config",
                meta={"value": value},
            ))

    # ------------------------------------------------------------------
    # INI
    # ------------------------------------------------------------------

    def _parse_ini(
        self,
        file_path: str,
        source: str,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Parse an INI file using ``configparser``.

        Sections become VARIABLE entities; keys within sections are
        emitted as VARIABLE entities with dotted names
        (``section.key``).  Each key entity gets a CONTAINS edge from
        its parent section entity.
        """
        parser = configparser.ConfigParser()
        # Preserve key casing.
        parser.optionxform = str  # type: ignore[assignment]
        parser.read_string(source)

        for section in parser.sections():
            section_id = self.make_entity_id("VAR", file_path, section)
            entities.append(Entity(
                id=section_id,
                type=EntityType.VARIABLE,
                name=section,
                qualified_name=section,
                location=Location(
                    file=file_path,
                    start_line=1,
                    end_line=1,
                ),
                language="config",
            ))

            for key, value in parser.items(section):
                qualified = f"{section}.{key}"
                key_id = self.make_entity_id("VAR", file_path, qualified)
                entities.append(Entity(
                    id=key_id,
                    type=EntityType.VARIABLE,
                    name=key,
                    qualified_name=qualified,
                    location=Location(
                        file=file_path,
                        start_line=1,
                        end_line=1,
                    ),
                    language="config",
                    meta={"value": value},
                ))
                edges.append(Edge(
                    source=section_id,
                    target=key_id,
                    relation=RelationType.CONTAINS,
                ))

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _extract_from_dict(
        self,
        data: Dict[str, Any],
        file_path: str,
        entities: List[Entity],
        edges: List[Edge],
        prefix: str,
    ) -> None:
        """Recursively walk a parsed dict and emit VARIABLE entities.

        Nested dicts produce dotted-path qualified names
        (e.g. ``database.host``).  A parent key that itself contains
        nested children gets a CONTAINS edge to each child entity.
        """
        for key, value in data.items():
            qualified = f"{prefix}.{key}" if prefix else key
            entity_id = self.make_entity_id("VAR", file_path, qualified)

            # Determine the value to store in meta -- for scalars keep
            # the value directly; for containers just record the type.
            if isinstance(value, dict):
                meta_value: Any = f"<dict with {len(value)} keys>"
            elif isinstance(value, list):
                meta_value = f"<list with {len(value)} items>"
            else:
                meta_value = value

            entity = Entity(
                id=entity_id,
                type=EntityType.VARIABLE,
                name=key,
                qualified_name=qualified,
                location=Location(
                    file=file_path,
                    start_line=1,
                    end_line=1,
                ),
                language="config",
                meta={"value": meta_value},
            )
            entities.append(entity)

            # If there is a parent prefix, create a CONTAINS edge from
            # the parent entity to this entity.
            if prefix:
                parent_id = self.make_entity_id("VAR", file_path, prefix)
                edges.append(Edge(
                    source=parent_id,
                    target=entity_id,
                    relation=RelationType.CONTAINS,
                ))

            # Recurse into nested dicts.
            if isinstance(value, dict):
                self._extract_from_dict(
                    value, file_path, entities, edges, prefix=qualified,
                )


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(ConfigParser)
