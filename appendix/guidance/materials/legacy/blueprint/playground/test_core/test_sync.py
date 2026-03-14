"""Tests for the sync system."""

import json
import pytest
from pathlib import Path
import tempfile

from src.core.sync import (
    SyncManager,
    SyncStatus,
    get_sync_manager,
    export_to_bundle,
    import_from_bundle,
    check_sync_status,
)
from src.core.project import ProjectManager
from src.core.bundle import Bundle


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()
        (workspace / "projects").mkdir()
        (workspace / "recent").mkdir()
        (workspace / "results").mkdir()
        (workspace / "snapshots").mkdir()

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


@pytest.fixture
def setup_project(temp_workspace, temp_source):
    """Setup a project with results."""
    pm = ProjectManager(temp_workspace)
    pm.open_project(temp_source)

    # Create mock results
    results_dir = temp_workspace / "results" / "my-project" / "run-001"
    results_dir.mkdir(parents=True)
    (results_dir / "xray_result.json").write_text('{"entities": []}')
    (results_dir / "run_meta.json").write_text('{"run_id": "run-001"}')

    # Update project run info
    pm.update_project_run("my-project", "run-001")

    return {
        "workspace": temp_workspace,
        "source": temp_source,
        "project_name": "my-project",
        "run_id": "run-001",
    }


class TestSyncExport:
    """Tests for exporting to bundle."""

    def test_export_project(self, setup_project):
        """Can export project to bundle."""
        sync = SyncManager(setup_project["workspace"])

        result = sync.export_project(
            project_name=setup_project["project_name"],
            run_id=setup_project["run_id"],
        )

        assert result is True

        # Check bundle was created
        bundle = Bundle(setup_project["source"])
        assert bundle.exists()

        # Check results were copied
        assert (bundle.results_dir / "xray_result.json").exists()

    def test_export_with_config(self, setup_project):
        """Export includes run config."""
        sync = SyncManager(setup_project["workspace"])

        sync.export_project(
            project_name=setup_project["project_name"],
            run_id=setup_project["run_id"],
            run_config={"domains": ["xray"], "preset": "deep"},
        )

        bundle = Bundle(setup_project["source"])
        config = bundle.get_last_run_config()

        assert config is not None
        assert config.domains == ["xray"]
        assert config.preset == "deep"


class TestSyncImport:
    """Tests for importing from bundle."""

    def test_import_project(self, temp_workspace, temp_source):
        """Can import project from bundle."""
        # Create a bundle first
        bundle = Bundle(temp_source)
        bundle.create()
        (bundle.results_dir / "xray_result.json").write_text('{"entities": []}')

        # Update manifest with run_id
        manifest = json.loads(bundle.manifest_path.read_text())
        manifest["last_run_id"] = "run-001"
        bundle.manifest_path.write_text(json.dumps(manifest))

        # Import
        sync = SyncManager(temp_workspace)
        result = sync.import_project(temp_source)

        assert result is not None
        assert result["project_name"] == "my-project"

        # Check results were imported
        imported = temp_workspace / "results" / "my-project" / "run-001"
        assert imported.exists()


class TestSyncStatus:
    """Tests for sync status."""

    def test_status_no_workspace_no_bundle(self, temp_workspace, temp_source):
        """Status when neither workspace nor bundle exists."""
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        sync = SyncManager(temp_workspace)
        status = sync.get_sync_status("my-project")

        assert status.workspace_exists is True
        assert status.bundle_exists is False
        assert status.recommendation == "export"

    def test_status_with_bundle_only(self, temp_workspace, temp_source):
        """Status when only bundle exists."""
        # Create bundle but don't open project
        bundle = Bundle(temp_source)
        bundle.create()

        sync = SyncManager(temp_workspace)
        # First need to create a project entry to check
        pm = ProjectManager(temp_workspace)
        pm.open_project(temp_source)

        status = sync.get_sync_status("my-project")

        assert status.bundle_exists is True

    def test_status_in_sync(self, setup_project):
        """Status when workspace and bundle are in sync."""
        sync = SyncManager(setup_project["workspace"])

        # Export first
        sync.export_project(
            project_name=setup_project["project_name"],
            run_id=setup_project["run_id"],
        )

        status = sync.get_sync_status(setup_project["project_name"])

        assert status.workspace_exists is True
        assert status.bundle_exists is True
        assert status.in_sync is True
        assert status.recommendation == "none"


