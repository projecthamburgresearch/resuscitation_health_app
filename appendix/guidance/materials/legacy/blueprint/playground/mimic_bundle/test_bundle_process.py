"""Mimic tests for the bundle system process.

These tests simulate the complete bundle workflow:
1. Bundle creation
2. Export from workspace
3. Import to workspace
4. Sync history tracking

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
from pathlib import Path
from datetime import datetime

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestBundleCreation:
    """Test bundle creation workflow."""

    def test_create_bundle_directory_structure(self, tmp_path):
        """Bundle should create correct directory structure."""
        from src.core.bundle import Bundle

        # Bundle is created from project_root
        project_root = tmp_path / "my-project"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        bundle_path = project_root / "my-project_blueprint"
        # Check structure
        assert bundle_path.exists()
        assert (bundle_path / "bundle.json").exists()
        assert (bundle_path / "results").is_dir()
        assert (bundle_path / "configs").is_dir()

    def test_bundle_json_has_metadata(self, tmp_path):
        """bundle.json should have proper metadata."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "meta-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create(workspace_link="/workspace/projects/meta-test")

        bundle_path = project_root / "meta-test_blueprint"
        with open(bundle_path / "bundle.json") as f:
            data = json.load(f)

        assert data["project_name"] == "meta-test"
        assert "created_at" in data
        assert data["workspace_link"] == "/workspace/projects/meta-test"


class TestBundleExport:
    """Test exporting workspace data to bundle."""

    def test_export_copies_results(self, tmp_path):
        """Export should copy run results to bundle."""
        from src.core.bundle import Bundle

        # Set up workspace with results
        workspace = tmp_path / "workspace"
        results_dir = workspace / "results" / "export-test" / "run-001"
        results_dir.mkdir(parents=True)
        (results_dir / "xray.json").write_text('{"entities": []}')
        (results_dir / "manifest.json").write_text('{"files": []}')

        # Create project and bundle
        project_root = tmp_path / "export-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()
        bundle.export_from_workspace(workspace, "export-test", "run-001")

        # Check results copied
        bundle_results = bundle.bundle_dir / "results"
        assert bundle_results.exists()
        # Results are copied to results/ not results/run-001/
        assert any(f.suffix == ".json" for f in bundle_results.rglob("*"))

    def test_export_records_sync_history(self, tmp_path):
        """Export should record sync in history."""
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"
        results_dir = workspace / "results" / "sync-test" / "run-002"
        results_dir.mkdir(parents=True)
        (results_dir / "data.json").write_text("{}")

        project_root = tmp_path / "sync-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()
        bundle.export_from_workspace(workspace, "sync-test", "run-002")

        # Check sync history
        sync_history = bundle.get_sync_history()
        assert len(sync_history) == 1
        assert sync_history[0].run_id == "run-002"
        assert sync_history[0].direction == "export"


