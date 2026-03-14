"""Tree-sitter-based Ruby parser for Blueprint X-Ray.

Extracts classes, modules, methods, constants, and call
relationships from Ruby source files.
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


class RubyParser(LanguageParser):
    """Parser for Ruby source files."""

    def language_name(self) -> str:
        return "ruby"

    def file_extensions(self) -> List[str]:
        return [".rb", ".rake", ".gemspec"]

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
            language="ruby",
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
            if child.type == "class":
                self._extract_class(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "module":
                self._extract_module(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "method":
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                )
            elif child.type == "singleton_method":
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, defined_names, parent_class,
                    is_singleton=True,
                )
            elif child.type == "assignment":
                self._extract_constant(
                    child, file_path, source_bytes,
                    entities, defined_names,
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
        metrics = compute_entity_metrics(node, source, source_bytes, "ruby")

        # Superclass
        superclass = None
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            superclass = self.node_text(superclass_node, source_bytes)
            # Remove leading "< "
            if superclass.startswith("< "):
                superclass = superclass[2:].strip()
            elif superclass.startswith("<"):
                superclass = superclass[1:].strip()

        bases_str = f" < {superclass}" if superclass else ""
        signature = f"class {class_name}{bases_str}"

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
            language="ruby",
            signature=signature,
            metrics=metrics,
            meta={"superclass": superclass} if superclass else {},
        ))
        defined_names[class_name] = entity_id

        if superclass:
            edges.append(Edge(
                source=entity_id,
                target=self.make_entity_id("CLASS", file_path, superclass),
                relation=RelationType.INHERITS,
            ))

        # Recurse into class body
        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=class_name,
            )

    def _extract_module(
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

        mod_name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("MODULE", file_path, mod_name)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.MODULE,
            name=mod_name,
            qualified_name=mod_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="ruby",
            signature=f"module {mod_name}",
        ))
        defined_names[mod_name] = entity_id

        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=mod_name,
            )

    def _extract_method(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
        is_singleton: bool = False,
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
        params_str = ", ".join(params)
        prefix = "self." if is_singleton else ""
        signature = f"def {prefix}{method_name}({params_str})" if params else f"def {prefix}{method_name}"

        metrics = compute_entity_metrics(node, source, source_bytes, "ruby")
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
            language="ruby",
            signature=signature,
            parameters=params,
            metrics=metrics,
            meta={"singleton": True} if is_singleton else {},
        ))
        defined_names[method_name] = entity_id
        if parent_class:
            defined_names[qualified] = entity_id

    def _extract_constant(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        left = node.child_by_field_name("left")
        if not left or left.type != "constant":
            return

        const_name = self.node_text(left, source_bytes)
        entity_id = self.make_entity_id("CONST", file_path, const_name)

        entities.append(Entity(
            id=entity_id,
            type=EntityType.CONSTANT,
            name=const_name,
            qualified_name=const_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="ruby",
        ))
        defined_names[const_name] = entity_id

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

        call_nodes = self.find_descendants(root, "call", "method_call")
        for call_node in call_nodes:
            method_node = call_node.child_by_field_name("method")
            if not method_node:
                continue

            call_name = self.node_text(method_node, source_bytes)
            call_line = self.node_line(call_node)

            target_id = defined_names.get(call_name)
            if not target_id:
                target_id = self.make_entity_id("METHOD", file_path, call_name)

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
        # Ruby uses require/require_relative/load
        call_nodes = self.find_descendants(root, "call", "method_call")

        for call_node in call_nodes:
            method_node = call_node.child_by_field_name("method")
            if not method_node:
                continue

            method_name = self.node_text(method_node, source_bytes)
            if method_name not in ("require", "require_relative", "load"):
                continue

            args = call_node.child_by_field_name("arguments")
            if not args:
                continue

            for arg in args.children:
                if arg.type == "string":
                    import_path = self.node_text(arg, source_bytes).strip("'\"")
                    line = self.node_line(call_node)
                    imp_id = self.make_entity_id("IMPORT", file_path, import_path)
                    entities.append(Entity(
                        id=imp_id,
                        type=EntityType.IMPORT,
                        name=import_path,
                        qualified_name=import_path,
                        location=Location(
                            file=file_path, start_line=line,
                            end_line=self.node_end_line(call_node),
                        ),
                        language="ruby",
                        signature=f'{method_name} "{import_path}"',
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
            if c.type in ("identifier", "optional_parameter",
                          "splat_parameter", "keyword_parameter",
                          "hash_splat_parameter", "block_parameter"):
                params.append(self.node_text(c, source_bytes))
        return params


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(RubyParser)
