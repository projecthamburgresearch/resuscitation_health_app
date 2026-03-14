"""Tree-sitter-based Go parser for Blueprint X-Ray.

Extracts functions, methods, structs, interfaces, type declarations,
imports, and call relationships from Go source files.
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


class GoParser(LanguageParser):
    """Parser for Go source files."""

    def language_name(self) -> str:
        return "go"

    def file_extensions(self) -> List[str]:
        return [".go"]

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
            language="go",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        defined_names: Dict[str, str] = {}

        # Extract package name
        pkg_name = ""
        for child in root.children:
            if child.type == "package_clause":
                for c in child.children:
                    if c.type == "package_identifier":
                        pkg_name = self.node_text(c, source_bytes)

        self._extract_entities(
            root, file_path, source, source_bytes,
            entities, edges, defined_names, pkg_name,
        )
        self._extract_calls(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )
        self._extract_imports(
            root, file_path, source_bytes, entities, edges,
        )

        # CONTAINS edges
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
        pkg_name: str,
    ) -> None:
        for child in node.children:
            if child.type == "function_declaration":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "method_declaration":
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "type_declaration":
                self._extract_type_declaration(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )

    def _extract_function(
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
            if c.type == "identifier":
                name_node = c
                break
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("FUNC", file_path, func_name)

        params = self._get_params(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f" {return_type}" if return_type else ""
        signature = f"func {func_name}({params_str}){ret_str}"

        metrics = compute_entity_metrics(node, source, source_bytes, "go")
        metrics.parameter_count = len(params)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.FUNCTION,
            name=func_name,
            qualified_name=func_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="go",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
        ))
        defined_names[func_name] = entity_id

    def _extract_method(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        # Method: func (receiver) Name(params) return_type { ... }
        field_id_node = None
        for c in node.children:
            if c.type == "field_identifier":
                field_id_node = c
                break
        if not field_id_node:
            return

        method_name = self.node_text(field_id_node, source_bytes)

        # Get receiver type
        receiver_type = ""
        for c in node.children:
            if c.type == "parameter_list":
                # First parameter_list is the receiver
                for pc in c.children:
                    if pc.type == "parameter_declaration":
                        for tc in pc.children:
                            if tc.type in ("type_identifier", "pointer_type"):
                                receiver_type = self.node_text(tc, source_bytes).lstrip("*")
                break

        qualified = f"{receiver_type}.{method_name}" if receiver_type else method_name
        entity_id = self.make_entity_id("METHOD", file_path, qualified)

        params = self._get_method_params(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f" {return_type}" if return_type else ""
        recv_str = f"({receiver_type}) " if receiver_type else ""
        signature = f"func {recv_str}{method_name}({params_str}){ret_str}"

        metrics = compute_entity_metrics(node, source, source_bytes, "go")
        metrics.parameter_count = len(params)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.METHOD,
            name=method_name,
            qualified_name=qualified,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="go",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
        ))
        defined_names[method_name] = entity_id
        if receiver_type:
            defined_names[qualified] = entity_id

    def _extract_type_declaration(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        for child in node.children:
            if child.type != "type_spec":
                continue
            name_node = None
            type_node = None
            for c in child.children:
                if c.type == "type_identifier":
                    name_node = c
                elif c.type in ("struct_type", "interface_type"):
                    type_node = c

            if not name_node:
                continue

            type_name = self.node_text(name_node, source_bytes)

            if type_node and type_node.type == "struct_type":
                entity_type = EntityType.STRUCT
                prefix = "STRUCT"
                signature = f"type {type_name} struct"
            elif type_node and type_node.type == "interface_type":
                entity_type = EntityType.INTERFACE
                prefix = "INTERFACE"
                signature = f"type {type_name} interface"
            else:
                entity_type = EntityType.TYPE_ALIAS
                prefix = "TYPE"
                signature = f"type {type_name}"

            entity_id = self.make_entity_id(prefix, file_path, type_name)
            metrics = compute_entity_metrics(child, source, source_bytes, "go")

            entities.append(Entity(
                id=entity_id,
                type=entity_type,
                name=type_name,
                qualified_name=type_name,
                location=Location(
                    file=file_path,
                    start_line=self.node_line(child),
                    start_col=child.start_point[1],
                    end_line=self.node_end_line(child),
                    end_col=child.end_point[1],
                ),
                language="go",
                signature=signature,
                metrics=metrics,
            ))
            defined_names[type_name] = entity_id

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
        import_nodes = self.find_descendants(root, "import_spec")

        for imp_node in import_nodes:
            imp_text = self.node_text(imp_node, source_bytes).strip().strip('"')
            if not imp_text:
                continue
            line = self.node_line(imp_node)
            imp_id = self.make_entity_id("IMPORT", file_path, imp_text)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=imp_text.split("/")[-1],
                qualified_name=imp_text,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(imp_node),
                ),
                language="go",
                signature=f'import "{imp_text}"',
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    def _get_params(self, func_node: Any, source_bytes: bytes) -> List[str]:
        for c in func_node.children:
            if c.type == "parameter_list":
                params = []
                for pc in c.children:
                    if pc.type == "parameter_declaration":
                        params.append(self.node_text(pc, source_bytes))
                return params
        return []

    def _get_method_params(self, method_node: Any, source_bytes: bytes) -> List[str]:
        # Skip first parameter_list (receiver), use second
        param_lists = [c for c in method_node.children if c.type == "parameter_list"]
        if len(param_lists) >= 2:
            params = []
            for pc in param_lists[1].children:
                if pc.type == "parameter_declaration":
                    params.append(self.node_text(pc, source_bytes))
            return params
        return []

    def _get_return_type(self, func_node: Any, source_bytes: bytes) -> Optional[str]:
        # Return type comes after parameter lists, before block
        found_params = False
        for c in func_node.children:
            if c.type == "parameter_list":
                found_params = True
            elif found_params and c.type not in ("block", "{", "}"):
                if c.type in ("type_identifier", "pointer_type", "qualified_type",
                              "slice_type", "map_type", "parameter_list"):
                    return self.node_text(c, source_bytes)
        return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(GoParser)