class TestSyncProject:
    """Tests for full project sync."""

    def test_sync_exports_when_needed(self, setup_project):
        """Sync exports when workspace is ahead."""
        sync = SyncManager(setup_project["workspace"])

        result = sync.sync_project(setup_project["project_name"])

        assert result["action"] == "export"
        assert result["success"] is True

    def test_sync_already_synced(self, setup_project):
        """Sync does nothing when already synced."""
        sync = SyncManager(setup_project["workspace"])

        # First sync
        sync.sync_project(setup_project["project_name"])

        # Second sync
        result = sync.sync_project(setup_project["project_name"])

        assert result["action"] == "none"


class TestAutoSync:
    """Tests for auto-sync after runs."""

    def test_auto_sync_after_run(self, setup_project):
        """Auto sync works after a run."""
        sync = SyncManager(setup_project["workspace"])

        result = sync.auto_sync_after_run(
            project_name=setup_project["project_name"],
            run_id=setup_project["run_id"],
            run_config={"domains": ["xray"]},
        )

        assert result is True

        # Check bundle was created
        bundle = Bundle(setup_project["source"])
        assert bundle.exists()


class TestListOutOfSync:
    """Tests for listing out-of-sync projects."""

    def test_list_out_of_sync(self, setup_project):
        """Can list out-of-sync projects."""
        sync = SyncManager(setup_project["workspace"])

        out_of_sync = sync.list_out_of_sync()

        assert len(out_of_sync) == 1
        assert out_of_sync[0].project_name == setup_project["project_name"]

    def test_list_out_of_sync_empty_after_sync(self, setup_project):
        """No out-of-sync after syncing."""
        sync = SyncManager(setup_project["workspace"])

        sync.sync_project(setup_project["project_name"])
        out_of_sync = sync.list_out_of_sync()

        assert len(out_of_sync) == 0


class TestSyncAll:
    """Tests for syncing all projects."""

    def test_sync_all(self, temp_workspace):
        """Can sync all projects."""
        pm = ProjectManager(temp_workspace)
        sync = SyncManager(temp_workspace)

        # Create multiple projects
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["proj1", "proj2"]:
                source = Path(tmpdir) / name
                source.mkdir()
                pm.open_project(source)

                # Create mock results
                results = temp_workspace / "results" / name / "run-001"
                results.mkdir(parents=True)
                (results / "result.json").write_text("{}")
                pm.update_project_run(name, "run-001")

            results = sync.sync_all()

            assert len(results) == 2
            assert all(r["success"] for r in results)


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_sync_manager(self, temp_workspace):
        """get_sync_manager returns manager."""
        sync = get_sync_manager(temp_workspace)

        assert isinstance(sync, SyncManager)

    def test_export_to_bundle_function(self, setup_project):
        """export_to_bundle function works."""
        result = export_to_bundle(
            workspace_root=setup_project["workspace"],
            project_name=setup_project["project_name"],
            run_id=setup_project["run_id"],
        )

        assert result is True

    def test_check_sync_status_function(self, setup_project):
        """check_sync_status function works."""
        status = check_sync_status(
            workspace_root=setup_project["workspace"],
            project_name=setup_project["project_name"],
        )

        assert isinstance(status, SyncStatus)


class TestSyncStatusDataclass:
    """Tests for SyncStatus dataclass."""

    def test_sync_status_to_dict(self):
        """SyncStatus serializes to dict."""
        status = SyncStatus(
            project_name="test",
            workspace_exists=True,
            bundle_exists=True,
            in_sync=True,
            workspace_run_id="run-001",
            bundle_run_id="run-001",
            workspace_last_modified="2026-02-05T19:00:00",
            bundle_last_sync="2026-02-05T19:00:00",
            recommendation="none",
        )

        data = status.to_dict()

        assert data["project_name"] == "test"
        assert data["in_sync"] is True
        assert data["recommendation"] == "none"
