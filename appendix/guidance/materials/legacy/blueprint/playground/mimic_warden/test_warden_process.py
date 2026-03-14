"""Mimic tests for the warden system process.

These tests simulate the warden (LLM operator) workflow:
1. Warden configuration
2. Memory persistence
3. Decision audit trail
4. Context management
5. Error recovery
6. Local commit tracking

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
from pathlib import Path
from datetime import datetime

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestWardenConfiguration:
    """Test warden configuration management."""

    def test_load_default_config(self, tmp_path):
        """Warden should load default configuration."""
        from src.warden.config import WardenConfig, load_warden_config

        workspace = tmp_path / "workspace" / "warden" / "configs"
        workspace.mkdir(parents=True)

        config = load_warden_config(workspace.parent)

        assert config is not None
        assert config.purpose == ""
        assert "xray" in config.tool_levers
        assert config.auto_recover is True

    def test_save_and_load_config(self, tmp_path):
        """Warden config should persist."""
        from src.warden.config import WardenConfig, save_warden_config, load_warden_config

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        config = WardenConfig(
            purpose="Analyze React components for accessibility issues",
            tool_levers={"xray": True, "sonar": True, "synapse": False},
            context_window=50000,
            auto_recover=True,
            max_retries=3,
        )

        save_warden_config(config, workspace)
        loaded = load_warden_config(workspace)

        assert loaded.purpose == "Analyze React components for accessibility issues"
        assert loaded.tool_levers["synapse"] is False
        assert loaded.max_retries == 3

    def test_config_from_deploy_yaml(self, tmp_path):
        """Warden should read purpose from deploy.yaml."""
        from src.warden.config import WardenConfig

        deploy_yaml = {
            "purpose": "Security audit of authentication module",
            "domains": ["xray", "sonar"],
            "preset": "deep",
        }

        config = WardenConfig.from_deploy(deploy_yaml)

        assert config.purpose == "Security audit of authentication module"
        assert config.tool_levers["xray"] is True
        assert config.tool_levers["synapse"] is False  # Not in domains


class TestWardenMemory:
    """Test warden memory persistence."""

    def test_memory_save_and_load(self, tmp_path):
        """Warden memory should persist across sessions."""
        from src.warden.memory import WardenMemory

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        memory = WardenMemory(workspace)

        # Record some learnings
        memory.remember(
            key="parser_fix_ts",
            value="TypeScript parser needs --jsx flag for .tsx files",
            category="learnings",
        )
        memory.remember(
            key="project_structure",
            value="Uses monorepo with packages/",
            category="context",
        )

        memory.save()

        # Load in new instance
        memory2 = WardenMemory(workspace)
        memory2.load()

        assert memory2.recall("parser_fix_ts") == "TypeScript parser needs --jsx flag for .tsx files"
        assert memory2.recall("project_structure") == "Uses monorepo with packages/"

    def test_memory_categories(self, tmp_path):
        """Memory should organize by categories."""
        from src.warden.memory import WardenMemory

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        memory = WardenMemory(workspace)

        memory.remember("fix1", "Fixed parser", "learnings")
        memory.remember("fix2", "Another fix", "learnings")
        memory.remember("ctx1", "Project uses React", "context")

        learnings = memory.get_category("learnings")
        assert len(learnings) == 2

        context = memory.get_category("context")
        assert len(context) == 1

    def test_memory_for_context_limit(self, tmp_path):
        """Memory should support context window management."""
        from src.warden.memory import WardenMemory

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        memory = WardenMemory(workspace)

        # Add items with estimated token counts
        for i in range(10):
            memory.remember(
                key=f"item_{i}",
                value=f"This is memory item {i} with some content",
                category="context",
                estimated_tokens=100,
            )

        # Get context within limit
        context = memory.get_context_for_limit(token_limit=500)

        # Should return most recent items that fit
        assert len(context) <= 5  # 5 items * 100 tokens = 500


class TestWardenDecisions:
    """Test warden decision audit trail."""

    def test_record_decision(self, tmp_path):
        """Warden should record decisions."""
        from src.warden.decisions import DecisionLog

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        log = DecisionLog(workspace)

        decision_id = log.record(
            action="skip_file",
            target="node_modules/",
            reason="Standard exclusion pattern",
            confidence=1.0,
        )

        assert decision_id is not None

        decisions = log.get_decisions()
        assert len(decisions) == 1
        assert decisions[0]["action"] == "skip_file"

    def test_decision_audit_trail(self, tmp_path):
        """Decisions should form an audit trail."""
        from src.warden.decisions import DecisionLog

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        log = DecisionLog(workspace)

        # Make a series of decisions
        log.record("analyze", "src/", "Main source directory", 0.9)
        log.record("skip", "dist/", "Build output", 1.0)
        log.record("deep_scan", "src/auth/", "Security-critical code", 0.8)

        log.save()

        # Reload
        log2 = DecisionLog(workspace)
        log2.load()

        decisions = log2.get_decisions()
        assert len(decisions) == 3

        # Check chronological order
        assert decisions[0]["action"] == "analyze"
        assert decisions[2]["action"] == "deep_scan"

    def test_decision_with_outcome(self, tmp_path):
        """Decisions should track outcomes."""
        from src.warden.decisions import DecisionLog

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        log = DecisionLog(workspace)

        decision_id = log.record(
            action="retry_parse",
            target="complex.tsx",
            reason="Initial parse failed",
            confidence=0.6,
        )

        # Record outcome
        log.record_outcome(
            decision_id=decision_id,
            success=True,
            result={"entities": 45, "edges": 120},
        )

        decisions = log.get_decisions()
        decision = next(d for d in decisions if d["id"] == decision_id)

        assert decision["outcome"]["success"] is True
        assert decision["outcome"]["result"]["entities"] == 45


class TestWardenErrorRecovery:
    """Test warden error recovery capabilities."""

    def test_record_error(self, tmp_path):
        """Warden should record errors for learning."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)

        engine = WardenEngine(workspace)

        engine.record_error(
            component="typescript_parser",
            error_type="SyntaxError",
            message="Unexpected token",
            file_path="src/broken.ts",
            context={"line": 42},
        )

        errors = engine.get_recent_errors()
        assert len(errors) == 1
        assert errors[0]["component"] == "typescript_parser"

    def test_suggest_recovery_action(self, tmp_path):
        """Warden should suggest recovery actions."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)

        engine = WardenEngine(workspace)

        # Record a pattern of errors
        for i in range(3):
            engine.record_error(
                component="jsx_parser",
                error_type="SyntaxError",
                message="JSX not enabled",
                file_path=f"src/component{i}.tsx",
            )

        # Should suggest enabling JSX
        suggestions = engine.suggest_recovery()

        assert len(suggestions) > 0
        # Pattern recognition should trigger suggestion


class TestWardenCommits:
    """Test warden local commit tracking."""

    def test_create_local_commit(self, tmp_path):
        """Warden should create local commits."""
        from src.warden.commits import CommitManager

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        manager = CommitManager(workspace)

        commit_id = manager.create_commit(
            message="Added TypeScript support",
            changes=[
                {"file": "src/xray/parser.py", "type": "modify"},
                {"file": "src/xray/ts_parser.py", "type": "add"},
            ],
        )

        assert commit_id is not None

        commits = manager.get_commits()
        assert len(commits) == 1
        assert commits[0]["message"] == "Added TypeScript support"

    def test_commit_revert(self, tmp_path):
        """Warden should support reverting commits."""
        from src.warden.commits import CommitManager

        workspace = tmp_path / "workspace" / "warden"
        workspace.mkdir(parents=True)

        manager = CommitManager(workspace)

        # Create commits
        c1 = manager.create_commit("First change", [])
        c2 = manager.create_commit("Second change", [])
        c3 = manager.create_commit("Third change", [])

        # Revert to c1
        success = manager.revert_to(c1)

        assert success

        # Check revert was recorded
        commits = manager.get_commits()
        revert_commits = [c for c in commits if "Revert" in c.get("message", "")]
        assert len(revert_commits) >= 1


class TestWardenIntegration:
    """Test warden integration with other systems."""

    def test_warden_checkpoint_before_run(self, tmp_path):
        """Warden should create checkpoint before risky operations."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)
        snapshot_dir = workspace / "snapshots" / "test-snap"
        (snapshot_dir / "src").mkdir(parents=True)
        (snapshot_dir / "src" / "mod.py").write_text("original")

        engine = WardenEngine(workspace)

        # Before risky operation
        checkpoint_id = engine.checkpoint_before_operation(
            operation="deep_refactor",
            snapshot_dir=snapshot_dir,
        )

        assert checkpoint_id is not None

    def test_warden_respects_certificate(self, tmp_path):
        """Warden should check certificate before operations."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)
        blueprint_root = tmp_path / "blueprint"
        (blueprint_root / "src").mkdir(parents=True)
        (blueprint_root / "playground").mkdir()
        (blueprint_root / "workspace" / "status" / "certificate").mkdir(parents=True)

        engine = WardenEngine(workspace, blueprint_root=blueprint_root)

        # Should block without certificate
        can_proceed, reason = engine.check_can_boot()

        assert can_proceed is False
        assert "certificate" in reason.lower()


class TestWardenContextManagement:
    """Test warden context window management."""

    def test_summarize_for_context(self, tmp_path):
        """Warden should summarize data for context limits."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)

        engine = WardenEngine(workspace)

        # Large analysis result
        result = {
            "entities": [{"name": f"Entity{i}"} for i in range(1000)],
            "edges": [{"from": i, "to": i + 1} for i in range(5000)],
        }

        summary = engine.summarize_for_context(result, max_tokens=500)

        # Summary should be much smaller
        assert len(json.dumps(summary)) < len(json.dumps(result))
        assert "entity_count" in summary or "entities" in summary

    def test_prioritize_context(self, tmp_path):
        """Warden should prioritize what goes in context."""
        from src.warden.engine import WardenEngine

        workspace = tmp_path / "workspace"
        (workspace / "warden").mkdir(parents=True)

        engine = WardenEngine(workspace)

        context_items = [
            {"type": "error", "content": "Parse failed", "priority": 10},
            {"type": "result", "content": "Analysis complete", "priority": 5},
            {"type": "hint", "content": "Consider refactoring", "priority": 2},
        ]

        prioritized = engine.prioritize_context(context_items, max_items=2)

        # Should get highest priority items
        assert len(prioritized) == 2
        assert prioritized[0]["type"] == "error"
        assert prioritized[1]["type"] == "result"
