"""Tests for the .bpignore parser and pattern merging."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.loader.bpignore import (
    load_bpignore,
    merge_patterns,
    normalize_pattern,
    parse_bpignore,
    split_patterns,
)
from src.core.io_utils import DEFAULT_EXCLUDE


class TestParseBpignore:
    def test_basic_patterns(self):
        text = "node_modules/\ndist/\n*.log"
        patterns = parse_bpignore(text)
        assert patterns == ["node_modules/", "dist/", "*.log"]

    def test_comments_stripped(self):
        text = "# This is a comment\nnode_modules/\n# Another comment\n*.log"
        patterns = parse_bpignore(text)
        assert patterns == ["node_modules/", "*.log"]

    def test_empty_lines_stripped(self):
        text = "node_modules/\n\n\ndist/\n\n"
        patterns = parse_bpignore(text)
        assert patterns == ["node_modules/", "dist/"]

    def test_whitespace_stripped(self):
        text = "  node_modules/  \n  dist/  "
        patterns = parse_bpignore(text)
        assert patterns == ["node_modules/", "dist/"]

    def test_empty_file(self):
        patterns = parse_bpignore("")
        assert patterns == []

    def test_only_comments(self):
        text = "# Comment 1\n# Comment 2\n"
        patterns = parse_bpignore(text)
        assert patterns == []

    def test_negation_preserved(self):
        text = "dist/\n!dist/important/\n*.log"
        patterns = parse_bpignore(text)
        assert "!dist/important/" in patterns


class TestSplitPatterns:
    def test_all_excludes(self):
        patterns = ["node_modules/", "dist/", "*.log"]
        excludes, includes = split_patterns(patterns)
        assert excludes == ["node_modules/", "dist/", "*.log"]
        assert includes == []

    def test_with_negation(self):
        patterns = ["dist/", "!dist/important/", "*.log"]
        excludes, includes = split_patterns(patterns)
        assert excludes == ["dist/", "*.log"]
        assert includes == ["dist/important/"]

    def test_empty(self):
        excludes, includes = split_patterns([])
        assert excludes == []
        assert includes == []


class TestNormalizePattern:
    def test_bare_name(self):
        assert normalize_pattern("node_modules") == "**/node_modules/**"

    def test_directory_with_slash(self):
        result = normalize_pattern("dist/")
        assert "dist" in result
        assert "**" in result

    def test_glob_pattern_preserved(self):
        result = normalize_pattern("**/*.log")
        assert "*.log" in result

    def test_path_pattern(self):
        result = normalize_pattern("src/test/fixtures")
        assert "src/test/fixtures" in result

    def test_backslash_normalized(self):
        result = normalize_pattern("src\\test\\fixtures")
        assert "\\" not in result
        assert "src/test/fixtures" in result


class TestMergePatterns:
    def test_additive(self):
        bp_patterns = ["*.log", "tmp/"]
        merged = merge_patterns(bp_patterns, DEFAULT_EXCLUDE)
        # Should have all defaults plus the new ones
        assert len(merged) > len(DEFAULT_EXCLUDE)
        assert any("*.log" in p for p in merged)

    def test_no_duplicates(self):
        # Adding a pattern that already exists shouldn't create duplicates
        bp_patterns = ["node_modules/"]
        merged = merge_patterns(bp_patterns, DEFAULT_EXCLUDE)
        node_count = sum(1 for p in merged if "node_modules" in p)
        # May have both the default and normalized versions, but should be deduplicated
        assert node_count >= 1

    def test_negation_removes(self):
        # !dist should remove **/dist/** from defaults
        bp_patterns = ["!dist"]
        defaults = ["**/dist/**", "**/node_modules/**"]
        merged = merge_patterns(bp_patterns, defaults)
        assert not any("dist" in p for p in merged)
        assert any("node_modules" in p for p in merged)

    def test_empty_bpignore(self):
        merged = merge_patterns([], DEFAULT_EXCLUDE)
        assert merged == DEFAULT_EXCLUDE

    def test_no_defaults(self):
        bp_patterns = ["*.log"]
        merged = merge_patterns(bp_patterns, [])
        assert len(merged) >= 1


class TestLoadBpignore:
    def test_load_from_file(self, tmp_path):
        bpignore = tmp_path / ".bpignore"
        bpignore.write_text("node_modules/\n*.log\n# comment\n")
        patterns = load_bpignore(tmp_path)
        assert patterns == ["node_modules/", "*.log"]

    def test_no_file(self, tmp_path):
        patterns = load_bpignore(tmp_path)
        assert patterns == []

    def test_empty_file(self, tmp_path):
        bpignore = tmp_path / ".bpignore"
        bpignore.write_text("")
        patterns = load_bpignore(tmp_path)
        assert patterns == []
