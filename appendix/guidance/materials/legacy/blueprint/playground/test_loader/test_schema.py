"""Tests for workspace schema models."""

from __future__ import annotations

from datetime import datetime

from src.loader.schema import (
    DeployConfig,
    DeployTarget,
    RunMeta,
    TargetType,
    WorkspaceConfig,
)


class TestDeployTarget:
    def test_default_values(self):
        t = DeployTarget()
        assert t.type == TargetType.LOCAL
        assert t.name == ""
        assert t.bpignore is True
        assert t.files == []
        assert t.include == []
        assert t.ref == "main"

    def test_local_target(self):
        t = DeployTarget(type=TargetType.LOCAL, path="/project", name="proj")
        assert t.type == TargetType.LOCAL
        assert t.path == "/project"
        assert t.name == "proj"

    def test_github_target(self):
        t = DeployTarget(
            type=TargetType.GITHUB,
            repo="owner/repo",
            ref="develop",
            token_env="GH_TOKEN",
            name="my-repo",
        )
        assert t.type == TargetType.GITHUB
        assert t.repo == "owner/repo"
        assert t.ref == "develop"
        assert t.token_env == "GH_TOKEN"

    def test_target_with_focus(self):
        t = DeployTarget(path="/project", focus="src/api", name="api")
        assert t.focus == "src/api"

    def test_target_with_files(self):
        t = DeployTarget(path="/project", files=["a.py", "b.py"], name="models")
        assert len(t.files) == 2


class TestDeployConfig:
    def test_default_config(self):
        c = DeployConfig()
        assert c.version == "1.0"
        assert len(c.targets) == 0
        assert len(c.domains) > 0
        assert c.preset == "standard"

    def test_custom_config(self):
        c = DeployConfig(
            targets=[DeployTarget(path="/p", name="test")],
            domains=["xray", "sonar"],
            preset="quick",
        )
        assert len(c.targets) == 1
        assert c.domains == ["xray", "sonar"]
        assert c.preset == "quick"


class TestRunMeta:
    def test_creation(self):
        meta = RunMeta(
            run_id="2026-02-04_120000",
            project_name="test-project",
            domains_run=["xray", "sonar"],
            files_scanned=42,
            entities_found=100,
        )
        assert meta.run_id == "2026-02-04_120000"
        assert meta.project_name == "test-project"
        assert meta.files_scanned == 42

    def test_json_serializable(self):
        meta = RunMeta(
            run_id="test",
            project_name="proj",
        )
        data = meta.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["run_id"] == "test"

    def test_default_values(self):
        meta = RunMeta(run_id="test", project_name="proj")
        assert meta.source_type == "local"
        assert meta.duration_seconds == 0.0
        assert meta.errors == []


class TestWorkspaceConfig:
    def test_default_paths(self):
        wc = WorkspaceConfig()
        assert wc.workspace_root == "workspace"
        assert wc.intake_dir == "workspace/intake"
        assert wc.results_dir == "workspace/results"
        assert wc.control_dir == "workspace/control"


class TestTargetType:
    def test_values(self):
        assert TargetType.LOCAL.value == "local"
        assert TargetType.GITHUB.value == "github"
