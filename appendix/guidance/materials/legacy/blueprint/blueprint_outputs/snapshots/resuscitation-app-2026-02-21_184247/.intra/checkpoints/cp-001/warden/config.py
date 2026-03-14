"""Warden configuration management.

Manages configuration for the Warden LLM operator including:
- Purpose statement from deploy.yaml
- Tool levers (which domains/features to enable)
- Context management settings
- Error recovery settings
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WardenConfig:
    """Configuration for the Warden operator.

    Attributes:
        purpose: The high-level goal from deploy.yaml (guides warden decisions)
        tool_levers: Which tools/domains are enabled {name: enabled}
        context_window: Estimated token limit for context
        auto_recover: Whether to automatically attempt error recovery
        max_retries: Maximum retry attempts for failed operations
        checkpoint_before_changes: Whether to checkpoint before risky operations
        sync_after_run: Whether to auto-sync to bundle after runs
        verbose: Whether to log detailed warden decisions
    """
    purpose: str = ""
    tool_levers: Dict[str, bool] = field(default_factory=lambda: {
        "xray": True,
        "manifest": True,
        "cortex": True,
        "registry": True,
        "sonar": True,
        "synapse": True,
    })
    context_window: int = 100000  # ~100k tokens default
    auto_recover: bool = True
    max_retries: int = 3
    checkpoint_before_changes: bool = True
    sync_after_run: bool = True
    verbose: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "purpose": self.purpose,
            "tool_levers": self.tool_levers,
            "context_window": self.context_window,
            "auto_recover": self.auto_recover,
            "max_retries": self.max_retries,
            "checkpoint_before_changes": self.checkpoint_before_changes,
            "sync_after_run": self.sync_after_run,
            "verbose": self.verbose,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WardenConfig":
        return cls(
            purpose=data.get("purpose", ""),
            tool_levers=data.get("tool_levers", cls().tool_levers),
            context_window=data.get("context_window", 100000),
            auto_recover=data.get("auto_recover", True),
            max_retries=data.get("max_retries", 3),
            checkpoint_before_changes=data.get("checkpoint_before_changes", True),
            sync_after_run=data.get("sync_after_run", True),
            verbose=data.get("verbose", False),
        )

    @classmethod
    def from_deploy(cls, deploy_data: Dict[str, Any]) -> "WardenConfig":
        """Create config from deploy.yaml data.

        Extracts purpose and domains to create appropriate configuration.
        """
        purpose = deploy_data.get("purpose", "")
        domains = deploy_data.get("domains", [])

        # Build tool levers from domains list
        all_domains = ["xray", "manifest", "cortex", "registry", "sonar", "synapse"]
        tool_levers = {}

        if domains:
            for domain in all_domains:
                tool_levers[domain] = domain in domains
        else:
            # If no domains specified, enable all
            tool_levers = {d: True for d in all_domains}

        return cls(
            purpose=purpose,
            tool_levers=tool_levers,
        )


def load_warden_config(warden_dir: Path) -> WardenConfig:
    """Load warden configuration from workspace/warden/config.json.

    Args:
        warden_dir: Path to workspace/warden/

    Returns:
        Loaded configuration or default if none exists.
    """
    config_file = warden_dir / "configs" / "active.json"

    if not config_file.exists():
        return WardenConfig()

    try:
        data = json.loads(config_file.read_text())
        return WardenConfig.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return WardenConfig()


def save_warden_config(config: WardenConfig, warden_dir: Path) -> None:
    """Save warden configuration to workspace/warden/config.json.

    Args:
        config: Configuration to save.
        warden_dir: Path to workspace/warden/
    """
    configs_dir = warden_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    config_file = configs_dir / "active.json"
    config_file.write_text(json.dumps(config.to_dict(), indent=2))


def merge_deploy_config(
    base_config: WardenConfig,
    deploy_data: Dict[str, Any],
) -> WardenConfig:
    """Merge deploy.yaml settings into existing config.

    Purpose from deploy.yaml takes precedence.
    Domains from deploy.yaml update tool_levers.

    Args:
        base_config: Existing warden configuration.
        deploy_data: Data from deploy.yaml.

    Returns:
        Merged configuration.
    """
    # Start with base
    merged = WardenConfig.from_dict(base_config.to_dict())

    # Override purpose if specified
    if deploy_data.get("purpose"):
        merged.purpose = deploy_data["purpose"]

    # Update tool levers if domains specified
    if deploy_data.get("domains"):
        domains = deploy_data["domains"]
        all_domains = ["xray", "manifest", "cortex", "registry", "sonar", "synapse"]
        for domain in all_domains:
            merged.tool_levers[domain] = domain in domains

    return merged
