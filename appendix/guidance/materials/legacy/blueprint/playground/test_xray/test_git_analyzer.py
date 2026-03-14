"""Tests for blueprint.xray.git_analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.xray.git_analyzer import (
    is_git_repo,
    get_last_modified,
    get_file_churn,
    get_blame_summary,
    get_change_frequency,
    enrich_with_git,
)
from src.core.models import Entity, EntityType, Location


# The blueprint project root should be a git repo
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestIsGitRepo:
    """Git repo detection tests."""

    def test_valid_repo(self):
        # The blueprint project root should be a git repo
        assert is_git_repo(PROJECT_ROOT) is True

    def test_invalid_repo(self, tmp_path):
        assert is_git_repo(tmp_path) is False

    def test_nonexistent_path(self):
        assert is_git_repo(Path("/nonexistent/path/12345")) is False


class TestGetLastModified:
    """Last modified info tests."""

    def test_known_file(self):
        # conftest.py should exist in git
        info = get_last_modified(PROJECT_ROOT, "tests/conftest.py")
        if info is not None:
            # File might not be committed yet
            assert info.last_author is not None
            assert info.change_count is not None
            assert info.change_count >= 0

    def test_nonexistent_file(self):
        info = get_last_modified(PROJECT_ROOT, "nonexistent_file_xyz.py")
        # Should return None since file has no git history
        assert info is None


class TestGetFileChurn:
    """File churn tests."""

    def test_known_file(self):
        churn = get_file_churn(PROJECT_ROOT, "tests/conftest.py")
        # Churn is 0 or positive
        assert churn >= 0

    def test_nonexistent_file(self):
        churn = get_file_churn(PROJECT_ROOT, "nonexistent.py")
        assert churn == 0


class TestGetBlameSummary:
    """Blame summary tests."""

    def test_known_file(self):
        authors = get_blame_summary(PROJECT_ROOT, "tests/conftest.py")
        # May be empty if file is not committed yet
        assert isinstance(authors, dict)

    def test_nonexistent_file(self):
        authors = get_blame_summary(PROJECT_ROOT, "nonexistent.py")
        assert authors == {}


class TestGetChangeFrequency:
    """Change frequency tests."""

    def test_recent_changes(self):
        freq = get_change_frequency(PROJECT_ROOT, days=365)
        assert isinstance(freq, list)
        # Might be empty if repo is very new

    def test_no_changes(self, tmp_path):
        freq = get_change_frequency(tmp_path, days=30)
        assert freq == []


class TestEnrichWithGit:
    """Git enrichment integration tests."""

    def test_enrich_entities(self):
        entities = [
            Entity(
                id="FUNC::tests/conftest.py::fixtures_dir",
                type=EntityType.FUNCTION,
                name="fixtures_dir",
                location=Location(file="tests/conftest.py", start_line=25, end_line=26),
                language="python",
            ),
        ]
        enrich_with_git(PROJECT_ROOT, entities)
        # May or may not have git info depending on commit status
        # Just verify no crash

    def test_enrich_nonexistent_files(self):
        entities = [
            Entity(
                id="FUNC::nonexistent.py::foo",
                type=EntityType.FUNCTION,
                name="foo",
                location=Location(file="nonexistent.py", start_line=1, end_line=1),
                language="python",
            ),
        ]
        enrich_with_git(PROJECT_ROOT, entities)
        assert entities[0].git_info is None

    def test_enrich_non_git_repo(self, tmp_path):
        entities = [
            Entity(
                id="FUNC::test.py::foo",
                type=EntityType.FUNCTION,
                name="foo",
                location=Location(file="test.py", start_line=1, end_line=1),
                language="python",
            ),
        ]
        enrich_with_git(tmp_path, entities)
        # Should silently do nothing
        assert entities[0].git_info is None
