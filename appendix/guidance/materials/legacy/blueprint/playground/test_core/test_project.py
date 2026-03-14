"""Tests for the project management system."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from src.core.project import (
    ProjectManager,
    ProjectInfo,
    get_project_manager,
    open_project,
    list_projects,
)
from src.core.bundle import Bundle


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        yield workspace


@pytest.fixture
def temp_source():
    """Create a temporary source project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "my-project"
        source.mkdir()
        (source / "src").mkdir()
        (source / "src" / "main.py").write_text("print('hello')")

        yield source


class TestProjectManagerInit:
    """Tests for ProjectManager initialization."""

    def test_creates_directories(self, temp_workspace):
        """ProjectManager creates workspace directories."""
        pm = ProjectManager(temp_workspace)

        assert (temp_workspace / "projects").exists()
        assert (temp_workspace / "recent").exists()
        assert (temp_workspace / "snapshots").exists()
        assert (temp_workspace / "results").exists()


class TestOpenProject:
    """Tests for opening projects."""

    def test_open_project(self, temp_workspace, temp_source):
        """Can open a project."""
        pm = ProjectManager(temp_workspace)

        info = pm.open_project(temp_source)

        assert info is not None
        assert info.project_name == "my-project"
        assert info.status == "active"
        assert (temp_workspace / "projects" / "my-project").exists()

    def test_open_project_creates_marker(self, temp_workspace, temp_source):
        """Opening project creates .active marker."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        assert (temp_workspace / "projects" / "my-project" / ".active").exists()

    def test_open_project_saves_info(self, temp_workspace, temp_source):
        """Opening project saves project.json."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        info_path = temp_workspace / "projects" / "my-project" / "project.json"
        assert info_path.exists()

        data = json.loads(info_path.read_text())
        assert data["project_name"] == "my-project"
        assert data["source_root"] == str(temp_source.resolve())

    def test_open_already_active(self, temp_workspace, temp_source):
        """Opening already active project returns existing info."""
        pm = ProjectManager(temp_workspace)

        info1 = pm.open_project(temp_source)
        info2 = pm.open_project(temp_source)

        assert info1.project_name == info2.project_name
        assert info1.opened_at == info2.opened_at  # Same instance

    def test_open_with_notes(self, temp_workspace, temp_source):
        """Can open project with notes."""
        pm = ProjectManager(temp_workspace)

        info = pm.open_project(temp_source, notes="Test project for demos")

        assert info.notes == "Test project for demos"


