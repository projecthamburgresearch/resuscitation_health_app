"""Portable Blueprint bundle system.

A bundle is a self-contained, portable copy of Blueprint analysis that lives
alongside the source code (like SciTools .und files). It contains everything
needed to understand and re-run the analysis.

Bundle location: {project_root}/{project_name}_blueprint/

Key concepts:
- Bundle: Portable folder containing config + results
- Export: Copy workspace results to bundle
- Import: Restore workspace from bundle
- Sync: Keep workspace and bundle aligned

Usage:
    from src.core.bundle import Bundle

    # Create or load bundle
    bundle = Bundle(project_root)

    # Export current workspace state to bundle
    bundle.export_from_workspace(workspace_root, run_id)

    # Import bundle to workspace (restore)
    bundle.import_to_workspace(workspace_root)

    # Check if bundle exists
    if bundle.exists():
        info = bundle.get_info()
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BundleManifest:
    """Manifest for a Blueprint bundle."""
    project_name: str
    project_root: str
    created_at: str
    last_sync: Optional[str] = None
    blueprint_version: str = "0.2.0"
    workspace_link: Optional[str] = None
    total_syncs: int = 0
    last_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_root": self.project_root,
            "created_at": self.created_at,
            "last_sync": self.last_sync,
            "blueprint_version": self.blueprint_version,
            "workspace_link": self.workspace_link,
            "total_syncs": self.total_syncs,
            "last_run_id": self.last_run_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BundleManifest":
        return cls(
            project_name=data["project_name"],
            project_root=data["project_root"],
            created_at=data["created_at"],
            last_sync=data.get("last_sync"),
            blueprint_version=data.get("blueprint_version", "0.2.0"),
            workspace_link=data.get("workspace_link"),
            total_syncs=data.get("total_syncs", 0),
            last_run_id=data.get("last_run_id"),
        )


@dataclass
class RunConfig:
    """Configuration for a Blueprint run."""
    run_id: str
    domains: List[str]
    preset: str
    focus_path: Optional[str] = None
    output_config: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "domains": self.domains,
            "preset": self.preset,
            "focus_path": self.focus_path,
            "output_config": self.output_config,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunConfig":
        return cls(
            run_id=data["run_id"],
            domains=data.get("domains", ["xray", "manifest", "sonar"]),
            preset=data.get("preset", "standard"),
            focus_path=data.get("focus_path"),
            output_config=data.get("output_config", {}),
            timestamp=data.get("timestamp"),
        )


@dataclass
class SyncRecord:
    """Record of a sync operation."""
    sync_id: str
    timestamp: str
    direction: str  # "export" or "import"
    run_id: Optional[str]
    files_synced: List[str]
    workspace_path: Optional[str] = None
    success: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "run_id": self.run_id,
            "files_synced": self.files_synced,
            "workspace_path": self.workspace_path,
            "success": self.success,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncRecord":
        return cls(
            sync_id=data["sync_id"],
            timestamp=data["timestamp"],
            direction=data["direction"],
            run_id=data.get("run_id"),
            files_synced=data.get("files_synced", []),
            workspace_path=data.get("workspace_path"),
            success=data.get("success", True),
            notes=data.get("notes", ""),
        )


class Bundle:
    """Portable Blueprint bundle for a project."""

    BUNDLE_SUFFIX = "_blueprint"

    def __init__(self, project_root: Path):
        """Initialize bundle for a project.

        Args:
            project_root: Path to the project's source code.
        """
        self.project_root = Path(project_root).resolve()
        self.project_name = self.project_root.name
        self.bundle_dir = self.project_root / f"{self.project_name}{self.BUNDLE_SUFFIX}"

        # Bundle subdirectories
        self.last_run_dir = self.bundle_dir / "last-run"
        self.results_dir = self.bundle_dir / "results"
        self.configs_dir = self.bundle_dir / "configs"
        self.warden_dir = self.bundle_dir / "warden"
        self.manifest_path = self.bundle_dir / "bundle.json"
        self.sync_history_path = self.bundle_dir / "sync-history.json"

    def exists(self) -> bool:
        """Check if bundle exists."""
        return self.bundle_dir.exists() and self.manifest_path.exists()

    def create(self, workspace_link: Optional[str] = None) -> bool:
        """Create a new bundle.

        Args:
            workspace_link: Optional link to workspace project.

        Returns:
            True if created successfully.
        """
        if self.exists():
            return True  # Already exists

        try:
            # Create directories
            self.bundle_dir.mkdir(parents=True, exist_ok=True)
            self.last_run_dir.mkdir(exist_ok=True)
            self.results_dir.mkdir(exist_ok=True)
            self.configs_dir.mkdir(exist_ok=True)
            self.warden_dir.mkdir(exist_ok=True)
            (self.warden_dir / "commits").mkdir(exist_ok=True)
            (self.warden_dir / "decisions").mkdir(exist_ok=True)

            # Create manifest
            manifest = BundleManifest(
                project_name=self.project_name,
                project_root=str(self.project_root),
                created_at=datetime.now().isoformat(),
                workspace_link=workspace_link,
            )
            self._save_manifest(manifest)

            # Create empty sync history
            self._save_sync_history([])

            return True
        except OSError:
            return False

    def get_info(self) -> Optional[Dict[str, Any]]:
        """Get bundle information.

        Returns:
            Bundle info dict, or None if bundle doesn't exist.
        """
        if not self.exists():
            return None

        manifest = self._load_manifest()
        if not manifest:
            return None

        # Get additional info
        has_results = self.results_dir.exists() and any(self.results_dir.iterdir())
        has_last_run = self.last_run_dir.exists() and (self.last_run_dir / "config.json").exists()

        return {
            "project_name": manifest.project_name,
            "project_root": manifest.project_root,
            "bundle_path": str(self.bundle_dir),
            "created_at": manifest.created_at,
            "last_sync": manifest.last_sync,
            "blueprint_version": manifest.blueprint_version,
            "workspace_link": manifest.workspace_link,
            "total_syncs": manifest.total_syncs,
            "last_run_id": manifest.last_run_id,
            "has_results": has_results,
            "has_last_run": has_last_run,
        }

    def export_from_workspace(
        self,
        workspace_root: Path,
        project_name: str,
        run_id: str,
        run_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Export workspace results to bundle.

        Args:
            workspace_root: Path to workspace root.
            project_name: Name of the project.
            run_id: Run ID to export.
            run_config: Optional run configuration to save.

        Returns:
            True if export successful.
        """
        workspace_root = Path(workspace_root)

        # Ensure bundle exists
        if not self.exists():
            self.create(workspace_link=str(workspace_root / "projects" / project_name))

        # Find results directory
        results_source = workspace_root / "results" / project_name / run_id
        if not results_source.exists():
            return False

        try:
            # Clear and copy results
            if self.results_dir.exists():
                shutil.rmtree(self.results_dir)
            shutil.copytree(results_source, self.results_dir)

            # Save run config
            if run_config:
                config = RunConfig(
                    run_id=run_id,
                    domains=run_config.get("domains", ["xray", "manifest", "sonar"]),
                    preset=run_config.get("preset", "standard"),
                    focus_path=run_config.get("focus_path"),
                    output_config=run_config.get("output_config", {}),
                    timestamp=datetime.now().isoformat(),
                )
                self._save_run_config(config)

            # Copy run_meta if exists
            run_meta_source = results_source / "run_meta.json"
            if run_meta_source.exists():
                shutil.copy2(run_meta_source, self.last_run_dir / "meta.json")

            # Update manifest
            manifest = self._load_manifest()
            if manifest:
                manifest.last_sync = datetime.now().isoformat()
                manifest.last_run_id = run_id
                manifest.total_syncs += 1
                manifest.workspace_link = str(workspace_root / "projects" / project_name)
                self._save_manifest(manifest)

            # Record sync
            self._record_sync(
                direction="export",
                run_id=run_id,
                files_synced=self._list_files(self.results_dir),
                workspace_path=str(workspace_root),
            )

            return True
        except OSError:
            return False

    def import_to_workspace(
        self,
        workspace_root: Path,
    ) -> Optional[Dict[str, Any]]:
        """Import bundle to workspace.

        Args:
            workspace_root: Path to workspace root.

        Returns:
            Dict with import info, or None if failed.
        """
        if not self.exists():
            return None

        workspace_root = Path(workspace_root)
        manifest = self._load_manifest()
        if not manifest:
            return None

        try:
            # Determine run_id
            run_id = manifest.last_run_id or datetime.now().strftime("%Y-%m-%d_%H%M%S")

            # Create results directory in workspace
            results_dest = workspace_root / "results" / self.project_name / run_id
            results_dest.mkdir(parents=True, exist_ok=True)

            # Copy results
            if self.results_dir.exists():
                for item in self.results_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, results_dest / item.name)

            # Load run config
            run_config = self._load_run_config()

            # Update manifest
            manifest.workspace_link = str(workspace_root / "projects" / self.project_name)
            manifest.last_sync = datetime.now().isoformat()
            manifest.total_syncs += 1
            self._save_manifest(manifest)

            # Record sync
            self._record_sync(
                direction="import",
                run_id=run_id,
                files_synced=self._list_files(results_dest),
                workspace_path=str(workspace_root),
            )

            return {
                "project_name": self.project_name,
                "run_id": run_id,
                "results_path": str(results_dest),
                "run_config": run_config.to_dict() if run_config else None,
            }
        except OSError:
            return None

    def get_last_run_config(self) -> Optional[RunConfig]:
        """Get the last run configuration."""
        return self._load_run_config()

    def get_sync_history(self) -> List[SyncRecord]:
        """Get sync history."""
        return self._load_sync_history()

    def export_warden_state(
        self,
        workspace_warden_dir: Path,
    ) -> bool:
        """Export warden state from workspace to bundle.

        Args:
            workspace_warden_dir: Path to workspace/warden/

        Returns:
            True if export successful.
        """
        workspace_warden_dir = Path(workspace_warden_dir)
        if not workspace_warden_dir.exists():
            return False

        try:
            # Export decisions
            decisions_src = workspace_warden_dir / "decisions" / "decisions.json"
            if decisions_src.exists():
                decisions_dest = self.warden_dir / "decisions"
                decisions_dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(decisions_src, decisions_dest / "decisions.json")

            # Export commits
            commits_src = workspace_warden_dir / "commits" / "commits.json"
            if commits_src.exists():
                commits_dest = self.warden_dir / "commits"
                commits_dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(commits_src, commits_dest / "commits.json")

            # Export memory summary (not full memory for portability)
            memory_src = workspace_warden_dir / "memory" / "memory.json"
            if memory_src.exists():
                memory_data = json.loads(memory_src.read_text())
                # Only keep learnings category for portability
                learnings = [
                    item for item in memory_data.get("items", [])
                    if item.get("category") == "learnings"
                ]
                memory_summary = {
                    "exported_at": datetime.now().isoformat(),
                    "learnings": learnings,
                }
                (self.warden_dir / "memory_summary.json").write_text(
                    json.dumps(memory_summary, indent=2)
                )

            return True
        except OSError:
            return False

    def import_warden_state(
        self,
        workspace_warden_dir: Path,
    ) -> bool:
        """Import warden state from bundle to workspace.

        Args:
            workspace_warden_dir: Path to workspace/warden/

        Returns:
            True if import successful.
        """
        workspace_warden_dir = Path(workspace_warden_dir)
        workspace_warden_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Import decisions
            decisions_src = self.warden_dir / "decisions" / "decisions.json"
            if decisions_src.exists():
                decisions_dest = workspace_warden_dir / "decisions"
                decisions_dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(decisions_src, decisions_dest / "decisions.json")

            # Import commits
            commits_src = self.warden_dir / "commits" / "commits.json"
            if commits_src.exists():
                commits_dest = workspace_warden_dir / "commits"
                commits_dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(commits_src, commits_dest / "commits.json")

            # Import learnings to memory
            memory_summary_src = self.warden_dir / "memory_summary.json"
            if memory_summary_src.exists():
                memory_data = json.loads(memory_summary_src.read_text())
                learnings = memory_data.get("learnings", [])

                if learnings:
                    memory_dest = workspace_warden_dir / "memory"
                    memory_dest.mkdir(parents=True, exist_ok=True)
                    memory_file = memory_dest / "memory.json"

                    # Merge with existing memory if present
                    existing = {"items": []}
                    if memory_file.exists():
                        try:
                            existing = json.loads(memory_file.read_text())
                        except json.JSONDecodeError:
                            pass

                    # Add imported learnings
                    existing_keys = {item["key"] for item in existing.get("items", [])}
                    for learning in learnings:
                        if learning["key"] not in existing_keys:
                            existing["items"].append(learning)

                    memory_file.write_text(json.dumps(existing, indent=2))

            return True
        except OSError:
            return False

    def get_warden_summary(self) -> Dict[str, Any]:
        """Get summary of warden state in bundle."""
        summary = {
            "has_decisions": False,
            "decision_count": 0,
            "has_commits": False,
            "commit_count": 0,
            "has_learnings": False,
            "learning_count": 0,
        }

        decisions_file = self.warden_dir / "decisions" / "decisions.json"
        if decisions_file.exists():
            try:
                data = json.loads(decisions_file.read_text())
                summary["has_decisions"] = True
                summary["decision_count"] = len(data.get("decisions", []))
            except (json.JSONDecodeError, OSError):
                pass

        commits_file = self.warden_dir / "commits" / "commits.json"
        if commits_file.exists():
            try:
                data = json.loads(commits_file.read_text())
                summary["has_commits"] = True
                summary["commit_count"] = len(data.get("commits", []))
            except (json.JSONDecodeError, OSError):
                pass

        memory_file = self.warden_dir / "memory_summary.json"
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text())
                learnings = data.get("learnings", [])
                summary["has_learnings"] = len(learnings) > 0
                summary["learning_count"] = len(learnings)
            except (json.JSONDecodeError, OSError):
                pass

        return summary

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get bundle metadata from bundle.json."""
        if not self.manifest_path.exists():
            return None
        try:
            data = json.loads(self.manifest_path.read_text())
            return {
                "name": data.get("project_name", self.project_name),
                "version": data.get("blueprint_version", "0.2.0"),
                "created_at": data.get("created_at"),
                "last_sync": data.get("last_sync"),
            }
        except (json.JSONDecodeError, OSError):
            return None

    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------

    def _load_manifest(self) -> Optional[BundleManifest]:
        """Load bundle manifest."""
        if not self.manifest_path.exists():
            return None
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return BundleManifest.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_manifest(self, manifest: BundleManifest) -> None:
        """Save bundle manifest."""
        self.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _load_run_config(self) -> Optional[RunConfig]:
        """Load last run config."""
        config_path = self.last_run_dir / "config.json"
        if not config_path.exists():
            return None
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return RunConfig.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_run_config(self, config: RunConfig) -> None:
        """Save run config."""
        self.last_run_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.last_run_dir / "config.json"
        config_path.write_text(
            json.dumps(config.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def _load_sync_history(self) -> List[SyncRecord]:
        """Load sync history."""
        if not self.sync_history_path.exists():
            return []
        try:
            data = json.loads(self.sync_history_path.read_text(encoding="utf-8"))
            return [SyncRecord.from_dict(r) for r in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_sync_history(self, history: List[SyncRecord]) -> None:
        """Save sync history."""
        self.sync_history_path.write_text(
            json.dumps([r.to_dict() for r in history], indent=2, default=str),
            encoding="utf-8",
        )

    def _record_sync(
        self,
        direction: str,
        run_id: Optional[str],
        files_synced: List[str],
        workspace_path: Optional[str] = None,
        notes: str = "",
    ) -> None:
        """Record a sync operation."""
        history = self._load_sync_history()

        sync_id = f"sync-{len(history) + 1:03d}"
        record = SyncRecord(
            sync_id=sync_id,
            timestamp=datetime.now().isoformat(),
            direction=direction,
            run_id=run_id,
            files_synced=files_synced,
            workspace_path=workspace_path,
            notes=notes,
        )
        history.append(record)

        self._save_sync_history(history)

    def _list_files(self, directory: Path) -> List[str]:
        """List files in a directory (relative paths)."""
        if not directory.exists():
            return []
        return [str(f.relative_to(directory)) for f in directory.rglob("*") if f.is_file()]


# -----------------------------------------------------------------------------
# Convenience functions
# -----------------------------------------------------------------------------

def get_bundle(project_root: Path) -> Bundle:
    """Get or create a bundle for a project."""
    return Bundle(project_root)


def find_bundle(project_root: Path) -> Optional[Bundle]:
    """Find existing bundle for a project, or None if not exists."""
    bundle = Bundle(project_root)
    if bundle.exists():
        return bundle
    return None


def list_bundles(search_root: Path, max_depth: int = 3) -> List[Bundle]:
    """Find all Blueprint bundles under a directory.

    Args:
        search_root: Directory to search.
        max_depth: Maximum directory depth to search.

    Returns:
        List of Bundle objects found.
    """
    bundles = []
    search_root = Path(search_root)

    def search(path: Path, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            for item in path.iterdir():
                if item.is_dir():
                    if item.name.endswith(Bundle.BUNDLE_SUFFIX):
                        # Found a bundle directory
                        project_name = item.name[:-len(Bundle.BUNDLE_SUFFIX)]
                        project_root = item.parent
                        bundle = Bundle(project_root)
                        if bundle.exists():
                            bundles.append(bundle)
                    else:
                        search(item, depth + 1)
        except PermissionError:
            pass

    search(search_root, 0)
    return bundles
