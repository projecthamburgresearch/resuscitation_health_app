"""Mimic tests for the sync system process.

These tests simulate the complete sync workflow:
1. Workspace to bundle sync
2. Bundle to workspace sync
3. Auto-sync after runs
4. Conflict detection

Unlike unit tests, mimic tests exercise the full process with real files.

Note: Some of these tests require full project setup with ProjectManager.
For basic functionality, see the bundle tests which test export/import directly.
"""

import json
from pathlib import Path
from datetime import datetime

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestSyncManagerBasics:
    """Test basic sync manager functionality."""

    def test_sync_manager_initialization(self, tmp_path):
        """SyncManager should initialize correctly."""
        from src.core.sync import SyncManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = SyncManager(workspace)

        assert manager.workspace_root == workspace
        assert manager.project_manager is not None

    def test_get_sync_status_for_nonexistent(self, tmp_path):
        """Should handle nonexistent projects gracefully."""
        from src.core.sync import SyncManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        manager = SyncManager(workspace)
        status = manager.get_sync_status("nonexistent-project")

        assert status.project_name == "nonexistent-project"
        assert status.workspace_exists is False
        assert status.bundle_exists is False


class TestSyncStatus:
    """Test sync status checking."""

    def test_sync_status_when_no_bundle(self, tmp_path):
        """Should report no bundle when bundle doesn't exist."""
        from src.core.sync import SyncManager
        from src.core.project import ProjectManager

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a project
        source = tmp_path / "my-project"
        source.mkdir()

        pm = ProjectManager(workspace)
        pm.open_project(source)

        sm = SyncManager(workspace)
        status = sm.get_sync_status("my-project")

        assert status.workspace_exists is True
        assert status.bundle_exists is False
        assert status.recommendation == "export"

    def test_sync_status_when_has_bundle(self, tmp_path):
        """Should report bundle when it exists."""
        from src.core.sync import SyncManager
        from src.core.project import ProjectManager
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create project with bundle
        source = tmp_path / "bundled-project"
        source.mkdir()

        bundle = Bundle(source)
        bundle.create()

        pm = ProjectManager(workspace)
        pm.open_project(source)

        sm = SyncManager(workspace)
        status = sm.get_sync_status("bundled-project")

        assert status.workspace_exists is True
        assert status.bundle_exists is True


class TestSyncHelpers:
    """Test sync helper functions."""

    def test_get_sync_status_function(self, tmp_path):
        """get_sync_status should return detailed info."""
        from src.core.sync import get_sync_status
        from src.core.project import ProjectManager
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source = tmp_path / "status-test"
        source.mkdir()

        pm = ProjectManager(workspace)
        pm.open_project(source)

        result = get_sync_status(workspace, "status-test")

        assert result["project_name"] == "status-test"
        assert "missing_in_workspace" in result
        assert "missing_in_bundle" in result
        assert "conflicts" in result


class TestWardenSyncIntegration:
    """Test warden-related sync functionality."""

    def test_sync_warden_creates_directory(self, tmp_path):
        """Syncing warden state should create directories."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "project"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        # Warden directory should exist in bundle
        assert bundle.warden_dir.exists()
        assert (bundle.warden_dir / "commits").exists()
        assert (bundle.warden_dir / "decisions").exists()

    def test_export_warden_state(self, tmp_path):
        """Should export warden state from workspace to bundle."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create workspace warden state
        workspace_warden = tmp_path / "workspace" / "warden"
        (workspace_warden / "decisions").mkdir(parents=True)
        (workspace_warden / "decisions" / "decisions.json").write_text(
            '{"decisions": [{"action": "test"}]}'
        )

        bundle = Bundle(project_root)
        bundle.create()

        success = bundle.export_warden_state(workspace_warden)

        assert success
        assert (bundle.warden_dir / "decisions" / "decisions.json").exists()

    def test_import_warden_state(self, tmp_path):
        """Should import warden state from bundle to workspace."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "project"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        # Create bundle warden state
        (bundle.warden_dir / "decisions").mkdir(parents=True, exist_ok=True)
        (bundle.warden_dir / "decisions" / "decisions.json").write_text(
            '{"decisions": [{"action": "imported"}]}'
        )

        workspace_warden = tmp_path / "workspace" / "warden"

        success = bundle.import_warden_state(workspace_warden)

        assert success
        assert (workspace_warden / "decisions" / "decisions.json").exists()

    def test_warden_summary(self, tmp_path):
        """Should get warden summary from bundle."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "project"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        # Create some warden data
        (bundle.warden_dir / "decisions").mkdir(parents=True, exist_ok=True)
        (bundle.warden_dir / "decisions" / "decisions.json").write_text(
            '{"decisions": [{"id": "1"}, {"id": "2"}]}'
        )

        summary = bundle.get_warden_summary()

        assert summary["has_decisions"] is True
        assert summary["decision_count"] == 2
