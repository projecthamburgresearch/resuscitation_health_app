"""Tree-sitter-based Python parser for Blueprint X-Ray.

Extracts functions, classes, methods, variables, imports, decorators,
docstrings, call relationships, and per-entity metrics.
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


class PythonParser(LanguageParser):
    """Full Python parser using tree-sitter."""

    def language_name(self) -> str:
        return "python"

    def file_extensions(self) -> List[str]:
        return [".py", ".pyw"]

    def parse_file(
        self,
        file_path: str,
        source: str,
        *,
        extract_symbols: bool = True,
    ) -> Tuple[List[Entity], List[Edge]]:
        """Parse a Python file and extract entities and edges."""
        tree = self.get_tree(source)
        if tree is None:
            return [], []

        source_bytes = source.encode("utf-8")
        root = tree.root_node
        entities: List[Entity] = []
        edges: List[Edge] = []

        # Create FILE entity
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
            language="python",
        )
        entities.append(file_entity)

        if not extract_symbols:
            return entities, edges

        # Track defined names for call resolution
        defined_names: Dict[str, str] = {}  # simple_name -> entity_id

        # Pass 1: Extract all entities
        self._extract_top_level(
            root, file_path, source, source_bytes,
            entities, edges, defined_names,
            parent_class=None,
        )

        # Pass 2: Extract call edges
        self._extract_calls(
            root, file_path, source_bytes,
            entities, edges, defined_names,
        )

        # Pass 3: Extract imports
        self._extract_imports(
            root, file_path, source_bytes,
            entities, edges,
        )

        # Add CONTAINS edges (file -> top-level entities)
        for ent in entities:
            if ent.type != EntityType.FILE and ent.location:
                edges.append(Edge(
                    source=file_entity.id,
                    target=ent.id,
                    relation=RelationType.CONTAINS,
                ))

        return entities, edges

    # ------------------------------------------------------------------
    # Pass 1: Entity extraction
    # ------------------------------------------------------------------

    def _extract_top_level(
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
        """Recursively extract entities from the AST."""
        for child in node.children:
            if child.type == "function_definition":
                self._extract_function(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names, parent_class,
                )
            elif child.type == "class_definition":
                self._extract_class(
                    child, file_path, source, source_bytes,
                    entities, edges, defined_names,
                )
            elif child.type == "decorated_definition":
                # Decorated function or class
                inner = None
                for c in child.children:
                    if c.type in ("function_definition", "class_definition"):
                        inner = c
                        break
                if inner:
                    if inner.type == "function_definition":
                        decorators = self._get_decorators(child, source_bytes)
                        self._extract_function(
                            inner, file_path, source, source_bytes,
                            entities, edges, defined_names, parent_class,
                            decorators=decorators,
                        )
                    elif inner.type == "class_definition":
                        decorators = self._get_decorators(child, source_bytes)
                        self._extract_class(
                            inner, file_path, source, source_bytes,
                            entities, edges, defined_names,
                            decorators=decorators,
                        )
            elif child.type == "expression_statement":
                # Top-level variable assignments (wrapped in expression_statement)
                for expr_child in child.children:
                    if expr_child.type == "assignment":
                        self._extract_variable(
                            expr_child, file_path, source_bytes,
                            entities, defined_names, parent_class,
                        )
            elif child.type == "assignment":
                # Top-level variable assignments (direct assignment node)
                self._extract_variable(
                    child, file_path, source_bytes,
                    entities, defined_names, parent_class,
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
        decorators: Optional[List[str]] = None,
    ) -> None:
        """Extract a function or method entity."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = self.node_text(name_node, source_bytes)

        # Determine if it's a method
        if parent_class:
            entity_type = EntityType.METHOD
            qualified_name = f"{parent_class}.{func_name}"
            entity_id = self.make_entity_id("METHOD", file_path, qualified_name)
        else:
            entity_type = EntityType.FUNCTION
            qualified_name = func_name
            entity_id = self.make_entity_id("FUNC", file_path, func_name)

        # Parameters
        params = self._get_parameters(node, source_bytes)

        # Return type annotation
        return_type = self._get_return_type(node, source_bytes)

        # Signature
        params_str = ", ".join(params)
        ret_str = f" -> {return_type}" if return_type else ""
        signature = f"def {func_name}({params_str}){ret_str}"

        # Docstring
        docstring = self._get_docstring(node, source_bytes)

        # Metrics
        metrics = compute_entity_metrics(node, source, source_bytes, "python")
        metrics.parameter_count = len(params)

        entity = Entity(
            id=entity_id,
            type=entity_type,
            name=func_name,
            qualified_name=qualified_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="python",
            signature=signature,
            return_type=return_type,
            parameters=params,
            decorators=decorators,
            docstring=docstring,
            metrics=metrics,
        )
        entities.append(entity)
        defined_names[func_name] = entity_id
        if parent_class:
            defined_names[qualified_name] = entity_id

    def _extract_class(
        self,
        node: Any,
        file_path: str,
        source: str,
        source_bytes: bytes,
        entities: List[Entity],
        edges: List[Edge],
        defined_names: Dict[str, str],
        decorators: Optional[List[str]] = None,
    ) -> None:
        """Extract a class entity and its methods."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self.node_text(name_node, source_bytes)
        entity_id = self.make_entity_id("CLASS", file_path, class_name)

        # Base classes
        bases = self._get_base_classes(node, source_bytes)

        # Docstring
        docstring = self._get_docstring(node, source_bytes)

        # Metrics
        metrics = compute_entity_metrics(node, source, source_bytes, "python")

        # Signature
        bases_str = f"({', '.join(bases)})" if bases else ""
        signature = f"class {class_name}{bases_str}"

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
            language="python",
            signature=signature,
            decorators=decorators,
            docstring=docstring,
            metrics=metrics,
            meta={"bases": bases} if bases else {},
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
                evidence=[Evidence(
                    file=file_path,
                    start_line=self.node_line(node),
                    end_line=self.node_line(node),
                    snippet=signature,
                )],
            ))

        # Recurse into class body for methods
        body = node.child_by_field_name("body")
        if body:
            self._extract_top_level(
                body, file_path, source, source_bytes,
                entities, edges, defined_names,
                parent_class=class_name,
            )

    def _extract_variable(
        self,
        node: Any,
        file_path: str,
        source_bytes: bytes,
        entities: List[Entity],
        defined_names: Dict[str, str],
        parent_class: Optional[str],
    ) -> None:
        """Extract a variable/constant from an assignment."""
        # Get left side
        left = node.child_by_field_name("left")
        if not left or left.type != "identifier":
            return

        var_name = self.node_text(left, source_bytes)

        # Determine if constant (ALL_CAPS)
        is_constant = var_name.isupper() and "_" in var_name or (
            var_name.isupper() and len(var_name) > 1
        )
        entity_type = EntityType.CONSTANT if is_constant else EntityType.VARIABLE

        if parent_class:
            qualified_name = f"{parent_class}.{var_name}"
        else:
            qualified_name = var_name

        entity_id = self.make_entity_id(
            "CONST" if is_constant else "VAR",
            file_path,
            qualified_name,
        )

        # Type annotation
        type_node = node.child_by_field_name("type")
        type_str = self.node_text(type_node, source_bytes) if type_node else None

        entity = Entity(
            id=entity_id,
            type=entity_type,
            name=var_name,
            qualified_name=qualified_name,
            location=Location(
                file=file_path,
                start_line=self.node_line(node),
                start_col=node.start_point[1],
                end_line=self.node_end_line(node),
                end_col=node.end_point[1],
            ),
            language="python",
            return_type=type_str,
        )
        entities.append(entity)
        defined_names[var_name] = entity_id

    # ------------------------------------------------------------------
    # Pass 2: Call extraction
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
        """Find all call_expression nodes and create CALLS edges."""
        # Build entity lookup by location
        entity_at_line: Dict[int, str] = {}
        for ent in entities:
            if ent.location and ent.type in (
                EntityType.FUNCTION, EntityType.METHOD,
            ):
                for ln in range(ent.location.start_line, ent.location.end_line + 1):
                    entity_at_line[ln] = ent.id

        # Find all call nodes
        call_nodes = self.find_descendants(root, "call")
        for call_node in call_nodes:
            func_node = call_node.child_by_field_name("function")
            if not func_node:
                continue

            call_name = self.node_text(func_node, source_bytes)
            call_line = self.node_line(call_node)

            # Resolve callee
            # Handle attribute calls: obj.method() -> just method name
            simple_name = call_name.split(".")[-1] if "." in call_name else call_name

            # Try to find a matching defined entity
            target_id = defined_names.get(call_name) or defined_names.get(simple_name)

            if not target_id:
                # Create an unresolved reference target
                target_id = self.make_entity_id("FUNC", file_path, simple_name)

            # Find the containing function/method (caller)
            caller_id = self._find_containing_entity(call_line, entity_at_line)
            if not caller_id:
                # Call at module level
                caller_id = self.make_file_entity_id(file_path)

            # Don't self-reference
            if caller_id == target_id:
                continue

            # Create CALLS edge
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

    def _find_containing_entity(
        self,
        line: int,
        entity_at_line: Dict[int, str],
    ) -> Optional[str]:
        """Find which function/method contains the given line."""
        return entity_at_line.get(line)

    # ------------------------------------------------------------------
    # Pass 3: Import extraction
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

        import_nodes = self.find_descendants(
            root, "import_statement", "import_from_statement",
        )

        for imp_node in import_nodes:
            imp_text = self.node_text(imp_node, source_bytes).strip()
            line = self.node_line(imp_node)

            # Extract module name
            if imp_node.type == "import_statement":
                # import foo, import foo.bar
                module_names = []
                for child in imp_node.children:
                    if child.type in ("dotted_name", "aliased_import"):
                        module_names.append(self.node_text(child, source_bytes))
                for mod in module_names:
                    clean_name = mod.split(" as ")[0].strip() if " as " in mod else mod
                    imp_id = self.make_entity_id("IMPORT", file_path, clean_name)
                    entities.append(Entity(
                        id=imp_id,
                        type=EntityType.IMPORT,
                        name=clean_name,
                        qualified_name=clean_name,
                        location=Location(
                            file=file_path,
                            start_line=line,
                            end_line=self.node_end_line(imp_node),
                        ),
                        language="python",
                        signature=imp_text,
                    ))
                    edges.append(Edge(
                        source=file_id,
                        target=imp_id,
                        relation=RelationType.IMPORTS,
                    ))
            elif imp_node.type == "import_from_statement":
                # from foo import bar, baz
                module_node = imp_node.child_by_field_name("module_name")
                module_name = self.node_text(module_node, source_bytes) if module_node else ""

                # Get imported names
                imported = []
                for child in imp_node.children:
                    if child.type in ("dotted_name", "aliased_import") and child != module_node:
                        imported.append(self.node_text(child, source_bytes))
                    elif child.type == "import_prefix":
                        continue

                if not imported:
                    # Might be wildcard: from foo import *
                    for child in imp_node.children:
                        if child.type == "wildcard_import":
                            imported.append("*")

                for name in imported:
                    clean_name = name.split(" as ")[0].strip() if " as " in name else name
                    full_name = f"{module_name}.{clean_name}" if module_name else clean_name
                    imp_id = self.make_entity_id("IMPORT", file_path, full_name)
                    entities.append(Entity(
                        id=imp_id,
                        type=EntityType.IMPORT,
                        name=clean_name,
                        qualified_name=full_name,
                        location=Location(
                            file=file_path,
                            start_line=line,
                            end_line=self.node_end_line(imp_node),
                        ),
                        language="python",
                        signature=imp_text,
                    ))
                    edges.append(Edge(
                        source=file_id,
                        target=imp_id,
                        relation=RelationType.IMPORTS,
                    ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_parameters(self, func_node: Any, source_bytes: bytes) -> List[str]:
        """Extract parameter list from a function definition."""
        params_node = func_node.child_by_field_name("parameters")
        if not params_node:
            return []

        params: List[str] = []
        for child in params_node.children:
            if child.type in ("identifier", "typed_parameter",
                              "default_parameter", "typed_default_parameter",
                              "list_splat_pattern", "dictionary_splat_pattern"):
                param_text = self.node_text(child, source_bytes)
                # Skip self/cls for methods
                if param_text.strip() in ("self", "cls"):
                    continue
                params.append(param_text)
        return params

    def _get_return_type(self, func_node: Any, source_bytes: bytes) -> Optional[str]:
        """Extract return type annotation from a function definition."""
        ret_node = func_node.child_by_field_name("return_type")
        if ret_node:
            return self.node_text(ret_node, source_bytes)
        return None

    def _get_docstring(self, node: Any, source_bytes: bytes) -> Optional[str]:
        """Extract docstring from a function or class body."""
        body = node.child_by_field_name("body")
        if not body or not body.children:
            return None

        first_stmt = body.children[0]

        # tree-sitter may represent the docstring as:
        # 1. expression_statement > string
        # 2. direct string node in the body
        doc_node = None
        if first_stmt.type == "expression_statement":
            expr = first_stmt.children[0] if first_stmt.children else None
            if expr and expr.type == "string":
                doc_node = expr
        elif first_stmt.type == "string":
            doc_node = first_stmt

        if doc_node:
            doc = self.node_text(doc_node, source_bytes)
            # Strip surrounding quotes
            for q in ('"""', "'''", '"', "'"):
                if doc.startswith(q) and doc.endswith(q):
                    doc = doc[len(q):-len(q)]
                    break
            return doc.strip()
        return None

    def _get_decorators(self, decorated_node: Any, source_bytes: bytes) -> List[str]:
        """Extract decorator names from a decorated_definition."""
        decorators: List[str] = []
        for child in decorated_node.children:
            if child.type == "decorator":
                dec_text = self.node_text(child, source_bytes)
                # Remove the @ prefix
                if dec_text.startswith("@"):
                    dec_text = dec_text[1:]
                decorators.append(dec_text.strip())
        return decorators

    def _get_base_classes(self, class_node: Any, source_bytes: bytes) -> List[str]:
        """Extract base classes from a class definition."""
        bases: List[str] = []
        superclasses = class_node.child_by_field_name("superclasses")
        if not superclasses:
            return bases

        for child in superclasses.children:
            if child.type in ("identifier", "attribute"):
                bases.append(self.node_text(child, source_bytes))
            elif child.type == "argument_list":
                for arg in child.children:
                    if arg.type in ("identifier", "attribute"):
                        bases.append(self.node_text(arg, source_bytes))
        return bases


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from src.xray.parsers import register_parser  # noqa: E402

register_parser(PythonParser)
