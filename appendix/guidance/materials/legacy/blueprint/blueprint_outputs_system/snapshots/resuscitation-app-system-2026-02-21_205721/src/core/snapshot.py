"""Snapshot system for creating bootable Blueprint copies.

When running Blueprint on a project, the system first creates a snapshot
(a copy of the Blueprint src) that can be modified independently of main.
This enables:

1. Project-specific customizations without polluting main
2. Reproducible runs with exact code versions
3. Autonomous agents can modify snapshots to fix issues
4. Each project can have its own patches and workarounds

Architecture:
    workspace/
    └── snapshots/
        └── <project>-<run-id>/
            ├── src/              # Copy of Blueprint src at run time
            ├── patches/          # Patches applied for this project
            │   └── *.patch       # Individual patch files
            ├── manifest.json     # What was changed and why
            └── .ready            # Marker that snapshot is bootable

Lifecycle:
    1. create_snapshot() - Copy src to snapshots/<project>-<run-id>/
    2. apply_patch() - Apply fixes from status analysis
    3. run_snapshot() - Execute the snapshot against the project
    4. archive_snapshot() - Move to cold storage after use
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Patch:
    """A patch applied to a snapshot."""
    patch_id: str
    description: str
    reason: str               # Why this patch was needed
    affected_files: List[str]
    created_at: str
    source: str               # "manual", "agent", "status-fix"
    status_run_id: Optional[str] = None  # Link to status report that triggered this

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "description": self.description,
            "reason": self.reason,
            "affected_files": self.affected_files,
            "created_at": self.created_at,
            "source": self.source,
            "status_run_id": self.status_run_id,
        }


@dataclass
class SnapshotManifest:
    """Manifest tracking a snapshot's state and history."""
    snapshot_id: str
    project_name: str
    created_at: str
    blueprint_version: str
    source_commit: Optional[str] = None  # Git commit of main Blueprint
    status: str = "created"              # created, ready, running, completed, failed, archived
    patches: List[Patch] = field(default_factory=list)
    runs: List[Dict[str, Any]] = field(default_factory=list)  # History of runs with this snapshot
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "blueprint_version": self.blueprint_version,
            "source_commit": self.source_commit,
            "status": self.status,
            "patches": [p.to_dict() for p in self.patches],
            "runs": self.runs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnapshotManifest:
        patches = [Patch(**p) for p in data.get("patches", [])]
        return cls(
            snapshot_id=data["snapshot_id"],
            project_name=data["project_name"],
            created_at=data["created_at"],
            blueprint_version=data["blueprint_version"],
            source_commit=data.get("source_commit"),
            status=data.get("status", "created"),
            patches=patches,
            runs=data.get("runs", []),
            notes=data.get("notes", ""),
        )


