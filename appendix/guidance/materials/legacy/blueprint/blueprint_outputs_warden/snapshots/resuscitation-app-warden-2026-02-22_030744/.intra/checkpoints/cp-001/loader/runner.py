"""Workspace run orchestrator.

Loads deploy targets, applies .bpignore, runs selected domains,
and writes results to the workspace results folder.

Integrates with the status system for observability and anomaly detection.
Each run creates a snapshot (bootable Blueprint copy) for isolation and patching.

Execution modes:
    1. Snapshot mode (default): Boot a snapshot and run analysis from it.
       - Creates workspace/snapshots/<project>-<run-id>/src/
       - Runs via subprocess with snapshot's src on PYTHONPATH
       - Enables patching and re-runs within the same snapshot

    2. Direct mode (use_snapshot=False): Run analysis directly from main src/.
       - No snapshot created
       - Faster but no isolation or patching capability
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src import __version__
from src.core.config import BlueprintConfig
from src.core.io_utils import ensure_dir
from src.core.models import AnalysisResult
from src.core.snapshot import (
    boot_and_run,
    boot_snapshot,
    run_snapshot,
    SnapshotRunResult,
)
from src.core.status import StatusReporter, create_status_reporter
from src.loader.bpignore import load_bpignore, merge_patterns
from src.loader.deploy import (
    auto_discover_local_targets,
    load_deploy_yaml,
    resolve_target_path,
)
from src.loader.schema import (
    DeployConfig,
    DeployTarget,
    RunMeta,
    TargetType,
    WorkspaceConfig,
)


# ---------------------------------------------------------------------------
# Domain registry -- lazy imports to avoid circular dependencies
# ---------------------------------------------------------------------------

def _get_domain_engine(domain_name: str):
    """Lazy-import and return a domain engine instance by name."""
    if domain_name == "xray":
        from src.xray.engine import XRayEngine
        return XRayEngine()
    elif domain_name == "manifest":
        from src.manifest.builder import build_manifest, save_manifest
        return ("manifest", build_manifest, save_manifest)
    elif domain_name == "cortex":
        from src.cortex.engine import CortexEngine
        return CortexEngine()
    elif domain_name == "registry":
        from src.registry.engine import RegistryEngine
        return RegistryEngine()
    elif domain_name == "sonar":
        from src.sonar.engine import SonarEngine
        return SonarEngine()
    elif domain_name == "synapse":
        from src.synapse.engine import SynapseEngine
        return SynapseEngine()
    else:
        raise ValueError(f"Unknown domain: {domain_name}")


# ---------------------------------------------------------------------------
# Run orchestrator
# ---------------------------------------------------------------------------

def run_target(
    target: DeployTarget,
    workspace_root: Path,
    domains: List[str],
    preset: str = "standard",
    output_config: Optional[Dict[str, Any]] = None,
    status_reporter: Optional[StatusReporter] = None,
    use_snapshot: bool = True,
) -> RunMeta:
    """Run Blueprint analysis on a single deploy target.

    Args:
        target: The deploy target to analyze.
        workspace_root: Root of the workspace folder.
        domains: List of domain names to run.
        preset: Analysis preset (quick/standard/deep).
        output_config: Output preferences from deploy.yaml.
        status_reporter: Optional StatusReporter for observability.
        use_snapshot: If True (default), boot a snapshot and run from it.
                      If False, run directly from main src/ (faster but no isolation).

    Returns:
        RunMeta with results metadata.
    """
    out_cfg = output_config or {}
    project_name = target.name or "unknown"

    # Resolve the target path first (needed for both modes)
    project_root: Optional[Path] = None

    if target.type == TargetType.GITHUB:
        from src.loader.github import clone_or_pull
        clone_dir = workspace_root / "intake" / "local" / (
            target.name or target.repo.split("/")[-1]
        )
        try:
            project_root = clone_or_pull(target, clone_dir)
        except RuntimeError as exc:
            return _error_meta(target, f"Clone failed: {exc}")
    else:
        project_root = resolve_target_path(target, workspace_root)
        if project_root is None or not project_root.exists():
            return _error_meta(target, f"Target path not found: {target.path}")

    # Load .bpignore patterns
    bpignore_patterns: List[str] = []
    if target.bpignore:
        bpignore_patterns = load_bpignore(project_root)

    merged_excludes = merge_patterns(bpignore_patterns)

    # Build focus path
    focus_path: Optional[Path] = None
    if target.focus:
        focus_path = (project_root / target.focus).resolve()
        if not focus_path.exists():
            return _error_meta(target, f"Focus path not found: {target.focus}")

    # Get project name from target or path
    project_name = target.name or project_root.name

    # Include patterns
    include_patterns = target.include or []
    if target.files:
        include_patterns = target.files

    # -------------------------------------------------------------------------
    # SNAPSHOT MODE: Boot a snapshot and run from it
    # -------------------------------------------------------------------------
    if use_snapshot:
        result = boot_and_run(
            workspace_root=workspace_root,
            project_root=project_root,
            project_name=project_name,
            domains=domains,
            preset=preset,
            output_config=out_cfg,
            bpignore_patterns=bpignore_patterns,
            focus_path=focus_path,
            include_patterns=include_patterns,
            exclude_patterns=merged_excludes,
        )

        # Convert SnapshotRunResult to RunMeta
        return RunMeta(
            run_id=result.run_id,
            project_name=project_name,
            source_type=target.type.value,
            source_path=str(project_root),
            domains_run=domains,
            preset=preset,
            duration_seconds=result.duration_seconds,
            blueprint_version=__version__,
            bpignore_patterns=bpignore_patterns,
            files_scanned=result.files_scanned,
            entities_found=result.entities_found,
            edges_found=result.edges_found,
            errors=[{"error": result.error_message}] if result.error_message else [],
            snapshot_id=result.snapshot_id,
        )

    # -------------------------------------------------------------------------
    # DIRECT MODE: Run directly from main src/ (legacy, no isolation)
    # -------------------------------------------------------------------------
    return _run_target_direct(
        target=target,
        project_root=project_root,
        workspace_root=workspace_root,
        domains=domains,
        preset=preset,
        output_config=out_cfg,
        status_reporter=status_reporter,
        bpignore_patterns=bpignore_patterns,
        merged_excludes=merged_excludes,
        focus_path=focus_path,
        include_patterns=include_patterns,
    )


def _run_target_direct(
    target: DeployTarget,
    project_root: Path,
    workspace_root: Path,
    domains: List[str],
    preset: str,
    output_config: Dict[str, Any],
    status_reporter: Optional[StatusReporter],
    bpignore_patterns: List[str],
    merged_excludes: List[str],
    focus_path: Optional[Path],
    include_patterns: List[str],
) -> RunMeta:
    """Run Blueprint analysis directly from main src/ (no snapshot).

    This is the legacy mode - faster but no isolation or patching capability.
    """
    t0 = time.time()
    project_name = target.name or project_root.name

    # Create status reporter if not provided
    reporter = status_reporter or create_status_reporter(project_name)
    reporter.start_run({
        "target_name": project_name,
        "target_type": target.type.value,
        "domains": domains,
        "preset": preset,
        "mode": "direct",
    })

    # Build config
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    results_dir = workspace_root / "results" / project_name / run_id
    ensure_dir(results_dir)

    config = BlueprintConfig(
        root_path=project_root,
        output_path=results_dir,
        xray_preset=preset,
        extract_git=output_config.get("git_analysis", False),
        manifest_format=output_config.get("manifest_format", "yaml"),
        exclude_patterns=merged_excludes,
        include_patterns=include_patterns,
        focus_path=focus_path,
        cortex_dry_run=True,
    )
    config.apply_preset(preset)

    # --- Run domains in pipeline order ---
    all_results: List[AnalysisResult] = []
    all_errors: List[Dict[str, Any]] = []
    xray_result: Optional[AnalysisResult] = None

    # Domain execution order matters (later domains depend on xray)
    domain_order = ["xray", "manifest", "cortex", "registry", "sonar", "synapse"]
    domains_to_run = [d for d in domain_order if d in domains]

    for domain_name in domains_to_run:
        try:
            reporter.start_domain(domain_name, __version__)
            result = _run_single_domain(
                domain_name, config, all_results, xray_result, results_dir, output_config,
                reporter=reporter,
            )
            if result:
                all_results.append(result)
                reporter.end_domain(
                    domain_name,
                    entities=result.entity_count(),
                    edges=result.edge_count(),
                    success=True,
                    errors=result.errors if result.errors else None,
                )
                if domain_name == "xray":
                    xray_result = result
            else:
                reporter.end_domain(domain_name, success=True)
        except Exception as exc:
            reporter.log_error(domain_name, f"Domain failed: {exc}", exception=exc)
            reporter.end_domain(domain_name, success=False, errors=[{"error": str(exc)}])
            all_errors.append({
                "domain": domain_name,
                "error": str(exc),
            })

    # Build run metadata
    elapsed = round(time.time() - t0, 3)
    files_scanned = 0
    entities_found = 0
    edges_found = 0
    if xray_result:
        files_scanned = xray_result.stats.get("files_scanned", 0)
        entities_found = xray_result.entity_count()
        edges_found = xray_result.edge_count()

    run_meta = RunMeta(
        run_id=run_id,
        project_name=project_name,
        source_type=target.type.value,
        source_path=str(project_root),
        domains_run=domains_to_run,
        preset=preset,
        duration_seconds=elapsed,
        blueprint_version=__version__,
        bpignore_patterns=bpignore_patterns,
        files_scanned=files_scanned,
        entities_found=entities_found,
        edges_found=edges_found,
        errors=all_errors,
    )

    # Save run metadata
    meta_path = results_dir / "run_meta.json"
    meta_path.write_text(
        json.dumps(run_meta.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )

    # End run and save status report
    success = len(all_errors) == 0
    reporter.end_run(success=success)
    reporter.save(workspace_root)

    # Update latest symlink (skip on Windows if symlinks not available)
    _update_latest_link(workspace_root / "results" / project_name, run_id)

    return run_meta


def _run_single_domain(
    domain_name: str,
    config: BlueprintConfig,
    prior_results: List[AnalysisResult],
    xray_result: Optional[AnalysisResult],
    results_dir: Path,
    output_config: Dict[str, Any],
    reporter: Optional[StatusReporter] = None,
) -> Optional[AnalysisResult]:
    """Run a single domain and save its output.

    Returns:
        The AnalysisResult, or None if the domain is handled specially.
    """
    if domain_name == "manifest":
        # Manifest is special -- uses builder, not engine
        if xray_result is None:
            return None
        from src.manifest.builder import build_manifest, save_manifest
        m = build_manifest(xray_result)
        fmt = output_config.get("manifest_format", "yaml")
        save_manifest(m, results_dir, fmt=fmt)
        # Return a minimal AnalysisResult for tracking
        return AnalysisResult(
            domain="manifest",
            version="1.0.0",
            root_path=str(config.root_path),
            stats={
                "entities_indexed": len(m.entities),
                "relationships": len(m.relationships),
            },
        )

    # Standard domain engine
    engine = _get_domain_engine(domain_name)

    if domain_name == "xray":
        result = engine.run(config)
        # Export xray outputs
        from src.xray.exporter import export_json, export_llm_bundle, export_markdown
        export_json(result, results_dir)
        export_llm_bundle(result, results_dir,
                          max_nodes=config.llm_max_nodes,
                          max_edges=config.llm_max_edges)
        export_markdown(result, results_dir)
        return result

    # Domains that depend on xray
    if xray_result is None:
        return None

    result = engine.run(config, prior_results=[xray_result] + prior_results)

    # Save domain-specific output
    _save_domain_result(domain_name, result, results_dir)

    return result


def _save_domain_result(
    domain_name: str,
    result: AnalysisResult,
    results_dir: Path,
) -> None:
    """Save a domain's result as JSON."""
    output_path = results_dir / f"{domain_name}_report.json"
    data = result.model_dump(mode="json")
    output_path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def _error_meta(target: DeployTarget, message: str) -> RunMeta:
    """Create an error RunMeta when a target cannot be processed."""
    return RunMeta(
        run_id=datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        project_name=target.name or "unknown",
        source_type=target.type.value,
        source_path=target.path or target.repo,
        errors=[{"error": message}],
    )


