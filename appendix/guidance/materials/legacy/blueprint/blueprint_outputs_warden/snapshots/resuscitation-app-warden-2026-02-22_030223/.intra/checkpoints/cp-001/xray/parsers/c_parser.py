"""Tree-sitter-based C/C++ parser for Blueprint X-Ray.

Extracts functions, structs, enums, typedefs, classes (C++),
includes, and call relationships from C and C++ source files.
"""

from __future__ import annotations

from pathlib import Path
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


class CParser(LanguageParser):
    """Parser for C and C++ source files."""

    def language_name(self) -> str:
        return "c"

    def file_extensions(self) -> List[str]:
        return [".c", ".h"]

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
            language="c",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        defined_names: Dict[str, str] = {}

        self._extract_entities(
            root, file_path, source, source_bytes,
            entities, edges, defined_names,
        )
        self._extract_calls(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )
        self._extract_includes(root, file_path, source_bytes, entities, edges)

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
    ) -> None:
        for child in node.children:
            if child.type == "function_definition":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "declaration":
                self._extract_declaration(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "struct_specifier":
                self._extract_struct(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "enum_specifier":
                self._extract_enum(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "type_definition":
                self._extract_typedef(
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
    ) -> None:
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        # Navigate to the function declarator to get the name
        func_name = self._get_declarator_name(declarator, source_bytes)
        if not func_name:
            return

        entity_id = self.make_entity_id("FUNC", file_path, func_name)
        params = self._get_params(declarator, source_bytes)
        return_type = self._get_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f"{return_type} " if return_type else ""
        signature = f"{ret_str}{func_name}({params_str})"

        metrics = compute_entity_metrics(node, source, source_bytes, "c")
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
            language="c",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
        ))
        defined_names[func_name] = entity_id

    def _extract_declaration(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        # Check if this is a struct/enum declaration
        for child in node.children:
            if child.type == "struct_specifier":
                self._extract_struct(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "enum_specifier":
                self._extract_enum(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )

    def _extract_struct(
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
        entity_id = self.make_entity_id("STRUCT", file_path, name)
        metrics = compute_entity_metrics(node, source, source_bytes, "c")

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
            language="c",
            signature=f"struct {name}",
            metrics=metrics,
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
            language="c",
            signature=f"enum {name}",
        ))
        defined_names[name] = entity_id

    def _extract_typedef(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        # typedef <type> <name>;
        # Get the last identifier-like child as the name
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        name = self._get_declarator_name(declarator, source_bytes)
        if not name:
            name = self.node_text(declarator, source_bytes)

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
            language="c",
            signature=f"typedef {name}",
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
            simple_name = call_name.split(".")[-1] if "." in call_name else call_name
            simple_name = simple_name.split("->")[-1] if "->" in simple_name else simple_name

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

    def _extract_includes(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        file_id = self.make_file_entity_id(file_path)
        include_nodes = self.find_descendants(root, "preproc_include")

        for inc_node in include_nodes:
            path_node = inc_node.child_by_field_name("path")
            if not path_node:
                continue

            inc_path = self.node_text(path_node, source_bytes).strip('"<>')
            line = self.node_line(inc_node)

            imp_id = self.make_entity_id("IMPORT", file_path, inc_path)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=inc_path,
                qualified_name=inc_path,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(inc_node),
                ),
                language="c",
                signature=f'#include "{inc_path}"',
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    def _get_declarator_name(self, node: Any, source_bytes: bytes) -> Optional[str]:
        """Extract function/variable name from a declarator node."""
        if node.type == "identifier":
            return self.node_text(node, source_bytes)
        if node.type == "function_declarator":
            decl = node.child_by_field_name("declarator")
            if decl:
                return self._get_declarator_name(decl, source_bytes)
        if node.type == "pointer_declarator":
            decl = node.child_by_field_name("declarator")
            if decl:
                return self._get_declarator_name(decl, source_bytes)
        # Fallback: look for identifier child
        for c in node.children:
            if c.type == "identifier":
                return self.node_text(c, source_bytes)
        return None

    def _get_params(self, declarator: Any, source_bytes: bytes) -> List[str]:
        """Extract parameters from a function declarator."""
        # Find the function_declarator
        func_decl = declarator
        if func_decl.type != "function_declarator":
            for c in declarator.children:
                if c.type == "function_declarator":
                    func_decl = c
                    break
        if func_decl.type != "function_declarator":
            return []

        params_node = func_decl.child_by_field_name("parameters")
        if not params_node:
            return []

        params = []
        for c in params_node.children:
            if c.type == "parameter_declaration":
                params.append(self.node_text(c, source_bytes))
            elif c.type == "variadic_parameter":
                params.append("...")
        return params

    def _get_type(self, node: Any, source_bytes: bytes) -> Optional[str]:
        type_node = node.child_by_field_name("type")
        if type_node:
            return self.node_text(type_node, source_bytes)
        return None


class CppParser(LanguageParser):
    """Parser for C++ source files. Extends C parsing with classes."""

    def language_name(self) -> str:
        return "cpp"

    def file_extensions(self) -> List[str]:
        return [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h++", ".c++"]

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
            language="cpp",
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
        self._extract_includes(root, file_path, source_bytes, entities, edges)

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
            if child.type == "function_definition":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                )
            elif child.type == "class_specifier":
                self._extract_class(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "struct_specifier":
                self._extract_struct(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "enum_specifier":
                self._extract_enum(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "declaration":
                for dc in child.children:
                    if dc.type == "class_specifier":
                        self._extract_class(
                            dc, file_path, source, source_bytes,
                            entities, edges, defined_names,
                        )
                    elif dc.type == "struct_specifier":
                        self._extract_struct(
                            dc, file_path, source, source_bytes,
                            entities, defined_names,
                        )
                    elif dc.type == "enum_specifier":
                        self._extract_enum(
                            dc, file_path, source_bytes,
                            entities, defined_names,
                        )
            elif child.type == "namespace_definition":
                body = child.child_by_field_name("body")
                if body:
                    self._extract_entities(
                        body, file_path, source, source_bytes,
                        entities, edges, defined_names, parent_class,
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
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        func_name = self._get_declarator_name(declarator, source_bytes)
        if not func_name:
            return

        if parent_class:
            qualified = f"{parent_class}::{func_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
            entity_type = EntityType.METHOD
        else:
            qualified = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)
            entity_type = EntityType.FUNCTION

        return_type = self._get_type(node, source_bytes)
        signature = f"{return_type + ' ' if return_type else ''}{func_name}"

        metrics = compute_entity_metrics(node, source, source_bytes, "cpp")

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
            language="cpp",
            signature=signature,
            return_type=return_type,
            metrics=metrics,
        ))
        defined_names[func_name] = entity_id
        if parent_class:
            defined_names[qualified] = entity_id

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
        metrics = compute_entity_metrics(node, source, source_bytes, "cpp")

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
            language="cpp",
            signature=f"class {class_name}",
            metrics=metrics,
        ))
        defined_names[class_name] = entity_id

        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=class_name,
            )

    def _extract_struct(
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
            language="cpp",
            signature=f"struct {name}",
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
            language="cpp",
            signature=f"enum {name}",
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
            simple_name = simple_name.split("->")[-1] if "->" in simple_name else simple_name

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

    def _extract_includes(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        file_id = self.make_file_entity_id(file_path)
        include_nodes = self.find_descendants(root, "preproc_include")

        for inc_node in include_nodes:
            path_node = inc_node.child_by_field_name("path")
            if not path_node:
                continue

            inc_path = self.node_text(path_node, source_bytes).strip('"<>')
            line = self.node_line(inc_node)

            imp_id = self.make_entity_id("IMPORT", file_path, inc_path)
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=inc_path,
                qualified_name=inc_path,
                location=Location(
                    file=file_path, start_line=line,
                    end_line=self.node_end_line(inc_node),
                ),
                language="cpp",
                signature=f'#include "{inc_path}"',
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    def _get_declarator_name(self, node: Any, source_bytes: bytes) -> Optional[str]:
        if node.type == "identifier":
            return self.node_text(node, source_bytes)
        if node.type in ("function_declarator", "pointer_declarator",
                         "reference_declarator"):
            decl = node.child_by_field_name("declarator")
            if decl:
                return self._get_declarator_name(decl, source_bytes)
        if node.type == "qualified_identifier":
            name = node.child_by_field_name("name")
            if name:
                return self.node_text(name, source_bytes)
        for c in node.children:
            if c.type == "identifier":
                return self.node_text(c, source_bytes)
            if c.type == "field_identifier":
                return self.node_text(c, source_bytes)
        return None

    def _get_type(self, node: Any, source_bytes: bytes) -> Optional[str]:
        type_node = node.child_by_field_name("type")
        if type_node:
            return self.node_text(type_node, source_bytes)
        return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(CParser)
register_parser(CppParser)
