"""Mimic tests for the certificate system process.

These tests simulate the complete certificate workflow:
1. Certificate issuance
2. Certificate validation
3. Certificate revocation
4. Boot gating

Unlike unit tests, mimic tests exercise the full process with real files.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

import pytest

BLUEPRINT_ROOT = Path(__file__).parent.parent.parent.resolve()


class TestCertificateIssuance:
    """Test certificate issuance workflow."""

    def test_issue_certificate_creates_file(self, tmp_path):
        """Issuing a certificate should create current.json."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "src" / "__init__.py").write_text("# src")
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        cert, success = manager.issue_certificate()

        assert success
        assert cert is not None
        assert (blueprint / "workspace" / "status" / "certificate" / "current.json").exists()

    def test_certificate_includes_src_hash(self, tmp_path):
        """Certificate should include hash of src/."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "src" / "module.py").write_text("print('hello')")
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        cert, _ = manager.issue_certificate()

        assert cert.src_hash is not None
        assert len(cert.src_hash) == 16  # Truncated SHA256

    def test_certificate_has_expiration(self, tmp_path):
        """Certificate should have expiration time."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        cert, _ = manager.issue_certificate()

        expires_at = datetime.fromisoformat(cert.expires_at)
        issued_at = datetime.fromisoformat(cert.issued_at)

        # Should expire after issue time
        assert expires_at > issued_at

        # Default is 24 hours
        delta = expires_at - issued_at
        assert delta.total_seconds() == 24 * 60 * 60


class TestCertificateValidation:
    """Test certificate validation workflow."""

    def test_validate_valid_certificate(self, tmp_path):
        """Valid certificate should pass validation."""
        from src.core.certificate import CertificateManager, CertificateStatus

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "src" / "mod.py").write_text("x = 1")
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        manager.issue_certificate()

        status, cert = manager.validate()

        assert status == CertificateStatus.VALID
        assert cert is not None

    def test_validate_detects_src_change(self, tmp_path):
        """Validation should detect src/ changes."""
        from src.core.certificate import CertificateManager, CertificateStatus

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "src" / "mod.py").write_text("VERSION = 1")
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        manager.issue_certificate()

        # Modify src/
        (blueprint / "src" / "mod.py").write_text("VERSION = 2")

        status, cert = manager.validate()

        assert status == CertificateStatus.INVALIDATED
        assert "hash changed" in cert.revocation_reason

    def test_validate_detects_expired(self, tmp_path):
        """Validation should detect expired certificates."""
        from src.core.certificate import CertificateManager, CertificateStatus, Certificate

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        cert_dir = blueprint / "workspace" / "status" / "certificate"
        cert_dir.mkdir(parents=True)

        # Write an already-expired certificate
        expired_cert = {
            "certificate_id": "cert-expired",
            "issued_at": "2020-01-01T00:00:00",
            "expires_at": "2020-01-02T00:00:00",  # Long expired
            "src_hash": "abc123",
            "test_results": [],
            "status": "valid",
        }
        (cert_dir / "current.json").write_text(json.dumps(expired_cert))

        manager = CertificateManager(blueprint)
        status, cert = manager.validate()

        assert status == CertificateStatus.EXPIRED

    def test_validate_missing_certificate(self, tmp_path):
        """Validation should handle missing certificate."""
        from src.core.certificate import CertificateManager, CertificateStatus

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        status, cert = manager.validate()

        assert status == CertificateStatus.MISSING
        assert cert is None


class TestCertificateRevocation:
    """Test certificate revocation workflow."""

    def test_revoke_certificate(self, tmp_path):
        """Revoking a certificate should mark it as revoked."""
        from src.core.certificate import CertificateManager, CertificateStatus

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        manager.issue_certificate()

        # Revoke
        success = manager.revoke("Manual test revocation")

        assert success

        status, cert = manager.validate()
        assert status == CertificateStatus.REVOKED
        assert "Manual test revocation" in cert.revocation_reason

    def test_revoke_nonexistent(self, tmp_path):
        """Revoking nonexistent certificate should return False."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)
        success = manager.revoke("No cert to revoke")

        assert success is False


class TestBootGating:
    """Test certificate-based boot gating."""

    def test_boot_blocked_without_certificate(self, tmp_path):
        """Boot should be blocked without certificate."""
        from src.core.certificate import check_boot_certificate

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        can_boot, message = check_boot_certificate(blueprint)

        assert can_boot is False
        assert "No certificate" in message or "missing" in message.lower()

    def test_boot_allowed_with_certificate(self, tmp_path):
        """Boot should be allowed with valid certificate."""
        from src.core.certificate import CertificateManager, check_boot_certificate

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        # Issue certificate first
        manager = CertificateManager(blueprint)
        manager.issue_certificate()

        can_boot, message = check_boot_certificate(blueprint)

        assert can_boot is True
        assert "valid" in message.lower()

    def test_ensure_certificate_auto_issues(self, tmp_path):
        """ensure_certificate should auto-issue if needed."""
        from src.core.certificate import ensure_certificate

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "src" / "x.py").write_text("")
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        success, message, cert = ensure_certificate(blueprint, auto_issue=True)

        assert success
        assert cert is not None
        assert "issued" in message.lower()


class TestCertificateHistory:
    """Test certificate history tracking."""

    def test_history_accumulates(self, tmp_path):
        """Certificate history should accumulate."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)

        # Issue multiple certificates
        for i in range(3):
            (blueprint / "src" / f"mod{i}.py").write_text(f"V{i}")
            manager.issue_certificate(force=True)

        history_file = blueprint / "workspace" / "status" / "certificate" / "history.json"
        with open(history_file) as f:
            history = json.load(f)

        assert len(history) == 3

    def test_history_limited(self, tmp_path):
        """History should be limited to last N entries."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        manager = CertificateManager(blueprint)

        # Issue many certificates
        for i in range(60):
            (blueprint / "src" / "mod.py").write_text(f"V{i}")
            manager.issue_certificate(force=True)

        history_file = blueprint / "workspace" / "status" / "certificate" / "history.json"
        with open(history_file) as f:
            history = json.load(f)

        # Should be capped at 50
        assert len(history) <= 50


class TestMimicTestIntegration:
    """Test that mimic tests affect certificate issuance."""

    def test_passing_tests_issue_certificate(self, tmp_path):
        """Passing mimic tests should result in certificate."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        (blueprint / "playground").mkdir()
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        # No mimic tests = auto-pass
        manager = CertificateManager(blueprint)
        cert, success = manager.issue_certificate()

        assert success

    def test_failing_tests_deny_certificate(self, tmp_path):
        """Failing mimic tests should deny certificate."""
        from src.core.certificate import CertificateManager

        blueprint = tmp_path / "blueprint"
        (blueprint / "src").mkdir(parents=True)
        mimic_dir = blueprint / "playground" / "mimic_fail"
        mimic_dir.mkdir(parents=True)
        (blueprint / "workspace" / "status" / "certificate").mkdir(parents=True)

        # Create a failing test
        (mimic_dir / "test_always_fails.py").write_text("""
def test_always_fails():
    assert False, "This test always fails"
""")

        manager = CertificateManager(blueprint)
        cert, success = manager.issue_certificate()

        assert not success
        assert cert is not None  # Failed cert still returned for diagnostics
        failed_tests = [t for t in cert.test_results if not t.passed]
        assert len(failed_tests) > 0
