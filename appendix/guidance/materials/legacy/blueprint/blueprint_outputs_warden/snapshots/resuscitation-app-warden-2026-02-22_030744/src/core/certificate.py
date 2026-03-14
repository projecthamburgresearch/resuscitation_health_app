"""Certificate system for Blueprint src/ validation.

The certificate system ensures that src/ passes all mimic tests before
any snapshot can boot. This prevents corrupted or broken code from
running analysis on real projects.

Architecture:
- Certificate: A signed attestation that src/ is valid at a point in time
- CertificateManager: Issues, validates, and revokes certificates
- Tests run from playground/mimic_* directories
- Certificate stored in workspace/status/certificate/

Flow:
1. Run all mimic_* tests in playground/
2. If all pass, issue certificate with timestamp and hash of src/
3. Boot checks for valid certificate before proceeding
4. Any changes to src/ invalidate the certificate
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CertificateStatus(str, Enum):
    """Status of a certificate."""
    VALID = "valid"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"  # src/ changed since issue
    MISSING = "missing"
    REVOKED = "revoked"


@dataclass
class TestResult:
    """Result of a single mimic test."""
    test_name: str
    passed: bool
    duration_ms: float
    output: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 2),
            "output": self.output[:500] if self.output else "",
            "error": self.error[:500] if self.error else "",
        }


@dataclass
class Certificate:
    """A certificate attesting that src/ is valid.

    Attributes:
        certificate_id: Unique ID for this certificate
        issued_at: When the certificate was issued
        expires_at: When the certificate expires
        src_hash: Hash of src/ contents when certificate was issued
        test_results: Results of all mimic tests that passed
        issuer: Who/what issued the certificate (e.g., "mimic_runner")
        status: Current status of the certificate
        revocation_reason: Why the certificate was revoked (if applicable)
    """
    certificate_id: str
    issued_at: str
    expires_at: str
    src_hash: str
    test_results: List[TestResult] = field(default_factory=list)
    issuer: str = "mimic_runner"
    status: CertificateStatus = CertificateStatus.VALID
    revocation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "src_hash": self.src_hash,
            "test_results": [t.to_dict() for t in self.test_results],
            "issuer": self.issuer,
            "status": self.status.value,
            "revocation_reason": self.revocation_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Certificate":
        return cls(
            certificate_id=data["certificate_id"],
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            src_hash=data["src_hash"],
            test_results=[
                TestResult(
                    test_name=t["test_name"],
                    passed=t["passed"],
                    duration_ms=t["duration_ms"],
                    output=t.get("output", ""),
                    error=t.get("error", ""),
                )
                for t in data.get("test_results", [])
            ],
            issuer=data.get("issuer", "mimic_runner"),
            status=CertificateStatus(data.get("status", "valid")),
            revocation_reason=data.get("revocation_reason"),
        )


def _compute_src_hash(src_path: Path) -> str:
    """Compute a hash of all Python files in src/.

    This hash changes when any source file is modified.
    """
    hasher = hashlib.sha256()

    # Get all Python files sorted for deterministic hash
    py_files = sorted(src_path.rglob("*.py"))

    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_bytes()
            # Include relative path in hash so renames are detected
            rel_path = py_file.relative_to(src_path)
            hasher.update(str(rel_path).encode())
            hasher.update(content)
        except (OSError, IOError):
            continue

    return hasher.hexdigest()[:16]


def _run_mimic_tests(playground_path: Path) -> Tuple[List[TestResult], bool]:
    """Run all mimic_* tests in the playground directory.

    Returns:
        Tuple of (test_results, all_passed)
    """
    results: List[TestResult] = []
    all_passed = True

    # Find all mimic_* directories
    mimic_dirs = sorted([
        d for d in playground_path.iterdir()
        if d.is_dir() and d.name.startswith("mimic_")
    ])

    if not mimic_dirs:
        # No mimic tests defined yet - pass by default
        return [], True

    for mimic_dir in mimic_dirs:
        # Look for test files
        test_files = list(mimic_dir.glob("test_*.py"))
        if not test_files:
            continue

        for test_file in test_files:
            start = datetime.now()
            try:
                # Run the test with pytest
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=playground_path.parent,  # Run from blueprint root
                )
                duration_ms = (datetime.now() - start).total_seconds() * 1000

                passed = result.returncode == 0
                test_result = TestResult(
                    test_name=f"{mimic_dir.name}/{test_file.name}",
                    passed=passed,
                    duration_ms=duration_ms,
                    output=result.stdout,
                    error=result.stderr if not passed else "",
                )
            except subprocess.TimeoutExpired:
                duration_ms = (datetime.now() - start).total_seconds() * 1000
                test_result = TestResult(
                    test_name=f"{mimic_dir.name}/{test_file.name}",
                    passed=False,
                    duration_ms=duration_ms,
                    error="Test timed out after 120 seconds",
                )
            except Exception as e:
                duration_ms = (datetime.now() - start).total_seconds() * 1000
                test_result = TestResult(
                    test_name=f"{mimic_dir.name}/{test_file.name}",
                    passed=False,
                    duration_ms=duration_ms,
                    error=str(e),
                )

            results.append(test_result)
            if not test_result.passed:
                all_passed = False

    return results, all_passed


class CertificateManager:
    """Manages certificate lifecycle: issue, validate, revoke.

    Usage:
        manager = CertificateManager(blueprint_root)

        # Issue a new certificate (runs all mimic tests)
        cert, success = manager.issue_certificate()
        if not success:
            print("Tests failed, cannot boot")

        # Check if current certificate is valid
        status, cert = manager.validate()
        if status == CertificateStatus.VALID:
            # OK to boot
        else:
            # Need to re-issue
    """

    def __init__(self, blueprint_root: Path):
        self.blueprint_root = Path(blueprint_root)
        self.src_path = self.blueprint_root / "src"
        self.playground_path = self.blueprint_root / "playground"
        self.workspace_path = self.blueprint_root / "workspace"
        self.cert_dir = self.workspace_path / "status" / "certificate"
        self.cert_file = self.cert_dir / "current.json"
        self.history_file = self.cert_dir / "history.json"

        # Default certificate lifetime: 24 hours
        self.certificate_lifetime_hours = 24

    def _load_certificate(self) -> Optional[Certificate]:
        """Load the current certificate from disk."""
        if not self.cert_file.exists():
            return None
        try:
            data = json.loads(self.cert_file.read_text())
            return Certificate.from_dict(data)
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _save_certificate(self, cert: Certificate) -> None:
        """Save a certificate to disk."""
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.cert_file.write_text(json.dumps(cert.to_dict(), indent=2))

        # Also update history
        self._append_history(cert)

    def _append_history(self, cert: Certificate) -> None:
        """Append certificate to history log."""
        history: List[Dict] = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, OSError):
                history = []

        # Add summary to history
        history.append({
            "certificate_id": cert.certificate_id,
            "issued_at": cert.issued_at,
            "status": cert.status.value,
            "src_hash": cert.src_hash,
            "tests_passed": sum(1 for t in cert.test_results if t.passed),
            "tests_total": len(cert.test_results),
        })

        # Keep last 50 entries
        history = history[-50:]

        self.history_file.write_text(json.dumps(history, indent=2))

    def issue_certificate(
        self,
        force: bool = False,
    ) -> Tuple[Optional[Certificate], bool]:
        """Issue a new certificate by running all mimic tests.

        Args:
            force: If True, issue even if current certificate is valid

        Returns:
            Tuple of (certificate, success). Certificate is None if tests failed.
        """
        # Check if we need to issue
        if not force:
            status, existing = self.validate()
            if status == CertificateStatus.VALID:
                return existing, True

        # Compute current src hash
        src_hash = _compute_src_hash(self.src_path)

        # Run all mimic tests
        test_results, all_passed = _run_mimic_tests(self.playground_path)

        # Generate certificate
        now = datetime.now()
        cert_id = f"cert-{now.strftime('%Y%m%d_%H%M%S')}-{src_hash[:8]}"

        if all_passed:
            cert = Certificate(
                certificate_id=cert_id,
                issued_at=now.isoformat(),
                expires_at=(now + timedelta(hours=self.certificate_lifetime_hours)).isoformat(),
                src_hash=src_hash,
                test_results=test_results,
                issuer="mimic_runner",
                status=CertificateStatus.VALID,
            )
            self._save_certificate(cert)
            return cert, True
        else:
            # Create a failed certificate record (not saved as current)
            cert = Certificate(
                certificate_id=cert_id,
                issued_at=now.isoformat(),
                expires_at=now.isoformat(),  # Already expired
                src_hash=src_hash,
                test_results=test_results,
                issuer="mimic_runner",
                status=CertificateStatus.INVALIDATED,
                revocation_reason="Tests failed",
            )
            self._append_history(cert)
            return cert, False

    def validate(self) -> Tuple[CertificateStatus, Optional[Certificate]]:
        """Validate the current certificate.

        Returns:
            Tuple of (status, certificate). Certificate may be None if missing.
        """
        cert = self._load_certificate()

        if cert is None:
            return CertificateStatus.MISSING, None

        # Check if revoked
        if cert.status == CertificateStatus.REVOKED:
            return CertificateStatus.REVOKED, cert

        # Check if expired
        expires_at = datetime.fromisoformat(cert.expires_at)
        if datetime.now() > expires_at:
            cert.status = CertificateStatus.EXPIRED
            self._save_certificate(cert)
            return CertificateStatus.EXPIRED, cert

        # Check if src/ has changed
        current_hash = _compute_src_hash(self.src_path)
        if current_hash != cert.src_hash:
            cert.status = CertificateStatus.INVALIDATED
            cert.revocation_reason = f"src/ hash changed from {cert.src_hash} to {current_hash}"
            self._save_certificate(cert)
            return CertificateStatus.INVALIDATED, cert

        return CertificateStatus.VALID, cert

    def revoke(self, reason: str = "Manual revocation") -> bool:
        """Revoke the current certificate.

        Returns:
            True if a certificate was revoked, False if none existed.
        """
        cert = self._load_certificate()
        if cert is None:
            return False

        cert.status = CertificateStatus.REVOKED
        cert.revocation_reason = reason
        self._save_certificate(cert)
        return True

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of certificate status for display."""
        status, cert = self.validate()

        summary = {
            "status": status.value,
            "can_boot": status == CertificateStatus.VALID,
            "message": "",
            "certificate": None,
        }

        if status == CertificateStatus.VALID:
            summary["message"] = f"Certificate valid until {cert.expires_at}"
            summary["certificate"] = {
                "id": cert.certificate_id,
                "issued_at": cert.issued_at,
                "expires_at": cert.expires_at,
                "tests_passed": len(cert.test_results),
            }
        elif status == CertificateStatus.MISSING:
            summary["message"] = "No certificate found. Run mimic tests to issue one."
        elif status == CertificateStatus.EXPIRED:
            summary["message"] = f"Certificate expired at {cert.expires_at}. Re-run tests."
        elif status == CertificateStatus.INVALIDATED:
            summary["message"] = f"Certificate invalidated: {cert.revocation_reason}"
        elif status == CertificateStatus.REVOKED:
            summary["message"] = f"Certificate revoked: {cert.revocation_reason}"

        return summary


