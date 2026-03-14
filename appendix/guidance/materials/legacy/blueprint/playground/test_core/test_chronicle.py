"""Tests for core.chronicle — run history, milestones, storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.chronicle import (
    Chronicle,
    DeltaRecord,
    Milestone,
    RunRecord,
    start_run,
    end_run,
    record_delta,
    create_milestone,
    save_chronicle,
    load_chronicle,
    get_or_create_chronicle,
)
from src.core.models import AnalysisResult


@pytest.fixture
def chronicle() -> Chronicle:
    return Chronicle(project_root="/test/project")


class TestModels:
    def test_empty_chronicle(self, chronicle):
        assert chronicle.run_count == 0
        assert chronicle.latest_run is None

    def test_run_record(self):
        from datetime import datetime
        run = RunRecord(
            id="abc123",
            started_at=datetime.now(),
            domains_run=["xray"],
            root_path="/project",
        )
        assert not run.is_complete

    def test_milestone(self):
        ms = Milestone(
            name="v1.0",
            description="First release",
            tags=["release"],
        )
        assert ms.name == "v1.0"


class TestTracker:
    def test_start_run(self, chronicle):
        run = start_run(chronicle, "/project", ["xray", "manifest"])
        assert chronicle.run_count == 1
        assert not run.is_complete
        assert "xray" in run.domains_run

    def test_end_run(self, chronicle):
        run = start_run(chronicle, "/project", ["xray"])
        result = AnalysisResult(
            domain="xray",
            version="2.0.0",
            root_path="/project",
            stats={"files_scanned": 10},
        )
        end_run(run, [result])
        assert run.is_complete
        assert run.duration_seconds is not None
        assert run.duration_seconds >= 0

    def test_record_delta(self, chronicle):
        run1 = start_run(chronicle, "/project", ["xray"])
        run2 = start_run(chronicle, "/project", ["xray"])
        delta = record_delta(
            chronicle, run1.id, run2.id,
            added=5, removed=2, modified=3,
        )
        assert len(chronicle.deltas) == 1
        assert delta.entities_added == 5

    def test_create_milestone(self, chronicle):
        run = start_run(chronicle, "/project", ["xray"])
        ms = create_milestone(
            chronicle, "v1.0",
            description="Initial analysis",
            tags=["release"],
            checklist=[{"task": "Review entities", "done": False}],
        )
        assert len(chronicle.milestones) == 1
        assert ms.run_id == run.id
        assert len(ms.checklist) == 1

    def test_get_run(self, chronicle):
        run = start_run(chronicle, "/project", ["xray"])
        found = chronicle.get_run(run.id)
        assert found is not None
        assert found.id == run.id

    def test_get_milestone(self, chronicle):
        create_milestone(chronicle, "test-ms")
        found = chronicle.get_milestone("test-ms")
        assert found is not None


class TestStorage:
    def test_save_load_roundtrip(self, chronicle, tmp_path):
        run = start_run(chronicle, "/project", ["xray"])
        result = AnalysisResult(
            domain="xray", version="2.0.0", root_path="/project",
        )
        end_run(run, [result])
        create_milestone(chronicle, "v1.0")

        path = save_chronicle(chronicle, tmp_path)
        assert path.exists()

        loaded = load_chronicle(path)
        assert loaded.run_count == 1
        assert len(loaded.milestones) == 1
        assert loaded.milestones[0].name == "v1.0"

    def test_get_or_create_new(self, tmp_path):
        c = get_or_create_chronicle(tmp_path)
        assert c.run_count == 0

    def test_get_or_create_existing(self, chronicle, tmp_path):
        start_run(chronicle, "/project", ["xray"])
        save_chronicle(chronicle, tmp_path)

        loaded = get_or_create_chronicle(tmp_path)
        assert loaded.run_count == 1
