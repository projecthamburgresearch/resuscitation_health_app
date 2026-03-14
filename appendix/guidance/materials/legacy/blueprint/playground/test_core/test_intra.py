"""Tests for the intra-run versioning system."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from src.core.intra import (
    IntraVersioning,
    Checkpoint,
    Change,
    IntraLog,
    init_intra_versioning,
    load_intra_log,
)


@pytest.fixture
def temp_snapshot():
    """Create a temporary snapshot directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_dir = Path(tmpdir) / "test-snapshot-001"
        snapshot_dir.mkdir()

        # Create src/ with some files
        src_dir = snapshot_dir / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("__version__ = '1.0.0'")
        (src_dir / "core").mkdir()
        (src_dir / "core" / "config.py").write_text("preset = 'standard'")

        yield snapshot_dir


class TestIntraVersioningInit:
    """Tests for initialization."""

    def test_initializes_on_first_access(self, temp_snapshot):
        """IntraVersioning creates .intra/ directory on first access."""
        iv = IntraVersioning(temp_snapshot)

        assert (temp_snapshot / ".intra").exists()
        assert (temp_snapshot / ".intra" / "checkpoints").exists()
        assert (temp_snapshot / ".intra" / "intra-log.json").exists()

    def test_creates_initial_checkpoint(self, temp_snapshot):
        """IntraVersioning creates an 'initial' checkpoint on init."""
        iv = IntraVersioning(temp_snapshot)

        checkpoints = iv.get_checkpoints()
        assert len(checkpoints) == 1
        assert checkpoints[0].name == "initial"
        assert checkpoints[0].description == "Original boot state from src/"

    def test_initial_checkpoint_contains_src(self, temp_snapshot):
        """The initial checkpoint should contain the src/ files."""
        iv = IntraVersioning(temp_snapshot)

        checkpoint_path = temp_snapshot / ".intra" / "checkpoints" / "cp-001"
        assert checkpoint_path.exists()
        assert (checkpoint_path / "__init__.py").exists()
        assert (checkpoint_path / "core" / "config.py").exists()


class TestCheckpoints:
    """Tests for checkpoint functionality."""

    def test_create_checkpoint(self, temp_snapshot):
        """Can create a named checkpoint."""
        iv = IntraVersioning(temp_snapshot)

        cp_id = iv.checkpoint("before-change", description="Testing checkpoint")

        assert cp_id == "cp-002"  # cp-001 is initial
        checkpoints = iv.get_checkpoints()
        assert len(checkpoints) == 2
        assert checkpoints[1].name == "before-change"

    def test_checkpoint_preserves_state(self, temp_snapshot):
        """Checkpoint preserves the current src/ state."""
        iv = IntraVersioning(temp_snapshot)

        # Modify a file
        config_path = temp_snapshot / "src" / "core" / "config.py"
        config_path.write_text("preset = 'deep'")

        # Create checkpoint
        cp_id = iv.checkpoint("after-preset-change")

        # Verify checkpoint has modified content
        checkpoint_path = temp_snapshot / ".intra" / "checkpoints" / cp_id
        saved_config = (checkpoint_path / "core" / "config.py").read_text()
        assert saved_config == "preset = 'deep'"

    def test_multiple_checkpoints(self, temp_snapshot):
        """Can create multiple checkpoints."""
        iv = IntraVersioning(temp_snapshot)

        iv.checkpoint("checkpoint-a")
        iv.checkpoint("checkpoint-b")
        iv.checkpoint("checkpoint-c")

        checkpoints = iv.get_checkpoints()
        assert len(checkpoints) == 4  # initial + 3


class TestChanges:
    """Tests for change logging."""

    def test_log_change(self, temp_snapshot):
        """Can log a change."""
        iv = IntraVersioning(temp_snapshot)

        change_id = iv.log_change(
            change_type="parameter",
            description="Changed preset from standard to deep",
            before={"preset": "standard"},
            after={"preset": "deep"},
            auto_checkpoint=False,
        )

        assert change_id == "ch-001"
        changes = iv.get_changes()
        assert len(changes) == 1
        assert changes[0].change_type == "parameter"
        assert changes[0].before == {"preset": "standard"}
        assert changes[0].after == {"preset": "deep"}

    def test_log_change_with_auto_checkpoint(self, temp_snapshot):
        """Auto-checkpoint creates a checkpoint before the change."""
        iv = IntraVersioning(temp_snapshot)

        initial_checkpoints = len(iv.get_checkpoints())

        iv.log_change(
            change_type="code",
            description="Modified parser",
            auto_checkpoint=True,
        )

        # Should have one more checkpoint
        assert len(iv.get_checkpoints()) == initial_checkpoints + 1

    def test_record_outcome(self, temp_snapshot):
        """Can record the outcome of a change."""
        iv = IntraVersioning(temp_snapshot)

        change_id = iv.log_change(
            change_type="parameter",
            description="Changed preset",
            auto_checkpoint=False,
        )

        iv.record_outcome(
            change_id,
            outcome="Entities increased from 164 to 210",
            run_id="2026-02-05_180000",
        )

        changes = iv.get_changes()
        assert changes[0].outcome == "Entities increased from 164 to 210"
        assert changes[0].run_id == "2026-02-05_180000"