# ---------------------------------------------------------------------------
# Boot gate function
# ---------------------------------------------------------------------------

def check_boot_certificate(blueprint_root: Path) -> Tuple[bool, str]:
    """Check if src/ has a valid certificate for booting.

    This is the main gate function that should be called before any
    snapshot boots. If the certificate is invalid, the caller should
    either re-run tests or abort.

    Args:
        blueprint_root: Root of the Blueprint installation.

    Returns:
        Tuple of (can_boot, message).
    """
    manager = CertificateManager(blueprint_root)
    summary = manager.get_status_summary()
    return summary["can_boot"], summary["message"]


def ensure_certificate(
    blueprint_root: Path,
    auto_issue: bool = True,
) -> Tuple[bool, str, Optional[Certificate]]:
    """Ensure a valid certificate exists, optionally issuing one.

    Args:
        blueprint_root: Root of the Blueprint installation.
        auto_issue: If True, run tests and issue certificate if needed.

    Returns:
        Tuple of (success, message, certificate).
    """
    manager = CertificateManager(blueprint_root)
    status, cert = manager.validate()

    if status == CertificateStatus.VALID:
        return True, f"Certificate valid: {cert.certificate_id}", cert

    if not auto_issue:
        return False, f"Certificate {status.value}. Run tests to issue.", cert

    # Try to issue a new certificate
    new_cert, success = manager.issue_certificate(force=True)

    if success:
        return True, f"New certificate issued: {new_cert.certificate_id}", new_cert
    else:
        failed_tests = [t for t in new_cert.test_results if not t.passed]
        test_names = ", ".join(t.test_name for t in failed_tests[:3])
        return False, f"Certificate denied: {len(failed_tests)} tests failed ({test_names}...)", new_cert
