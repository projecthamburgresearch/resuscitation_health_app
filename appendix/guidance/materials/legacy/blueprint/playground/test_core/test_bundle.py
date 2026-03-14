"""Tests for the bundle system."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from src.core.bundle import (
    Bundle,
    BundleManifest,
    RunConfig,
    SyncRecord,
    get_bundle,
    find_bundle,
    list_bundles,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test-project"
        project_root.mkdir()

        # Create some source files
        (project_root / "src").mkdir()
        (project_root / "src" / "main.py").write_text("print('hello')")
        (project_root / "package.json").write_text('{"name": "test-project"}')

        yield project_root


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()
        (workspace / "results").mkdir()
        (workspace / "projects").mkdir()

        yield workspace


class TestBundleCreation:
    """Tests for bundle creation."""

    def test_bundle_init(self, temp_project):
        """Bundle initializes with correct paths."""
        bundle = Bundle(temp_project)

        assert bundle.project_name == "test-project"
        assert bundle.bundle_dir.name == "test-project_blueprint"
        assert not bundle.exists()

    def test_create_bundle(self, temp_project):
        """Can create a new bundle."""
        bundle = Bundle(temp_project)
        result = bundle.create()

        assert result is True
        assert bundle.exists()
        assert bundle.bundle_dir.exists()
        assert bundle.manifest_path.exists()
        assert bundle.last_run_dir.exists()
        assert bundle.results_dir.exists()

    def test_create_bundle_idempotent(self, temp_project):
        """Creating bundle twice is safe."""
        bundle = Bundle(temp_project)
        bundle.create()
        result = bundle.create()  # Second call

        assert result is True
        assert bundle.exists()

    def test_bundle_manifest_created(self, temp_project):
        """Bundle manifest is created with correct data."""
        bundle = Bundle(temp_project)
        bundle.create()

        manifest = json.loads(bundle.manifest_path.read_text())

        assert manifest["project_name"] == "test-project"
        # Use Path comparison to handle Windows path normalization
        assert Path(manifest["project_root"]).name == temp_project.name
        assert "created_at" in manifest


class TestBundleInfo:
    """Tests for bundle info."""

    def test_get_info(self, temp_project):
        """Can get bundle info."""
        bundle = Bundle(temp_project)
        bundle.create()

        info = bundle.get_info()

        assert info is not None
        assert info["project_name"] == "test-project"
        assert info["has_results"] is False
        assert info["has_last_run"] is False

    def test_get_info_nonexistent(self, temp_project):
        """get_info returns None for nonexistent bundle."""
        bundle = Bundle(temp_project)

        info = bundle.get_info()

        assert info is None


class TestBundleExport:
    """Tests for exporting to bundle."""

    def test_export_from_workspace(self, temp_project, temp_workspace):
        """Can export workspace results to bundle."""
        bundle = Bundle(temp_project)

        # Create mock results in workspace
        results_dir = temp_workspace / "results" / "test-project" / "run-001"
        results_dir.mkdir(parents=True)
        (results_dir / "xray_result.json").write_text('{"entities": []}')
        (results_dir / "run_meta.json").write_text('{"run_id": "run-001"}')

        # Export
        result = bundle.export_from_workspace(
            workspace_root=temp_workspace,
            project_name="test-project",
            run_id="run-001",
            run_config={"domains": ["xray"], "preset": "standard"},
        )

        assert result is True
        assert bundle.exists()
        assert (bundle.results_dir / "xray_result.json").exists()
        assert (bundle.last_run_dir / "config.json").exists()

    def test_export_updates_manifest(self, temp_project, temp_workspace):
        """Export updates bundle manifest."""
        bundle = Bundle(temp_project)
        bundle.create()

        # Create mock results
        results_dir = temp_workspace / "results" / "test-project" / "run-002"
        results_dir.mkdir(parents=True)
        (results_dir / "result.json").write_text('{}')

        # Export
        bundle.export_from_workspace(
            workspace_root=temp_workspace,
            project_name="test-project",
            run_id="run-002",
        )

        info = bundle.get_info()
        assert info["last_run_id"] == "run-002"
        assert info["total_syncs"] == 1


class TestBundleImport:
    """Tests for importing from bundle."""

    def test_import_to_workspace(self, temp_project, temp_workspace):
        """Can import bundle to workspace."""
        bundle = Bundle(temp_project)
        bundle.create()

        # Add some results to bundle
        (bundle.results_dir / "xray_result.json").write_text('{"entities": []}')

        # Save a config
        config = RunConfig(
            run_id="run-001",
            domains=["xray"],
            preset="standard",
        )
        (bundle.last_run_dir / "config.json").write_text(
            json.dumps(config.to_dict())
        )

        # Update manifest
        manifest = json.loads(bundle.manifest_path.read_text())
        manifest["last_run_id"] = "run-001"
        bundle.manifest_path.write_text(json.dumps(manifest))

        # Import
        result = bundle.import_to_workspace(temp_workspace)

        assert result is not None
        assert result["project_name"] == "test-project"
        assert result["run_id"] == "run-001"

        # Check results were copied
        imported_results = temp_workspace / "results" / "test-project" / "run-001"
        assert imported_results.exists()
        assert (imported_results / "xray_result.json").exists()


class TestSyncHistory:
    """Tests for sync history."""

    def test_sync_history_recorded(self, temp_project, temp_workspace):
        """Sync operations are recorded in history."""
        bundle = Bundle(temp_project)

        # Create mock results
        results_dir = temp_workspace / "results" / "test-project" / "run-001"
        results_dir.mkdir(parents=True)
        (results_dir / "result.json").write_text('{}')

        # Export
        bundle.export_from_workspace(
            workspace_root=temp_workspace,
            project_name="test-project",
            run_id="run-001",
        )

        history = bundle.get_sync_history()
        assert len(history) == 1
        assert history[0].direction == "export"
        assert history[0].run_id == "run-001"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_bundle(self, temp_project):
        """get_bundle returns a Bundle object."""
        bundle = get_bundle(temp_project)

        assert isinstance(bundle, Bundle)
        assert bundle.project_name == "test-project"

    def test_find_bundle_exists(self, temp_project):
        """find_bundle returns bundle when it exists."""
        Bundle(temp_project).create()

        bundle = find_bundle(temp_project)

        assert bundle is not None
        assert bundle.exists()

    def test_find_bundle_not_exists(self, temp_project):
        """find_bundle returns None when bundle doesn't exist."""
        bundle = find_bundle(temp_project)

        assert bundle is None

    def test_list_bundles(self):
        """list_bundles finds bundles in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create two projects with bundles
            proj1 = root / "project1"
            proj1.mkdir()
            Bundle(proj1).create()

            proj2 = root / "project2"
            proj2.mkdir()
            Bundle(proj2).create()

            # Create a project without bundle
            proj3 = root / "project3"
            proj3.mkdir()

            bundles = list_bundles(root)

            assert len(bundles) == 2
            names = [b.project_name for b in bundles]
            assert "project1" in names
            assert "project2" in names


class TestDataclasses:
    """Tests for dataclass serialization."""

    def test_bundle_manifest_roundtrip(self):
        """BundleManifest serializes and deserializes."""
        manifest = BundleManifest(
            project_name="test",
            project_root="/path/to/test",
            created_at="2026-02-05T19:00:00",
            last_sync="2026-02-05T19:30:00",
            total_syncs=5,
        )

        data = manifest.to_dict()
        restored = BundleManifest.from_dict(data)

        assert restored.project_name == manifest.project_name
        assert restored.total_syncs == 5

    def test_run_config_roundtrip(self):
        """RunConfig serializes and deserializes."""
        config = RunConfig(
            run_id="run-001",
            domains=["xray", "sonar"],
            preset="deep",
            focus_path="/src",
        )

        data = config.to_dict()
        restored = RunConfig.from_dict(data)

        assert restored.run_id == config.run_id
        assert restored.domains == ["xray", "sonar"]
        assert restored.preset == "deep"

    def test_sync_record_roundtrip(self):
        """SyncRecord serializes and deserializes."""
        record = SyncRecord(
            sync_id="sync-001",
            timestamp="2026-02-05T19:00:00",
            direction="export",
            run_id="run-001",
            files_synced=["file1.json", "file2.json"],
        )

        data = record.to_dict()
        restored = SyncRecord.from_dict(data)

        assert restored.sync_id == record.sync_id
        assert restored.direction == "export"
        assert len(restored.files_synced) == 2
