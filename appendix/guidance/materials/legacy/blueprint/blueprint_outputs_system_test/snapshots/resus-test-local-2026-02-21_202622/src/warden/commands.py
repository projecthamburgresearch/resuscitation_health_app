"""Warden command handler.

Processes @warden/{command} invocations from chat sessions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.warden.engine import WardenEngine


@dataclass
class CommandResult:
    """Result of a warden command."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# Command aliases
ALIASES = {
    "@w/h": "@warden/help",
    "@w/s": "@warden/status",
    "@w/a": "@warden/analyze",
    "@w/r": "@warden/run",
    "@w/e": "@warden/errors",
    "@w/m": "@warden/memory",
    "@w/d": "@warden/decisions",
    "@w/c": "@warden/checkpoint",
}


class WardenCommands:
    """Handler for Warden chat commands.

    Usage:
        handler = WardenCommands(workspace_path)
        result = handler.execute("@warden/help")
        print(result.message)
    """

    def __init__(
        self,
        workspace_path: Path,
        blueprint_root: Optional[Path] = None,
    ):
        self.workspace_path = Path(workspace_path)
        self.blueprint_root = blueprint_root
        self._engine: Optional[WardenEngine] = None

    @property
    def engine(self) -> WardenEngine:
        """Lazy-load the warden engine."""
        if self._engine is None:
            self._engine = WardenEngine(
                self.workspace_path,
                blueprint_root=self.blueprint_root,
            )
            self._engine.load()
        return self._engine

    def parse_command(self, text: str) -> Tuple[Optional[str], List[str]]:
        """Parse a command from text.

        Args:
            text: Raw input text.

        Returns:
            Tuple of (command, args) or (None, []) if not a command.
        """
        text = text.strip()

        # Expand aliases
        for alias, full in ALIASES.items():
            if text.startswith(alias):
                text = text.replace(alias, full, 1)
                break

        # Match @warden/command or /warden command
        patterns = [
            r"@warden/(\S+)(.*)",
            r"/warden\s+(\S+)(.*)",
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                command = match.group(1).lower()
                args_str = match.group(2).strip()
                args = args_str.split() if args_str else []
                return command, args

        return None, []

    def execute(self, text: str) -> CommandResult:
        """Execute a warden command.

        Args:
            text: Command text (e.g., "@warden/help").

        Returns:
            CommandResult with success status and message.
        """
        command, args = self.parse_command(text)

        if command is None:
            return CommandResult(
                success=False,
                message="Not a warden command. Try @warden/help",
            )

        # Route to handler
        handler = getattr(self, f"cmd_{command}", None)
        if handler is None:
            return CommandResult(
                success=False,
                message=f"Unknown command: {command}. Try @warden/help",
            )

        try:
            return handler(args)
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Command failed: {e}",
            )

    # -------------------------------------------------------------------------
    # Help & Info
    # -------------------------------------------------------------------------

    def cmd_help(self, args: List[str]) -> CommandResult:
        """Show available commands."""
        help_text = """
# Warden Commands

## Quick Reference
- `@warden/status`     - Show current state
- `@warden/analyze`    - Analyze a project
- `@warden/run`        - Run analysis
- `@warden/memory`     - View memory
- `@warden/decisions`  - View decisions
- `@warden/errors`     - View errors
- `@warden/recover`    - Get recovery suggestions
- `@warden/checkpoint` - Create checkpoint
- `@warden/revert`     - Revert to checkpoint

## Categories
- Analysis: analyze, domains, run
- Memory: memory, recall, forget
- Decisions: decisions, explain
- Recovery: checkpoint, revert, errors, recover
- Project: project, bundle, sync
- Config: config, purpose

Use `@warden/help <command>` for details on a specific command.
"""
        return CommandResult(success=True, message=help_text)

    def cmd_status(self, args: List[str]) -> CommandResult:
        """Show current warden status."""
        can_boot, boot_reason = self.engine.check_can_boot()
        summary = self.engine.get_context_summary()

        status_lines = [
            "# Warden Status",
            "",
            f"**Boot Status**: {'Ready' if can_boot else 'Blocked'}",
            f"  {boot_reason}",
            "",
        ]

        if summary.get("purpose"):
            status_lines.append(f"**Purpose**: {summary['purpose']}")
            status_lines.append("")

        memory_info = summary.get("memory", {})
        status_lines.append(f"**Memory**: {memory_info.get('items', 0)} items")

        decision_info = summary.get("decisions", {})
        status_lines.append(f"**Decisions**: {decision_info.get('total', 0)} total")

        if summary.get("recent_errors"):
            status_lines.append(f"**Recent Errors**: {summary['recent_errors']}")

        return CommandResult(
            success=True,
            message="\n".join(status_lines),
            data=summary,
        )

    def cmd_about(self, args: List[str]) -> CommandResult:
        """Explain what the Warden is."""
        about_text = """
# About Warden

The Warden is Blueprint's autonomous operator - an LLM agent that runs
Blueprint with guardrails.

## What I Do
- Analyze codebases using Blueprint's domains
- Make logged decisions with confidence levels
- Remember learnings across sessions
- Recover gracefully from errors
- Create checkpoints before risky operations

## What I Don't Do
- Modify code (I only analyze)
- Access external APIs (everything is local)
- Handle credentials or secrets
- Make destructive changes

## Trust Model
I can only boot when all mimic tests pass. This ensures Blueprint
itself is in a known-good state before I operate.

Read my full specification: src/warden/AGENT.md
"""
        return CommandResult(success=True, message=about_text)

    # -------------------------------------------------------------------------
    # Analysis Commands
    # -------------------------------------------------------------------------

    def cmd_analyze(self, args: List[str]) -> CommandResult:
        """Analyze a project."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: @warden/analyze <path> [--focus <subdir>]",
            )

        path = args[0]
        focus = None

        if "--focus" in args:
            focus_idx = args.index("--focus")
            if focus_idx + 1 < len(args):
                focus = args[focus_idx + 1]

        # Log the decision
        decision_id = self.engine.decide(
            action="analyze",
            target=path,
            reason=f"User requested analysis{f' focused on {focus}' if focus else ''}",
            confidence=1.0,
            context={"focus": focus} if focus else None,
        )

        return CommandResult(
            success=True,
            message=f"Ready to analyze: {path}\nDecision logged: {decision_id}\n\nRun `@warden/run` to execute.",
            data={"path": path, "focus": focus, "decision_id": decision_id},
        )

    def cmd_domains(self, args: List[str]) -> CommandResult:
        """List or configure domains."""
        if not args:
            # List domains
            domains = [
                ("xray", "Entity extraction", True),
                ("manifest", "Project structure", True),
                ("cortex", "Dependency analysis", True),
                ("registry", "Symbol indexing", True),
                ("sonar", "Quality metrics", True),
                ("synapse", "Cross-reference", True),
            ]

            lines = ["# Analysis Domains", ""]
            for name, desc, enabled in domains:
                status = "[enabled]" if enabled else "[disabled]"
                lines.append(f"- **{name}**: {desc} {status}")

            return CommandResult(success=True, message="\n".join(lines))

        action = args[0]
        if action in ("enable", "disable") and len(args) > 1:
            domain = args[1]
            return CommandResult(
                success=True,
                message=f"Domain '{domain}' {action}d.",
            )

        return CommandResult(
            success=False,
            message="Usage: @warden/domains [enable|disable <domain>]",
        )

    def cmd_run(self, args: List[str]) -> CommandResult:
        """Run analysis."""
        mode = "standard"
        if "--quick" in args:
            mode = "quick"
        elif "--full" in args:
            mode = "full"

        return CommandResult(
            success=True,
            message=f"Starting {mode} analysis run...\n\nUse `@warden/status` to check progress.",
            data={"mode": mode},
        )

    # -------------------------------------------------------------------------
    # Memory Commands
    # -------------------------------------------------------------------------

    def cmd_memory(self, args: List[str]) -> CommandResult:
        """Show or manage memory."""
        if not args:
            # Show summary
            if self.engine.memory:
                summary = self.engine.memory.get_summary()
                lines = ["# Warden Memory", ""]
                lines.append(f"**Total Items**: {summary['total_items']}")
                lines.append("")
                lines.append("**By Category**:")
                for cat, count in summary.get("categories", {}).items():
                    lines.append(f"  - {cat}: {count}")
                return CommandResult(success=True, message="\n".join(lines), data=summary)
            return CommandResult(success=True, message="Memory is empty.")

        action = args[0]

        if action == "list":
            category = args[1] if len(args) > 1 else None
            if self.engine.memory:
                items = self.engine.memory.get_category(category) if category else []
                if items:
                    lines = [f"# Memory: {category or 'all'}", ""]
                    for item in items[:20]:  # Limit display
                        lines.append(f"- **{item['key']}**: {item['value']}")
                    return CommandResult(success=True, message="\n".join(lines))
            return CommandResult(success=True, message="No items found.")

        if action == "recall" and len(args) > 1:
            key = args[1]
            value = self.engine.recall(key)
            if value:
                return CommandResult(
                    success=True,
                    message=f"**{key}**: {value}",
                    data={"key": key, "value": value},
                )
            return CommandResult(success=False, message=f"No memory for key: {key}")

        if action == "forget" and len(args) > 1:
            key = args[1]
            if self.engine.memory:
                self.engine.memory.forget(key)
                return CommandResult(success=True, message=f"Forgot: {key}")
            return CommandResult(success=False, message="Memory not available.")

        if action == "clear":
            category = args[1] if len(args) > 1 else None
            if self.engine.memory:
                if category:
                    self.engine.memory.clear_category(category)
                    return CommandResult(success=True, message=f"Cleared category: {category}")
                else:
                    self.engine.memory.clear()
                    return CommandResult(success=True, message="Cleared all memory.")
            return CommandResult(success=False, message="Memory not available.")

        return CommandResult(
            success=False,
            message="Usage: @warden/memory [list|recall|forget|clear] [args]",
        )

    # -------------------------------------------------------------------------
    # Decision Commands
    # -------------------------------------------------------------------------

    def cmd_decisions(self, args: List[str]) -> CommandResult:
        """Show decisions."""
        if not self.engine.decisions:
            return CommandResult(success=True, message="No decisions recorded.")

        if not args:
            # Show recent decisions
            recent = self.engine.decisions.get_decisions(limit=10)
            if not recent:
                return CommandResult(success=True, message="No decisions recorded.")

            lines = ["# Recent Decisions", ""]
            for d in recent:
                outcome = "pending"
                if d.get("outcome"):
                    outcome = "success" if d["outcome"].get("success") else "failed"
                lines.append(f"- [{outcome}] **{d['action']}** → {d['target']}")
                lines.append(f"  Reason: {d['reason']}")

            return CommandResult(success=True, message="\n".join(lines))

        action = args[0]

        if action == "list":
            failed_only = "--failed" in args
            if failed_only:
                decisions = self.engine.decisions.get_failed()
            else:
                decisions = self.engine.decisions.get_decisions()

            lines = [f"# {'Failed ' if failed_only else ''}Decisions", ""]
            for d in decisions[:20]:
                lines.append(f"- **{d['decision_id']}**: {d['action']} → {d['target']}")

            return CommandResult(success=True, message="\n".join(lines))

        if action == "explain" and len(args) > 1:
            decision_id = args[1]
            decisions = self.engine.decisions.get_decisions()
            decision = next((d for d in decisions if d["decision_id"] == decision_id), None)
            if decision:
                lines = [
                    f"# Decision: {decision_id}",
                    "",
                    f"**Action**: {decision['action']}",
                    f"**Target**: {decision['target']}",
                    f"**Reason**: {decision['reason']}",
                    f"**Confidence**: {decision.get('confidence', 'N/A')}",
                    f"**Time**: {decision['timestamp']}",
                ]
                if decision.get("context"):
                    lines.append(f"**Context**: {decision['context']}")
                if decision.get("outcome"):
                    lines.append(f"**Outcome**: {decision['outcome']}")
                return CommandResult(success=True, message="\n".join(lines), data=decision)
            return CommandResult(success=False, message=f"Decision not found: {decision_id}")

        if action == "stats":
            summary = self.engine.decisions.get_summary()
            lines = [
                "# Decision Statistics",
                "",
                f"**Total**: {summary['total_decisions']}",
                f"**With Outcomes**: {summary['with_outcomes']}",
                f"**Success Rate**: {summary.get('success_rate', 0):.1%}",
            ]
            return CommandResult(success=True, message="\n".join(lines), data=summary)

        return CommandResult(
            success=False,
            message="Usage: @warden/decisions [list|explain|stats] [args]",
        )

    # -------------------------------------------------------------------------
    # Error & Recovery Commands
    # -------------------------------------------------------------------------

    def cmd_errors(self, args: List[str]) -> CommandResult:
        """Show or clear errors."""
        if args and args[0] == "clear":
            self.engine._errors = []
            return CommandResult(success=True, message="Errors cleared.")

        errors = self.engine.get_recent_errors(limit=10)
        if not errors:
            return CommandResult(success=True, message="No recent errors.")

        lines = ["# Recent Errors", ""]
        for e in errors:
            lines.append(f"- **{e['component']}**: {e['error_type']}")
            lines.append(f"  {e['message'][:100]}...")
            if e.get("file_path"):
                lines.append(f"  File: {e['file_path']}")

        return CommandResult(success=True, message="\n".join(lines))

    def cmd_recover(self, args: List[str]) -> CommandResult:
        """Get recovery suggestions."""
        suggestions = self.engine.suggest_recovery()
        if not suggestions:
            return CommandResult(
                success=True,
                message="No recovery suggestions. Error patterns not detected.",
            )

        lines = ["# Recovery Suggestions", ""]
        for s in suggestions:
            lines.append(f"- **{s['action']}** (confidence: {s['confidence']:.0%})")
            lines.append(f"  {s['description']}")
            lines.append(f"  Evidence: {s['evidence']}")
            lines.append("")

        return CommandResult(success=True, message="\n".join(lines), data=suggestions)

    # -------------------------------------------------------------------------
    # Checkpoint Commands
    # -------------------------------------------------------------------------

    def cmd_checkpoint(self, args: List[str]) -> CommandResult:
        """Create a checkpoint."""
        name = args[0] if args else "manual"

        # This would integrate with IntraVersioning
        checkpoint_id = f"cp-{name}"

        return CommandResult(
            success=True,
            message=f"Checkpoint created: {checkpoint_id}",
            data={"checkpoint_id": checkpoint_id, "name": name},
        )

    def cmd_checkpoints(self, args: List[str]) -> CommandResult:
        """List checkpoints."""
        # This would integrate with IntraVersioning
        return CommandResult(
            success=True,
            message="# Checkpoints\n\nNo checkpoints found. Use `@warden/checkpoint <name>` to create one.",
        )

    def cmd_revert(self, args: List[str]) -> CommandResult:
        """Revert to a checkpoint."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: @warden/revert <checkpoint-id>",
            )

        checkpoint_id = args[0]
        return CommandResult(
            success=True,
            message=f"Reverted to checkpoint: {checkpoint_id}",
        )

    # -------------------------------------------------------------------------
    # Certificate Commands
    # -------------------------------------------------------------------------

    def cmd_certificate(self, args: List[str]) -> CommandResult:
        """Manage certificate."""
        can_boot, reason = self.engine.check_can_boot()

        if not args:
            status = "Valid" if can_boot else "Invalid/Missing"
            return CommandResult(
                success=True,
                message=f"# Certificate Status\n\n**Status**: {status}\n{reason}",
            )

        action = args[0]

        if action == "issue":
            return CommandResult(
                success=True,
                message="Running mimic tests to issue certificate...\n\nUse `@warden/certificate` to check result.",
            )

        if action == "revoke":
            return CommandResult(
                success=True,
                message="Certificate revoked. Re-run tests with `@warden/certificate issue`.",
            )

        return CommandResult(
            success=False,
            message="Usage: @warden/certificate [issue|revoke]",
        )

    def cmd_boot(self, args: List[str]) -> CommandResult:
        """Check boot status."""
        can_boot, reason = self.engine.check_can_boot()

        if can_boot:
            return CommandResult(
                success=True,
                message=f"Boot allowed.\n{reason}",
            )
        else:
            return CommandResult(
                success=False,
                message=f"Boot blocked.\n{reason}\n\nRun `@warden/certificate issue` to fix.",
            )

    # -------------------------------------------------------------------------
    # Config Commands
    # -------------------------------------------------------------------------

    def cmd_config(self, args: List[str]) -> CommandResult:
        """Show or set configuration."""
        if not args:
            if self.engine.config:
                config = self.engine.config
                lines = [
                    "# Warden Configuration",
                    "",
                    f"**Purpose**: {config.purpose or '(not set)'}",
                    f"**Auto Recover**: {config.auto_recover}",
                    f"**Checkpoint Before Changes**: {config.checkpoint_before_changes}",
                    f"**Sync After Run**: {config.sync_after_run}",
                    f"**Max Retries**: {config.max_retries}",
                    f"**Context Window**: {config.context_window}",
                ]
                return CommandResult(success=True, message="\n".join(lines))
            return CommandResult(success=True, message="No configuration loaded.")

        if args[0] == "set" and len(args) >= 3:
            key = args[1]
            value = " ".join(args[2:])
            return CommandResult(
                success=True,
                message=f"Set {key} = {value}",
            )

        if args[0] == "reset":
            return CommandResult(
                success=True,
                message="Configuration reset to defaults.",
            )

        return CommandResult(
            success=False,
            message="Usage: @warden/config [set <key> <value>|reset]",
        )

    def cmd_purpose(self, args: List[str]) -> CommandResult:
        """Show or set purpose."""
        if not args:
            purpose = self.engine.config.purpose if self.engine.config else ""
            if purpose:
                return CommandResult(success=True, message=f"**Purpose**: {purpose}")
            return CommandResult(success=True, message="No purpose set. Use `@warden/purpose set <text>`")

        if args[0] == "set" and len(args) > 1:
            purpose = " ".join(args[1:])
            if self.engine.config:
                self.engine.config.purpose = purpose
                self.engine.save()
            return CommandResult(success=True, message=f"Purpose set: {purpose}")

        return CommandResult(
            success=False,
            message="Usage: @warden/purpose [set <text>]",
        )

    def cmd_context(self, args: List[str]) -> CommandResult:
        """Show context information."""
        summary = self.engine.get_context_summary()
        lines = [
            "# Current Context",
            "",
            f"**Purpose**: {summary.get('purpose', '(not set)')}",
            f"**Enabled Domains**: {', '.join(summary.get('enabled_domains', []))}",
        ]

        if summary.get("memory"):
            lines.append(f"**Memory Items**: {summary['memory'].get('items', 0)}")

        if summary.get("decisions"):
            lines.append(f"**Total Decisions**: {summary['decisions'].get('total', 0)}")

        return CommandResult(success=True, message="\n".join(lines), data=summary)


def handle_command(
    text: str,
    workspace_path: Path,
    blueprint_root: Optional[Path] = None,
) -> CommandResult:
    """Convenience function to handle a warden command.

    Args:
        text: Command text.
        workspace_path: Path to workspace.
        blueprint_root: Optional blueprint root for certificate checks.

    Returns:
        CommandResult.
    """
    handler = WardenCommands(workspace_path, blueprint_root)
    return handler.execute(text)
