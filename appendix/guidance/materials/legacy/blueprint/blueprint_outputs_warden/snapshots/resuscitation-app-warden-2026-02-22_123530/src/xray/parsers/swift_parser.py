"""Tree-sitter-based Swift parser for Blueprint X-Ray.

Extracts classes, structs, enums, protocols, functions, methods,
imports, and call relationships from Swift source files.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    RelationType,
)
from src.xray.metrics import compute_entity_metrics
from src.xray.parsers.base import LanguageParser


class SwiftParser(LanguageParser):
    """Parser for Swift source files."""

    def language_name(self) -> str:
        return "swift"

    def file_extensions(self) -> List[str]:
        return [".swift"]

    def parse_file(
        self,
        file_path: str,
        source: str,
        *,
        extract_symbols: bool = True,
    ) -> Tuple[List[Entity], List[Edge]]:
        tree = self.get_tree(source)
        if tree is None:
            return [], []

        source_bytes = source.encode("utf-8")
        root = tree.root_node
        entities: List[Entity] = []
        edges: List[Edge] = []

        file_entity = Entity(
            id=self.make_file_entity_id(file_path),
            type=EntityType.FILE,
            name=file_path.split("/")[-1],
            qualified_name=file_path,
            location=Location(
                file=file_path, start_line=1,
                end_line=root.end_point[0] + 1,
            ),
            language="swift",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        defined_names: Dict[str, str] = {}

        self._extract_entities(
            root, file_path, source, source_bytes,
            entities, edges, defined_names, parent_class=None,
        )
        self._extract_calls(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )
        self._extract_imports(root, file_path, source_bytes, entities, edges)

        for ent in entities:
            if ent.type != EntityType.FILE and ent.location:
                edges.append(Edge(
                    source=file_entity.id,
                    target=ent.id,
                    relation=RelationType.CONTAINS,
                ))

        return entities, edges

    def _extract_entities(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
    ) -> None:
        for child in node.children:
            if child.type == "class_declaration":
                # Swift tree-sitter uses class_declaration for class/struct/enum/protocol
                # Distinguish by checking the keyword child node
                kind = self._get_swift_type_kind(child, source_bytes)
                if kind == "struct":
                    self._extract_type_decl(
                        child, file_path, source, source_bytes,
                        entities, edges, defined_names,
                        entity_type=EntityType.STRUCT, prefix="STRUCT",
                        keyword="struct",
                    )
                elif kind == "enum":
                    self._extract_type_decl(
                        child, file_path, source, source_bytes,
                        entities, edges, defined_names,
                        entity_type=EntityType.ENUM, prefix="ENUM",
                        keyword="enum",
                    )
                elif kind == "protocol":
                    self._extract_type_decl(
                        child, file_path, source, source_bytes,
                        entities, edges, defined_names,
                        entity_type=EntityType.INTERFACE, prefix="INTERFACE",
                        keyword="protocol",
                    )
                else:
                    self._extract_type_decl(
                        child, file_path, source, source_bytes,
                        entities, edges, defined_names,
                        entity_type=EntityType.CLASS, prefix="CLASS",
                        keyword="class",
                    )
            elif child.type == "protocol_declaration":
                self._extract_type_decl(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                    entity_type=EntityType.INTERFACE, prefix="INTERFACE",
                    keyword="protocol",
                )
            elif child.type == "function_declaration":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                )
            elif child.type == "typealias_declaration":
                self._extract_typealias(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )

    def _get_swift_type_kind(self, node: Any, source_bytes: bytes) -> str:
        """Determine the kind of a Swift class_declaration node.

        Swift's tree-sitter grammar uses class_declaration for class, struct,
        enum, and protocol. This checks the keyword child to distinguish them.
        """
        for c in node.children:
            if c.type in ("struct", "enum", "protocol", "class"):
                return c.type
        # Fallback: check first few chars of node text
        text = self.node_text(node, source_bytes).lstrip()
        for kw in ("struct ", "enum ", "protocol "):
            if text.startswith(kw):
                return kw.strip()
        return "class"

    def _extract_type_decl(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
        entity_type: EntityType,
        prefix: str,
        keyword: str,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            # Fallback: find first type_identifier child
            for c in node.children:
                if c.type == "type_identifier":
                    name_node = c
                    break
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id(prefix, file_path, name)
        metrics = compute_entity_metrics(node, source, source_bytes, "swift")

        entities.append(Entity(
            id=entity_id,
            type=entity_type,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="swift",
            signature=f"{keyword} {name}",
            metrics=metrics,
        ))
        defined_names[name] = entity_id

        # Recurse into body
        body = node.child_by_field_name("body")
        if not body:
            for c in node.children:
                if c.type == "class_body":
                    body = c
                    break
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=name,
            )

    def _extract_function(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type == "simple_identifier":
                    name_node = c
                    break
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)

        if parent_class:
            qualified = f"{parent_class}.{func_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
            entity_type = EntityType.METHOD
        else:
            qualified = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)
            entity_type = EntityType.FUNCTION

        metrics = compute_entity_metrics(node, source, source_bytes, "swift")
        signature = f"func {func_name}"

        entities.append(Entity(
            id=entity_id,
            type=entity_type,
            name=func_name,
            qualified_name=qualified,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="swift",
            signature=signature,
            metrics=metrics,
        ))
        defined_names[func_name] = entity_id
        if parent_class:
            defined_names[qualified] = entity_id

    def _extract_typealias(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type == "type_identifier":
                    name_node = c
                    break
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("TYPE", file_path, name)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.TYPE_ALIAS,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="swift",
            signature=f"typealias {name}",
        ))
        defined_names[name] = entity_id

    def _extract_calls(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        entity_at_line: Dict[int, str] = {}
        for ent in entities:
            if ent.location and ent.type in (EntityType.FUNCTION, EntityType.METHOD):
                for ln in range(ent.location.start_line, ent.location.end_line + 1):
                    entity_at_line[ln] = ent.id

        call_nodes = self.find_descendants(root, "call_expression")
        for call_node in call_nodes:
            # First child is usually the function name
            func_node = call_node.children[0] if call_node.children else None
            if not func_node:
                continue

            call_name = self.node_text(func_node, source_bytes)
            call_line = self.node_line(call_node)
            simple_name = call_name.split(".")[-1] if "." in call_name else call_name

            target_id = defined_names.get(call_name) or defined_names.get(simple_name)
            if not target_id:
                target_id = self.make_entity_id("FUNC", file_path, simple_name)

            caller_id = entity_at_line.get(call_line)
            if not caller_id:
                caller_id = self.make_file_entity_id(file_path)

            if caller_id == target_id:
                continue

            snippet = self.node_text(call_node, source_bytes)
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."

            edges.append(Edge(
                source=caller_id,
                target=target_id,
                relation=RelationType.CALLS,
                confidence=1.0 if target_id in {e.id for e in entities} else 0.6,
                evidence=[Evidence(
                    file=file_path,
                    start_line=call_line,
                    end_line=self.node_end_line(call_node),
                    snippet=snippet,
                )],
            ))

    def _extract_imports(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        file_id = self.make_file_entity_id(file_path)
        import_nodes = self.find_descendants(root, "import_declaration")

        for imp_node in import_nodes:
            imp_text = self.node_text(imp_node, source_bytes).strip()
            import_path = imp_text
            if import_path.startswith("import "):
                import_path = import_path[7:].strip()
            line = self.node_line(imp_node)

            imp_id = self.make_entity_id("IMPORT", file_path, import_path)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=import_path,
                qualified_name=import_path,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(imp_node),
                ),
                language="swift",
                signature=imp_text,
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(SwiftParser)
