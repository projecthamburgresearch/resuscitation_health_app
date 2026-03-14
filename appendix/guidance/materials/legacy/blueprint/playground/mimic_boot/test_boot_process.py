"""Mimic tests for the boot process.

These tests simulate the complete boot flow:
1. Snapshot creation from src/
2. Manifest generation
3. Intra-versioning initialization
4. Subprocess isolation

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest


# Get blueprint root (4 levels up from this file)
BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestSnapshotCreation:
    """Test that snapshots are created correctly from src/."""

    def test_snapshot_creates_directory(self, tmp_path):
        """Snapshot should create a proper directory structure."""
        from src.core.snapshot import create_snapshot

        # Set up a fake blueprint root
        fake_blueprint = tmp_path / "blueprint"
        fake_src = fake_blueprint / "src"
        fake_src.mkdir(parents=True)
        (fake_src / "core").mkdir()
        (fake_src / "core" / "__init__.py").write_text("# core")
        (fake_src / "xray").mkdir()
        (fake_src / "xray" / "__init__.py").write_text("# xray")

        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()

        # Create snapshot
        snapshot_dir = create_snapshot(
            blueprint_root=fake_blueprint,
            workspace_root=workspace_root,
            project_name="test-project",
            run_id="run-001",
        )

        assert snapshot_dir.exists()
        assert (snapshot_dir / "src" / "core" / "__init__.py").exists()
        assert (snapshot_dir / "src" / "xray" / "__init__.py").exists()

    def test_snapshot_has_manifest(self, tmp_path):
        """Snapshot should create a manifest file."""
        from src.core.snapshot import create_snapshot

        fake_blueprint = tmp_path / "blueprint"
        fake_src = fake_blueprint / "src"
        fake_src.mkdir(parents=True)
        (fake_src / "__init__.py").write_text("")

        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()

        snapshot_dir = create_snapshot(
            blueprint_root=fake_blueprint,
            workspace_root=workspace_root,
            project_name="test-project",
            run_id="run-002",
        )

        manifest_path = snapshot_dir / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)
            assert manifest["project_name"] == "test-project"
            assert "created_at" in manifest


class TestSnapshotManifest:
    """Test manifest loading and saving."""

    def test_manifest_roundtrip(self, tmp_path):
        """Manifest should survive save/load cycle."""
        from src.core.snapshot import SnapshotManifest, save_manifest, load_manifest

        manifest = SnapshotManifest(
            snapshot_id="test-snap-001",
            project_name="test-project",
            created_at="2026-01-01T00:00:00",
            blueprint_version="0.2.0",
        )

        snapshot_dir = tmp_path / "snap"
        snapshot_dir.mkdir()

        save_manifest(manifest, snapshot_dir)
        loaded = load_manifest(snapshot_dir)

        assert loaded is not None
        assert loaded.snapshot_id == manifest.snapshot_id
        assert loaded.project_name == manifest.project_name


class TestIntraVersioningInit:
    """Test that intra-versioning is initialized properly on boot."""

    def test_intra_creates_checkpoint_on_boot(self, tmp_path):
        """IntraVersioning should create checkpoint when requested."""
        from src.core.intra import IntraVersioning

        # Set up a snapshot directory structure
        snapshot_dir = tmp_path / "snapshots" / "snap-001"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "core").mkdir()
        (src_dir / "core" / "__init__.py").write_text("# init")

        intra = IntraVersioning(snapshot_dir)

        # Create a checkpoint manually (simulating boot)
        checkpoint_id = intra.checkpoint("boot", "Boot checkpoint")

        assert checkpoint_id.startswith("cp-")
        history = intra.get_history()
        # Should have at least one checkpoint named 'boot'
        boot_checkpoints = [c for c in history["checkpoints"] if c["name"] == "boot"]
        assert len(boot_checkpoints) >= 1


class TestBootGate:
    """Test certificate-gated boot process."""

    def test_boot_blocked_without_certificate(self, tmp_path):
        """Boot should be blocked if no certificate exists."""
        from src.core.certificate import check_boot_certificate

        # Create a minimal blueprint structure
        fake_blueprint = tmp_path / "blueprint"
        (fake_blueprint / "src").mkdir(parents=True)
        (fake_blueprint / "playground").mkdir()
        (fake_blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        can_boot, message = check_boot_certificate(fake_blueprint)

        assert can_boot is False
        assert "No certificate found" in message or "missing" in message.lower()

    def test_boot_allowed_with_valid_certificate(self, tmp_path):
        """Boot should be allowed with a valid certificate."""
        from src.core.certificate import CertificateManager, CertificateStatus

        # Create a minimal blueprint structure
        fake_blueprint = tmp_path / "blueprint"
        (fake_blueprint / "src").mkdir(parents=True)
        (fake_blueprint / "src" / "__init__.py").write_text("# test")
        (fake_blueprint / "playground").mkdir()
        (fake_blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(fake_blueprint)
        cert, success = manager.issue_certificate()

        # Since no mimic tests exist, it should pass
        assert success
        assert cert is not None

        # Now validation should pass
        status, loaded_cert = manager.validate()
        assert status == CertificateStatus.VALID


class TestProcessIsolation:
    """Test subprocess isolation for snapshot execution."""

    def test_snapshot_creates_isolated_copy(self, tmp_path):
        """Snapshot execution should use snapshot's src, not main src."""
        from src.core.snapshot import create_snapshot

        fake_blueprint = tmp_path / "blueprint"
        fake_src = fake_blueprint / "src"
        fake_src.mkdir(parents=True)
        (fake_src / "__init__.py").write_text("VERSION = 'original'")

        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()

        snapshot_dir = create_snapshot(
            blueprint_root=fake_blueprint,
            workspace_root=workspace_root,
            project_name="isolation-test",
            run_id="run-iso",
        )

        # Modify the snapshot's version (simulating intra changes)
        snapshot_init = snapshot_dir / "src" / "__init__.py"
        snapshot_init.write_text("VERSION = 'modified'")

        # Original should be unchanged
        assert (fake_src / "__init__.py").read_text() == "VERSION = 'original'"
        # Snapshot should have modification
        assert snapshot_init.read_text() == "VERSION = 'modified'"