class TestCloseProject:
    """Tests for closing projects."""

    def test_close_project(self, temp_workspace, temp_source):
        """Can close a project."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        result = pm.close_project("my-project")

        assert result is True
        assert not (temp_workspace / "projects" / "my-project").exists()
        assert (temp_workspace / "recent" / "my-project").exists()

    def test_close_creates_recent_marker(self, temp_workspace, temp_source):
        """Closing project creates .recent marker."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        assert (temp_workspace / "recent" / "my-project" / ".recent").exists()

    def test_close_saves_summary(self, temp_workspace, temp_source):
        """Closing project saves summary."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        summary_path = temp_workspace / "recent" / "my-project" / "summary.json"
        assert summary_path.exists()

    def test_close_nonexistent(self, temp_workspace):
        """Closing nonexistent project returns False."""
        pm = ProjectManager(temp_workspace)

        result = pm.close_project("nonexistent")

        assert result is False


class TestRestoreProject:
    """Tests for restoring projects."""

    def test_restore_project(self, temp_workspace, temp_source):
        """Can restore a closed project."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        info = pm.restore_project("my-project")

        assert info is not None
        assert info.status == "active"
        assert (temp_workspace / "projects" / "my-project").exists()
        assert not (temp_workspace / "recent" / "my-project").exists()

    def test_restore_nonexistent(self, temp_workspace):
        """Restoring nonexistent project returns None."""
        pm = ProjectManager(temp_workspace)

        info = pm.restore_project("nonexistent")

        assert info is None

    def test_open_restores_from_recent(self, temp_workspace, temp_source):
        """Opening a project in recent restores it."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        # Open again
        info = pm.open_project(temp_source)

        assert info is not None
        assert info.status == "active"


class TestListProjects:
    """Tests for listing projects."""

    def test_list_active(self, temp_workspace, temp_source):
        """Can list active projects."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        active = pm.list_active()

        assert len(active) == 1
        assert active[0].project_name == "my-project"
        assert active[0].status == "active"

    def test_list_recent(self, temp_workspace, temp_source):
        """Can list recent projects."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        recent = pm.list_recent()

        assert len(recent) == 1
        assert recent[0].project_name == "my-project"
        assert recent[0].status == "recent"

    def test_list_all(self, temp_workspace):
        """Can list all projects."""
        pm = ProjectManager(temp_workspace)

        # Create multiple temp sources
        with tempfile.TemporaryDirectory() as tmpdir:
            proj1 = Path(tmpdir) / "project1"
            proj1.mkdir()
            proj2 = Path(tmpdir) / "project2"
            proj2.mkdir()

            pm.open_project(proj1)
            pm.open_project(proj2)
            pm.close_project("project1")

            all_projects = pm.list_all()

            assert len(all_projects["active"]) == 1
            assert len(all_projects["recent"]) == 1


class TestGetProject:
    """Tests for getting project info."""

    def test_get_active_project(self, temp_workspace, temp_source):
        """Can get active project info."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        info = pm.get_project("my-project")

        assert info is not None
        assert info.status == "active"

    def test_get_recent_project(self, temp_workspace, temp_source):
        """Can get recent project info."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        info = pm.get_project("my-project")

        assert info is not None
        assert info.status == "recent"

    def test_get_nonexistent_project(self, temp_workspace):
        """Getting nonexistent project returns None."""
        pm = ProjectManager(temp_workspace)

        info = pm.get_project("nonexistent")

        assert info is None


class TestUpdateProjectRun:
    """Tests for updating project with run info."""

    def test_update_project_run(self, temp_workspace, temp_source):
        """Can update project with run info."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        result = pm.update_project_run("my-project", "run-001")

        assert result is True

        info = pm.get_project("my-project")
        assert info.last_run_id == "run-001"
        assert info.total_runs == 1

    def test_multiple_runs(self, temp_workspace, temp_source):
        """Multiple runs increment counter."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        pm.update_project_run("my-project", "run-001")
        pm.update_project_run("my-project", "run-002")
        pm.update_project_run("my-project", "run-003")

        info = pm.get_project("my-project")
        assert info.total_runs == 3
        assert info.last_run_id == "run-003"


class TestDeleteProject:
    """Tests for deleting projects."""

    def test_delete_from_recent(self, temp_workspace, temp_source):
        """Can delete project from recent."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)
        pm.close_project("my-project")

        result = pm.delete_project("my-project", from_recent=True)

        assert result is True
        assert not (temp_workspace / "recent" / "my-project").exists()

    def test_delete_from_active(self, temp_workspace, temp_source):
        """Can delete project from active."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        result = pm.delete_project("my-project", from_recent=False)

        assert result is True
        assert not (temp_workspace / "projects" / "my-project").exists()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_project_manager(self, temp_workspace):
        """get_project_manager returns manager."""
        pm = get_project_manager(temp_workspace)

        assert isinstance(pm, ProjectManager)

    def test_open_project_function(self, temp_workspace, temp_source):
        """open_project function works."""
        info = open_project(temp_workspace, temp_source)

        assert info is not None
        assert info.project_name == "my-project"

    def test_list_projects_function(self, temp_workspace, temp_source):
        """list_projects function works."""
        open_project(temp_workspace, temp_source)

        projects = list_projects(temp_workspace)

        assert len(projects["active"]) == 1


class TestDataclass:
    """Tests for ProjectInfo dataclass."""

    def test_project_info_roundtrip(self):
        """ProjectInfo serializes and deserializes."""
        info = ProjectInfo(
            project_name="test",
            source_root="/path/to/test",
            workspace_path="/workspace/projects/test",
            status="active",
            opened_at="2026-02-05T19:00:00",
            last_run_id="run-001",
            total_runs=5,
        )

        data = info.to_dict()
        restored = ProjectInfo.from_dict(data)

        assert restored.project_name == info.project_name
        assert restored.total_runs == 5
        assert restored.last_run_id == "run-001"