def get_git_commit(repo_path: Path) -> Optional[str]:
    """Get the current git commit hash of a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def create_snapshot(
    blueprint_root: Path,
    workspace_root: Path,
    project_name: str,
    run_id: str,
) -> Path:
    """Create a new snapshot of Blueprint src for a project run.

    Args:
        blueprint_root: Root of the main Blueprint installation.
        workspace_root: Root of the workspace folder.
        project_name: Name of the project being analyzed.
        run_id: Unique run identifier.

    Returns:
        Path to the snapshot directory.
    """
    from src import __version__

    snapshot_id = f"{project_name}-{run_id}"
    snapshot_dir = workspace_root / "snapshots" / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Copy src directory
    src_source = blueprint_root / "src"
    src_dest = snapshot_dir / "src"
    if src_source.is_dir():
        shutil.copytree(src_source, src_dest, dirs_exist_ok=True)

    # Create patches directory
    (snapshot_dir / "patches").mkdir(exist_ok=True)

    # Get git commit if available
    source_commit = get_git_commit(blueprint_root)

    # Create manifest
    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        project_name=project_name,
        created_at=datetime.now().isoformat(),
        blueprint_version=__version__,
        source_commit=source_commit,
        status="created",
    )

    save_manifest(manifest, snapshot_dir)

    # Create .ready marker
    (snapshot_dir / ".ready").touch()

    return snapshot_dir


def save_manifest(manifest: SnapshotManifest, snapshot_dir: Path) -> None:
    """Save the manifest to a snapshot directory."""
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2),
        encoding="utf-8",
    )


def load_manifest(snapshot_dir: Path) -> Optional[SnapshotManifest]:
    """Load the manifest from a snapshot directory."""
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SnapshotManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def list_snapshots(workspace_root: Path) -> List[SnapshotManifest]:
    """List all snapshots in a workspace."""
    snapshots_dir = workspace_root / "snapshots"
    if not snapshots_dir.is_dir():
        return []

    manifests = []
    for snapshot_dir in snapshots_dir.iterdir():
        if snapshot_dir.is_dir():
            manifest = load_manifest(snapshot_dir)
            if manifest:
                manifests.append(manifest)

    # Sort by creation date, newest first
    manifests.sort(key=lambda m: m.created_at, reverse=True)
    return manifests


def apply_patch(
    snapshot_dir: Path,
    patch_file: Path,
    description: str,
    reason: str,
    source: str = "manual",
    status_run_id: Optional[str] = None,
) -> bool:
    """Apply a patch to a snapshot.

    Args:
        snapshot_dir: Path to the snapshot directory.
        patch_file: Path to the .patch file to apply.
        description: Human-readable description of the patch.
        reason: Why this patch is being applied.
        source: Origin of the patch ("manual", "agent", "status-fix").
        status_run_id: If from status analysis, the run ID that triggered it.

    Returns:
        True if patch applied successfully, False otherwise.
    """
    import uuid

    manifest = load_manifest(snapshot_dir)
    if not manifest:
        return False

    src_dir = snapshot_dir / "src"
    if not src_dir.is_dir():
        return False

    # Copy patch to patches directory
    patch_id = f"patch-{uuid.uuid4().hex[:8]}"
    patches_dir = snapshot_dir / "patches"
    dest_patch = patches_dir / f"{patch_id}.patch"
    shutil.copy(patch_file, dest_patch)

    # Try to apply the patch
    try:
        result = subprocess.run(
            ["git", "apply", "--check", str(dest_patch)],
            cwd=src_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            # Patch doesn't apply cleanly
            dest_patch.unlink()
            return False

        # Actually apply it
        subprocess.run(
            ["git", "apply", str(dest_patch)],
            cwd=src_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # git not available, try manual application
        # For now, just record the patch and let human apply
        pass

    # Determine affected files from patch
    affected_files = []
    try:
        patch_content = dest_patch.read_text(encoding="utf-8")
        for line in patch_content.splitlines():
            if line.startswith("--- a/") or line.startswith("+++ b/"):
                file_path = line[6:]  # Strip prefix
                if file_path not in affected_files and file_path != "/dev/null":
                    affected_files.append(file_path)
    except (OSError, UnicodeDecodeError):
        pass

    # Record the patch
    patch = Patch(
        patch_id=patch_id,
        description=description,
        reason=reason,
        affected_files=affected_files,
        created_at=datetime.now().isoformat(),
        source=source,
        status_run_id=status_run_id,
    )
    manifest.patches.append(patch)
    save_manifest(manifest, snapshot_dir)

    return True


def record_run(
    snapshot_dir: Path,
    run_id: str,
    success: bool,
    summary: Dict[str, Any],
) -> None:
    """Record a run against this snapshot and update status."""
    manifest = load_manifest(snapshot_dir)
    if not manifest:
        return

    # Update status based on run outcome
    manifest.status = "completed" if success else "failed"

    manifest.runs.append({
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "summary": summary,
    })
    save_manifest(manifest, snapshot_dir)


def archive_snapshot(
    snapshot_dir: Path,
    archive_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Archive a snapshot (compress and optionally move).

    Args:
        snapshot_dir: Path to the snapshot directory.
        archive_dir: Optional directory to move archive to.

    Returns:
        Path to the archive file, or None if failed.
    """
    manifest = load_manifest(snapshot_dir)
    if manifest:
        manifest.status = "archived"
        save_manifest(manifest, snapshot_dir)

    # Create tar.gz archive
    archive_name = f"{snapshot_dir.name}.tar.gz"
    archive_path = snapshot_dir.parent / archive_name

    try:
        shutil.make_archive(
            str(archive_path).replace(".tar.gz", ""),
            "gztar",
            snapshot_dir.parent,
            snapshot_dir.name,
        )

        # Remove original directory
        shutil.rmtree(snapshot_dir)

        # Move to archive_dir if specified
        if archive_dir:
            archive_dir.mkdir(parents=True, exist_ok=True)
            final_path = archive_dir / archive_name
            shutil.move(archive_path, final_path)
            return final_path

        return archive_path
    except (OSError, shutil.Error):
        return None


