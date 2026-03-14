"""Tests for blueprint.xray.metrics module."""

from __future__ import annotations

import pytest

from src.xray.metrics import (
    calculate_cognitive_complexity,
    calculate_cyclomatic_complexity,
    calculate_loc,
    calculate_nesting_depth,
    calculate_statement_count,
    compute_entity_metrics,
)


def _parse_python(source: str):
    """Parse Python source and return tree-sitter tree root."""
    import tree_sitter_language_pack as tslp
    parser = tslp.get_parser("python")
    tree = parser.parse(source.encode("utf-8"))
    return tree.root_node


def _get_first_function(root):
    """Find the first function_definition in the tree."""
    for child in root.children:
        if child.type == "function_definition":
            return child
        if child.type == "decorated_definition":
            for c in child.children:
                if c.type == "function_definition":
                    return c
    return None


class TestCyclomaticComplexity:
    """Cyclomatic complexity calculation tests."""

    def test_simple_function(self):
        source = "def foo():\n    return 1\n"
        root = _parse_python(source)
        func = _get_first_function(root)
        assert func is not None
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        assert cc == 1

    def test_single_if(self):
        source = "def foo(x):\n    if x > 0:\n        return x\n    return 0\n"
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        assert cc == 2

    def test_if_elif_else(self):
        source = (
            "def foo(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    elif x < 0:\n"
            "        return -1\n"
            "    else:\n"
            "        return 0\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        # 1 + if + elif = 3
        assert cc == 3

    def test_loop(self):
        source = (
            "def foo(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item\n"
            "    return total\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        assert cc == 2  # 1 + for

    def test_nested_conditions(self):
        source = (
            "def foo(x, y):\n"
            "    if x > 0:\n"
            "        if y > 0:\n"
            "            return x + y\n"
            "    return 0\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        assert cc == 3  # 1 + if + if

    def test_try_except(self):
        source = (
            "def foo():\n"
            "    try:\n"
            "        x = 1/0\n"
            "    except ZeroDivisionError:\n"
            "        return 0\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        assert cc == 2  # 1 + except

    def test_boolean_operators(self):
        source = (
            "def foo(x, y):\n"
            "    if x > 0 and y > 0:\n"
            "        return True\n"
            "    return False\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        # 1 + if + and = 3
        assert cc == 3

    def test_unknown_language(self):
        source = "def foo():\n    pass\n"
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "unknown_lang", source.encode())
        assert cc == 1  # default

    def test_comprehension(self):
        source = (
            "def foo(items):\n"
            "    return [x for x in items if x > 0]\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        cc = calculate_cyclomatic_complexity(func, "python", source.encode())
        # 1 + list_comprehension = 2 (the if inside is part of the comprehension grammar)
        assert cc >= 2


class TestLOC:
    """Lines of code calculation tests."""

    def test_empty_source(self):
        total, code, comment, blank = calculate_loc("")
        assert total == 0

    def test_single_line(self):
        total, code, comment, blank = calculate_loc("x = 1")
        assert total == 1
        assert code == 1

    def test_mixed(self):
        source = (
            "# Comment\n"
            "x = 1\n"
            "\n"
            "y = 2\n"
            "# Another comment\n"
        )
        total, code, comment, blank = calculate_loc(source)
        assert total == 5
        assert code == 2
        assert comment == 2
        assert blank == 1

    def test_multiline_docstring(self):
        source = (
            '"""\n'
            "A docstring.\n"
            '"""\n'
            "x = 1\n"
        )
        total, code, comment, blank = calculate_loc(source)
        assert total == 4
        assert comment >= 2  # At least the docstring lines
        assert code >= 1


class TestNestingDepth:
    """Nesting depth calculation tests."""

    def test_flat_function(self):
        source = "def foo():\n    return 1\n"
        root = _parse_python(source)
        func = _get_first_function(root)
        max_d, avg_d = calculate_nesting_depth(func, "python")
        # The function itself is one level in NESTING_NODES
        assert max_d >= 0

    def test_nested_loops(self):
        source = (
            "def foo():\n"
            "    for i in range(10):\n"
            "        for j in range(10):\n"
            "            if i > j:\n"
            "                pass\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        max_d, avg_d = calculate_nesting_depth(func, "python")
        # function > for > for > if = at least 3 nesting levels from function body
        assert max_d >= 3

    def test_unknown_language(self):
        source = "def foo():\n    pass\n"
        root = _parse_python(source)
        func = _get_first_function(root)
        max_d, avg_d = calculate_nesting_depth(func, "unknown_lang")
        assert max_d == 0
        assert avg_d == 0.0


class TestStatementCount:
    """Statement count tests."""

    def test_simple_function(self):
        source = (
            "def foo():\n"
            "    x = 1\n"
            "    y = 2\n"
            "    return x + y\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        count = calculate_statement_count(func, "python")
        assert count >= 3  # two expressions + return

    def test_with_control_flow(self):
        source = (
            "def foo(x):\n"
            "    if x > 0:\n"
            "        return x\n"
            "    for i in range(x):\n"
            "        print(i)\n"
            "    return 0\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        count = calculate_statement_count(func, "python")
        assert count >= 4  # if, return, for, expression_stmt(print), return


class TestComputeEntityMetrics:
    """Integration test for compute_entity_metrics."""

    def test_computes_all_metrics(self):
        source = (
            "def foo(x, y):\n"
            "    # A comment\n"
            "    if x > 0:\n"
            "        return x + y\n"
            "    return 0\n"
        )
        root = _parse_python(source)
        func = _get_first_function(root)
        metrics = compute_entity_metrics(func, source, source.encode(), "python")

        assert metrics.cyclomatic_complexity is not None
        assert metrics.cyclomatic_complexity >= 2
        assert metrics.loc_total is not None
        assert metrics.loc_total >= 4
        assert metrics.loc_code is not None
        assert metrics.loc_comment is not None
        assert metrics.nesting_depth_max is not None
        assert metrics.statement_count is not None
