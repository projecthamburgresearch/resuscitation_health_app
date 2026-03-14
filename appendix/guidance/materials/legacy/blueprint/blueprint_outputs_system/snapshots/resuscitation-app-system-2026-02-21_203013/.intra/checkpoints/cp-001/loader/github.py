"""GitHub repository cloning and checkout for cloud deploy targets.

Handles cloning public and private repositories into the workspace
intake directory for local analysis.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from src.loader.schema import DeployTarget


def clone_or_pull(
    target: DeployTarget,
    clone_dir: Path,
    timeout: int = 300,
) -> Path:
    """Clone a GitHub repo (or pull if already cloned).

    Args:
        target: Deploy target with repo, ref, and optional token_env.
        clone_dir: Directory where the repo should be cloned.
        timeout: Timeout in seconds for git operations.

    Returns:
        Path to the cloned repository.

    Raises:
        RuntimeError: If git operations fail.
    """
    repo = target.repo
    ref = target.ref or "main"

    # Build clone URL
    clone_url = _build_clone_url(repo, target.token_env)

    if clone_dir.exists() and (clone_dir / ".git").is_dir():
        # Already cloned -- pull latest
        _run_git(["git", "fetch", "--all"], cwd=clone_dir, timeout=timeout)
        _run_git(["git", "checkout", ref], cwd=clone_dir, timeout=timeout)
        _run_git(["git", "pull", "--ff-only"], cwd=clone_dir, timeout=timeout)
    else:
        # Fresh clone
        clone_dir.parent.mkdir(parents=True, exist_ok=True)
        _run_git(
            ["git", "clone", "--branch", ref, "--depth", "1", clone_url, str(clone_dir)],
            timeout=timeout,
        )

    return clone_dir


def _build_clone_url(repo: str, token_env: str = "") -> str:
    """Build a GitHub clone URL, optionally with auth token.

    Args:
        repo: GitHub repo in "owner/name" format.
        token_env: Name of environment variable holding the token.

    Returns:
        HTTPS clone URL.
    """
    if token_env:
        token = os.environ.get(token_env, "")
        if token:
            return f"https://{token}@github.com/{repo}.git"

    return f"https://github.com/{repo}.git"


def _run_git(
    cmd: list,
    cwd: Optional[Path] = None,
    timeout: int = 300,
) -> str:
    """Run a git command and return stdout.

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        timeout: Timeout in seconds.

    Returns:
        stdout text.

    Raises:
        RuntimeError: If the command fails.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Git command timed out after {timeout}s: {' '.join(cmd)}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Git is not installed or not on PATH. "
            "Install git to use GitHub deploy targets."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{stderr}")

    return result.stdout.strip()


def validate_github_target(target: DeployTarget) -> list:
    """Validate a GitHub deploy target configuration.

    Args:
        target: Deploy target to validate.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if not target.repo:
        errors.append("GitHub target is missing 'repo' field.")
    elif "/" not in target.repo:
        errors.append(f"GitHub repo '{target.repo}' must be in 'owner/name' format.")

    if target.token_env:
        token = os.environ.get(target.token_env, "")
        if not token:
            errors.append(
                f"Environment variable '{target.token_env}' is not set. "
                f"Required for private repo access."
            )

    return errors