def get_snapshot_path(workspace_root: Path, snapshot_id: str) -> Optional[Path]:
    """Get the path to a snapshot by ID."""
    snapshot_dir = workspace_root / "snapshots" / snapshot_id
    if snapshot_dir.is_dir():
        return snapshot_dir

    # Try partial match
    snapshots_dir = workspace_root / "snapshots"
    if snapshots_dir.is_dir():
        matches = [d for d in snapshots_dir.iterdir() if snapshot_id in d.name]
        if len(matches) == 1:
            return matches[0]

    return None


def is_snapshot_ready(snapshot_dir: Path) -> bool:
    """Check if a snapshot is ready to run."""
    ready_marker = snapshot_dir / ".ready"
    src_dir = snapshot_dir / "src"
    manifest = load_manifest(snapshot_dir)

    return (
        ready_marker.exists()
        and src_dir.is_dir()
        and manifest is not None
        and manifest.status in ("created", "ready", "completed")
    )


# ---------------------------------------------------------------------------
# Snapshot Execution
# ---------------------------------------------------------------------------

@dataclass
class SnapshotRunResult:
    """Result of running a snapshot."""
    success: bool
    run_id: str
    snapshot_id: str
    results_dir: Path
    files_scanned: int = 0
    entities_found: int = 0
    edges_found: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


def get_blueprint_root() -> Path:
    """Get the root directory of the Blueprint installation.

    Returns the parent of the src/ directory.
    """
    # This file is at src/core/snapshot.py
    # Blueprint root is two levels up
    this_file = Path(__file__).resolve()
    src_dir = this_file.parent.parent  # src/
    blueprint_root = src_dir.parent     # blueprint/
    return blueprint_root


