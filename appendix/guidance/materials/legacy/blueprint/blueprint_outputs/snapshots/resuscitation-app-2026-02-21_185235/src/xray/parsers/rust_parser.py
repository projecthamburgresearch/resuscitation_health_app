"""Tree-sitter-based Rust parser for Blueprint X-Ray.

Extracts functions, methods, structs, traits, enums, impl blocks,
imports, and call relationships from Rust source files.
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


class RustParser(LanguageParser):
    """Parser for Rust source files."""

    def language_name(self) -> str:
        return "rust"

    def file_extensions(self) -> List[str]:
        return [".rs"]

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
            language="rust",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        defined_names: Dict[str, str] = {}

        self._extract_entities(
            root, file_path, source, source_bytes,
            entities, edges, defined_names, parent_impl=None,
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
        parent_impl: Optional[str],
    ) -> None:
        for child in node.children:
            if child.type == "function_item":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_impl,
                )
            elif child.type == "struct_item":
                self._extract_struct(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "enum_item":
                self._extract_enum(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "trait_item":
                self._extract_trait(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "impl_item":
                self._extract_impl(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "type_item":
                self._extract_type_alias(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )

    def _extract_function(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_impl: Optional[str],
    ) -> None:
        name_node = None
        for c in node.children:
            if c.type == "identifier":
                name_node = c
                break
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)

        if parent_impl:
            entity_type = EntityType.METHOD
            qualified = f"{parent_impl}::{func_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
        else:
            entity_type = EntityType.FUNCTION
            qualified = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)

        params = self._get_params(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f" -> {return_type}" if return_type else ""
        is_pub = any(c.type == "visibility_modifier" for c in node.children)
        pub_str = "pub " if is_pub else ""
        signature = f"{pub_str}fn {func_name}({params_str}){ret_str}"

        metrics = compute_entity_metrics(node, source, source_bytes, "rust")
        metrics.parameter_count = len(params)

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
            language="rust",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
            meta={"public": is_pub},
        ))
        defined_names[func_name] = entity_id
        if parent_impl:
            defined_names[qualified] = entity_id

    def _extract_struct(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = None
        for c in node.children:
            if c.type == "type_identifier":
                name_node = c
                break
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("STRUCT", file_path, name)
        metrics = compute_entity_metrics(node, source, source_bytes, "rust")

        entities.append(Entity(
            id=entity_id,
            type=EntityType.STRUCT,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="rust",
            signature=f"struct {name}",
            metrics=metrics,
        ))
        defined_names[name] = entity_id

    def _extract_enum(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = None
        for c in node.children:
            if c.type == "type_identifier":
                name_node = c
                break
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("ENUM", file_path, name)
        metrics = compute_entity_metrics(node, source, source_bytes, "rust")

        entities.append(Entity(
            id=entity_id,
            type=EntityType.ENUM,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="rust",
            signature=f"enum {name}",
            metrics=metrics,
        ))
        defined_names[name] = entity_id

    def _extract_trait(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = None
        for c in node.children:
            if c.type == "type_identifier":
                name_node = c
                break
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("TRAIT", file_path, name)
        metrics = compute_entity_metrics(node, source, source_bytes, "rust")

        entities.append(Entity(
            id=entity_id,
            type=EntityType.TRAIT,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="rust",
            signature=f"trait {name}",
            metrics=metrics,
        ))
        defined_names[name] = entity_id

    def _extract_impl(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        # impl [Trait for] Type { ... }
        type_names = [c for c in node.children if c.type == "type_identifier"]
        impl_type = ""
        trait_name = ""

        # Check for "for" keyword to distinguish impl Trait for Type vs impl Type
        has_for = any(c.type == "for" for c in node.children)
        if has_for and len(type_names) >= 2:
            trait_name = self.node_text(type_names[0], source_bytes)
            impl_type = self.node_text(type_names[1], source_bytes)
        elif type_names:
            impl_type = self.node_text(type_names[0], source_bytes)

        if trait_name and impl_type:
            # Create IMPLEMENTS edge
            type_id = self.make_entity_id("STRUCT", file_path, impl_type)
            trait_id = self.make_entity_id("TRAIT", file_path, trait_name)
            edges.append(Edge(
                source=type_id,
                target=trait_id,
                relation=RelationType.IMPLEMENTS,
            ))

        # Recurse into impl body for methods
        body = None
        for c in node.children:
            if c.type == "declaration_list":
                body = c
                break
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_impl=impl_type or None,
            )

    def _extract_type_alias(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = None
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
            language="rust",
            signature=f"type {name}",
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
            func_node = call_node.child_by_field_name("function")
            if not func_node:
                continue

            call_name = self.node_text(func_node, source_bytes)
            call_line = self.node_line(call_node)
            simple_name = call_name.split("::")[-1] if "::" in call_name else call_name
            simple_name = simple_name.split(".")[-1] if "." in simple_name else simple_name

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
        use_nodes = self.find_descendants(root, "use_declaration")

        for use_node in use_nodes:
            use_text = self.node_text(use_node, source_bytes).strip()
            # Remove 'use ' prefix and trailing ';'
            import_path = use_text
            if import_path.startswith("use "):
                import_path = import_path[4:]
            import_path = import_path.rstrip(";").strip()
            line = self.node_line(use_node)

            imp_id = self.make_entity_id("IMPORT", file_path, import_path)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=import_path.split("::")[-1],
                qualified_name=import_path,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(use_node),
                ),
                language="rust",
                signature=use_text,
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    def _get_params(self, func_node: Any, source_bytes: bytes) -> List[str]:
        for c in func_node.children:
            if c.type == "parameters":
                params = []
                for pc in c.children:
                    if pc.type == "parameter":
                        text = self.node_text(pc, source_bytes)
                        if text not in ("self", "&self", "&mut self"):
                            params.append(text)
                return params
        return []

    def _get_return_type(self, func_node: Any, source_bytes: bytes) -> Optional[str]:
        # Look for -> type pattern
        found_arrow = False
        for c in func_node.children:
            if c.type == "->":
                found_arrow = True
            elif found_arrow and c.type != "block":
                return self.node_text(c, source_bytes)
        return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(RustParser)
