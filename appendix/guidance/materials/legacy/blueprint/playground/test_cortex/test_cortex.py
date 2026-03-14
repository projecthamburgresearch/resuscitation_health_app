"""Tests for the Cortex domain (schema, formatters, injector, reader, engine)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.cortex.schema import CortexBlock
from src.cortex.formatters import get_formatter_for_file
from src.cortex.formatters.hash_fmt import HashFormatter
from src.cortex.formatters.slash_fmt import SlashFormatter
from src.cortex.injector import inject_cortex_blocks, InjectionResult
from src.cortex.reader import read_cortex_blocks
from src.core.models import (
    Entity,
    EntityType,
    Location,
    Metrics,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestCortexBlock:
    def test_create_block(self):
        block = CortexBlock(
            id="FUNC::app.py::main",
            entity_type="function",
            calls=["FUNC::app.py::helper"],
            complexity=5,
        )
        assert block.id == "FUNC::app.py::main"
        assert len(block.calls) == 1

    def test_to_comment_dict(self):
        block = CortexBlock(
            id="FUNC::a.py::foo",
            entity_type="function",
            complexity=3,
            loc=10,
        )
        d = block.to_comment_dict()
        assert d["id"] == "FUNC::a.py::foo"
        assert d["complexity"] == 3
        assert "created" in d
        assert "last_visited" in d

    def test_roundtrip(self):
        block = CortexBlock(
            id="FUNC::a.py::foo",
            entity_type="function",
            calls=["FUNC::a.py::bar"],
            complexity=5,
            tags=["important"],
        )
        d = block.to_comment_dict()
        restored = CortexBlock.from_comment_dict(d)
        assert restored.id == block.id
        assert restored.calls == block.calls
        assert restored.complexity == block.complexity
        assert restored.tags == block.tags

    def test_empty_fields_excluded(self):
        block = CortexBlock(
            id="FUNC::a.py::foo",
            entity_type="function",
        )
        d = block.to_comment_dict()
        assert "calls" not in d  # Empty list excluded
        assert "complexity" not in d  # None excluded


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------

class TestFormatters:
    def test_get_formatter_python(self):
        fmt = get_formatter_for_file("test.py")
        assert fmt is not None
        assert isinstance(fmt, HashFormatter)

    def test_get_formatter_typescript(self):
        fmt = get_formatter_for_file("test.ts")
        assert fmt is not None
        assert isinstance(fmt, SlashFormatter)

    def test_get_formatter_unknown(self):
        fmt = get_formatter_for_file("test.xyz")
        assert fmt is None

    def test_hash_format(self):
        fmt = HashFormatter()
        block = CortexBlock(
            id="FUNC::a.py::foo",
            entity_type="function",
            complexity=3,
        )
        comment = fmt.format_block(block)
        assert "# @blueprint:cortex" in comment
        assert "# @end:cortex" in comment
        assert '"complexity": 3' in comment

    def test_slash_format(self):
        fmt = SlashFormatter()
        block = CortexBlock(
            id="FUNC::a.ts::foo",
            entity_type="function",
        )
        comment = fmt.format_block(block)
        assert "// @blueprint:cortex" in comment
        assert "// @end:cortex" in comment

    def test_hash_roundtrip(self):
        fmt = HashFormatter()
        block = CortexBlock(
            id="FUNC::a.py::foo",
            entity_type="function",
            calls=["FUNC::a.py::bar"],
            complexity=5,
        )
        comment = fmt.format_block(block)
        blocks = fmt.extract_blocks_from_source(comment)
        assert len(blocks) == 1
        assert blocks[0].id == block.id
        assert blocks[0].calls == block.calls

    def test_slash_roundtrip(self):
        fmt = SlashFormatter()
        block = CortexBlock(
            id="FUNC::a.ts::greet",
            entity_type="function",
            complexity=2,
            tags=["api"],
        )
        comment = fmt.format_block(block)
        blocks = fmt.extract_blocks_from_source(comment)
        assert len(blocks) == 1
        assert blocks[0].complexity == 2
        assert blocks[0].tags == ["api"]


# ---------------------------------------------------------------------------
# Injector tests
# ---------------------------------------------------------------------------

class TestInjector:
    @pytest.fixture
    def sample_entities(self):
        return [
            Entity(
                id="FUNC::test.py::greet",
                type=EntityType.FUNCTION,
                name="greet",
                location=Location(file="test.py", start_line=3, end_line=5),
                language="python",
                metrics=Metrics(cyclomatic_complexity=1, loc_code=3),
            ),
            Entity(
                id="FUNC::test.py::main",
                type=EntityType.FUNCTION,
                name="main",
                location=Location(file="test.py", start_line=7, end_line=12),
                language="python",
                metrics=Metrics(cyclomatic_complexity=3, loc_code=6),
            ),
        ]

    def test_dry_run(self, sample_entities):
        source = (
            "# Module\n"
            "\n"
            "def greet(name):\n"
            "    return f'Hello {name}'\n"
            "\n"
            "\n"
            "def main():\n"
            "    print(greet('world'))\n"
        )
        result = inject_cortex_blocks(
            file_path="test.py",
            source=source,
            entities=sample_entities,
            calls_map={"FUNC::test.py::main": ["FUNC::test.py::greet"]},
            uses_map={},
            dry_run=True,
        )
        assert result.blocks_inserted >= 1
        assert result.new_source is not None

    def test_no_entities(self):
        result = inject_cortex_blocks(
            file_path="test.py",
            source="x = 1\n",
            entities=[],
            calls_map={},
            uses_map={},
        )
        assert result.blocks_inserted == 0
        assert not result.has_changes

    def test_unsupported_format(self):
        result = inject_cortex_blocks(
            file_path="test.xyz",
            source="something",
            entities=[
                Entity(
                    id="FUNC::test.xyz::foo",
                    type=EntityType.FUNCTION,
                    name="foo",
                    location=Location(file="test.xyz", start_line=1, end_line=1),
                ),
            ],
            calls_map={},
            uses_map={},
        )
        assert result.blocks_inserted == 0


# ---------------------------------------------------------------------------
# Reader tests
# ---------------------------------------------------------------------------

class TestReader:
    def test_read_python_blocks(self):
        source = (
            "# @blueprint:cortex\n"
            '# {\n'
            '#   "id": "FUNC::a.py::foo",\n'
            '#   "type": "function",\n'
            '#   "created": "2024-01-01T00:00:00",\n'
            '#   "last_visited": "2024-06-01T00:00:00",\n'
            '#   "complexity": 5\n'
            '# }\n'
            "# @end:cortex\n"
            "def foo():\n"
            "    pass\n"
        )
        blocks = read_cortex_blocks("a.py", source)
        assert len(blocks) == 1
        assert blocks[0].id == "FUNC::a.py::foo"
        assert blocks[0].complexity == 5

    def test_read_typescript_blocks(self):
        source = (
            "// @blueprint:cortex\n"
            '// {\n'
            '//   "id": "FUNC::a.ts::bar",\n'
            '//   "type": "function",\n'
            '//   "created": "2024-01-01T00:00:00",\n'
            '//   "last_visited": "2024-06-01T00:00:00"\n'
            '// }\n'
            "// @end:cortex\n"
            "function bar() {}\n"
        )
        blocks = read_cortex_blocks("a.ts", source)
        assert len(blocks) == 1
        assert blocks[0].id == "FUNC::a.ts::bar"

    def test_read_no_blocks(self):
        source = "def foo():\n    pass\n"
        blocks = read_cortex_blocks("a.py", source)
        assert len(blocks) == 0

    def test_read_multiple_blocks(self):
        fmt = HashFormatter()
        block1 = CortexBlock(id="A", entity_type="function")
        block2 = CortexBlock(id="B", entity_type="class")
        source = (
            fmt.format_block(block1) + "\n"
            "def foo():\n    pass\n\n"
            + fmt.format_block(block2) + "\n"
            "class Bar:\n    pass\n"
        )
        blocks = read_cortex_blocks("test.py", source)
        assert len(blocks) == 2