class TestBundleImport:
    """Test importing bundle data to workspace."""

    def test_import_copies_results(self, tmp_path):
        """Import should copy bundle results to workspace."""
        from src.core.bundle import Bundle

        # Create project and bundle with results
        project_root = tmp_path / "import-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()
        (bundle.results_dir / "run-003").mkdir(parents=True)
        (bundle.results_dir / "run-003" / "data.json").write_text('{"key": "value"}')

        # Update manifest with last_run_id
        manifest = bundle._load_manifest()
        manifest.last_run_id = "run-003"
        bundle._save_manifest(manifest)

        # Import to workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        result = bundle.import_to_workspace(workspace)

        # Check import result
        assert result is not None
        assert result.get("run_id") == "run-003"

    def test_import_records_sync_history(self, tmp_path):
        """Import should record sync in history."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "history-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()
        (bundle.results_dir / "run-004").mkdir(parents=True)
        (bundle.results_dir / "run-004" / "x.json").write_text("{}")

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        bundle.import_to_workspace(workspace)

        sync_history = bundle.get_sync_history()
        assert any(s.direction == "import" for s in sync_history)


class TestSyncHistory:
    """Test sync history tracking."""

    def test_sync_history_accumulates(self, tmp_path):
        """Multiple syncs should accumulate in history."""
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"

        project_root = tmp_path / "multi-sync"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        # Multiple exports
        for i in range(3):
            run_dir = workspace / "results" / "multi-sync" / f"run-{i:03d}"
            run_dir.mkdir(parents=True)
            (run_dir / "data.json").write_text("{}")
            bundle.export_from_workspace(workspace, "multi-sync", f"run-{i:03d}")

        history = bundle.get_sync_history()
        assert len(history) == 3

    def test_sync_history_persists(self, tmp_path):
        """Sync history should persist across Bundle instances."""
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"
        run_dir = workspace / "results" / "persist-test" / "run-x"
        run_dir.mkdir(parents=True)
        (run_dir / "data.json").write_text("{}")

        project_root = tmp_path / "persist-test"
        project_root.mkdir()

        # First instance
        bundle1 = Bundle(project_root)
        bundle1.create()
        bundle1.export_from_workspace(workspace, "persist-test", "run-x")

        # Second instance
        bundle2 = Bundle(project_root)
        history = bundle2.get_sync_history()

        assert len(history) == 1
        assert history[0].run_id == "run-x"


class TestBundleConfig:
    """Test bundle configuration storage."""

    def test_config_saved_with_run(self, tmp_path):
        """Run config should be saved with results."""
        from src.core.bundle import Bundle

        workspace = tmp_path / "workspace"
        run_dir = workspace / "results" / "config-test" / "run-cfg"
        run_dir.mkdir(parents=True)
        (run_dir / "data.json").write_text("{}")

        project_root = tmp_path / "config-test"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        run_config = {
            "domains": ["xray", "manifest"],
            "preset": "quick",
            "focus": "src/api",
        }

        bundle.export_from_workspace(workspace, "config-test", "run-cfg", run_config)

        # Check config saved in last-run
        config_file = bundle.last_run_dir / "config.json"
        assert config_file.exists()

        with open(config_file) as f:
            saved_config = json.load(f)
            assert saved_config["domains"] == ["xray", "manifest"]
            assert saved_config["preset"] == "quick"


class TestBundlePortability:
    """Test bundle portability features."""

    def test_bundle_self_contained(self, tmp_path):
        """Bundle should be self-contained."""
        from src.core.bundle import Bundle

        project_root = tmp_path / "portable"
        project_root.mkdir()

        bundle = Bundle(project_root)
        bundle.create()

        # Bundle should have the basic structure
        assert bundle.bundle_dir.exists()
        assert bundle.manifest_path.exists()

    def test_bundle_movable(self, tmp_path):
        """Bundle should work after being moved."""
        from src.core.bundle import Bundle
        import shutil

        # Create project and bundle
        project_root = tmp_path / "original" / "movable"
        project_root.mkdir(parents=True)

        bundle1 = Bundle(project_root)
        bundle1.create()
        (bundle1.results_dir / "run-1").mkdir(parents=True)
        (bundle1.results_dir / "run-1" / "data.json").write_text("{}")

        original_bundle_dir = bundle1.bundle_dir

        # Move to new location
        new_project = tmp_path / "moved" / "movable"
        new_project.mkdir(parents=True)
        new_bundle_dir = new_project / "movable_blueprint"
        shutil.move(str(original_bundle_dir), str(new_bundle_dir))

        # Load from new location
        bundle2 = Bundle(new_project)
        metadata = bundle2.get_metadata()

        assert metadata is not None
        assert metadata["name"] == "movable"


class TestBundleDiscovery:
    """Test bundle discovery in project directories."""

    def test_discover_bundle_in_project(self, tmp_path):
        """Should discover bundle inside project directory."""
        from src.core.bundle import find_bundle

        project_dir = tmp_path / "my-app"
        project_dir.mkdir()
        (project_dir / "src").mkdir()

        # Bundle is inside the project
        bundle_dir = project_dir / "my-app_blueprint"
        bundle_dir.mkdir()
        (bundle_dir / "bundle.json").write_text('{"project_name": "my-app"}')

        found = find_bundle(project_dir)
        assert found is not None
        assert found.bundle_dir.name == "my-app_blueprint"
