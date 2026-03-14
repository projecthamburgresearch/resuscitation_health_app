"""Tree-sitter-based C# parser for Blueprint X-Ray.

Extracts classes, interfaces, enums, structs, methods, properties,
imports, and call relationships from C# source files.
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


class CSharpParser(LanguageParser):
    """Parser for C# source files."""

    def language_name(self) -> str:
        return "csharp"

    def file_extensions(self) -> List[str]:
        return [".cs"]

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
            language="csharp",
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
                    entities, edges, defined_names,
                )
            elif child.type == "enum_declaration":
                self._extract_enum(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "struct_declaration":
                self._extract_struct(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "method_declaration":
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                )
            elif child.type == "constructor_declaration":
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                    is_constructor=True,
                )
            elif child.type == "namespace_declaration":
                # Recurse into namespace body
                body = child.child_by_field_name("body")
                if body:
                    self._extract_entities(
                        body, file_path, source, source_bytes,
                        entities, edges, defined_names, parent_class,
                    )
            elif child.type == "file_scoped_namespace_declaration":
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
        metrics = compute_entity_metrics(node, source, source_bytes, "c_sharp")

        # Base types
        bases = []
        for c in node.children:
            if c.type == "base_list":
                for bc in c.children:
                    if bc.type in ("identifier", "qualified_name", "generic_name"):
                        bases.append(self.node_text(bc, source_bytes))

        mod_str = self._get_modifiers_str(node, source_bytes)
        bases_str = f" : {', '.join(bases)}" if bases else ""
        signature = f"{mod_str}class {class_name}{bases_str}"

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
            language="csharp",
            signature=signature,
            metrics=metrics,
            meta={"bases": bases} if bases else {},
        ))
        defined_names[class_name] = entity_id

        for base in bases:
            edges.append(Edge(
                source=entity_id,
                target=self.make_entity_id("CLASS", file_path, base),
                relation=RelationType.INHERITS,
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
        edges: List[Edge],
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
            language="csharp",
            signature=f"interface {name}",
        ))
        defined_names[name] = entity_id

        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=name,
            )

    def _extract_struct(
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

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("STRUCT", file_path, name)

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
            language="csharp",
            signature=f"struct {name}",
        ))
        defined_names[name] = entity_id

        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=name,
            )

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
            language="csharp",
            signature=f"enum {name}",
        ))
        defined_names[name] = entity_id

    def _extract_method(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
        is_constructor: bool = False,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self.node_text(name_node, source_bytes)

        if parent_class:
            qualified = f"{parent_class}.{method_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
            entity_type = EntityType.METHOD
        else:
            qualified = method_name
            entity_id = self.make_entity_id("FUNC", file_path, method_name)
            entity_type = EntityType.FUNCTION

        params = self._get_params(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        mod_str = self._get_modifiers_str(node, source_bytes)
        ret_str = f"{return_type} " if return_type and not is_constructor else ""
        signature = f"{mod_str}{ret_str}{method_name}({params_str})"

        metrics = compute_entity_metrics(node, source, source_bytes, "c_sharp")
        metrics.parameter_count = len(params)

        entities.append(Entity(
            id=entity_id,
            type=entity_type,
            name=method_name,
            qualified_name=qualified,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="csharp",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
            meta={"constructor": True} if is_constructor else {},
        ))
        defined_names[method_name] = entity_id
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

        call_nodes = self.find_descendants(root, "invocation_expression")
        for call_node in call_nodes:
            # Get the function being called
            func_node = call_node.children[0] if call_node.children else None
            if not func_node:
                continue

            call_name = self.node_text(func_node, source_bytes)
            call_line = self.node_line(call_node)
            simple_name = call_name.split(".")[-1] if "." in call_name else call_name

            target_id = defined_names.get(call_name) or defined_names.get(simple_name)
            if not target_id:
                target_id = self.make_entity_id("METHOD", file_path, simple_name)

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
        using_nodes = self.find_descendants(root, "using_directive")

        for using_node in using_nodes:
            using_text = self.node_text(using_node, source_bytes).strip()
            namespace = using_text
            if namespace.startswith("using "):
                namespace = namespace[6:]
            namespace = namespace.rstrip(";").strip()
            line = self.node_line(using_node)

            imp_id = self.make_entity_id("IMPORT", file_path, namespace)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=namespace.split(".")[-1],
                qualified_name=namespace,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(using_node),
                ),
                language="csharp",
                signature=using_text,
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
            if c.type == "parameter":
                params.append(self.node_text(c, source_bytes))
        return params

    def _get_return_type(self, node: Any, source_bytes: bytes) -> Optional[str]:
        type_node = node.child_by_field_name("type")
        if type_node:
            return self.node_text(type_node, source_bytes)
        # For some nodes the return type is the 'returns' field
        ret_node = node.child_by_field_name("returns")
        if ret_node:
            return self.node_text(ret_node, source_bytes)
        return None

    def _get_modifiers_str(self, node: Any, source_bytes: bytes) -> str:
        modifiers = []
        for c in node.children:
            if c.type == "modifier":
                modifiers.append(self.node_text(c, source_bytes))
        return " ".join(modifiers) + " " if modifiers else ""


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(CSharpParser)
