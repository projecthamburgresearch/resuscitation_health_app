"""Tree-sitter-based PHP parser for Blueprint X-Ray.

Extracts classes, interfaces, traits, functions, methods, constants,
imports, and call relationships from PHP source files.
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


class PHPParser(LanguageParser):
    """Parser for PHP source files."""

    def language_name(self) -> str:
        return "php"

    def file_extensions(self) -> List[str]:
        return [".php", ".phtml"]

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
            language="php",
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
                self._extract_class(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "interface_declaration":
                self._extract_interface(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "trait_declaration":
                self._extract_trait(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "function_definition":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                )
            elif child.type == "method_declaration":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                    is_method=True,
                )
            elif child.type == "enum_declaration":
                self._extract_enum(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "namespace_definition":
                # Recurse into namespace body
                body = child.child_by_field_name("body")
                if body:
                    self._extract_entities(
                        body, file_path, source, source_bytes,
                        entities, edges, defined_names, parent_class,
                    )
            elif child.type == "program":
                # PHP wraps in program node sometimes
                self._extract_entities(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )

    def _extract_class(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("CLASS", file_path, class_name)
        metrics = compute_entity_metrics(node, source, source_bytes, "php")

        # Base class and interfaces
        bases = []
        implements = []
        for c in node.children:
            if c.type == "base_clause":
                for bc in c.children:
                    if bc.type == "name":
                        bases.append(self.node_text(bc, source_bytes))
                    elif bc.type == "qualified_name":
                        bases.append(self.node_text(bc, source_bytes))
            elif c.type == "class_interface_clause":
                for ic in c.children:
                    if ic.type in ("name", "qualified_name"):
                        implements.append(self.node_text(ic, source_bytes))

        signature = f"class {class_name}"
        if bases:
            signature += f" extends {', '.join(bases)}"
        if implements:
            signature += f" implements {', '.join(implements)}"

        entities.append(Entity(
            id=entity_id,
            type=EntityType.CLASS,
            name=class_name,
            qualified_name=class_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="php",
            signature=signature,
            metrics=metrics,
        ))
        defined_names[class_name] = entity_id

        for base in bases:
            edges.append(Edge(
                source=entity_id,
                target=self.make_entity_id("CLASS", file_path, base),
                relation=RelationType.INHERITS,
            ))
        for iface in implements:
            edges.append(Edge(
                source=entity_id,
                target=self.make_entity_id("INTERFACE", file_path, iface),
                relation=RelationType.IMPLEMENTS,
            ))

        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=class_name,
            )

    def _extract_interface(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("INTERFACE", file_path, name)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.INTERFACE,
            name=name,
            qualified_name=name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="php",
            signature=f"interface {name}",
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
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("TRAIT", file_path, name)

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
            language="php",
            signature=f"trait {name}",
        ))
        defined_names[name] = entity_id

    def _extract_enum(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("ENUM", file_path, name)

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
            language="php",
            signature=f"enum {name}",
        ))
        defined_names[name] = entity_id

    def _extract_function(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
        is_method: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)

        if parent_class or is_method:
            qualified = f"{parent_class}.{func_name}" if parent_class else func_name
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
            entity_type = EntityType.METHOD
        else:
            qualified = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)
            entity_type = EntityType.FUNCTION

        params = self._get_params(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f": {return_type}" if return_type else ""
        signature = f"function {func_name}({params_str}){ret_str}"

        metrics = compute_entity_metrics(node, source, source_bytes, "php")
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
            language="php",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
        ))
        defined_names[func_name] = entity_id
        if parent_class:
            defined_names[qualified] = entity_id

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

        call_nodes = self.find_descendants(
            root, "function_call_expression", "member_call_expression",
            "scoped_call_expression",
        )
        for call_node in call_nodes:
            func_node = call_node.child_by_field_name("function")
            if not func_node:
                func_node = call_node.child_by_field_name("name")
            if not func_node:
                continue

            call_name = self.node_text(func_node, source_bytes)
            call_line = self.node_line(call_node)
            simple_name = call_name.split("\\")[-1] if "\\" in call_name else call_name
            simple_name = simple_name.split("->")[-1] if "->" in simple_name else simple_name
            simple_name = simple_name.split("::")[-1] if "::" in simple_name else simple_name

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

        # PHP use statements (namespace imports)
        use_nodes = self.find_descendants(root, "namespace_use_declaration")
        for use_node in use_nodes:
            use_text = self.node_text(use_node, source_bytes).strip()
            namespace = use_text
            if namespace.startswith("use "):
                namespace = namespace[4:]
            namespace = namespace.rstrip(";").strip()
            line = self.node_line(use_node)

            imp_id = self.make_entity_id("IMPORT", file_path, namespace)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=namespace.split("\\")[-1],
                qualified_name=namespace,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(use_node),
                ),
                language="php",
                signature=use_text,
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    def _get_params(self, node: Any, source_bytes: bytes) -> List[str]:
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return []
        params = []
        for c in params_node.children:
            if c.type in ("simple_parameter", "variadic_parameter",
                          "property_promotion_parameter"):
                params.append(self.node_text(c, source_bytes))
        return params

    def _get_return_type(self, node: Any, source_bytes: bytes) -> Optional[str]:
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            text = self.node_text(ret_node, source_bytes)
            return text.lstrip(": ").strip()
        return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(PHPParser)
