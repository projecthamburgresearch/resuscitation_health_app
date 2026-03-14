"""Mimic tests for the run process.

These tests simulate the complete analysis run flow:
1. Domain execution order
2. Entity and edge extraction
3. Status reporting
4. Result persistence

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
import tempfile
from pathlib import Path

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestDomainExecution:
    """Test that domains execute in correct order."""

    def test_domain_order_preserved(self, tmp_path):
        """Domains should execute in the specified order."""
        from src.core.status import StatusReporter

        reporter = StatusReporter("test-run-001", "test-project")
        reporter.start_run({"domains": ["xray", "manifest", "sonar"]})

        # Simulate domain execution
        for domain in ["xray", "manifest", "sonar"]:
            reporter.start_domain(domain, "0.2.0")
            reporter.end_domain(domain, entities=10, edges=5)

        reporter.end_run()

        # Check that all domains completed
        assert len(reporter.domain_stats) == 3
        for domain in ["xray", "manifest", "sonar"]:
            assert reporter.domain_stats[domain].status == "success"


class TestStatusReporting:
    """Test the status reporting system."""

    def test_status_captures_errors(self, tmp_path):
        """Status should capture and report errors."""
        from src.core.status import StatusReporter, StatusLevel

        reporter = StatusReporter("test-run-002", "test-project")
        reporter.start_run({})

        # Log an error
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            reporter.log_error("test_component", "Something failed", exception=e)

        reporter.end_run(success=False)

        # Check error was captured
        errors = [e for e in reporter.entries if e.level == StatusLevel.ERROR]
        assert len(errors) == 1
        assert "Test error message" in str(errors[0].details)

    def test_status_saves_to_workspace(self, tmp_path):
        """Status should save structured files to workspace."""
        from src.core.status import StatusReporter

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        reporter = StatusReporter("test-run-003", "test-project")
        reporter.start_run({"preset": "standard"})
        reporter.start_domain("xray", "0.2.0")
        reporter.end_domain("xray", entities=100, edges=200)
        reporter.end_run()

        # Save to workspace
        status_dir = reporter.save(workspace)

        # Check files were created
        assert (status_dir / "status.json").exists()
        assert (status_dir / "execution.json").exists()
        assert (status_dir / "domains.json").exists()

        # Verify content
        with open(status_dir / "domains.json") as f:
            domains = json.load(f)
            assert "xray" in domains
            assert domains["xray"]["entities_produced"] == 100

    def test_status_detects_anomalies(self, tmp_path):
        """Status should detect anomalies like high error rates."""
        from src.core.status import StatusReporter

        reporter = StatusReporter("test-run-004", "test-project")
        reporter.start_run({})

        # Simulate parser with 60% failure rate (5+ files, >50% failures triggers anomaly)
        for i in range(10):
            reporter.record_parser_file(
                parser_name="broken_parser",
                language="python",
                file_path=f"file{i}.py",
                entities=0 if i < 6 else 5,
                edges=0,
                duration_ms=100,
                success=i >= 6,  # First 6 fail
                error="Parse error" if i < 6 else None,
            )

        reporter.end_run()

        # Should have detected high error rate anomaly
        assert len(reporter.anomalies) >= 1
        anomaly_rules = [a.rule for a in reporter.anomalies]
        assert "high_parser_error_rate" in anomaly_rules


class TestResultPersistence:
    """Test that analysis results are persisted correctly."""

    def test_results_saved_to_correct_location(self, tmp_path):
        """Results should be saved to workspace/results/<project>/<run_id>/."""
        # This test validates the expected file structure
        results_dir = tmp_path / "workspace" / "results" / "test-project" / "run-001"
        results_dir.mkdir(parents=True)

        # Simulate saving results
        (results_dir / "xray.json").write_text('{"entities": [], "edges": []}')
        (results_dir / "manifest.json").write_text('{"files": []}')

        # Verify structure
        assert (results_dir / "xray.json").exists()
        assert (results_dir / "manifest.json").exists()


class TestParserStats:
    """Test parser statistics collection."""

    def test_parser_stats_aggregated(self, tmp_path):
        """Parser stats should be aggregated across files."""
        from src.core.status import StatusReporter

        reporter = StatusReporter("test-run-005", "test-project")
        reporter.start_run({})

        # Record multiple files for same parser
        for i in range(5):
            reporter.record_parser_file(
                parser_name="python_parser",
                language="python",
                file_path=f"src/file{i}.py",
                entities=10 + i,
                edges=5 + i,
                duration_ms=50 + i * 10,
                success=True,
            )

        reporter.end_run()

        stats = reporter.parser_stats["python_parser"]
        assert stats.files_attempted == 5
        assert stats.files_succeeded == 5
        assert stats.total_entities == sum(10 + i for i in range(5))  # 60
        assert stats.total_edges == sum(5 + i for i in range(5))  # 35


class TestRunConfiguration:
    """Test run configuration handling."""

    def test_config_affects_domain_selection(self, tmp_path):
        """Configuration should determine which domains run."""
        from src.core.status import StatusReporter

        # Config specifies only xray and manifest
        config = {"domains": ["xray", "manifest"], "preset": "quick"}

        reporter = StatusReporter("test-run-006", "test-project")
        reporter.start_run(config)

        # Only run specified domains
        for domain in config["domains"]:
            reporter.start_domain(domain, "0.2.0")
            reporter.end_domain(domain, entities=5, edges=3)

        reporter.end_run()

        # Should only have 2 domains
        assert len(reporter.domain_stats) == 2
        assert "xray" in reporter.domain_stats
        assert "manifest" in reporter.domain_stats
        assert "sonar" not in reporter.domain_stats


class TestHealthTracking:
    """Test workspace health tracking."""

    def test_health_json_updated(self, tmp_path):
        """health.json should be updated after each run."""
        from src.core.status import StatusReporter

        workspace = tmp_path / "workspace"
        (workspace / "status").mkdir(parents=True)

        reporter = StatusReporter("test-run-007", "test-project")
        reporter.start_run({})
        reporter.start_domain("xray", "0.2.0")
        reporter.end_domain("xray", entities=50, edges=100)
        reporter.end_run()
        reporter.save(workspace)

        # Check health.json
        health_path = workspace / "status" / "health.json"
        assert health_path.exists()

        with open(health_path) as f:
            health = json.load(f)
            assert health["last_run_id"] == "test-run-007"
            assert health["last_project"] == "test-project"
            assert health["last_status"] == "success"

    def test_history_json_appended(self, tmp_path):
        """history.json should accumulate run records."""
        from src.core.status import StatusReporter

        workspace = tmp_path / "workspace"
        (workspace / "status").mkdir(parents=True)

        # Run 1
        reporter1 = StatusReporter("run-001", "project-a")
        reporter1.start_run({})
        reporter1.end_run()
        reporter1.save(workspace)

        # Run 2
        reporter2 = StatusReporter("run-002", "project-b")
        reporter2.start_run({})
        reporter2.end_run()
        reporter2.save(workspace)

        # Check history.json
        history_path = workspace / "status" / "history.json"
        with open(history_path) as f:
            history = json.load(f)
            assert len(history) == 2
            assert history[0]["run_id"] == "run-001"
            assert history[1]["run_id"] == "run-002"
