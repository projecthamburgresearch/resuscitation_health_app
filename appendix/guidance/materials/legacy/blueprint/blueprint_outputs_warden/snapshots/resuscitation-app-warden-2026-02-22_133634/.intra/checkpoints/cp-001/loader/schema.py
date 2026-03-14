"""Pydantic models for the Blueprint workspace system.

Defines deploy targets, run metadata, and workspace configuration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Target types
# ---------------------------------------------------------------------------

class TargetType(str, Enum):
    """Source type for a deployment target."""
    LOCAL = "local"
    GITHUB = "github"


# ---------------------------------------------------------------------------
# Deploy target
# ---------------------------------------------------------------------------

class DeployTarget(BaseModel):
    """A single project/folder/file set to analyze."""
    type: TargetType = TargetType.LOCAL
    name: str = ""
    path: str = ""  # local filesystem path (absolute or relative to workspace)
    focus: Optional[str] = None  # subdirectory within the project
    files: List[str] = Field(default_factory=list)  # explicit file list
    include: List[str] = Field(default_factory=list)  # glob include patterns
    bpignore: bool = True  # respect .bpignore in project root

    # GitHub-specific
    repo: str = ""  # owner/repo
    ref: str = "main"  # branch, tag, or commit
    token_env: str = ""  # env var name holding the GitHub token


# ---------------------------------------------------------------------------
# Deploy config (the full deploy.yaml)
# ---------------------------------------------------------------------------

class DeployConfig(BaseModel):
    """Parsed deploy.yaml -- describes what to analyze and how."""
    version: str = "1.0"
    targets: List[DeployTarget] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=lambda: [
        "xray", "manifest", "cortex", "registry", "sonar", "synapse",
    ])
    preset: str = "standard"
    output: Dict[str, Any] = Field(default_factory=lambda: {
        "formats": ["json", "markdown"],
        "manifest_format": "yaml",
        "git_analysis": False,
    })
    # Warden configuration
    purpose: str = ""  # High-level purpose for warden guidance
    warden: Dict[str, Any] = Field(default_factory=lambda: {
        "auto_recover": True,
        "checkpoint_before_changes": True,
        "sync_after_run": True,
        "max_retries": 3,
    })


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------

class RunMeta(BaseModel):
    """Metadata for a single workspace run."""
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    project_name: str
    source_type: str = "local"
    source_path: str = ""
    domains_run: List[str] = Field(default_factory=list)
    preset: str = "standard"
    duration_seconds: float = 0.0
    blueprint_version: str = ""
    bpignore_patterns: List[str] = Field(default_factory=list)
    files_scanned: int = 0
    entities_found: int = 0
    edges_found: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    snapshot_id: Optional[str] = None  # ID of snapshot used for this run (if snapshot mode)


# ---------------------------------------------------------------------------
# Workspace config
# ---------------------------------------------------------------------------

class WorkspaceConfig(BaseModel):
    """Top-level workspace configuration."""
    workspace_root: str = "workspace"
    intake_dir: str = "workspace/intake"
    local_dir: str = "workspace/intake/local"
    results_dir: str = "workspace/results"
    control_dir: str = "workspace/control"
    deploy_file: str = "workspace/intake/deploy.yaml"
