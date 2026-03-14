"""Regex-based HTML/CSS/XML parser for Blueprint X-Ray.

Handles .html, .htm, .css, .scss, .less, .xml, .svg, .xhtml files.
Uses regex-based extraction since tree-sitter is optional for these formats.
Extracts script/link imports, form endpoints, element IDs, CSS selectors,
CSS custom properties, @import rules, @media queries, and URL references.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    RelationType,
)
from src.xray.parsers.base import LanguageParser


# ---------------------------------------------------------------------------
# Regex patterns for HTML extraction
# ---------------------------------------------------------------------------

# <script src="...">
_RE_SCRIPT_SRC = re.compile(
    r"""<script\s[^>]*?\bsrc\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE | re.DOTALL,
)

# <link href="..."> (stylesheets, icons, etc.)
_RE_LINK_HREF = re.compile(
    r"""<link\s[^>]*?\bhref\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE | re.DOTALL,
)

# <a href="...">
_RE_A_HREF = re.compile(
    r"""<a\s[^>]*?\bhref\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE | re.DOTALL,
)

# <form action="..."> with optional method
_RE_FORM_ACTION = re.compile(
    r"""<form\s[^>]*?\baction\s*=\s*(?:"([^"]*?)"|'([^']*?)')"""
    r"""(?:\s[^>]*?\bmethod\s*=\s*(?:"([^"]*?)"|'([^']*?)'))?""",
    re.IGNORECASE | re.DOTALL,
)

# id="..."
_RE_ID_ATTR = re.compile(
    r"""\bid\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE,
)

# class="..."
_RE_CLASS_ATTR = re.compile(
    r"""\bclass\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Regex patterns for CSS extraction
# ---------------------------------------------------------------------------

# CSS @import url("...") or @import "..."
_RE_CSS_IMPORT = re.compile(
    r"""@import\s+(?:url\(\s*(?:"([^"]*?)"|'([^']*?)'|([^)]*?))\s*\)|"""
    r""""([^"]*?)"|'([^']*?)')""",
    re.IGNORECASE,
)

# CSS selectors: class (.name) and id (#name)
# Matches selectors at start of a rule block
_RE_CSS_SELECTOR_BLOCK = re.compile(
    r"""^([^{}@/][^{]*?)\{""",
    re.MULTILINE,
)

# Individual class selectors within a selector string
_RE_CSS_CLASS_SELECTOR = re.compile(r"""\.([\w-]+)""")

# Individual id selectors within a selector string
_RE_CSS_ID_SELECTOR = re.compile(r"""#([\w-]+)""")

# CSS custom properties (--var-name)
_RE_CSS_CUSTOM_PROP = re.compile(r"""--([\w-]+)\s*:""")

# @media queries
_RE_CSS_MEDIA = re.compile(
    r"""@media\s+([^{]+)""",
    re.IGNORECASE,
)

# url(...) references in CSS
_RE_CSS_URL = re.compile(
    r"""url\(\s*(?:"([^"]*?)"|'([^']*?)'|([^)]*?))\s*\)""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Regex patterns for XML extraction
# ---------------------------------------------------------------------------

# Root element tag
_RE_XML_ROOT = re.compile(
    r"""<\?xml[^?]*\?>\s*(?:<!--.*?-->\s*)*<(\w[\w:.-]*)""",
    re.DOTALL,
)

# Fallback: first opening tag
_RE_XML_FIRST_TAG = re.compile(
    r"""<(\w[\w:.-]*)[\s>]""",
)

# Namespace declarations xmlns:prefix="uri" or xmlns="uri"
_RE_XML_NAMESPACE = re.compile(
    r"""\bxmlns(?::(\w+))?\s*=\s*(?:"([^"]*?)"|'([^']*?)')""",
)


def _pick(match_groups: tuple) -> str:
    """Return the first non-None group from a regex match."""
    for g in match_groups:
        if g is not None:
            return g
    return ""


def _line_number(source: str, pos: int) -> int:
    """Return 1-based line number for the given character position."""
    return source.count("\n", 0, pos) + 1


