"""Tests for the workspace runner orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.loader.runner import run_target, run_workspace
from src.loader.schema import DeployConfig, DeployTarget, RunMeta, TargetType


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal sample project for testing."""
    project = tmp_path / "intake" / "local" / "sample"
    project.mkdir(parents=True)

    # Create a simple Python file
    (project / "main.py").write_text(
        'def hello():\n    return "Hello, World!"\n\ndef main():\n    print(hello())\n',
        encoding="utf-8",
    )
    (project / "utils.py").write_text(
        'def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n',
        encoding="utf-8",
    )

    # Results directory
    (tmp_path / "results").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def sample_project_with_bpignore(sample_project):
    """Sample project with a .bpignore file."""
    project = sample_project / "intake" / "local" / "sample"
    (project / ".bpignore").write_text(
        "# Ignore test files\n*.test.py\ntmp/\n",
        encoding="utf-8",
    )
    # Create a file that should be ignored
    (project / "test_ignore.test.py").write_text("# should be ignored\n")
    return sample_project


class TestRunTarget:
    def test_run_local_target(self, sample_project):
        target = DeployTarget(
            type=TargetType.LOCAL,
            path=str(sample_project / "intake" / "local" / "sample"),
            name="sample",
        )
        meta = run_target(
            target=target,
            workspace_root=sample_project,
            domains=["xray"],
            preset="quick",
        )
        assert isinstance(meta, RunMeta)
        assert meta.project_name == "sample"
        assert "xray" in meta.domains_run
        assert meta.files_scanned > 0
        assert meta.entities_found > 0

    def test_run_nonexistent_target(self, sample_project):
        target = DeployTarget(
            type=TargetType.LOCAL,
            path="/nonexistent/path",
            name="missing",
        )
        meta = run_target(
            target=target,
            workspace_root=sample_project,
            domains=["xray"],
        )
        assert len(meta.errors) > 0

    def test_run_with_bpignore(self, sample_project_with_bpignore):
        target = DeployTarget(
            type=TargetType.LOCAL,
            path=str(sample_project_with_bpignore / "intake" / "local" / "sample"),
            name="sample",
            bpignore=True,
        )
        meta = run_target(
            target=target,
            workspace_root=sample_project_with_bpignore,
            domains=["xray"],
            preset="quick",
        )
        assert meta.bpignore_patterns == ["*.test.py", "tmp/"]

    def test_run_creates_output(self, sample_project):
        target = DeployTarget(
            type=TargetType.LOCAL,
            path=str(sample_project / "intake" / "local" / "sample"),
            name="sample",
        )
        meta = run_target(
            target=target,
            workspace_root=sample_project,
            domains=["xray"],
            preset="quick",
        )
        results_dir = sample_project / "results" / "sample" / meta.run_id
        assert results_dir.exists()
        assert (results_dir / "run_meta.json").exists()

        # Verify run_meta.json is valid JSON
        meta_data = json.loads(
            (results_dir / "run_meta.json").read_text(encoding="utf-8")
        )
        assert meta_data["project_name"] == "sample"

    def test_run_with_focus(self, tmp_path):
        # Create project with subdirectories
        project = tmp_path / "intake" / "local" / "multi"
        (project / "src" / "api").mkdir(parents=True)
        (project / "src" / "web").mkdir(parents=True)
        (tmp_path / "results").mkdir(parents=True)

        (project / "src" / "api" / "handler.py").write_text(
            "def handle():\n    pass\n"
        )
        (project / "src" / "web" / "view.py").write_text(
            "def render():\n    pass\n"
        )

        target = DeployTarget(
            type=TargetType.LOCAL,
            path=str(project),
            name="multi-api",
            focus="src/api",
        )
        meta = run_target(
            target=target,
            workspace_root=tmp_path,
            domains=["xray"],
            preset="quick",
        )
        assert meta.project_name == "multi-api"
        # Should only scan api files, not web files
        assert meta.files_scanned >= 1

    def test_run_multiple_domains(self, sample_project):
        target = DeployTarget(
            type=TargetType.LOCAL,
            path=str(sample_project / "intake" / "local" / "sample"),
            name="sample",
        )
        meta = run_target(
            target=target,
            workspace_root=sample_project,
            domains=["xray", "sonar", "synapse"],
            preset="quick",
        )
        assert "xray" in meta.domains_run
        assert "sonar" in meta.domains_run
        assert "synapse" in meta.domains_run


class TestRunWorkspace:
    def test_auto_discover_and_run(self, sample_project):
        results = run_workspace(
            workspace_root=sample_project,
            domain_filter=["xray"],
        )
        assert len(results) >= 1
        assert results[0].project_name == "sample"

    def test_target_filter(self, sample_project):
        # Create a second project
        project2 = sample_project / "intake" / "local" / "other"
        project2.mkdir(parents=True)
        (project2 / "app.py").write_text("x = 1\n")

        results = run_workspace(
            workspace_root=sample_project,
            target_filter="sample",
            domain_filter=["xray"],
        )
        assert len(results) == 1
        assert results[0].project_name == "sample"

    def test_empty_workspace(self, tmp_path):
        (tmp_path / "intake" / "local").mkdir(parents=True)
        (tmp_path / "results").mkdir(parents=True)
        results = run_workspace(workspace_root=tmp_path, domain_filter=["xray"])
        assert results == []

    def test_with_deploy_config(self, sample_project):
        config = DeployConfig(
            targets=[
                DeployTarget(
                    type=TargetType.LOCAL,
                    path=str(sample_project / "intake" / "local" / "sample"),
                    name="custom-name",
                ),
            ],
            domains=["xray"],
            preset="quick",
        )
        results = run_workspace(
            workspace_root=sample_project,
            deploy_config=config,
        )
        assert len(results) == 1
        assert results[0].project_name == "custom-name"