def boot_snapshot(
    workspace_root: Path,
    project_name: str,
    run_id: Optional[str] = None,
    blueprint_root: Optional[Path] = None,
) -> Path:
    """Boot a new snapshot for a project run.

    This is the "initial run" - creates a fresh snapshot from main src/.

    Args:
        workspace_root: Root of the workspace folder.
        project_name: Name of the project being analyzed.
        run_id: Optional run identifier. Generated if not provided.
        blueprint_root: Optional Blueprint root. Auto-detected if not provided.

    Returns:
        Path to the snapshot directory.
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if blueprint_root is None:
        blueprint_root = get_blueprint_root()

    snapshot_dir = create_snapshot(blueprint_root, workspace_root, project_name, run_id)

    # Update manifest status to ready
    manifest = load_manifest(snapshot_dir)
    if manifest:
        manifest.status = "ready"
        save_manifest(manifest, snapshot_dir)

    # Initialize intra-run versioning (creates initial checkpoint)
    from src.core.intra import IntraVersioning
    IntraVersioning(snapshot_dir)

    return snapshot_dir


def run_snapshot(
    snapshot_dir: Path,
    workspace_root: Path,
    project_root: Path,
    project_name: str,
    run_id: Optional[str] = None,
    domains: Optional[List[str]] = None,
    preset: str = "standard",
    output_config: Optional[Dict[str, Any]] = None,
    bpignore_patterns: Optional[List[str]] = None,
    focus_path: Optional[Path] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    is_intra_run: bool = False,
    timeout: int = 600,
) -> SnapshotRunResult:
    """Run Blueprint analysis from a snapshot via subprocess.

    This spawns a new Python process with the snapshot's src/ on PYTHONPATH,
    ensuring complete isolation from main src/.

    Args:
        snapshot_dir: Path to the snapshot directory.
        workspace_root: Root of the workspace folder.
        project_root: Path to the project being analyzed.
        project_name: Name of the project.
        run_id: Run identifier. Generated if not provided.
        domains: List of domains to run. Defaults to xray, manifest, sonar.
        preset: Analysis preset.
        output_config: Output preferences.
        bpignore_patterns: Patterns to exclude.
        focus_path: Focus on a specific path within the project.
        include_patterns: Patterns to include.
        exclude_patterns: Patterns to exclude.
        is_intra_run: Whether this is a re-run within the same snapshot.
        timeout: Timeout in seconds for the subprocess.

    Returns:
        SnapshotRunResult with run outcome.
    """
    import sys
    import tempfile

    if run_id is None:
        run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if domains is None:
        domains = ["xray", "manifest", "sonar"]

    # Resolve all paths to absolute
    snapshot_dir = snapshot_dir.resolve()
    workspace_root = workspace_root.resolve()
    project_root = project_root.resolve()
    if focus_path:
        focus_path = focus_path.resolve()

    # Check snapshot is ready
    if not is_snapshot_ready(snapshot_dir):
        return SnapshotRunResult(
            success=False,
            run_id=run_id,
            snapshot_id=snapshot_dir.name,
            results_dir=workspace_root / "results" / project_name / run_id,
            error_message="Snapshot is not ready",
        )

    # Create run config file
    config = {
        "project_root": str(project_root),
        "project_name": project_name,
        "run_id": run_id,
        "domains": domains,
        "preset": preset,
        "output_config": output_config or {},
        "bpignore_patterns": bpignore_patterns or [],
        "focus_path": str(focus_path) if focus_path else None,
        "include_patterns": include_patterns or [],
        "exclude_patterns": exclude_patterns or [],
    }

    # Write config to temp file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(config, f, indent=2)
        config_path = Path(f.name)

    try:
        # Build subprocess command
        cmd = [
            sys.executable,
            "-m", "src.core.snapshot_executor",
            "--snapshot-dir", str(snapshot_dir),
            "--workspace", str(workspace_root),
            "--config", str(config_path),
        ]
        if is_intra_run:
            cmd.append("--intra-run")

        # Run subprocess
        result = subprocess.run(
            cmd,
            cwd=str(snapshot_dir),  # Run from snapshot dir
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Parse output
        if result.returncode == 0 and result.stdout.strip():
            try:
                output = json.loads(result.stdout.strip().split("\n")[-1])
                return SnapshotRunResult(
                    success=output.get("success", False),
                    run_id=output.get("run_id", run_id),
                    snapshot_id=output.get("snapshot_id", snapshot_dir.name),
                    results_dir=Path(output.get("results_dir", "")),
                    files_scanned=output.get("files_scanned", 0),
                    entities_found=output.get("entities_found", 0),
                    edges_found=output.get("edges_found", 0),
                    errors=output.get("errors", 0),
                    duration_seconds=output.get("duration_seconds", 0.0),
                )
            except json.JSONDecodeError:
                pass

        # Failed
        error_msg = result.stderr or result.stdout or "Unknown error"
        return SnapshotRunResult(
            success=False,
            run_id=run_id,
            snapshot_id=snapshot_dir.name,
            results_dir=workspace_root / "results" / project_name / run_id,
            error_message=error_msg[:1000],  # Truncate long errors
        )

    except subprocess.TimeoutExpired:
        return SnapshotRunResult(
            success=False,
            run_id=run_id,
            snapshot_id=snapshot_dir.name,
            results_dir=workspace_root / "results" / project_name / run_id,
            error_message=f"Snapshot run timed out after {timeout} seconds",
        )
    except Exception as e:
        return SnapshotRunResult(
            success=False,
            run_id=run_id,
            snapshot_id=snapshot_dir.name,
            results_dir=workspace_root / "results" / project_name / run_id,
            error_message=str(e),
        )
    finally:
        # Clean up config file
        try:
            config_path.unlink()
        except OSError:
            pass


def boot_and_run(
    workspace_root: Path,
    project_root: Path,
    project_name: str,
    domains: Optional[List[str]] = None,
    preset: str = "standard",
    output_config: Optional[Dict[str, Any]] = None,
    bpignore_patterns: Optional[List[str]] = None,
    focus_path: Optional[Path] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    timeout: int = 600,
) -> SnapshotRunResult:
    """Boot a new snapshot and run analysis in one step.

    This is the typical workflow for a fresh analysis:
    1. Create snapshot from main src/
    2. Run analysis from snapshot

    Args:
        workspace_root: Root of the workspace folder.
        project_root: Path to the project being analyzed.
        project_name: Name of the project.
        domains: List of domains to run.
        preset: Analysis preset.
        output_config: Output preferences.
        bpignore_patterns: Patterns to exclude.
        focus_path: Focus on a specific path within the project.
        include_patterns: Patterns to include.
        exclude_patterns: Patterns to exclude.
        timeout: Timeout in seconds for the subprocess.

    Returns:
        SnapshotRunResult with run outcome.
    """
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Boot snapshot
    snapshot_dir = boot_snapshot(workspace_root, project_name, run_id)

    # Run from snapshot
    return run_snapshot(
        snapshot_dir=snapshot_dir,
        workspace_root=workspace_root,
        project_root=project_root,
        project_name=project_name,
        run_id=run_id,
        domains=domains,
        preset=preset,
        output_config=output_config,
        bpignore_patterns=bpignore_patterns,
        focus_path=focus_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        is_intra_run=False,
        timeout=timeout,
    )