def _update_latest_link(project_results_dir: Path, run_id: str) -> None:
    """Update the 'latest' symlink to point to the most recent run."""
    latest = project_results_dir / "latest"
    target = project_results_dir / run_id

    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(target.name)
    except OSError:
        # Symlinks may not be available on all Windows configurations.
        # Write a latest.txt file instead.
        try:
            latest_txt = project_results_dir / "latest.txt"
            latest_txt.write_text(run_id, encoding="utf-8")
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Batch runner - Single entry point for all Blueprint operations
# ---------------------------------------------------------------------------

def run_workspace(
    workspace_root: Path,
    deploy_config: Optional[DeployConfig] = None,
    target_filter: Optional[str] = None,
    domain_filter: Optional[List[str]] = None,
    auto_sync: bool = True,
) -> List[RunMeta]:
    """Run Blueprint analysis on all targets in the workspace.

    This is the SINGLE ENTRY POINT that integrates all systems:
    1. Reads deploy.yaml for targets, domains, preset
    2. Opens project via ProjectManager
    3. Boots snapshot with IntraVersioning
    4. Runs analysis domains
    5. Updates project with run results
    6. Syncs results to bundle (portable backup)

    Args:
        workspace_root: Root of the workspace folder.
        deploy_config: Pre-loaded deploy config. If None, loads from deploy.yaml.
        target_filter: Only run targets with this name.
        domain_filter: Override domain list from deploy.yaml.
        auto_sync: If True, sync results to bundle after each run.

    Returns:
        List of RunMeta for each target processed.
    """
    from src.core.project import ProjectManager
    from src.core.sync import SyncManager
    from src.core.intra import IntraVersioning

    # Load deploy config
    if deploy_config is None:
        deploy_path = workspace_root / "intake" / "deploy.yaml"
        if deploy_path.is_file():
            deploy_config = load_deploy_yaml(deploy_path)
        else:
            deploy_config = DeployConfig()

    # Auto-discover local targets if none specified
    targets = deploy_config.targets
    if not targets:
        targets = auto_discover_local_targets(workspace_root)

    # Apply target filter
    if target_filter:
        targets = [t for t in targets if t.name == target_filter]

    # Determine domains
    domains = domain_filter or deploy_config.domains

    # Initialize managers
    project_manager = ProjectManager(workspace_root)
    sync_manager = SyncManager(workspace_root) if auto_sync else None

    # Run each target
    results: List[RunMeta] = []
    for target in targets:
        meta = _run_target_full(
            target=target,
            workspace_root=workspace_root,
            domains=domains,
            preset=deploy_config.preset,
            output_config=deploy_config.output,
            project_manager=project_manager,
            sync_manager=sync_manager,
        )
        results.append(meta)

    return results


