"""Tests for deploy.yaml parsing and target resolution."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.loader.deploy import (
    auto_discover_local_targets,
    create_default_deploy,
    load_deploy_yaml,
    parse_deploy_yaml,
    resolve_all_targets,
    resolve_target_path,
)
from src.loader.schema import DeployConfig, DeployTarget, TargetType


class TestParseDeploy:
    def test_basic_parse(self):
        yaml_text = """
version: "1.0"
targets:
  - type: local
    path: "/home/user/project"
    name: "my-project"
domains:
  - xray
  - sonar
preset: "standard"
"""
        config = parse_deploy_yaml(yaml_text)
        assert config.version == "1.0"
        assert len(config.targets) == 1
        assert config.targets[0].name == "my-project"
        assert config.targets[0].type == TargetType.LOCAL
        assert "xray" in config.domains
        assert "sonar" in config.domains
        assert config.preset == "standard"

    def test_github_target(self):
        yaml_text = """
targets:
  - type: github
    repo: "owner/repo"
    ref: "main"
    name: "my-repo"
    token_env: "GITHUB_TOKEN"
"""
        config = parse_deploy_yaml(yaml_text)
        assert len(config.targets) == 1
        t = config.targets[0]
        assert t.type == TargetType.GITHUB
        assert t.repo == "owner/repo"
        assert t.ref == "main"
        assert t.token_env == "GITHUB_TOKEN"

    def test_focus_target(self):
        yaml_text = """
targets:
  - type: local
    path: "/home/user/project"
    name: "api-only"
    focus: "src/api"
"""
        config = parse_deploy_yaml(yaml_text)
        assert config.targets[0].focus == "src/api"

    def test_files_target(self):
        yaml_text = """
targets:
  - type: local
    path: "/home/user/project"
    name: "models"
    files:
      - "src/models/user.py"
      - "src/models/order.py"
"""
        config = parse_deploy_yaml(yaml_text)
        assert len(config.targets[0].files) == 2

    def test_include_patterns(self):
        yaml_text = """
targets:
  - type: local
    path: "/home/user/project"
    name: "python-only"
    include:
      - "**/*.py"
"""
        config = parse_deploy_yaml(yaml_text)
        assert "**/*.py" in config.targets[0].include

    def test_empty_yaml(self):
        config = parse_deploy_yaml("")
        assert len(config.targets) == 0
        assert len(config.domains) > 0  # defaults

    def test_invalid_preset_defaults(self):
        yaml_text = 'preset: "invalid"'
        config = parse_deploy_yaml(yaml_text)
        assert config.preset == "standard"

    def test_multiple_targets(self):
        yaml_text = """
targets:
  - type: local
    path: "/project1"
    name: "proj1"
  - type: local
    path: "/project2"
    name: "proj2"
  - type: github
    repo: "owner/repo"
    name: "repo"
"""
        config = parse_deploy_yaml(yaml_text)
        assert len(config.targets) == 3

    def test_output_config(self):
        yaml_text = """
output:
  formats:
    - json
  manifest_format: "json"
  git_analysis: true
"""
        config = parse_deploy_yaml(yaml_text)
        assert config.output.get("manifest_format") == "json"
        assert config.output.get("git_analysis") is True

    def test_bpignore_default_true(self):
        yaml_text = """
targets:
  - type: local
    path: "/project"
    name: "test"
"""
        config = parse_deploy_yaml(yaml_text)
        assert config.targets[0].bpignore is True

    def test_bpignore_explicit_false(self):
        yaml_text = """
targets:
  - type: local
    path: "/project"
    name: "test"
    bpignore: false
"""
        config = parse_deploy_yaml(yaml_text)
        assert config.targets[0].bpignore is False


class TestLoadDeploy:
    def test_load_from_file(self, tmp_path):
        deploy_file = tmp_path / "deploy.yaml"
        deploy_file.write_text("""
version: "1.0"
targets:
  - type: local
    path: "/project"
    name: "test"
preset: "quick"
""")
        config = load_deploy_yaml(deploy_file)
        assert config.preset == "quick"
        assert len(config.targets) == 1

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_deploy_yaml(tmp_path / "nonexistent.yaml")


class TestCreateDefault:
    def test_creates_file(self, tmp_path):
        deploy_path = tmp_path / "deploy.yaml"
        create_default_deploy(deploy_path)
        assert deploy_path.exists()
        content = deploy_path.read_text(encoding="utf-8")
        assert "version" in content
        assert "targets" in content

    def test_creates_parent_dirs(self, tmp_path):
        deploy_path = tmp_path / "subdir" / "deploy.yaml"
        create_default_deploy(deploy_path)
        assert deploy_path.exists()


class TestResolveTargetPath:
    def test_absolute_path(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        target = DeployTarget(type=TargetType.LOCAL, path=str(project), name="test")
        resolved = resolve_target_path(target, tmp_path)
        assert resolved == project.resolve()

    def test_relative_to_intake(self, tmp_path):
        # Create workspace structure
        local = tmp_path / "intake" / "local" / "my-project"
        local.mkdir(parents=True)
        target = DeployTarget(type=TargetType.LOCAL, path="./local/my-project", name="test")
        resolved = resolve_target_path(target, tmp_path)
        assert resolved is not None
        assert resolved.exists()

    def test_github_not_cloned(self, tmp_path):
        target = DeployTarget(type=TargetType.GITHUB, repo="owner/repo", name="repo")
        resolved = resolve_target_path(target, tmp_path)
        assert resolved is None  # Not cloned yet

    def test_github_already_cloned(self, tmp_path):
        clone_dir = tmp_path / "intake" / "local" / "repo"
        clone_dir.mkdir(parents=True)
        target = DeployTarget(type=TargetType.GITHUB, repo="owner/repo", name="repo")
        resolved = resolve_target_path(target, tmp_path)
        assert resolved is not None
        assert resolved.exists()

    def test_empty_path(self, tmp_path):
        target = DeployTarget(type=TargetType.LOCAL, path="", name="test")
        resolved = resolve_target_path(target, tmp_path)
        assert resolved is None


class TestAutoDiscover:
    def test_discover_projects(self, tmp_path):
        local = tmp_path / "intake" / "local"
        (local / "project-a").mkdir(parents=True)
        (local / "project-b").mkdir(parents=True)
        (local / ".hidden").mkdir(parents=True)  # Should be skipped

        targets = auto_discover_local_targets(tmp_path)
        names = [t.name for t in targets]
        assert "project-a" in names
        assert "project-b" in names
        assert ".hidden" not in names
        assert len(targets) == 2

    def test_empty_local(self, tmp_path):
        local = tmp_path / "intake" / "local"
        local.mkdir(parents=True)
        targets = auto_discover_local_targets(tmp_path)
        assert targets == []

    def test_no_local_dir(self, tmp_path):
        targets = auto_discover_local_targets(tmp_path)
        assert targets == []


class TestResolveAllTargets:
    def test_resolve_all(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        config = DeployConfig(targets=[
            DeployTarget(type=TargetType.LOCAL, path=str(project), name="test"),
        ])
        resolved = resolve_all_targets(config, tmp_path)
        assert len(resolved) == 1
        assert resolved[0]["resolved"] is True
        assert resolved[0]["name"] == "test"
