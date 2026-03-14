"""Mimic tests for the intra-run versioning process.

These tests simulate the complete intra-run workflow:
1. Checkpoint creation
2. Change logging
3. Outcome tracking
4. Revert operations

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
import shutil
from pathlib import Path

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestCheckpointCreation:
    """Test checkpoint creation and restoration."""

    def test_checkpoint_captures_src_state(self, tmp_path):
        """Checkpoint should capture exact state of src/."""
        from src.core.intra import IntraVersioning

        # Create snapshot structure
        snapshot_dir = tmp_path / "snap-001"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "module.py").write_text("VERSION = 1")

        intra = IntraVersioning(snapshot_dir)

        # Create checkpoint
        cp1 = intra.checkpoint("v1", "Version 1")

        # Modify src
        (src_dir / "module.py").write_text("VERSION = 2")

        # Create another checkpoint
        cp2 = intra.checkpoint("v2", "Version 2")

        # Both explicit checkpoints should exist (may have auto-initial too)
        history = intra.get_history()
        v1_checkpoints = [c for c in history["checkpoints"] if c["name"] == "v1"]
        v2_checkpoints = [c for c in history["checkpoints"] if c["name"] == "v2"]
        assert len(v1_checkpoints) == 1
        assert len(v2_checkpoints) == 1

        # Checkpoint 1 should have original content
        cp1_dir = snapshot_dir / ".intra" / "checkpoints" / cp1
        assert (cp1_dir / "module.py").read_text() == "VERSION = 1"

    def test_checkpoint_with_subdirectories(self, tmp_path):
        """Checkpoint should preserve directory structure."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-002"
        src_dir = snapshot_dir / "src"
        (src_dir / "core").mkdir(parents=True)
        (src_dir / "core" / "models.py").write_text("class Model: pass")
        (src_dir / "utils").mkdir()
        (src_dir / "utils" / "helpers.py").write_text("def helper(): pass")

        intra = IntraVersioning(snapshot_dir)
        cp = intra.checkpoint("initial", "Initial state")

        # Check structure preserved
        cp_dir = snapshot_dir / ".intra" / "checkpoints" / cp
        assert (cp_dir / "core" / "models.py").exists()
        assert (cp_dir / "utils" / "helpers.py").exists()


class TestRevertOperation:
    """Test reverting to previous checkpoints."""

    def test_revert_restores_exact_state(self, tmp_path):
        """Revert should restore exact file contents."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-003"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        # Version 1
        (src_dir / "config.py").write_text("DEBUG = False")

        intra = IntraVersioning(snapshot_dir)
        cp1 = intra.checkpoint("production", "Production config")

        # Version 2 (broken)
        (src_dir / "config.py").write_text("DEBUG = True  # OOPS")
        (src_dir / "new_file.py").write_text("# Should be removed on revert")

        # Revert to cp1
        success = intra.revert(cp1)

        assert success
        assert (src_dir / "config.py").read_text() == "DEBUG = False"
        assert not (src_dir / "new_file.py").exists()

    def test_revert_logs_change(self, tmp_path):
        """Revert should be logged in change history."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-004"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "test.py").write_text("pass")

        intra = IntraVersioning(snapshot_dir)
        cp = intra.checkpoint("before", "Before changes")

        # Make change
        (src_dir / "test.py").write_text("# changed")

        # Revert
        intra.revert(cp)

        # Check change log
        history = intra.get_history()
        reverts = [c for c in history["changes"] if c["change_type"] == "revert"]
        assert len(reverts) >= 1


class TestChangeLogging:
    """Test change logging functionality."""

    def test_log_change_with_diff(self, tmp_path):
        """Change log should capture before/after state."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-005"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        intra = IntraVersioning(snapshot_dir)

        change_id = intra.log_change(
            change_type="config_update",
            description="Changed timeout from 30 to 60",
            before={"timeout": 30},
            after={"timeout": 60},
            files_affected=["src/config.py"],  # Correct parameter name
            auto_checkpoint=False,  # Disable auto-checkpoint for this test
        )

        assert change_id.startswith("ch-")

        history = intra.get_history()
        change = next(c for c in history["changes"] if c["change_id"] == change_id)
        assert change["before"] == {"timeout": 30}
        assert change["after"] == {"timeout": 60}

    def test_change_outcome_tracking(self, tmp_path):
        """Changes should track whether they succeeded."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-006"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        intra = IntraVersioning(snapshot_dir)

        # Log a change
        change_id = intra.log_change(
            change_type="parser_fix",
            description="Fixed TypeScript parser",
            auto_checkpoint=False,
        )

        # Record success
        intra.record_outcome(
            change_id=change_id,
            outcome={
                "success": True,
                "tests_passed": 10,
                "entities_before": 50,
                "entities_after": 75,
            },
        )

        history = intra.get_history()
        change = next(c for c in history["changes"] if c["change_id"] == change_id)
        assert change["outcome"]["success"] is True
        assert change["outcome"]["entities_after"] == 75