class WebParser(LanguageParser):
    """Regex-based parser for HTML, CSS, and XML files.

    Since tree-sitter grammars for web formats are optional, this parser
    relies entirely on regular expressions to extract structural entities
    from HTML, CSS (including SCSS/LESS), XML, SVG, and XHTML files.
    """

    def language_name(self) -> str:
        return "html"

    def file_extensions(self) -> List[str]:
        return [".html", ".htm", ".css", ".scss", ".less", ".xml", ".svg", ".xhtml"]

    # ------------------------------------------------------------------
    # Override tree-sitter methods: not used for web formats
    # ------------------------------------------------------------------

    def get_tree(self, source: str) -> Optional[Any]:
        """No tree-sitter for web formats."""
        return None

    def _get_parser(self) -> Optional[Any]:
        """No tree-sitter parser for web formats."""
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
        """Parse a web file and extract entities and edges."""
        entities: List[Entity] = []
        edges: List[Edge] = []

        total_lines = source.count("\n") + 1

        # Determine file sub-type based on extension
        ext = PurePosixPath(file_path).suffix.lower()

        # Build the language label for entities
        if ext in (".css", ".scss", ".less"):
            lang = "css"
        elif ext in (".xml",):
            lang = "xml"
        elif ext in (".svg",):
            lang = "svg"
        else:
            lang = "html"

        # Create FILE entity
        file_entity = Entity(
            id=self.make_file_entity_id(file_path),
            type=EntityType.FILE,
            name=file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1],
            qualified_name=file_path,
            location=Location(
                file=file_path,
                start_line=1,
                end_line=total_lines,
            ),
            language=lang,
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        # Dispatch to the appropriate sub-parser
        if ext in (".html", ".htm", ".xhtml", ".svg"):
            self._parse_html(file_path, source, lang, entities, edges, file_entity)
        elif ext in (".css", ".scss", ".less"):
            self._parse_css(file_path, source, lang, entities, edges, file_entity)
        elif ext == ".xml":
            self._parse_xml(file_path, source, lang, entities, edges, file_entity)

        return entities, edges

    # ------------------------------------------------------------------
    # HTML / HTM / XHTML / SVG parsing
    # ------------------------------------------------------------------

    def _parse_html(
        self,
        file_path: str,
        source: str,
        lang: str,
        entities: List[Entity],
        edges: List[Edge],
        file_entity: Entity,
    ) -> None:
        """Extract entities from HTML-like files."""
        file_id = file_entity.id

        # --- <script src="..."> as IMPORT entities ---
        for m in _RE_SCRIPT_SRC.finditer(source):
            src = _pick(m.groups())
            if not src:
                continue
            line = _line_number(source, m.start())
            imp_id = self.make_entity_id("IMPORT", file_path, src)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=src,
                qualified_name=src,
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                signature=f'<script src="{src}">',
                meta={"import_kind": "script"},
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
                evidence=[Evidence(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                    snippet=m.group(0)[:200],
                )],
            ))

        # --- <link href="..."> as IMPORT entities ---
        for m in _RE_LINK_HREF.finditer(source):
            href = _pick(m.groups())
            if not href:
                continue
            line = _line_number(source, m.start())
            imp_id = self.make_entity_id("IMPORT", file_path, href)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=href,
                qualified_name=href,
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                signature=f'<link href="{href}">',
                meta={"import_kind": "link"},
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
                evidence=[Evidence(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                    snippet=m.group(0)[:200],
                )],
            ))

        # --- <a href="..."> links stored in meta ---
        links: List[Dict[str, Any]] = []
        for m in _RE_A_HREF.finditer(source):
            href = _pick(m.groups())
            if not href:
                continue
            line = _line_number(source, m.start())
            links.append({"href": href, "line": line})

        if links:
            file_entity.meta["links"] = links

        # --- <form action="..."> as ENDPOINT entities ---
        for m in _RE_FORM_ACTION.finditer(source):
            action = m.group(1) or m.group(2) or ""
            method = (m.group(3) or m.group(4) or "GET").upper()
            if not action:
                continue
            line = _line_number(source, m.start())
            endpoint_id = self.make_entity_id("ENDPOINT", file_path, action)
            entities.append(Entity(
                id=endpoint_id,
                type=EntityType.ENDPOINT,
                name=action,
                qualified_name=action,
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                signature=f'{method} {action}',
                meta={"method": method, "source_tag": "form"},
            ))
            edges.append(Edge(
                source=file_id,
                target=endpoint_id,
                relation=RelationType.CONTAINS,
                evidence=[Evidence(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                    snippet=m.group(0)[:200],
                )],
            ))

        # --- Elements with id="..." as VARIABLE entities ---
        seen_ids: Set[str] = set()
        for m in _RE_ID_ATTR.finditer(source):
            elem_id = _pick(m.groups())
            if not elem_id or elem_id in seen_ids:
                continue
            seen_ids.add(elem_id)
            line = _line_number(source, m.start())
            var_id = self.make_entity_id("VAR", file_path, f"#{elem_id}")
            entities.append(Entity(
                id=var_id,
                type=EntityType.VARIABLE,
                name=f"#{elem_id}",
                qualified_name=f"#{elem_id}",
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                meta={"html_id": elem_id},
            ))
            edges.append(Edge(
                source=file_id,
                target=var_id,
                relation=RelationType.CONTAINS,
            ))

        # --- Elements with class="..." extracted to meta on file entity ---
        css_classes: Set[str] = set()
        for m in _RE_CLASS_ATTR.finditer(source):
            classes_str = _pick(m.groups())
            if classes_str:
                for cls_name in classes_str.split():
                    cls_name = cls_name.strip()
                    if cls_name:
                        css_classes.add(cls_name)

        if css_classes:
            file_entity.meta["css_classes"] = sorted(css_classes)

    # ------------------------------------------------------------------
    # CSS / SCSS / LESS parsing
    # ------------------------------------------------------------------

    def _parse_css(
        self,
        file_path: str,
        source: str,
        lang: str,
        entities: List[Entity],
        edges: List[Edge],
        file_entity: Entity,
    ) -> None:
        """Extract entities from CSS-like files."""
        file_id = file_entity.id

        # --- @import rules as IMPORT entities ---
        for m in _RE_CSS_IMPORT.finditer(source):
            import_path = _pick(m.groups())
            if not import_path:
                continue
            import_path = import_path.strip()
            line = _line_number(source, m.start())
            imp_id = self.make_entity_id("IMPORT", file_path, import_path)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=import_path,
                qualified_name=import_path,
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                signature=m.group(0).strip(),
                meta={"import_kind": "css_import"},
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
                evidence=[Evidence(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                    snippet=m.group(0).strip()[:200],
                )],
            ))

        # --- CSS selectors (class and id) as VARIABLE entities ---
        seen_selectors: Set[str] = set()
        for m in _RE_CSS_SELECTOR_BLOCK.finditer(source):
            selector_text = m.group(1).strip()
            line = _line_number(source, m.start())

            # Extract class selectors
            for cls_m in _RE_CSS_CLASS_SELECTOR.finditer(selector_text):
                cls_name = cls_m.group(1)
                selector_key = f".{cls_name}"
                if selector_key in seen_selectors:
                    continue
                seen_selectors.add(selector_key)
                var_id = self.make_entity_id("VAR", file_path, selector_key)
                entities.append(Entity(
                    id=var_id,
                    type=EntityType.VARIABLE,
                    name=selector_key,
                    qualified_name=selector_key,
                    location=Location(
                        file=file_path,
                        start_line=line,
                        end_line=line,
                    ),
                    language=lang,
                    meta={"selector_type": "class"},
                ))
                edges.append(Edge(
                    source=file_id,
                    target=var_id,
                    relation=RelationType.CONTAINS,
                ))

            # Extract id selectors
            for id_m in _RE_CSS_ID_SELECTOR.finditer(selector_text):
                id_name = id_m.group(1)
                selector_key = f"#{id_name}"
                if selector_key in seen_selectors:
                    continue
                seen_selectors.add(selector_key)
                var_id = self.make_entity_id("VAR", file_path, selector_key)
                entities.append(Entity(
                    id=var_id,
                    type=EntityType.VARIABLE,
                    name=selector_key,
                    qualified_name=selector_key,
                    location=Location(
                        file=file_path,
                        start_line=line,
                        end_line=line,
                    ),
                    language=lang,
                    meta={"selector_type": "id"},
                ))
                edges.append(Edge(
                    source=file_id,
                    target=var_id,
                    relation=RelationType.CONTAINS,
                ))

        # --- CSS custom properties (--var-name) as VARIABLE entities ---
        seen_custom_props: Set[str] = set()
        for m in _RE_CSS_CUSTOM_PROP.finditer(source):
            prop_name = m.group(1)
            if prop_name in seen_custom_props:
                continue
            seen_custom_props.add(prop_name)
            line = _line_number(source, m.start())
            var_id = self.make_entity_id("VAR", file_path, f"--{prop_name}")
            entities.append(Entity(
                id=var_id,
                type=EntityType.VARIABLE,
                name=f"--{prop_name}",
                qualified_name=f"--{prop_name}",
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=line,
                ),
                language=lang,
                meta={"css_custom_property": True},
            ))
            edges.append(Edge(
                source=file_id,
                target=var_id,
                relation=RelationType.CONTAINS,
            ))

        # --- @media queries noted in meta ---
        media_queries: List[Dict[str, Any]] = []
        for m in _RE_CSS_MEDIA.finditer(source):
            query = m.group(1).strip()
            line = _line_number(source, m.start())
            media_queries.append({"query": query, "line": line})

        if media_queries:
            file_entity.meta["media_queries"] = media_queries

        # --- url(...) references stored in meta ---
        url_refs: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()
        for m in _RE_CSS_URL.finditer(source):
            url = _pick(m.groups()).strip()
            if not url or url in seen_urls:
                continue
            # Skip data URIs
            if url.startswith("data:"):
                continue
            seen_urls.add(url)
            line = _line_number(source, m.start())
            url_refs.append({"url": url, "line": line})

        if url_refs:
            file_entity.meta["url_references"] = url_refs

    # ------------------------------------------------------------------
    # XML parsing
    # ------------------------------------------------------------------

    def _parse_xml(
        self,
        file_path: str,
        source: str,
        lang: str,
        entities: List[Entity],
        edges: List[Edge],
        file_entity: Entity,
    ) -> None:
        """Extract metadata from XML files."""
        # --- Root element tag ---
        root_tag: Optional[str] = None
        m = _RE_XML_ROOT.search(source)
        if m:
            root_tag = m.group(1)
        else:
            m = _RE_XML_FIRST_TAG.search(source)
            if m:
                root_tag = m.group(1)

        if root_tag:
            file_entity.meta["root_element"] = root_tag

        # --- Namespace declarations ---
        namespaces: Dict[str, str] = {}
        for m in _RE_XML_NAMESPACE.finditer(source):
            prefix = m.group(1) or ""  # empty string for default namespace
            uri = m.group(2) or m.group(3) or ""
            ns_key = prefix if prefix else "(default)"
            namespaces[ns_key] = uri

        if namespaces:
            file_entity.meta["namespaces"] = namespaces


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(WebParser)