class TestRevert:
    """Tests for revert functionality."""

    def test_revert_to_checkpoint(self, temp_snapshot):
        """Can revert to a previous checkpoint."""
        iv = IntraVersioning(temp_snapshot)

        # Get original content
        config_path = temp_snapshot / "src" / "core" / "config.py"
        original = config_path.read_text()

        # Modify file
        config_path.write_text("preset = 'modified'")

        # Create checkpoint of modified state
        iv.checkpoint("modified-state")

        # Modify again
        config_path.write_text("preset = 'double-modified'")

        # Revert to initial
        result = iv.revert("cp-001")

        assert result is True
        assert config_path.read_text() == original

    def test_revert_logs_change(self, temp_snapshot):
        """Revert operation is logged as a change."""
        iv = IntraVersioning(temp_snapshot)

        iv.checkpoint("test-checkpoint")
        iv.revert("cp-001")

        changes = iv.get_changes()
        # Should have at least one change (the revert itself may auto-checkpoint)
        revert_changes = [c for c in changes if c.change_type == "revert"]
        assert len(revert_changes) == 1

    def test_revert_to_nonexistent_checkpoint(self, temp_snapshot):
        """Revert to nonexistent checkpoint returns False."""
        iv = IntraVersioning(temp_snapshot)

        result = iv.revert("cp-999")

        assert result is False

    def test_can_revert(self, temp_snapshot):
        """can_revert returns True when there are multiple checkpoints."""
        iv = IntraVersioning(temp_snapshot)

        # Only initial checkpoint
        assert iv.can_revert() is False

        # Add another
        iv.checkpoint("second")
        assert iv.can_revert() is True


class TestHistory:
    """Tests for history functionality."""

    def test_get_history(self, temp_snapshot):
        """Can get full history."""
        iv = IntraVersioning(temp_snapshot)

        iv.checkpoint("test-cp")
        iv.log_change(
            change_type="parameter",
            description="Test change",
            auto_checkpoint=False,
        )

        history = iv.get_history()

        assert history["snapshot_id"] == temp_snapshot.name
        assert history["total_checkpoints"] >= 2
        assert history["total_changes"] >= 1
        assert "changes_by_type" in history

    def test_changes_grouped_by_type(self, temp_snapshot):
        """Changes are grouped by type in history."""
        iv = IntraVersioning(temp_snapshot)

        iv.log_change(change_type="parameter", description="p1", auto_checkpoint=False)
        iv.log_change(change_type="parameter", description="p2", auto_checkpoint=False)
        iv.log_change(change_type="code", description="c1", auto_checkpoint=False)

        history = iv.get_history()

        assert history["changes_by_type"]["parameter"] == 2
        assert history["changes_by_type"]["code"] == 1


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_init_intra_versioning(self, temp_snapshot):
        """init_intra_versioning creates and returns IntraVersioning."""
        iv = init_intra_versioning(temp_snapshot)

        assert isinstance(iv, IntraVersioning)
        assert (temp_snapshot / ".intra").exists()

    def test_load_intra_log(self, temp_snapshot):
        """load_intra_log loads existing log."""
        # First initialize
        IntraVersioning(temp_snapshot)

        # Then load
        log = load_intra_log(temp_snapshot)

        assert log is not None
        assert log.snapshot_id == temp_snapshot.name

    def test_load_intra_log_returns_none_if_not_initialized(self, temp_snapshot):
        """load_intra_log returns None if not initialized."""
        log = load_intra_log(temp_snapshot)

        assert log is None


class TestDataclasses:
    """Tests for dataclass serialization."""

    def test_checkpoint_roundtrip(self):
        """Checkpoint can be serialized and deserialized."""
        cp = Checkpoint(
            checkpoint_id="cp-001",
            name="test",
            created_at="2026-02-05T18:00:00",
            description="Test checkpoint",
            run_id="run-001",
        )

        data = cp.to_dict()
        restored = Checkpoint.from_dict(data)

        assert restored.checkpoint_id == cp.checkpoint_id
        assert restored.name == cp.name
        assert restored.description == cp.description

    def test_change_roundtrip(self):
        """Change can be serialized and deserialized."""
        ch = Change(
            change_id="ch-001",
            timestamp="2026-02-05T18:00:00",
            change_type="parameter",
            description="Test change",
            before={"a": 1},
            after={"a": 2},
            files_affected=["file1.py", "file2.py"],
        )

        data = ch.to_dict()
        restored = Change.from_dict(data)

        assert restored.change_id == ch.change_id
        assert restored.before == ch.before
        assert restored.files_affected == ch.files_affected

    def test_intra_log_roundtrip(self):
        """IntraLog can be serialized and deserialized."""
        log = IntraLog(
            snapshot_id="test-001",
            created_at="2026-02-05T18:00:00",
            checkpoints=[
                Checkpoint("cp-001", "initial", "2026-02-05T18:00:00"),
            ],
            changes=[
                Change("ch-001", "2026-02-05T18:00:00", "parameter", "test", {}, {}),
            ],
            current_checkpoint="cp-001",
        )

        data = log.to_dict()
        restored = IntraLog.from_dict(data)

        assert restored.snapshot_id == log.snapshot_id
        assert len(restored.checkpoints) == 1
        assert len(restored.changes) == 1
        assert restored.current_checkpoint == "cp-001"
