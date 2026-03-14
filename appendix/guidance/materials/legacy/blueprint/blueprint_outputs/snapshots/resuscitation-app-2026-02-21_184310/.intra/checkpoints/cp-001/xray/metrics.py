"""Code metrics calculation using tree-sitter ASTs.

Computes cyclomatic complexity, cognitive complexity, LOC breakdown,
nesting depth, and statement count per entity.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import Metrics


# ---------------------------------------------------------------------------
# Decision node types per language (for cyclomatic complexity)
# ---------------------------------------------------------------------------

DECISION_NODES: Dict[str, Set[str]] = {
    "python": {
        "if_statement",
        "elif_clause",
        "for_statement",
        "while_statement",
        "except_clause",
        "with_statement",
        "assert_statement",
        "conditional_expression",      # ternary: x if cond else y
        "boolean_operator",            # and / or (each adds a path)
        "list_comprehension",          # implicit loop
        "set_comprehension",
        "dictionary_comprehension",
        "generator_expression",
    },
    "typescript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_case",                 # each case is a branch
        "catch_clause",
        "ternary_expression",
        "binary_expression",           # && || (filtered in code)
        "optional_chain_expression",   # ?. adds a path
    },
    "javascript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_case",
        "catch_clause",
        "ternary_expression",
        "binary_expression",
        "optional_chain_expression",
    },
    "go": {
        "if_statement",
        "for_statement",
        "expression_case",
        "type_case",
        "communication_case",
        "select_statement",
    },
    "rust": {
        "if_expression",
        "for_expression",
        "while_expression",
        "loop_expression",
        "match_arm",
        "binary_expression",
    },
    "java": {
        "if_statement",
        "for_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_block_statement_group",
        "ternary_expression",
    },
    "c_sharp": {
        "if_statement",
        "for_statement",
        "for_each_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_section",
        "conditional_expression",
    },
    "ruby": {
        "if",
        "elsif",
        "unless",
        "when",
        "while",
        "until",
        "for",
        "rescue",
        "conditional",
    },
    "php": {
        "if_statement",
        "elseif_clause",
        "for_statement",
        "foreach_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "case_statement",
        "match_condition_list",
    },
}

# Cognitive complexity increment nodes (nesting-sensitive)
COGNITIVE_INCREMENT: Dict[str, Set[str]] = {
    "python": {
        "if_statement",
        "elif_clause",
        "else_clause",
        "for_statement",
        "while_statement",
        "except_clause",
        "boolean_operator",
        "conditional_expression",
    },
    "typescript": {
        "if_statement",
        "else_clause",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_case",
        "ternary_expression",
    },
    "javascript": {
        "if_statement",
        "else_clause",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_case",
        "ternary_expression",
    },
}

# Nesting-depth increment nodes
NESTING_NODES: Dict[str, Set[str]] = {
    "python": {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
        "function_definition",
        "class_definition",
    },
    "typescript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "switch_statement",
        "arrow_function",
        "function_declaration",
        "class_declaration",
    },
    "javascript": {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "switch_statement",
        "arrow_function",
        "function_declaration",
        "class_declaration",
    },
}


# ---------------------------------------------------------------------------
# Cyclomatic Complexity
# ---------------------------------------------------------------------------

def calculate_cyclomatic_complexity(
    node: Any,
    language: str,
    source_bytes: bytes | None = None,
) -> int:
    """Calculate cyclomatic complexity from a tree-sitter AST node.

    M = 1 + number of decision points.

    Args:
        node: Tree-sitter node (typically a function/method body).
        language: Language identifier for node type lookup.
        source_bytes: Source code bytes (needed for operator checks).

    Returns:
        Cyclomatic complexity integer (minimum 1).
    """
    decision_types = DECISION_NODES.get(language, set())
    if not decision_types:
        return 1

    complexity = 1
    stack = [node]

    while stack:
        current = stack.pop()
        node_type = current.type

        if node_type in decision_types:
            # For binary_expression, only count && and || operators
            if node_type == "binary_expression" and source_bytes:
                op_node = current.child_by_field_name("operator")
                if op_node:
                    op_text = source_bytes[op_node.start_byte:op_node.end_byte].decode()
                    if op_text in ("&&", "||"):
                        complexity += 1
                # else: don't count arithmetic ops etc.
            elif node_type == "boolean_operator":
                # Python: `and` / `or` each add a path
                complexity += 1
            else:
                complexity += 1

        stack.extend(current.children)

    return complexity


# ---------------------------------------------------------------------------
# Cognitive Complexity
# ---------------------------------------------------------------------------

def calculate_cognitive_complexity(
    node: Any,
    language: str,
) -> int:
    """Calculate cognitive complexity (nesting-aware).

    Each structural increment adds 1. Nesting increases the increment
    for each nested level.

    Args:
        node: Tree-sitter node (function/method body).
        language: Language identifier.

    Returns:
        Cognitive complexity integer.
    """
    increment_types = COGNITIVE_INCREMENT.get(language)
    nesting_types = NESTING_NODES.get(language)
    if not increment_types or not nesting_types:
        return 0

    total = 0

    def _walk(n: Any, nesting: int) -> None:
        nonlocal total

        is_increment = n.type in increment_types
        is_nesting = n.type in nesting_types

        if is_increment:
            total += 1 + nesting

        child_nesting = nesting + (1 if is_nesting else 0)
        for child in n.children:
            _walk(child, child_nesting)

    for child in node.children:
        _walk(child, 0)

    return total


# ---------------------------------------------------------------------------
# LOC Breakdown
# ---------------------------------------------------------------------------

def calculate_loc(source: str) -> Tuple[int, int, int, int]:
    """Calculate lines of code breakdown.

    Returns:
        (total, code, comment, blank) line counts.
    """
    lines = source.splitlines()
    total = len(lines)
    blank = 0
    comment = 0
    in_multiline = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        # Multi-line string/comment detection (Python)
        if '"""' in stripped or "'''" in stripped:
            count = stripped.count('"""') + stripped.count("'''")
            if in_multiline:
                in_multiline = False
                comment += 1
                continue
            elif count == 1:
                in_multiline = True
                comment += 1
                continue
            elif count >= 2:
                # Opened and closed on same line
                comment += 1
                continue

        if in_multiline:
            comment += 1
            continue

        # Single-line comments
        if stripped.startswith("#") or stripped.startswith("//"):
            comment += 1
        elif stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                in_multiline = True
        elif stripped.startswith("*") or stripped.startswith("*/"):
            comment += 1
            if stripped.endswith("*/"):
                in_multiline = False

    code = total - blank - comment
    return total, max(0, code), comment, blank


