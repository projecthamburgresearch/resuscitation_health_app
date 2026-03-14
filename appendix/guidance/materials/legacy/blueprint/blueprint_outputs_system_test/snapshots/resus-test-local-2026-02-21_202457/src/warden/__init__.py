"""Warden - LLM operator system for Blueprint.

The Warden is an autonomous agent that operates Blueprint with guardrails.
It manages context, makes decisions, learns from errors, and maintains
a local commit trail for reverting changes.

Components:
- config: Configuration management (purpose, tool levers, limits)
- memory: Persistent memory across sessions
- decisions: Decision audit trail
- commits: Local version control
- engine: Core warden logic

Usage:
    from src.warden import WardenEngine

    warden = WardenEngine(workspace_path)
    warden.load()

    # Check if we can proceed
    can_boot, reason = warden.check_can_boot()

    # Make a decision
    warden.decide("analyze", "src/api/", "Critical business logic")

    # Handle errors
    warden.record_error("parser", "SyntaxError", "Unexpected token", "file.ts")

    # Save state
    warden.save()
"""

from src.warden.engine import WardenEngine
from src.warden.config import WardenConfig, load_warden_config, save_warden_config
from src.warden.memory import WardenMemory
from src.warden.decisions import DecisionLog
from src.warden.commits import CommitManager
from src.warden.commands import WardenCommands, CommandResult, handle_command

__all__ = [
    "WardenEngine",
    "WardenConfig",
    "load_warden_config",
    "save_warden_config",
    "WardenMemory",
    "DecisionLog",
    "CommitManager",
    "WardenCommands",
    "CommandResult",
    "handle_command",
]
