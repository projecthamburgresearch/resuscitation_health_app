"""Project management for Blueprint workspace.

Manages the lifecycle of projects in the workspace:
- projects/ : Active projects ready to run
- recent/   : Previously opened projects (can restore)

Like an IDE's project management - open, close, recent files menu.

Usage:
    from src.core.project import ProjectManager

    pm = ProjectManager(workspace_root)

    # Open a project (from source or from bundle)
    project = pm.open_project(project_root)

    # List active projects
    active = pm.list_active()

    # List recent (closed) projects
    recent = pm.list_recent()

    # Close a project (moves to recent)
    pm.close_project(project_name)

    # Restore from recent
    pm.restore_project(project_name)
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.bundle import Bundle, find_bundle


@dataclass
class ProjectInfo:
    """Information about a project in the workspace."""
    project_name: str
    source_root: str  # Path to original source code
    workspace_path: str  # Path in workspace (projects/ or recent/)
    status: str  # "active" or "recent"
    opened_at: str
    last_run_id: Optional[str] = None
    last_run_at: Optional[str] = None
    bundle_path: Optional[str] = None  # Path to _blueprint folder if exists
    total_runs: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "source_root": self.source_root,
            "workspace_path": self.workspace_path,
            "status": self.status,
            "opened_at": self.opened_at,
            "last_run_id": self.last_run_id,
            "last_run_at": self.last_run_at,
            "bundle_path": self.bundle_path,
            "total_runs": self.total_runs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectInfo":
        return cls(
            project_name=data["project_name"],
            source_root=data["source_root"],
            workspace_path=data["workspace_path"],
            status=data.get("status", "active"),
            opened_at=data["opened_at"],
            last_run_id=data.get("last_run_id"),
            last_run_at=data.get("last_run_at"),
            bundle_path=data.get("bundle_path"),
            total_runs=data.get("total_runs", 0),
            notes=data.get("notes", ""),
        )


class ProjectManager:
    """Manages projects in the Blueprint workspace."""

    def __init__(self, workspace_root: Path):
        """Initialize project manager.

        Args:
            workspace_root: Path to the workspace root.
        """
        self.workspace_root = Path(workspace_root).resolve()

        # Workspace directories
        self.projects_dir = self.workspace_root / "projects"
        self.recent_dir = self.workspace_root / "recent"
        self.snapshots_dir = self.workspace_root / "snapshots"
        self.results_dir = self.workspace_root / "results"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure workspace directories exist."""
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.recent_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def open_project(
        self,
        source_root: Path,
        notes: str = "",
    ) -> Optional[ProjectInfo]:
        """Open a project in the workspace.

        If project has an existing bundle, imports it.
        If project is in recent/, restores it to active.

        Args:
            source_root: Path to the project's source code.
            notes: Optional notes about the project.

        Returns:
            ProjectInfo for the opened project, or None if failed.
        """
        source_root = Path(source_root).resolve()
        project_name = source_root.name

        # Check if already active
        existing = self.get_project(project_name)
        if existing and existing.status == "active":
            return existing

        # Check if in recent (restore it)
        if existing and existing.status == "recent":
            return self.restore_project(project_name)

        # Create new project entry
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing bundle
        bundle = find_bundle(source_root)
        bundle_path = str(bundle.bundle_dir) if bundle else None

        # If bundle exists, import results
        if bundle:
            import_result = bundle.import_to_workspace(self.workspace_root)
            last_run_id = import_result.get("run_id") if import_result else None
        else:
            last_run_id = None

        # Create project info
        info = ProjectInfo(
            project_name=project_name,
            source_root=str(source_root),
            workspace_path=str(project_dir),
            status="active",
            opened_at=datetime.now().isoformat(),
            bundle_path=bundle_path,
            last_run_id=last_run_id,
            notes=notes,
        )

        # Save project info
        self._save_project_info(project_dir, info)

        # Create active marker
        (project_dir / ".active").touch()

        return info

    def close_project(self, project_name: str) -> bool:
        """Close a project (move to recent).

        Args:
            project_name: Name of the project to close.

        Returns:
            True if closed successfully.
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return False

        # Load project info
        info = self._load_project_info(project_dir)
        if not info:
            return False

        # Update status
        info.status = "recent"

        # Create summary for recent
        summary = self._create_recent_summary(info)

        # Move to recent
        recent_dir = self.recent_dir / project_name
        if recent_dir.exists():
            shutil.rmtree(recent_dir)

        # Don't move the whole directory, just create a lightweight reference
        recent_dir.mkdir(parents=True, exist_ok=True)

        # Save project info in recent
        info.workspace_path = str(recent_dir)
        self._save_project_info(recent_dir, info)

        # Save summary
        summary_path = recent_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )

        # Create recent marker
        (recent_dir / ".recent").touch()

        # Remove from active
        shutil.rmtree(project_dir)

        return True

    def restore_project(self, project_name: str) -> Optional[ProjectInfo]:
        """Restore a project from recent to active.

        Args:
            project_name: Name of the project to restore.

        Returns:
            ProjectInfo for the restored project, or None if failed.
        """
        recent_dir = self.recent_dir / project_name
        if not recent_dir.exists():
            return None

        # Load project info
        info = self._load_project_info(recent_dir)
        if not info:
            return None

        # Update status
        info.status = "active"

        # Create in projects
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Save project info
        info.workspace_path = str(project_dir)
        self._save_project_info(project_dir, info)

        # Create active marker
        (project_dir / ".active").touch()

        # Remove from recent
        shutil.rmtree(recent_dir)

        return info

    def get_project(self, project_name: str) -> Optional[ProjectInfo]:
        """Get project info by name.

        Args:
            project_name: Name of the project.

        Returns:
            ProjectInfo if found, None otherwise.
        """
        # Check active
        project_dir = self.projects_dir / project_name
        if project_dir.exists():
            info = self._load_project_info(project_dir)
            if info:
                info.status = "active"
                return info

        # Check recent
        recent_dir = self.recent_dir / project_name
        if recent_dir.exists():
            info = self._load_project_info(recent_dir)
            if info:
                info.status = "recent"
                return info

        return None

    def list_active(self) -> List[ProjectInfo]:
        """List all active projects.

        Returns:
            List of active ProjectInfo.
        """
        projects = []
        if self.projects_dir.exists():
            for item in self.projects_dir.iterdir():
                if item.is_dir() and (item / "project.json").exists():
                    info = self._load_project_info(item)
                    if info:
                        info.status = "active"
                        projects.append(info)
        return projects

    def list_recent(self) -> List[ProjectInfo]:
        """List all recent (closed) projects.

        Returns:
            List of recent ProjectInfo.
        """
        projects = []
        if self.recent_dir.exists():
            for item in self.recent_dir.iterdir():
                if item.is_dir() and (item / "project.json").exists():
                    info = self._load_project_info(item)
                    if info:
                        info.status = "recent"
                        projects.append(info)
        return projects

    def list_all(self) -> Dict[str, List[ProjectInfo]]:
        """List all projects (active and recent).

        Returns:
            Dict with 'active' and 'recent' lists.
        """
        return {
            "active": self.list_active(),
            "recent": self.list_recent(),
        }

    def update_project_run(
        self,
        project_name: str,
        run_id: str,
    ) -> bool:
        """Update project with a new run.

        Args:
            project_name: Name of the project.
            run_id: ID of the run.

        Returns:
            True if updated successfully.
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return False

        info = self._load_project_info(project_dir)
        if not info:
            return False

        info.last_run_id = run_id
        info.last_run_at = datetime.now().isoformat()
        info.total_runs += 1

        self._save_project_info(project_dir, info)
        return True

    def delete_project(self, project_name: str, from_recent: bool = True) -> bool:
        """Delete a project from workspace.

        Args:
            project_name: Name of the project.
            from_recent: If True, delete from recent. If False, delete from active.

        Returns:
            True if deleted successfully.
        """
        if from_recent:
            project_dir = self.recent_dir / project_name
        else:
            project_dir = self.projects_dir / project_name

        if project_dir.exists():
            shutil.rmtree(project_dir)
            return True
        return False

    def get_project_results(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all run results for a project.

        Args:
            project_name: Name of the project.

        Returns:
            List of run result summaries.
        """
        results = []
        results_dir = self.results_dir / project_name

        if results_dir.exists():
            for run_dir in sorted(results_dir.iterdir(), reverse=True):
                if run_dir.is_dir():
                    meta_path = run_dir / "run_meta.json"
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text(encoding="utf-8"))
                            results.append({
                                "run_id": run_dir.name,
                                "path": str(run_dir),
                                "meta": meta,
                            })
                        except json.JSONDecodeError:
                            pass

        return results

    def get_project_snapshots(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all snapshots for a project.

        Args:
            project_name: Name of the project.

        Returns:
            List of snapshot summaries.
        """
        snapshots = []

        if self.snapshots_dir.exists():
            for snap_dir in sorted(self.snapshots_dir.iterdir(), reverse=True):
                if snap_dir.is_dir() and snap_dir.name.startswith(project_name):
                    manifest_path = snap_dir / "manifest.json"
                    if manifest_path.exists():
                        try:
                            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                            snapshots.append({
                                "snapshot_id": snap_dir.name,
                                "path": str(snap_dir),
                                "manifest": manifest,
                            })
                        except json.JSONDecodeError:
                            pass

        return snapshots

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _load_project_info(self, project_dir: Path) -> Optional[ProjectInfo]:
        """Load project info from directory."""
        info_path = project_dir / "project.json"
        if not info_path.exists():
            return None
        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
            return ProjectInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_project_info(self, project_dir: Path, info: ProjectInfo) -> None:
        """Save project info to directory."""
        info_path = project_dir / "project.json"
        info_path.write_text(
            json.dumps(info.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _create_recent_summary(self, info: ProjectInfo) -> Dict[str, Any]:
        """Create a lightweight summary for recent projects."""
        return {
            "project_name": info.project_name,
            "source_root": info.source_root,
            "last_run_id": info.last_run_id,
            "last_run_at": info.last_run_at,
            "total_runs": info.total_runs,
            "closed_at": datetime.now().isoformat(),
        }


# -----------------------------------------------------------------------------
# Convenience functions
# -----------------------------------------------------------------------------

def get_project_manager(workspace_root: Path) -> ProjectManager:
    """Get a project manager for the workspace."""
    return ProjectManager(workspace_root)


def open_project(workspace_root: Path, source_root: Path) -> Optional[ProjectInfo]:
    """Open a project in the workspace."""
    pm = ProjectManager(workspace_root)
    return pm.open_project(source_root)


def list_projects(workspace_root: Path) -> Dict[str, List[ProjectInfo]]:
    """List all projects in the workspace."""
    pm = ProjectManager(workspace_root)
    return pm.list_all()