# ---------------------------------------------------------------------------
# Nesting Depth
# ---------------------------------------------------------------------------

def calculate_nesting_depth(
    node: Any,
    language: str,
) -> Tuple[int, float]:
    """Calculate max and average nesting depth within a node.

    Args:
        node: Tree-sitter node (function body).
        language: Language identifier.

    Returns:
        (max_depth, avg_depth)
    """
    nesting_types = NESTING_NODES.get(language, set())
    if not nesting_types:
        return 0, 0.0

    max_depth = 0
    depths: List[int] = []

    def _walk(n: Any, depth: int) -> None:
        nonlocal max_depth

        if n.type in nesting_types:
            depth += 1
            max_depth = max(max_depth, depth)
            depths.append(depth)

        for child in n.children:
            _walk(child, depth)

    _walk(node, 0)

    avg = sum(depths) / len(depths) if depths else 0.0
    return max_depth, round(avg, 2)


# ---------------------------------------------------------------------------
# Statement Count
# ---------------------------------------------------------------------------

STATEMENT_TYPES: Dict[str, Set[str]] = {
    "python": {
        "expression_statement",
        "assignment",
        "augmented_assignment",
        "return_statement",
        "pass_statement",
        "break_statement",
        "continue_statement",
        "raise_statement",
        "assert_statement",
        "delete_statement",
        "global_statement",
        "nonlocal_statement",
        "import_statement",
        "import_from_statement",
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
    },
    "typescript": {
        "expression_statement",
        "variable_declaration",
        "lexical_declaration",
        "return_statement",
        "break_statement",
        "continue_statement",
        "throw_statement",
        "import_statement",
        "export_statement",
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "try_statement",
    },
    "javascript": {
        "expression_statement",
        "variable_declaration",
        "lexical_declaration",
        "return_statement",
        "break_statement",
        "continue_statement",
        "throw_statement",
        "import_statement",
        "export_statement",
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "try_statement",
    },
}


def calculate_statement_count(node: Any, language: str) -> int:
    """Count the number of statements in an AST subtree.

    Args:
        node: Tree-sitter node.
        language: Language identifier.

    Returns:
        Statement count.
    """
    stmt_types = STATEMENT_TYPES.get(language, set())
    if not stmt_types:
        return 0

    count = 0
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in stmt_types:
            count += 1
        stack.extend(current.children)
    return count


# ---------------------------------------------------------------------------
# Combined Metrics for a Node
# ---------------------------------------------------------------------------

def compute_entity_metrics(
    node: Any,
    source: str,
    source_bytes: bytes,
    language: str,
) -> Metrics:
    """Compute all metrics for an entity's AST node.

    Args:
        node: The tree-sitter node for the entity (function_definition, etc.).
        source: Full file source text.
        source_bytes: Full file source bytes.
        language: Language identifier.

    Returns:
        Filled-out Metrics instance.
    """
    # Extract entity source for LOC
    entity_source = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    loc_total, loc_code, loc_comment, loc_blank = calculate_loc(entity_source)

    cc = calculate_cyclomatic_complexity(node, language, source_bytes)
    cog = calculate_cognitive_complexity(node, language)
    max_nest, avg_nest = calculate_nesting_depth(node, language)
    stmts = calculate_statement_count(node, language)

    return Metrics(
        cyclomatic_complexity=cc,
        cognitive_complexity=cog,
        loc_total=loc_total,
        loc_code=loc_code,
        loc_comment=loc_comment,
        loc_blank=loc_blank,
        nesting_depth_max=max_nest,
        nesting_depth_avg=avg_nest,
        statement_count=stmts,
    )
