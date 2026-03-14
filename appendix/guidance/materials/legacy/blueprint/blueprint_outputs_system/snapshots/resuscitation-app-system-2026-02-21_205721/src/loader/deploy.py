"""Deploy.yaml parser and target resolver.

Reads deploy.yaml files that describe what projects to analyze,
resolves local paths, and validates targets.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from src.loader.schema import DeployConfig, DeployTarget, TargetType


# ---------------------------------------------------------------------------
# Default deploy.yaml template
# ---------------------------------------------------------------------------

DEFAULT_DEPLOY_YAML = """\
# Blueprint Deploy Configuration
# Place projects in workspace/intake/local/ or reference paths here.
version: "1.0"

# Purpose: High-level goal for the warden (LLM operator)
# This helps guide autonomous decisions and prioritization.
# Example: "Security audit of authentication system"
# Example: "Analyze React components for accessibility issues"
purpose: ""

targets:
  # Local project example:
  # - type: local
  #   path: "./local/my-project"
  #   name: "my-project"
  #   bpignore: true
  #
  # Subfolder focus example:
  # - type: local
  #   path: "C:/Users/me/projects/my-app"
  #   name: "my-app-api"
  #   focus: "src/api"
  #
  # Specific files example:
  # - type: local
  #   path: "./local/my-project"
  #   name: "my-project-models"
  #   files:
  #     - "src/models/user.py"
  #     - "src/models/order.py"
  #
  # GitHub repo (public):
  # - type: github
  #   repo: "owner/repo-name"
  #   ref: "main"
  #   name: "repo-name"
  #
  # GitHub repo (private):
  # - type: github
  #   repo: "owner/private-repo"
  #   ref: "develop"
  #   token_env: "GITHUB_TOKEN"
  #   name: "private-repo"

# Which domains to run (default: all)
domains:
  - xray
  - manifest
  - sonar
  - synapse

# Analysis preset: quick | standard | deep
preset: "standard"

# Output preferences
output:
  formats:
    - json
    - markdown
  manifest_format: "yaml"
  git_analysis: false

# Warden (LLM operator) configuration
warden:
  auto_recover: true        # Automatically attempt error recovery
  checkpoint_before_changes: true  # Checkpoint before risky operations
  sync_after_run: true      # Auto-sync results to bundle after runs
  max_retries: 3            # Maximum retry attempts for failed operations
"""


def load_deploy_yaml(deploy_path: Path) -> DeployConfig:
    """Load and parse a deploy.yaml file.

    Args:
        deploy_path: Path to the deploy.yaml file.

    Returns:
        Parsed DeployConfig.

    Raises:
        FileNotFoundError: If deploy.yaml does not exist.
        ValueError: If the YAML is malformed or invalid.
    """
    if not deploy_path.is_file():
        raise FileNotFoundError(f"Deploy file not found: {deploy_path}")

    try:
        text = deploy_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot read deploy file: {exc}") from exc

    return parse_deploy_yaml(text)


def parse_deploy_yaml(text: str) -> DeployConfig:
    """Parse deploy.yaml content string into a DeployConfig.

    Args:
        text: Raw YAML text.

    Returns:
        Parsed DeployConfig.
    """
    data = yaml.safe_load(text)
    if not data or not isinstance(data, dict):
        return DeployConfig()

    # Parse targets
    targets: List[DeployTarget] = []
    raw_targets = data.get("targets", [])
    if isinstance(raw_targets, list):
        for t in raw_targets:
            if isinstance(t, dict):
                targets.append(DeployTarget(**t))

    # Parse domains
    domains = data.get("domains", DeployConfig().domains)
    if not isinstance(domains, list):
        domains = DeployConfig().domains

    # Parse preset
    preset = data.get("preset", "standard")
    if preset not in ("quick", "standard", "deep"):
        preset = "standard"

    # Parse output
    output = data.get("output", {})
    if not isinstance(output, dict):
        output = {}

    # Parse purpose
    purpose = data.get("purpose", "")
    if not isinstance(purpose, str):
        purpose = ""

    # Parse warden config
    warden = data.get("warden", {})
    if not isinstance(warden, dict):
        warden = {}

    return DeployConfig(
        version=str(data.get("version", "1.0")),
        targets=targets,
        domains=domains,
        preset=preset,
        output=output,
        purpose=purpose,
        warden=warden,
    )


def create_default_deploy(deploy_path: Path) -> None:
    """Write a default deploy.yaml template.

    Args:
        deploy_path: Where to create the file.
    """
    deploy_path.parent.mkdir(parents=True, exist_ok=True)
    deploy_path.write_text(DEFAULT_DEPLOY_YAML, encoding="utf-8")


def resolve_target_path(
    target: DeployTarget,
    workspace_root: Path,
) -> Optional[Path]:
    """Resolve a deploy target's path to an absolute filesystem path.

    Handles:
    - Absolute paths (used as-is)
    - Relative paths starting with ./ (relative to workspace/intake/)
    - Bare relative paths (relative to workspace/intake/local/)

    Args:
        target: The deploy target.
        workspace_root: Root of the workspace folder.

    Returns:
        Resolved absolute Path, or None if the target is a GitHub type
        that hasn't been cloned yet.
    """
    if target.type == TargetType.GITHUB:
        # GitHub targets get cloned into workspace/intake/local/<name>
        clone_dir = workspace_root / "intake" / "local" / (target.name or target.repo.split("/")[-1])
        if clone_dir.exists():
            return clone_dir.resolve()
        return None

    path_str = target.path
    if not path_str:
        return None

    path = Path(path_str)

    # Absolute path
    if path.is_absolute():
        return path.resolve()

    # Relative to workspace intake
    intake_path = workspace_root / "intake"
    resolved = (intake_path / path).resolve()
    if resolved.exists():
        return resolved

    # Try relative to workspace root
    resolved = (workspace_root / path).resolve()
    if resolved.exists():
        return resolved

    # Try relative to workspace/intake/local/
    local_path = (intake_path / "local" / path).resolve()
    if local_path.exists():
        return local_path

    # Return the intake-relative path even if it doesn't exist yet
    return (intake_path / path).resolve()


def resolve_all_targets(
    config: DeployConfig,
    workspace_root: Path,
) -> List[dict]:
    """Resolve all deploy targets to absolute paths with metadata.

    Args:
        config: The parsed deploy configuration.
        workspace_root: Root of the workspace folder.

    Returns:
        List of dicts with keys: name, path, target, resolved.
    """
    resolved = []
    for target in config.targets:
        path = resolve_target_path(target, workspace_root)
        name = target.name or (path.name if path else "unknown")
        resolved.append({
            "name": name,
            "path": path,
            "target": target,
            "resolved": path is not None and path.exists(),
        })
    return resolved


def auto_discover_local_targets(
    workspace_root: Path,
) -> List[DeployTarget]:
    """Auto-discover projects in workspace/intake/local/.

    Scans the local intake directory for subdirectories and creates
    DeployTargets for each one.

    Args:
        workspace_root: Root of the workspace folder.

    Returns:
        List of auto-discovered DeployTargets.
    """
    local_dir = workspace_root / "intake" / "local"
    if not local_dir.is_dir():
        return []

    targets: List[DeployTarget] = []
    for child in sorted(local_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            targets.append(DeployTarget(
                type=TargetType.LOCAL,
                name=child.name,
                path=str(child),
                bpignore=True,
            ))

    return targets