def _run_target_full(
    target: DeployTarget,
    workspace_root: Path,
    domains: List[str],
    preset: str,
    output_config: Dict[str, Any],
    project_manager,  # ProjectManager
    sync_manager,  # Optional[SyncManager]
) -> RunMeta:
    """Run a single target with full system integration.

    Integrates: ProjectManager, IntraVersioning, Snapshot, Bundle Sync
    """
    from src.core.intra import IntraVersioning

    # Resolve project path
    project_root = resolve_target_path(target, workspace_root)
    if project_root is None or not project_root.exists():
        return _error_meta(target, f"Target path not found: {target.path}")

    project_name = target.name or project_root.name

    # -------------------------------------------------------------------------
    # 1. PROJECT MANAGEMENT - Open/track project
    # -------------------------------------------------------------------------
    project_info = project_manager.open_project(project_root)

    # -------------------------------------------------------------------------
    # 2. RUN ANALYSIS (boots snapshot, runs domains)
    # -------------------------------------------------------------------------
    meta = run_target(
        target=target,
        workspace_root=workspace_root,
        domains=domains,
        preset=preset,
        output_config=output_config,
        use_snapshot=True,
    )

    # -------------------------------------------------------------------------
    # 3. INTRA-RUN VERSIONING - Log the run config and outcome
    # -------------------------------------------------------------------------
    if meta.snapshot_id:
        snapshot_dir = workspace_root / "snapshots" / meta.snapshot_id
        if snapshot_dir.exists():
            try:
                iv = IntraVersioning(snapshot_dir)
                change_id = iv.log_change(
                    change_type="parameter",
                    description=f"Run with preset={preset}, domains={domains}",
                    before={},
                    after={"preset": preset, "domains": domains},
                    run_id=meta.run_id,
                    auto_checkpoint=False,
                )
                iv.record_outcome(
                    change_id,
                    outcome=f"Files: {meta.files_scanned}, Entities: {meta.entities_found}, Edges: {meta.edges_found}",
                    run_id=meta.run_id,
                )
            except Exception:
                pass  # Don't fail the run if intra-versioning fails

    # -------------------------------------------------------------------------
    # 4. PROJECT UPDATE - Record run in project history
    # -------------------------------------------------------------------------
    project_manager.update_project_run(project_name, meta.run_id)

    # -------------------------------------------------------------------------
    # 5. BUNDLE SYNC - Export results to portable bundle
    # -------------------------------------------------------------------------
    if sync_manager and not meta.errors:
        try:
            sync_manager.auto_sync_after_run(
                project_name=project_name,
                run_id=meta.run_id,
                run_config={
                    "domains": domains,
                    "preset": preset,
                    "output_config": output_config,
                },
            )
        except Exception:
            pass  # Don't fail the run if sync fails

    return meta
