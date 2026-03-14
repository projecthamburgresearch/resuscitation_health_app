"""Bidirectional sync between workspace and bundle.

Keeps the workspace (ephemeral) and bundle (persistent) in sync.
The bundle is the source of truth for portability and backup.

Sync directions:
- EXPORT: workspace → bundle (after runs, save results to bundle)
- IMPORT: bundle → workspace (restore from bundle)
- FULL:   bidirectional (reconcile both sides)

Usage:
    from src.core.sync import SyncManager

    sync = SyncManager(workspace_root)

    # After a run, export to bundle
    sync.export_project(project_name, run_id)

    # Restore from bundle
    sync.import_project(source_root)

    # Check sync status
    status = sync.get_sync_status(project_name)

    # Full sync (reconcile)
    sync.sync_project(project_name)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.bundle import Bundle, find_bundle
from src.core.project import ProjectManager, ProjectInfo


@dataclass
class SyncStatus:
    """Status of sync between workspace and bundle."""
    project_name: str
    workspace_exists: bool
    bundle_exists: bool
    in_sync: bool
    workspace_run_id: Optional[str]
    bundle_run_id: Optional[str]
    workspace_last_modified: Optional[str]
    bundle_last_sync: Optional[str]
    recommendation: str  # "none", "export", "import", "conflict"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "workspace_exists": self.workspace_exists,
            "bundle_exists": self.bundle_exists,
            "in_sync": self.in_sync,
            "workspace_run_id": self.workspace_run_id,
            "bundle_run_id": self.bundle_run_id,
            "workspace_last_modified": self.workspace_last_modified,
            "bundle_last_sync": self.bundle_last_sync,
            "recommendation": self.recommendation,
        }


class SyncManager:
    """Manages sync between workspace and bundles."""

    def __init__(self, workspace_root: Path):
        """Initialize sync manager.

        Args:
            workspace_root: Path to the workspace root.
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.project_manager = ProjectManager(workspace_root)

    def export_project(
        self,
        project_name: str,
        run_id: str,
        run_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Export workspace results to bundle.

        Args:
            project_name: Name of the project.
            run_id: Run ID to export.
            run_config: Optional run configuration.

        Returns:
            True if export successful.
        """
        # Get project info
        project = self.project_manager.get_project(project_name)
        if not project:
            return False

        # Get or create bundle
        source_root = Path(project.source_root)
        bundle = Bundle(source_root)

        # Create bundle if needed
        if not bundle.exists():
            bundle.create(
                workspace_link=str(self.workspace_root / "projects" / project_name)
            )

        # Export
        success = bundle.export_from_workspace(
            workspace_root=self.workspace_root,
            project_name=project_name,
            run_id=run_id,
            run_config=run_config,
        )

        if success:
            # Update project info with bundle path
            project_dir = self.workspace_root / "projects" / project_name
            if project_dir.exists():
                project.bundle_path = str(bundle.bundle_dir)
                info_path = project_dir / "project.json"
                info_path.write_text(
                    json.dumps(project.to_dict(), indent=2, default=str),
                    encoding="utf-8",
                )

        return success

    def import_project(
        self,
        source_root: Path,
    ) -> Optional[Dict[str, Any]]:
        """Import bundle to workspace.

        Args:
            source_root: Path to the project's source code.

        Returns:
            Import result dict, or None if failed.
        """
        source_root = Path(source_root).resolve()

        # Find bundle
        bundle = find_bundle(source_root)
        if not bundle:
            return None

        # Import
        result = bundle.import_to_workspace(self.workspace_root)

        if result:
            # Open project in workspace
            self.project_manager.open_project(source_root)

        return result

    def get_sync_status(self, project_name: str) -> SyncStatus:
        """Get sync status for a project.

        Args:
            project_name: Name of the project.

        Returns:
            SyncStatus for the project.
        """
        # Check workspace
        project = self.project_manager.get_project(project_name)
        workspace_exists = project is not None and project.status == "active"

        workspace_run_id = None
        workspace_last_modified = None

        if project:
            workspace_run_id = project.last_run_id
            workspace_last_modified = project.last_run_at

        # Check bundle
        bundle = None
        bundle_exists = False
        bundle_run_id = None
        bundle_last_sync = None

        if project:
            source_root = Path(project.source_root)
            bundle = find_bundle(source_root)
            if bundle:
                bundle_exists = True
                info = bundle.get_info()
                if info:
                    bundle_run_id = info.get("last_run_id")
                    bundle_last_sync = info.get("last_sync")

        # Determine sync status
        in_sync = False
        recommendation = "none"

        if not workspace_exists and not bundle_exists:
            recommendation = "none"
        elif workspace_exists and not bundle_exists:
            recommendation = "export"  # Workspace has data, bundle doesn't
        elif not workspace_exists and bundle_exists:
            recommendation = "import"  # Bundle has data, workspace doesn't
        elif workspace_run_id == bundle_run_id:
            in_sync = True
            recommendation = "none"
        elif workspace_run_id and bundle_run_id:
            # Both have different run IDs - workspace is newer
            recommendation = "export"
        else:
            recommendation = "export"

        return SyncStatus(
            project_name=project_name,
            workspace_exists=workspace_exists,
            bundle_exists=bundle_exists,
            in_sync=in_sync,
            workspace_run_id=workspace_run_id,
            bundle_run_id=bundle_run_id,
            workspace_last_modified=workspace_last_modified,
            bundle_last_sync=bundle_last_sync,
            recommendation=recommendation,
        )

    def sync_project(
        self,
        project_name: str,
        prefer: str = "workspace",
    ) -> Dict[str, Any]:
        """Full sync for a project.

        Args:
            project_name: Name of the project.
            prefer: Which side to prefer on conflict ("workspace" or "bundle").

        Returns:
            Sync result dict.
        """
        status = self.get_sync_status(project_name)

        result = {
            "project_name": project_name,
            "action": "none",
            "success": True,
            "details": {},
        }

        if status.in_sync:
            result["action"] = "none"
            result["details"] = {"message": "Already in sync"}
            return result

        if status.recommendation == "export":
            if status.workspace_run_id:
                success = self.export_project(
                    project_name,
                    status.workspace_run_id,
                )
                result["action"] = "export"
                result["success"] = success
                result["details"] = {
                    "run_id": status.workspace_run_id,
                    "exported": success,
                }
        elif status.recommendation == "import":
            project = self.project_manager.get_project(project_name)
            if project:
                import_result = self.import_project(Path(project.source_root))
                result["action"] = "import"
                result["success"] = import_result is not None
                result["details"] = import_result or {"error": "Import failed"}
        elif status.recommendation == "conflict":
            if prefer == "workspace" and status.workspace_run_id:
                success = self.export_project(
                    project_name,
                    status.workspace_run_id,
                )
                result["action"] = "export (conflict resolved)"
                result["success"] = success
            elif prefer == "bundle":
                project = self.project_manager.get_project(project_name)
                if project:
                    import_result = self.import_project(Path(project.source_root))
                    result["action"] = "import (conflict resolved)"
                    result["success"] = import_result is not None

        return result

    def auto_sync_after_run(
        self,
        project_name: str,
        run_id: str,
        run_config: Optional[Dict[str, Any]] = None,
        sync_warden: bool = True,
    ) -> bool:
        """Automatically sync after a run completes.

        Call this after each successful run to keep bundle up to date.

        Args:
            project_name: Name of the project.
            run_id: Run ID that just completed.
            run_config: Run configuration used.
            sync_warden: Whether to also sync warden state.

        Returns:
            True if sync successful.
        """
        success = self.export_project(project_name, run_id, run_config)

        # Also sync warden state if requested
        if success and sync_warden:
            self.sync_warden_to_bundle(project_name)

        return success

    def sync_warden_to_bundle(self, project_name: str) -> bool:
        """Sync warden state from workspace to bundle.

        Args:
            project_name: Name of the project.

        Returns:
            True if sync successful.
        """
        project = self.project_manager.get_project(project_name)
        if not project:
            return False

        source_root = Path(project.source_root)
        bundle = find_bundle(source_root)
        if not bundle:
            return False

        workspace_warden_dir = self.workspace_root / "warden"
        if not workspace_warden_dir.exists():
            return False

        return bundle.export_warden_state(workspace_warden_dir)

    def sync_warden_from_bundle(self, project_name: str) -> bool:
        """Sync warden state from bundle to workspace.

        Args:
            project_name: Name of the project.

        Returns:
            True if sync successful.
        """
        project = self.project_manager.get_project(project_name)
        if not project:
            return False

        source_root = Path(project.source_root)
        bundle = find_bundle(source_root)
        if not bundle:
            return False

        workspace_warden_dir = self.workspace_root / "warden"
        return bundle.import_warden_state(workspace_warden_dir)

    def list_out_of_sync(self) -> List[SyncStatus]:
        """List all projects that are out of sync.

        Returns:
            List of SyncStatus for out-of-sync projects.
        """
        out_of_sync = []

        for project in self.project_manager.list_active():
            status = self.get_sync_status(project.project_name)
            if not status.in_sync and status.recommendation != "none":
                out_of_sync.append(status)

        return out_of_sync

    def sync_all(self, prefer: str = "workspace") -> List[Dict[str, Any]]:
        """Sync all out-of-sync projects.

        Args:
            prefer: Which side to prefer on conflict.

        Returns:
            List of sync results.
        """
        results = []

        for status in self.list_out_of_sync():
            result = self.sync_project(status.project_name, prefer)
            results.append(result)

        return results


# -----------------------------------------------------------------------------
# Convenience functions
# -----------------------------------------------------------------------------

def get_sync_manager(workspace_root: Path) -> SyncManager:
    """Get a sync manager for the workspace."""
    return SyncManager(workspace_root)


def export_to_bundle(
    workspace_root: Path,
    project_name: str,
    run_id: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Export workspace results to bundle."""
    sync = SyncManager(workspace_root)
    return sync.export_project(project_name, run_id, run_config)


def import_from_bundle(
    workspace_root: Path,
    source_root: Path,
) -> Optional[Dict[str, Any]]:
    """Import bundle to workspace."""
    sync = SyncManager(workspace_root)
    return sync.import_project(source_root)


def check_sync_status(
    workspace_root: Path,
    project_name: str,
) -> SyncStatus:
    """Check sync status for a project."""
    sync = SyncManager(workspace_root)
    return sync.get_sync_status(project_name)


def get_sync_status(
    workspace_root: Path,
    project_name: str,
) -> Dict[str, Any]:
    """Get detailed sync status for warden consumption.

    This function provides a dict with detailed sync information including
    what runs are missing on each side and any conflicts detected.

    Args:
        workspace_root: Path to workspace root.
        project_name: Name of the project.

    Returns:
        Dict with sync status details.
    """
    workspace_root = Path(workspace_root)
    sync = SyncManager(workspace_root)

    # Get basic status
    status = sync.get_sync_status(project_name)

    result = status.to_dict()

    # Get project for more details
    project = sync.project_manager.get_project(project_name)
    if not project:
        result["missing_in_workspace"] = []
        result["missing_in_bundle"] = []
        result["conflicts"] = []
        return result

    # Get runs in workspace
    workspace_runs_dir = workspace_root / "results" / project_name
    workspace_runs = set()
    if workspace_runs_dir.exists():
        workspace_runs = {d.name for d in workspace_runs_dir.iterdir() if d.is_dir()}

    # Get runs in bundle
    source_root = Path(project.source_root)
    bundle = find_bundle(source_root)
    bundle_runs = set()

    if bundle and bundle.results_dir.exists():
        bundle_runs = {d.name for d in bundle.results_dir.iterdir() if d.is_dir()}

    # Calculate differences
    result["missing_in_workspace"] = sorted(bundle_runs - workspace_runs)
    result["missing_in_bundle"] = sorted(workspace_runs - bundle_runs)

    # Check for conflicts (same run ID, different content)
    conflicts = []
    common_runs = workspace_runs & bundle_runs

    for run_id in common_runs:
        workspace_run = workspace_runs_dir / run_id
        bundle_run = bundle.results_dir / run_id if bundle else None

        if bundle_run and bundle_run.exists():
            # Compare file counts and sizes as a simple conflict check
            ws_files = list(workspace_run.rglob("*.json"))
            bd_files = list(bundle_run.rglob("*.json"))

            if len(ws_files) != len(bd_files):
                conflicts.append({
                    "run_id": run_id,
                    "reason": f"Different file counts: workspace={len(ws_files)}, bundle={len(bd_files)}",
                })
            else:
                # Check file sizes
                for ws_file in ws_files:
                    rel_path = ws_file.relative_to(workspace_run)
                    bd_file = bundle_run / rel_path
                    if bd_file.exists():
                        if ws_file.stat().st_size != bd_file.stat().st_size:
                            conflicts.append({
                                "run_id": run_id,
                                "reason": f"Different content in {rel_path}",
                            })
                            break

    result["conflicts"] = conflicts

    # Include source type if available
    result["source_type"] = project.to_dict().get("source_type", "local")

    return result
