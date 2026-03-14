"""Tree-sitter-based TypeScript/JavaScript parser for Blueprint X-Ray.

Handles .ts, .tsx, .js, .jsx files. Extracts functions, classes, methods,
interfaces, type aliases, imports, exports, arrow functions, and call edges.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import (
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    Metrics,
    RelationType,
)
from src.xray.metrics import compute_entity_metrics
from src.xray.parsers.base import LanguageParser


class TypeScriptParser(LanguageParser):
    """Parser for TypeScript and JavaScript files."""

    def language_name(self) -> str:
        return "typescript"

    def file_extensions(self) -> List[str]:
        return [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]

    def _get_ts_language_for_file(self, file_path: str) -> str:
        """Return the correct tree-sitter language based on extension."""
        if file_path.endswith((".tsx", ".jsx")):
            return "tsx"
        return "typescript"

    def parse_file(
        self,
        file_path: str,
        source: str,
        *,
        extract_symbols: bool = True,
    ) -> Tuple[List[Entity], List[Edge]]:
        """Parse a TypeScript/JavaScript file."""
        # Use the right language variant
        lang = self._get_ts_language_for_file(file_path)

        try:
            import tree_sitter_language_pack as tslp
            parser = tslp.get_parser(lang)
            tree = parser.parse(source.encode("utf-8"))
        except Exception:
            return [], []

        if tree is None:
            return [], []

        source_bytes = source.encode("utf-8")
        root = tree.root_node
        entities: List[Entity] = []
        edges: List[Edge] = []

        # File entity
        file_entity = Entity(
            id=self.make_file_entity_id(file_path),
            type=EntityType.FILE,
            name=file_path.split("/")[-1],
            qualified_name=file_path,
            location=Location(
                file=file_path,
                start_line=1,
                end_line=root.end_point[0] + 1,
            ),
            language="typescript",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        defined_names: Dict[str, str] = {}

        # Extract entities
        self._extract_entities(
            root, file_path, source, source_bytes,
            entities, edges, defined_names,
            parent_class=None,
        )

        # Extract calls
        self._extract_calls(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )

        # Extract JSX component usage (React components referenced via <Component />)
        self._extract_jsx_usage(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )

        # Extract imports
        self._extract_imports(
            root, file_path, source_bytes,
            entities, edges,
        )

        # Extract exports
        self._extract_exports(
            root, file_path, source_bytes,
            entities, edges,
        )

        # Add CONTAINS edges
        for ent in entities:
            if ent.type != EntityType.FILE and ent.location:
                edges.append(Edge(
                    source=file_entity.id,
                    target=ent.id,
                    relation=RelationType.CONTAINS,
                ))

        return entities, edges

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

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
        """Recursively extract entities from TS/JS AST."""
        for child in node.children:
            if child.type == "function_declaration":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )
            elif child.type == "class_declaration":
                self._extract_class(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "interface_declaration":
                self._extract_interface(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "type_alias_declaration":
                self._extract_type_alias(
                    child, file_path, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "enum_declaration":
                self._extract_enum(
                    child, file_path, source, source_bytes,
                    entities, defined_names,
                )
            elif child.type == "lexical_declaration":
                # const/let/var — might contain arrow functions
                self._extract_variable_declaration(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )
            elif child.type == "export_statement":
                # export default function ..., export class ..., export const ...
                self._extract_entities(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )
            elif child.type == "method_definition":
                # Inside class body
                self._extract_method(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )

    def _extract_function(
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
        """Extract a function declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)

        if parent_class:
            entity_type = EntityType.METHOD
            qualified = f"{parent_class}.{func_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified)
        else:
            entity_type = EntityType.FUNCTION
            qualified = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)

        params = self._get_parameters(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f": {return_type}" if return_type else ""
        signature = f"function {func_name}({params_str}){ret_str}"

        # Check for async
        is_async = any(
            c.type == "async" for c in node.children
        ) or self.node_text(node, source_bytes).lstrip().startswith("async")

        metrics = compute_entity_metrics(node, source, source_bytes, "typescript")
        metrics.parameter_count = len(params)

        entity = Entity(
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
            language="typescript",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
            meta={"async": is_async} if is_async else {},
        )
        entities.append(entity)
        defined_names[func_name] = entity_id

    def _extract_method(
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
        """Extract a method from a class body."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self.node_text(name_node, source_bytes)
        qualified = f"{parent_class}.{method_name}" if parent_class else method_name
        entity_id = self.make_entity_id("METHOD", file_path, qualified)

        params = self._get_parameters(node, source_bytes)
        return_type = self._get_return_type(node, source_bytes)
        params_str = ", ".join(params)
        ret_str = f": {return_type}" if return_type else ""
        signature = f"{method_name}({params_str}){ret_str}"

        metrics = compute_entity_metrics(node, source, source_bytes, "typescript")
        metrics.parameter_count = len(params)

        entity = Entity(
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
            language="typescript",
            signature=signature,
            return_type=return_type,
            parameters=params,
            metrics=metrics,
        )
        entities.append(entity)
        defined_names[method_name] = entity_id
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
        """Extract a class declaration and its members."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("CLASS", file_path, class_name)

        # Heritage (extends/implements)
        bases = []
        implements = []
        for child in node.children:
            if child.type == "class_heritage":
                heritage_text = self.node_text(child, source_bytes)
                if "extends" in heritage_text:
                    # Extract class name after extends
                    for hc in child.children:
                        if hc.type in ("identifier", "member_expression"):
                            bases.append(self.node_text(hc, source_bytes))
                if "implements" in heritage_text:
                    for hc in child.children:
                        if hc.type in ("identifier", "type_identifier"):
                            implements.append(self.node_text(hc, source_bytes))

        metrics = compute_entity_metrics(node, source, source_bytes, "typescript")
        bases_str = f" extends {', '.join(bases)}" if bases else ""
        impl_str = f" implements {', '.join(implements)}" if implements else ""
        signature = f"class {class_name}{bases_str}{impl_str}"

        entity = Entity(
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
            language="typescript",
            signature=signature,
            metrics=metrics,
            meta={"bases": bases, "implements": implements},
        )
        entities.append(entity)
        defined_names[class_name] = entity_id

        # Inheritance edges
        for base in bases:
            base_id = self.make_entity_id("CLASS", file_path, base)
            edges.append(Edge(
                source=entity_id,
                target=base_id,
                relation=RelationType.INHERITS,
            ))
        for iface in implements:
            iface_id = self.make_entity_id("INTERFACE", file_path, iface)
            edges.append(Edge(
                source=entity_id,
                target=iface_id,
                relation=RelationType.IMPLEMENTS,
            ))

        # Recurse into class body — track which entities are added
        entities_before = len(entities)
        body = node.child_by_field_name("body")
        if body:
            self._extract_entities(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=class_name,
            )

        # Add CONTAINS edges from class to its members
        for member in entities[entities_before:]:
            if member.type in (EntityType.METHOD, EntityType.FUNCTION):
                edges.append(Edge(
                    source=entity_id,
                    target=member.id,
                    relation=RelationType.CONTAINS,
                ))

    def _extract_interface(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        """Extract an interface declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("INTERFACE", file_path, name)

        metrics = compute_entity_metrics(node, source, source_bytes, "typescript")

        entity = Entity(
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
            language="typescript",
            signature=f"interface {name}",
            metrics=metrics,
        )
        entities.append(entity)
        defined_names[name] = entity_id

    def _extract_type_alias(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
    ) -> None:
        """Extract a type alias declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("TYPE", file_path, name)

        entity = Entity(
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
            language="typescript",
            signature=f"type {name}",
        )
        entities.append(entity)
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
        """Extract an enum declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("ENUM", file_path, name)

        entity = Entity(
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
            language="typescript",
            signature=f"enum {name}",
        )
        entities.append(entity)
        defined_names[name] = entity_id

    def _extract_variable_declaration(
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
        """Extract const/let/var declarations, especially arrow functions."""
        for child in node.children:
            if child.type != "variable_declarator":
                continue

            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if not name_node:
                continue

            var_name = self.node_text(name_node, source_bytes)

            # Check if this is an arrow function
            if value_node and value_node.type == "arrow_function":
                if parent_class:
                    entity_type = EntityType.METHOD
                    qualified = f"{parent_class}.{var_name}"
                    entity_id = self.make_entity_id("METHOD", file_path, qualified)
                else:
                    entity_type = EntityType.FUNCTION
                    qualified = var_name
                    entity_id = self.make_entity_id("FUNC", file_path, var_name)

                params = self._get_arrow_params(value_node, source_bytes)
                return_type = self._get_return_type(value_node, source_bytes)
                params_str = ", ".join(params)
                ret_str = f": {return_type}" if return_type else ""
                signature = f"const {var_name} = ({params_str}){ret_str} =>"

                metrics = compute_entity_metrics(
                    value_node, source, source_bytes, "typescript",
                )
                metrics.parameter_count = len(params)

                entity = Entity(
                    id=entity_id,
                    type=entity_type,
                    name=var_name,
                    qualified_name=qualified,
                    location=Location(
                        file=file_path,
                        start_line=self.node_line(node),
                        start_col=node.start_point[1],
                        end_line=self.node_end_line(value_node),
                        end_col=value_node.end_point[1],
                    ),
                    language="typescript",
                    signature=signature,
                    return_type=return_type,
                    parameters=params,
                    metrics=metrics,
                    meta={"arrow": True},
                )
                entities.append(entity)
                defined_names[var_name] = entity_id
            else:
                # Regular variable/constant
                is_const = any(
                    c.type in ("const",) for c in node.children
                ) or "const " in self.node_text(node, source_bytes)[:10]
                is_upper = var_name.isupper() and len(var_name) > 1

                if is_const and is_upper:
                    entity_type = EntityType.CONSTANT
                    prefix = "CONST"
                else:
                    entity_type = EntityType.VARIABLE
                    prefix = "VAR"

                entity_id = self.make_entity_id(prefix, file_path, var_name)
                entity = Entity(
                    id=entity_id,
                    type=entity_type,
                    name=var_name,
                    qualified_name=var_name,
                    location=Location(
                        file=file_path,
                        start_line=self.node_line(node),
                        start_col=node.start_point[1],
                        end_line=self.node_end_line(node),
                        end_col=node.end_point[1],
                    ),
                    language="typescript",
                )
                entities.append(entity)
                defined_names[var_name] = entity_id

    # ------------------------------------------------------------------
    # Call extraction
    # ------------------------------------------------------------------

    def _extract_calls(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        """Find call_expression nodes and create CALLS edges."""
        entity_at_line: Dict[int, str] = {}
        for ent in entities:
            if ent.location and ent.type in (
                EntityType.FUNCTION, EntityType.METHOD,
            ):
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

    # ------------------------------------------------------------------
    # JSX component usage extraction
    # ------------------------------------------------------------------

    def _extract_jsx_usage(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
    ) -> None:
        """Find JSX component usage and create CALLS edges.

        In React/JSX, <Component /> or <Component>...</Component> is
        semantically a call to that component function/class. Without
        detecting these, all React components appear to have zero callers,
        producing false dead-code findings.

        Handles:
        - <MainScreen />       (jsx_self_closing_element)
        - <View>...</View>     (jsx_element with jsx_opening_element)
        - <Animated.View />    (member expression components)
        """
        # Build entity_at_line for caller resolution (same as _extract_calls)
        entity_at_line: Dict[int, str] = {}
        for ent in entities:
            if ent.location and ent.type in (
                EntityType.FUNCTION, EntityType.METHOD,
            ):
                for ln in range(ent.location.start_line, ent.location.end_line + 1):
                    entity_at_line[ln] = ent.id

        # Track edges we've already created to avoid duplicates
        seen_edges: Set[Tuple[str, str]] = set()

        # Find all JSX self-closing elements: <Component />
        jsx_nodes = self.find_descendants(
            root,
            "jsx_self_closing_element",
            "jsx_opening_element",
        )

        for jsx_node in jsx_nodes:
            # The component name is the first identifier/member child
            tag_name = self._get_jsx_tag_name(jsx_node, source_bytes)
            if not tag_name:
                continue

            # Skip HTML/intrinsic elements (lowercase: div, span, etc.)
            # React components are PascalCase or member expressions (Animated.View)
            first_char = tag_name[0]
            if first_char.islower() and "." not in tag_name:
                continue

            jsx_line = self.node_line(jsx_node)

            # Resolve the component name to an entity ID
            simple_name = tag_name.split(".")[-1] if "." in tag_name else tag_name
            target_id = (
                defined_names.get(tag_name)
                or defined_names.get(simple_name)
            )
            if not target_id:
                target_id = self.make_entity_id("FUNC", file_path, simple_name)

            # Find the enclosing function/method that renders this JSX
            caller_id = entity_at_line.get(jsx_line)
            if not caller_id:
                caller_id = self.make_file_entity_id(file_path)

            # Skip self-references and duplicates
            if caller_id == target_id:
                continue
            edge_key = (caller_id, target_id)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            snippet = f"<{tag_name} />"
            edges.append(Edge(
                source=caller_id,
                target=target_id,
                relation=RelationType.CALLS,
                confidence=1.0 if target_id in {e.id for e in entities} else 0.6,
                evidence=[Evidence(
                    file=file_path,
                    start_line=jsx_line,
                    end_line=self.node_end_line(jsx_node),
                    snippet=snippet,
                )],
            ))

    def _get_jsx_tag_name(self, jsx_node: Any, source_bytes: bytes) -> Optional[str]:
        """Extract the component/tag name from a JSX element node.

        Handles:
        - Simple identifiers: <MainScreen /> → "MainScreen"
        - Member expressions: <Animated.View /> → "Animated.View"
        - Namespaced names: <my:Component /> → None (skip)
        """
        for child in jsx_node.children:
            if child.type == "identifier":
                return self.node_text(child, source_bytes)
            elif child.type == "member_expression":
                return self.node_text(child, source_bytes)
            elif child.type == "nested_identifier":
                return self.node_text(child, source_bytes)
        return None

    # ------------------------------------------------------------------
    # Import extraction
    # ------------------------------------------------------------------

    def _extract_imports(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Extract import statements."""
        file_id = self.make_file_entity_id(file_path)
        import_nodes = self.find_descendants(root, "import_statement")

        for imp_node in import_nodes:
            imp_text = self.node_text(imp_node, source_bytes).strip()
            line = self.node_line(imp_node)

            # Extract source module
            source_node = imp_node.child_by_field_name("source")
            module = ""
            if source_node:
                module = self.node_text(source_node, source_bytes).strip("'\"")

            imp_id = self.make_entity_id("IMPORT", file_path, module or imp_text[:50])
            entities.append(Entity(
                id=imp_id,
                type=EntityType.IMPORT,
                name=module or imp_text[:50],
                qualified_name=module,
                location=Location(
                    file=file_path,
                    start_line=line,
                    end_line=self.node_end_line(imp_node),
                ),
                language="typescript",
                signature=imp_text[:200],
            ))
            edges.append(Edge(
                source=file_id,
                target=imp_id,
                relation=RelationType.IMPORTS,
            ))

    # ------------------------------------------------------------------
    # Export extraction
    # ------------------------------------------------------------------

    def _extract_exports(
        self,
        root: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
    ) -> None:
        """Extract export statements."""
        file_id = self.make_file_entity_id(file_path)
        export_nodes = self.find_descendants(root, "export_statement")

        for exp_node in export_nodes:
            # Check for named exports
            for child in exp_node.children:
                if child.type == "export_clause":
                    for spec in child.children:
                        if spec.type == "export_specifier":
                            name_node = spec.child_by_field_name("name")
                            if name_node:
                                name = self.node_text(name_node, source_bytes)
                                exp_id = self.make_entity_id("EXPORT", file_path, name)
                                entities.append(Entity(
                                    id=exp_id,
                                    type=EntityType.EXPORT,
                                    name=name,
                                    qualified_name=name,
                                    location=Location(
                                        file=file_path,
                                        start_line=self.node_line(exp_node),
                                        end_line=self.node_end_line(exp_node),
                                    ),
                                    language="typescript",
                                ))
                                edges.append(Edge(
                                    source=file_id,
                                    target=exp_id,
                                    relation=RelationType.EXPORTS,
                                ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_parameters(self, func_node: Any, source_bytes: bytes) -> List[str]:
        """Extract parameter list from function/method."""
        params_node = func_node.child_by_field_name("parameters")
        if not params_node:
            return []

        params: List[str] = []
        for child in params_node.children:
            if child.type in (
                "required_parameter", "optional_parameter",
                "rest_parameter", "identifier",
            ):
                param_text = self.node_text(child, source_bytes)
                if param_text not in ("(", ")", ",", "this"):
                    params.append(param_text)
        return params

    def _get_arrow_params(self, arrow_node: Any, source_bytes: bytes) -> List[str]:
        """Extract parameters from an arrow function."""
        for child in arrow_node.children:
            if child.type == "formal_parameters":
                return self._get_params_from_formal(child, source_bytes)
            elif child.type == "identifier":
                # Single param without parens: x => ...
                return [self.node_text(child, source_bytes)]
        return []

    def _get_params_from_formal(self, node: Any, source_bytes: bytes) -> List[str]:
        """Extract params from formal_parameters node."""
        params: List[str] = []
        for child in node.children:
            if child.type in (
                "required_parameter", "optional_parameter",
                "rest_parameter", "identifier",
            ):
                param_text = self.node_text(child, source_bytes)
                if param_text not in ("(", ")", ","):
                    params.append(param_text)
        return params

    def _get_return_type(self, func_node: Any, source_bytes: bytes) -> Optional[str]:
        """Extract return type annotation."""
        ret_node = func_node.child_by_field_name("return_type")
        if ret_node:
            text = self.node_text(ret_node, source_bytes)
            # Remove leading colon
            return text.lstrip(": ").strip()
        return None


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(TypeScriptParser)