class TestChangeHistory:
    """Test change history queries."""

    def test_get_changes_since_checkpoint(self, tmp_path):
        """Should be able to get all changes since a checkpoint."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-007"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        intra = IntraVersioning(snapshot_dir)

        # Create checkpoint
        cp = intra.checkpoint("baseline", "Baseline")

        # Make several changes (without auto-checkpoints)
        intra.log_change("fix1", "First fix", auto_checkpoint=False)
        intra.log_change("fix2", "Second fix", auto_checkpoint=False)
        intra.log_change("fix3", "Third fix", auto_checkpoint=False)

        history = intra.get_history()
        changes = history["changes"]

        # Should have 3 explicit changes
        explicit_changes = [c for c in changes if c["change_type"] in ("fix1", "fix2", "fix3")]
        assert len(explicit_changes) == 3

    def test_history_persists_across_instances(self, tmp_path):
        """History should persist when IntraVersioning is reloaded."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-008"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        # First instance
        intra1 = IntraVersioning(snapshot_dir)
        cp = intra1.checkpoint("first", "First checkpoint")
        intra1.log_change("edit", "Made an edit", auto_checkpoint=False)

        # Second instance (simulating restart)
        intra2 = IntraVersioning(snapshot_dir)
        history = intra2.get_history()

        # Should have at least the "first" checkpoint
        first_checkpoints = [c for c in history["checkpoints"] if c["name"] == "first"]
        assert len(first_checkpoints) == 1

        # Should have the edit change
        edit_changes = [c for c in history["changes"] if c["change_type"] == "edit"]
        assert len(edit_changes) == 1


class TestRunTracking:
    """Test run tracking within intra-versioning."""

    def test_changes_associated_with_run(self, tmp_path):
        """Changes should be associated with run IDs."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-009"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        intra = IntraVersioning(snapshot_dir)

        # Log change with run ID
        change_id = intra.log_change(
            change_type="optimization",
            description="Added caching",
            run_id="run-2026-001",
            auto_checkpoint=False,
        )

        history = intra.get_history()
        change = next(c for c in history["changes"] if c["change_id"] == change_id)
        assert change["run_id"] == "run-2026-001"

    def test_checkpoint_associated_with_run(self, tmp_path):
        """Checkpoints should be associated with run IDs."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-010"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)

        intra = IntraVersioning(snapshot_dir)

        cp = intra.checkpoint("post-run", "After successful run", run_id="run-2026-002")

        history = intra.get_history()
        checkpoint = next(c for c in history["checkpoints"] if c["checkpoint_id"] == cp)
        assert checkpoint["run_id"] == "run-2026-002"


class TestSafetyGuards:
    """Test safety mechanisms in intra-versioning."""

    def test_invalid_checkpoint_id_fails(self, tmp_path):
        """Reverting to invalid checkpoint should fail gracefully."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-011"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "file.py").write_text("original")

        intra = IntraVersioning(snapshot_dir)

        # Try to revert to non-existent checkpoint
        success = intra.revert("cp-does-not-exist")

        assert success is False
        # Original file should be untouched
        assert (src_dir / "file.py").read_text() == "original"

    def test_checkpoint_excludes_pycache(self, tmp_path):
        """Checkpoints should not include __pycache__."""
        from src.core.intra import IntraVersioning

        snapshot_dir = tmp_path / "snap-012"
        src_dir = snapshot_dir / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "module.py").write_text("pass")
        (src_dir / "__pycache__").mkdir()
        (src_dir / "__pycache__" / "module.cpython-312.pyc").write_bytes(b"compiled")

        intra = IntraVersioning(snapshot_dir)
        cp = intra.checkpoint("clean", "Clean checkpoint")

        cp_dir = snapshot_dir / ".intra" / "checkpoints" / cp
        assert not (cp_dir / "__pycache__").exists()
