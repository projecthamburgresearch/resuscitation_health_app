"""Mimic tests for the project management process.

These tests simulate the complete project lifecycle:
1. Opening projects
2. Tracking runs
3. Closing and restoring projects
4. Project metadata management

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
from pathlib import Path
from datetime import datetime

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestProjectOpening:
    """Test project opening workflow."""

    def test_open_project_creates_entry(self, tmp_path):
        """Opening a project should create a project entry."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a source directory
        source_root = tmp_path / "my-app"
        source_root.mkdir()
        (source_root / "src").mkdir()
        (source_root / "src" / "main.py").write_text("# Main")

        manager = ProjectManager(workspace)
        project = manager.open_project(source_root, notes="Test project")

        assert project is not None
        assert project.project_name == "my-app"
        assert project.status == "active"
        assert "Test project" in project.notes

    def test_open_project_creates_workspace_dir(self, tmp_path):
        """Opening a project should create workspace directory."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "test-project"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        project = manager.open_project(source_root)

        project_workspace = workspace / "projects" / "test-project"
        assert project_workspace.exists()
        assert (project_workspace / "project.json").exists()

    def test_reopen_existing_project(self, tmp_path):
        """Reopening a project should preserve history."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "app"
        source_root.mkdir()

        manager = ProjectManager(workspace)

        # Open first time
        project1 = manager.open_project(source_root)
        manager.update_project_run("app", "run-001")

        # Open again
        project2 = manager.open_project(source_root)

        assert project2.total_runs == 1
        assert project2.last_run_id == "run-001"


class TestProjectRunTracking:
    """Test run tracking for projects."""

    def test_update_run_increments_counter(self, tmp_path):
        """Each run should increment the total runs counter."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "counter-test"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        manager.open_project(source_root)

        # Update with multiple runs
        manager.update_project_run("counter-test", "run-001")
        manager.update_project_run("counter-test", "run-002")
        manager.update_project_run("counter-test", "run-003")

        # Check counter
        projects = manager.list_active()
        project = next(p for p in projects if p.project_name == "counter-test")
        assert project.total_runs == 3
        assert project.last_run_id == "run-003"

    def test_run_timestamps_updated(self, tmp_path):
        """Run updates should update timestamps."""
        from src.core.project import ProjectManager
        import time

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "timestamp-test"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        project = manager.open_project(source_root)

        first_opened = project.opened_at

        time.sleep(0.1)  # Small delay
        manager.update_project_run("timestamp-test", "run-001")

        # Reload
        projects = manager.list_active()
        updated = next(p for p in projects if p.project_name == "timestamp-test")

        assert updated.last_run_at is not None
        assert updated.last_run_at != first_opened


class TestProjectClosing:
    """Test project closing and archiving."""

    def test_close_project_moves_to_recent(self, tmp_path):
        """Closing a project should move it to recent."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "closable"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        manager.open_project(source_root)

        # Close it
        success = manager.close_project("closable")

        assert success
        assert not (workspace / "projects" / "closable").exists()
        assert (workspace / "recent" / "closable").exists()

    def test_restore_project_from_recent(self, tmp_path):
        """Restoring a project should move it back to active."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "restorable"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        manager.open_project(source_root)
        manager.update_project_run("restorable", "run-before-close")
        manager.close_project("restorable")

        # Restore
        restored = manager.restore_project("restorable")

        assert restored is not None
        assert restored.status == "active"
        assert restored.last_run_id == "run-before-close"
        assert (workspace / "projects" / "restorable").exists()


class TestProjectListing:
    """Test project listing functionality."""

    def test_list_active_projects(self, tmp_path):
        """Should list all active projects."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = ProjectManager(workspace)

        # Create several projects
        for name in ["project-a", "project-b", "project-c"]:
            source = tmp_path / name
            source.mkdir()
            manager.open_project(source)

        projects = manager.list_active()
        names = [p.project_name for p in projects]

        assert len(projects) == 3
        assert "project-a" in names
        assert "project-b" in names
        assert "project-c" in names

    def test_list_recent_projects(self, tmp_path):
        """Should list recently closed projects."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = ProjectManager(workspace)

        # Create and close projects
        for name in ["old-a", "old-b"]:
            source = tmp_path / name
            source.mkdir()
            manager.open_project(source)
            manager.close_project(name)

        recent = manager.list_recent()

        assert len(recent) == 2
        names = [p.project_name for p in recent]
        assert "old-a" in names
        assert "old-b" in names


class TestBundleLinking:
    """Test project-to-bundle linking."""

    def test_project_tracks_bundle_path(self, tmp_path):
        """Project should track its bundle path."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "bundled-project"
        source_root.mkdir()

        # Create a bundle
        bundle_path = source_root / "bundled-project_blueprint"
        bundle_path.mkdir()
        (bundle_path / "bundle.json").write_text('{"name": "bundled-project"}')

        manager = ProjectManager(workspace)
        project = manager.open_project(source_root)

        # Bundle path should be detected
        assert project.bundle_path is not None
        assert "bundled-project_blueprint" in str(project.bundle_path)


class TestProjectMetadata:
    """Test project metadata handling."""

    def test_project_info_serialization(self, tmp_path):
        """ProjectInfo should serialize/deserialize correctly."""
        from src.core.project import ProjectInfo

        info = ProjectInfo(
            project_name="test-proj",
            source_root=tmp_path / "source",
            workspace_path=tmp_path / "workspace",
            status="active",
            opened_at="2026-01-01T00:00:00",
            last_run_id="run-123",
            last_run_at="2026-01-02T00:00:00",
            bundle_path=tmp_path / "bundle",
            total_runs=5,
            notes="Test notes",
        )

        # Serialize
        data = info.to_dict()
        assert data["project_name"] == "test-proj"
        assert data["total_runs"] == 5

        # Deserialize
        loaded = ProjectInfo.from_dict(data)
        assert loaded.project_name == "test-proj"
        assert loaded.total_runs == 5
        assert loaded.notes == "Test notes"

    def test_project_json_persisted(self, tmp_path):
        """project.json should persist all metadata."""
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source_root = tmp_path / "persistent"
        source_root.mkdir()

        manager = ProjectManager(workspace)
        manager.open_project(source_root, notes="Important project")
        manager.update_project_run("persistent", "run-x")

        # Read the JSON directly
        project_json = workspace / "projects" / "persistent" / "project.json"
        with open(project_json) as f:
            data = json.load(f)

        assert data["project_name"] == "persistent"
        assert data["notes"] == "Important project"
        assert data["last_run_id"] == "run-x"
        assert data["total_runs"] == 1
