"""Blueprint CLI - Command-line interface for all domains.

Commands:
- blueprint xray            - Run X-Ray static analysis
- blueprint cortex          - Run Cortex comment metadata injection
- blueprint manifest        - Build the Manifest knowledge graph
- blueprint registry        - Run Registry project indexing
- blueprint sonar           - Run Sonar code quality scanning
- blueprint synapse         - Run Synapse call chain analysis
- blueprint scan            - Full pipeline (all domains)
- blueprint history         - Show Chronicle run history
- blueprint workspace init  - Initialize a workspace
- blueprint workspace run   - Run analysis from workspace targets
- blueprint workspace status - Show workspace status
"""

from __future__ import annotations

import time
from pathlib import Path

import click

from src import __version__
from src.core.config import BlueprintConfig


@click.group()
@click.version_option(version=__version__, prog_name="blueprint")
def main():
    """Blueprint - Code Intelligence for LLMs."""
    pass


# ---------------------------------------------------------------------------
# X-Ray command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
@click.option("--git/--no-git", default=False, help="Include git analysis.")
@click.option("--focus", "-f", default=None, help="Focus on a subdirectory.")
@click.option("--max-files", default=0, help="Max files to scan (0=unlimited).")
def xray(root, output, preset, git, focus, max_files):
    """Run X-Ray static analysis on the project."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
        extract_git=git,
        focus_path=Path(focus).resolve() if focus else None,
        max_files=max_files,
    )
    config.apply_preset(preset)

    click.echo(f"[X-Ray] Scanning: {config.root_path}")
    click.echo(f"   Preset: {preset} | Git: {git}")

    from src.xray.engine import XRayEngine
    engine = XRayEngine()
    result = engine.run(config)

    # Export outputs
    from src.xray.exporter import export_json, export_llm_bundle, export_markdown

    json_path = export_json(result, config.output_path)
    bundle_path = export_llm_bundle(
        result, config.output_path,
        max_nodes=config.llm_max_nodes,
        max_edges=config.llm_max_edges,
    )
    md_path = export_markdown(result, config.output_path)

    click.echo(f"\n[OK] X-Ray complete!")
    click.echo(f"   Files scanned: {result.stats.get('files_scanned', 0)}")
    click.echo(f"   Entities: {result.entity_count()}")
    click.echo(f"   Edges: {result.edge_count()}")
    click.echo(f"   Errors: {len(result.errors)}")
    click.echo(f"   Time: {result.stats.get('elapsed_seconds', 0)}s")
    click.echo(f"\n   Output:")
    click.echo(f"   - {json_path}")
    click.echo(f"   - {bundle_path}")
    click.echo(f"   - {md_path}")


# ---------------------------------------------------------------------------
# Manifest command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--format", "fmt", type=click.Choice(["yaml", "json"]),
              default="yaml", help="Output format.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
def manifest(root, output, fmt, preset):
    """Build the Manifest knowledge graph (runs X-Ray first)."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
        manifest_format=fmt,
    )
    config.apply_preset(preset)

    click.echo(f"[Manifest] Building: {config.root_path}")

    # Run X-Ray first
    from src.xray.engine import XRayEngine
    engine = XRayEngine()
    xray_result = engine.run(config)

    # Build Manifest
    from src.manifest.builder import build_manifest, save_manifest
    m = build_manifest(xray_result)
    path = save_manifest(m, config.output_path, fmt=fmt)

    click.echo(f"\n[OK] Manifest built!")
    click.echo(f"   Entities indexed: {len(m.entities)}")
    click.echo(f"   Relationships: {len(m.relationships)}")
    click.echo(f"   Architecture groups: {len(m.architecture_groups)}")
    click.echo(f"   Output: {path}")


# ---------------------------------------------------------------------------
# Cortex command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--dry-run/--write", default=True, help="Dry run (default) or write changes.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing cortex blocks.")
def cortex(root, output, dry_run, overwrite):
    """Run Cortex comment metadata injection (dry-run by default)."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        cortex_dry_run=dry_run,
        cortex_overwrite=overwrite,
    )

    mode = "DRY RUN" if dry_run else "WRITE"
    click.echo(f"[Cortex] ({mode}): {config.root_path}")

    # Run X-Ray first
    from src.xray.engine import XRayEngine
    xray_engine = XRayEngine()
    xray_result = xray_engine.run(config)

    # Run Cortex
    from src.cortex.engine import CortexEngine
    cortex_engine = CortexEngine()
    result = cortex_engine.run(config, prior_results=[xray_result])

    click.echo(f"\n[OK] Cortex complete!")
    click.echo(f"   Blocks inserted: {result.stats.get('blocks_inserted', 0)}")
    click.echo(f"   Blocks updated: {result.stats.get('blocks_updated', 0)}")
    click.echo(f"   Blocks skipped: {result.stats.get('blocks_skipped', 0)}")
    click.echo(f"   Files modified: {result.stats.get('files_modified', 0)}")
    if dry_run:
        click.echo(f"\n   Note: Use --write to apply changes to source files.")


# ---------------------------------------------------------------------------
# Registry command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
def registry(root, output, preset):
    """Run Registry project indexing and zone partitioning."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
    )
    config.apply_preset(preset)

    click.echo(f"[Registry] Indexing: {config.root_path}")

    # Run X-Ray first
    from src.xray.engine import XRayEngine
    xray_engine = XRayEngine()
    xray_result = xray_engine.run(config)

    # Run Registry
    from src.registry.engine import RegistryEngine
    registry_engine = RegistryEngine()
    result = registry_engine.run(config, prior_results=[xray_result])

    click.echo(f"\n[OK] Registry complete!")
    zones = result.stats.get("zones", {})
    click.echo(f"   Files profiled: {result.stats.get('profile', {}).get('total_files', 0)}")
    click.echo(f"   Zones: {zones.get('count', 0)}")
    click.echo(f"   Index entries: {result.stats.get('index', {}).get('entry_count', 0)}")
    if result.errors:
        click.echo(f"   Errors: {len(result.errors)}")


# ---------------------------------------------------------------------------
# Sonar command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
def sonar(root, output, preset):
    """Run Sonar code quality scanning (naming, complexity, dead code)."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
    )
    config.apply_preset(preset)

    click.echo(f"[Sonar] Scanning: {config.root_path}")

    # Run X-Ray first
    from src.xray.engine import XRayEngine
    xray_engine = XRayEngine()
    xray_result = xray_engine.run(config)

    # Run Sonar
    from src.sonar.engine import SonarEngine
    sonar_engine = SonarEngine()
    result = sonar_engine.run(config, prior_results=[xray_result])

    click.echo(f"\n[OK] Sonar complete!")
    click.echo(f"   Total findings: {result.stats.get('total_findings', 0)}")
    by_cat = result.stats.get("findings_by_category", {})
    for cat, count in by_cat.items():
        click.echo(f"   - {cat}: {count}")
    by_level = result.stats.get("findings_by_level", {})
    if by_level:
        click.echo(f"   By level: {', '.join(f'{k}={v}' for k, v in by_level.items())}")
    if result.errors:
        click.echo(f"   Errors: {len(result.errors)}")


# ---------------------------------------------------------------------------
# Synapse command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
def synapse(root, output, preset):
    """Run Synapse call chain analysis and hotspot detection."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
    )
    config.apply_preset(preset)

    click.echo(f"[Synapse] Analyzing: {config.root_path}")

    # Run X-Ray first
    from src.xray.engine import XRayEngine
    xray_engine = XRayEngine()
    xray_result = xray_engine.run(config)

    # Run Synapse
    from src.synapse.engine import SynapseEngine
    synapse_engine = SynapseEngine()
    result = synapse_engine.run(config, prior_results=[xray_result])

    click.echo(f"\n[OK] Synapse complete!")
    click.echo(f"   Call graphs: {result.stats.get('call_graphs_count', 0)}")
    click.echo(f"   Entry points: {result.stats.get('entry_points_count', 0)}")
    click.echo(f"   Sequences: {result.stats.get('sequences_count', 0)}")
    click.echo(f"   Hotspots: {result.stats.get('hotspots_count', 0)}")
    by_type = result.stats.get("hotspots_by_type", {})
    for htype, count in by_type.items():
        click.echo(f"   - {htype}: {count}")
    if result.errors:
        click.echo(f"   Errors: {len(result.errors)}")


# ---------------------------------------------------------------------------
# Full scan command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--root", "-r", default=".", help="Project root directory.")
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="Analysis preset.")
@click.option("--git/--no-git", default=False, help="Include git analysis.")
@click.option("--format", "fmt", type=click.Choice(["yaml", "json"]),
              default="yaml", help="Manifest format.")
def scan(root, output, preset, git, fmt):
    """Full pipeline: X-Ray -> Manifest -> Cortex -> Registry -> Sonar -> Synapse."""
    config = BlueprintConfig(
        root_path=Path(root).resolve(),
        output_path=Path(output).resolve(),
        xray_preset=preset,
        extract_git=git,
        manifest_format=fmt,
        cortex_dry_run=True,  # Always dry-run in scan
    )
    config.apply_preset(preset)

    click.echo(f"[Blueprint] Full Scan: {config.root_path}")
    click.echo(f"   Preset: {preset} | Git: {git}")
    t0 = time.time()

    # 1. X-Ray
    click.echo("\n--- X-Ray ---")
    from src.xray.engine import XRayEngine
    from src.xray.exporter import export_json, export_llm_bundle, export_markdown

    xray_engine = XRayEngine()
    xray_result = xray_engine.run(config)
    export_json(xray_result, config.output_path)
    export_llm_bundle(xray_result, config.output_path,
                      max_nodes=config.llm_max_nodes,
                      max_edges=config.llm_max_edges)
    export_markdown(xray_result, config.output_path)
    click.echo(f"   Entities: {xray_result.entity_count()} | Edges: {xray_result.edge_count()}")

    # 2. Manifest
    click.echo("\n--- Manifest ---")
    from src.manifest.builder import build_manifest, save_manifest

    m = build_manifest(xray_result)
    manifest_path = save_manifest(m, config.output_path, fmt=fmt)
    click.echo(f"   Indexed: {len(m.entities)} entities | {len(m.relationships)} relationships")

    # 3. Cortex (dry-run)
    click.echo("\n--- Cortex (dry-run) ---")
    from src.cortex.engine import CortexEngine

    cortex_engine = CortexEngine()
    cortex_result = cortex_engine.run(config, prior_results=[xray_result])
    click.echo(f"   Would inject: {cortex_result.stats.get('blocks_inserted', 0)} blocks")

    # 4. Registry
    click.echo("\n--- Registry ---")
    from src.registry.engine import RegistryEngine

    registry_engine = RegistryEngine()
    registry_result = registry_engine.run(config, prior_results=[xray_result])
    zones = registry_result.stats.get("zones", {})
    click.echo(f"   Zones: {zones.get('count', 0)} | Index entries: {registry_result.stats.get('index', {}).get('entry_count', 0)}")

    # 5. Sonar
    click.echo("\n--- Sonar ---")
    from src.sonar.engine import SonarEngine

    sonar_engine = SonarEngine()
    sonar_result = sonar_engine.run(config, prior_results=[xray_result])
    click.echo(f"   Findings: {sonar_result.stats.get('total_findings', 0)}")

    # 6. Synapse
    click.echo("\n--- Synapse ---")
    from src.synapse.engine import SynapseEngine

    synapse_engine = SynapseEngine()
    synapse_result = synapse_engine.run(config, prior_results=[xray_result])
    click.echo(f"   Call graphs: {synapse_result.stats.get('call_graphs_count', 0)} | Hotspots: {synapse_result.stats.get('hotspots_count', 0)}")

    # 7. Chronicle
    from src.core.chronicle import Chronicle, start_run, end_run, get_or_create_chronicle, save_chronicle

    chronicle = get_or_create_chronicle(config.output_path)
    chronicle.project_root = str(config.root_path)
    run = start_run(chronicle, str(config.root_path),
                    ["xray", "manifest", "cortex", "registry", "sonar", "synapse"])
    end_run(run, [xray_result, cortex_result, registry_result, sonar_result, synapse_result])
    save_chronicle(chronicle, config.output_path)

    elapsed = round(time.time() - t0, 2)
    click.echo(f"\n[OK] Blueprint scan complete in {elapsed}s")
    click.echo(f"   Output: {config.output_path}")


# ---------------------------------------------------------------------------
# History command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--output", "-o", default="./blueprint_out", help="Output directory.")
def history(output):
    """Show Chronicle run history."""
    from src.core.chronicle import get_or_create_chronicle

    output_path = Path(output).resolve()
    chronicle = get_or_create_chronicle(output_path)

    if chronicle.run_count == 0:
        click.echo("No runs recorded yet. Run 'blueprint scan' first.")
        return

    click.echo(f"[Chronicle] {chronicle.run_count} run(s)\n")

    for run in chronicle.runs:
        status = "[OK]" if run.is_complete else "[..]"
        click.echo(f"  {status} Run {run.id}")
        click.echo(f"     Started: {run.started_at}")
        if run.duration_seconds:
            click.echo(f"     Duration: {run.duration_seconds:.2f}s")
        click.echo(f"     Domains: {', '.join(run.domains_run)}")
        click.echo(f"     Entities: {run.entity_count} | Edges: {run.edge_count} | Errors: {run.error_count}")
        click.echo()

    if chronicle.milestones:
        click.echo(f"[Milestones] ({len(chronicle.milestones)}):\n")
        for ms in chronicle.milestones:
            click.echo(f"  - {ms.name} ({ms.created_at})")
            if ms.description:
                click.echo(f"    {ms.description}")


# ---------------------------------------------------------------------------
# Workspace command group
# ---------------------------------------------------------------------------

@main.group()
def workspace():
    """Workspace management: init, run, status."""
    pass


@workspace.command("init")
@click.option("--path", "-p", default="./workspace", help="Workspace root directory.")
def workspace_init(path):
    """Initialize a Blueprint workspace (intake/results/control folders)."""
    workspace_root = Path(path).resolve()

    from src.core.io_utils import ensure_dir
    from src.loader.deploy import create_default_deploy

    # Create folder structure
    ensure_dir(workspace_root / "intake" / "local")
    ensure_dir(workspace_root / "results")
    ensure_dir(workspace_root / "control" / "profiles")
    ensure_dir(workspace_root / "status" / "runs")
    ensure_dir(workspace_root / "snapshots")

    # Create deploy.yaml if it doesn't exist
    deploy_path = workspace_root / "intake" / "deploy.yaml"
    if not deploy_path.exists():
        create_default_deploy(deploy_path)
        click.echo(f"   Created: {deploy_path}")

    click.echo(f"\n[OK] Workspace initialized: {workspace_root}")
    click.echo(f"   intake/local/   - Drop projects here")
    click.echo(f"   intake/deploy.yaml - Configure targets")
    click.echo(f"   results/        - Analysis output")
    click.echo(f"   control/        - Profiles and defaults")
    click.echo(f"   status/         - System observability logs")
    click.echo(f"   snapshots/      - Branched Blueprint copies for project-specific runs")
    click.echo(f"\n   Next: Place a project in intake/local/ and run:")
    click.echo(f"   blueprint workspace run --path {path}")


@workspace.command("run")
@click.option("--path", "-p", default="./workspace", help="Workspace root directory.")
@click.option("--target", "-t", default=None, help="Run only this target (by name).")
@click.option("--domains", "-d", default=None, help="Comma-separated list of domains to run.")
@click.option("--preset", type=click.Choice(["quick", "standard", "deep"]),
              default=None, help="Override analysis preset.")
def workspace_run(path, target, domains, preset):
    """Run Blueprint analysis on workspace targets."""
    workspace_root = Path(path).resolve()

    if not workspace_root.is_dir():
        click.echo(f"Workspace not found: {workspace_root}")
        click.echo(f"Run 'blueprint workspace init' first.")
        return

    click.echo(f"[Workspace] Running: {workspace_root}")

    from src.loader.deploy import load_deploy_yaml
    from src.loader.runner import run_workspace
    from src.loader.schema import DeployConfig

    # Load deploy config
    deploy_path = workspace_root / "intake" / "deploy.yaml"
    deploy_config = None
    if deploy_path.is_file():
        try:
            deploy_config = load_deploy_yaml(deploy_path)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"   Warning: {exc}")

    # Override preset if specified
    if preset and deploy_config:
        deploy_config.preset = preset

    # Parse domain filter
    domain_filter = None
    if domains:
        domain_filter = [d.strip() for d in domains.split(",")]

    results = run_workspace(
        workspace_root=workspace_root,
        deploy_config=deploy_config,
        target_filter=target,
        domain_filter=domain_filter,
    )

    if not results:
        click.echo("\n   No targets found. Place a project in intake/local/")
        click.echo("   or configure targets in intake/deploy.yaml")
        return

    click.echo(f"\n[OK] Workspace run complete: {len(results)} target(s)\n")
    for meta in results:
        status = "[OK]" if not meta.errors else "[!!]"
        click.echo(f"  {status} {meta.project_name}")
        click.echo(f"     Source: {meta.source_path}")
        click.echo(f"     Domains: {', '.join(meta.domains_run)}")
        click.echo(f"     Files: {meta.files_scanned} | Entities: {meta.entities_found} | Edges: {meta.edges_found}")
        click.echo(f"     Time: {meta.duration_seconds}s")
        if meta.errors:
            for err in meta.errors:
                click.echo(f"     Error: {err.get('error', '')}")
        click.echo()


@workspace.command("status")
@click.option("--path", "-p", default="./workspace", help="Workspace root directory.")
@click.option("--run-id", "-r", default=None, help="Show detailed status for a specific run.")
@click.option("--anomalies", "-a", is_flag=True, help="Show only anomalies.")
@click.option("--errors", "-e", is_flag=True, help="Show only errors.")
def workspace_status(path, run_id, anomalies, errors):
    """Show workspace status, recent runs, and system health."""
    import json
    workspace_root = Path(path).resolve()

    if not workspace_root.is_dir():
        click.echo(f"Workspace not found: {workspace_root}")
        return

    # If specific run requested, show detailed status
    if run_id:
        _show_run_status(workspace_root, run_id, anomalies, errors)
        return

    click.echo(f"[Workspace] {workspace_root}\n")

    # Show system health from status/health.json
    health_path = workspace_root / "status" / "health.json"
    if health_path.exists():
        try:
            health = json.loads(health_path.read_text(encoding="utf-8"))
            status_icon = "[OK]" if health.get("last_status") == "success" else "[!!]"
            click.echo(f"  System Health: {status_icon}")
            click.echo(f"    Last run: {health.get('last_run_id', 'N/A')}")
            click.echo(f"    Project: {health.get('last_project', 'N/A')}")
            click.echo(f"    Status: {health.get('last_status', 'N/A')}")
            if health.get("recent_anomalies", 0) > 0:
                click.echo(f"    Anomalies: {health.get('recent_anomalies')} (use --anomalies to see)")
            if health.get("recent_errors", 0) > 0:
                click.echo(f"    Errors: {health.get('recent_errors')} (use --errors to see)")
            click.echo()
        except (json.JSONDecodeError, OSError):
            pass

    # Show recent runs from status/history.json
    history_path = workspace_root / "status" / "history.json"
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
            if history:
                click.echo(f"  Recent Runs ({len(history)} total):")
                for run in history[-5:][::-1]:  # Last 5, newest first
                    status_icon = "[OK]" if run.get("error_count", 0) == 0 else "[!!]"
                    anomaly_tag = f" ({run.get('anomaly_count', 0)} anomalies)" if run.get("anomaly_count", 0) > 0 else ""
                    click.echo(f"    {status_icon} {run.get('run_id', '?')}: {run.get('project_name', '?')}{anomaly_tag}")
                click.echo(f"\n    Use --run-id <id> to see details")
                click.echo()
        except (json.JSONDecodeError, OSError):
            pass

    # List projects in intake/local
    local_dir = workspace_root / "intake" / "local"
    if local_dir.is_dir():
        projects = [d for d in sorted(local_dir.iterdir())
                    if d.is_dir() and not d.name.startswith(".")]
        click.echo(f"  Intake ({len(projects)} project(s)):")
        for p in projects:
            bpignore = (p / ".bpignore").exists()
            tag = " [.bpignore]" if bpignore else ""
            click.echo(f"    - {p.name}{tag}")
        if not projects:
            click.echo(f"    (empty)")
    else:
        click.echo(f"  Intake: not initialized")

    # List recent results
    results_dir = workspace_root / "results"
    if results_dir.is_dir():
        project_dirs = [d for d in sorted(results_dir.iterdir())
                        if d.is_dir() and not d.name.startswith(".")]
        click.echo(f"\n  Results ({len(project_dirs)} project(s)):")
        for pd in project_dirs:
            runs = sorted([r for r in pd.iterdir()
                          if r.is_dir() and not r.name.startswith(".")
                          and r.name != "latest"],
                         reverse=True)
            click.echo(f"    {pd.name}: {len(runs)} run(s)")
            for run_dir in runs[:3]:
                meta_path = run_dir / "run_meta.json"
                if meta_path.exists():
                    import json
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                        click.echo(f"      {run_dir.name} - {meta.get('files_scanned', 0)} files, "
                                   f"{meta.get('entities_found', 0)} entities, "
                                   f"{meta.get('duration_seconds', 0)}s")
                    except (json.JSONDecodeError, OSError):
                        click.echo(f"      {run_dir.name}")
                else:
                    click.echo(f"      {run_dir.name}")
            if len(runs) > 3:
                click.echo(f"      ... {len(runs) - 3} more")
        if not project_dirs:
            click.echo(f"    (no results yet)")
    else:
        click.echo(f"\n  Results: not initialized")

    # Deploy.yaml status
    deploy_path = workspace_root / "intake" / "deploy.yaml"
    click.echo(f"\n  Deploy: {'configured' if deploy_path.exists() else 'not configured'}")


def _show_run_status(workspace_root: Path, run_id: str, show_anomalies: bool, show_errors: bool):
    """Show detailed status for a specific run."""
    import json

    # Find the run in status/runs/
    status_dir = workspace_root / "status" / "runs" / run_id
    if not status_dir.is_dir():
        # Try partial match
        runs_dir = workspace_root / "status" / "runs"
        if runs_dir.is_dir():
            matches = [d for d in runs_dir.iterdir() if run_id in d.name]
            if len(matches) == 1:
                status_dir = matches[0]
            elif len(matches) > 1:
                click.echo(f"Multiple matches for '{run_id}':")
                for m in matches:
                    click.echo(f"  - {m.name}")
                return
            else:
                click.echo(f"Run not found: {run_id}")
                return
        else:
            click.echo(f"No status data found. Run 'blueprint workspace run' first.")
            return

    # Load status.json
    status_path = status_dir / "status.json"
    if not status_path.exists():
        click.echo(f"Status file not found for run: {run_id}")
        return

    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        click.echo(f"Error reading status: {e}")
        return

    click.echo(f"[Status] Run: {status.get('run_id', run_id)}")
    click.echo(f"  Project: {status.get('project_name', 'N/A')}")
    click.echo(f"  Started: {status.get('started_at', 'N/A')}")
    click.echo(f"  Ended: {status.get('ended_at', 'N/A')}")

    summary = status.get("summary", {})
    click.echo(f"\n  Summary:")
    click.echo(f"    Domains run: {summary.get('domains_run', 0)}")
    click.echo(f"    Total errors: {summary.get('total_errors', 0)}")
    click.echo(f"    Total warnings: {summary.get('total_warnings', 0)}")
    click.echo(f"    Anomalies: {summary.get('anomaly_count', 0)}")

    # Show domain stats
    domain_stats = status.get("domain_stats", {})
    if domain_stats and not show_anomalies and not show_errors:
        click.echo(f"\n  Domains:")
        for name, ds in domain_stats.items():
            status_icon = "[OK]" if ds.get("status") == "success" else "[!!]"
            click.echo(f"    {status_icon} {name} v{ds.get('version', '?')}")
            click.echo(f"        Entities: {ds.get('entities_produced', 0)} | Edges: {ds.get('edges_produced', 0)}")
            click.echo(f"        Duration: {ds.get('duration_ms', 0):.0f}ms")

    # Show parser stats
    parser_stats = status.get("parser_stats", {})
    if parser_stats and not show_anomalies and not show_errors:
        click.echo(f"\n  Parsers:")
        for name, ps in parser_stats.items():
            success_rate = ps.get("success_rate", 0)
            status_icon = "[OK]" if success_rate >= 90 else "[!!]" if success_rate < 50 else "[--]"
            click.echo(f"    {status_icon} {name} ({ps.get('language', '?')})")
            click.echo(f"        Files: {ps.get('files_succeeded', 0)}/{ps.get('files_attempted', 0)} ({success_rate:.0f}% success)")
            click.echo(f"        Entities: {ps.get('total_entities', 0)} | Duration: {ps.get('total_duration_ms', 0):.0f}ms")
            if ps.get("files_empty", 0) > 0:
                click.echo(f"        Empty files: {ps.get('files_empty', 0)}")

    # Show anomalies
    anomalies_data = status.get("anomalies", [])
    if anomalies_data and (show_anomalies or summary.get("anomaly_count", 0) > 0):
        click.echo(f"\n  Anomalies ({len(anomalies_data)}):")
        for a in anomalies_data:
            severity = a.get("severity", "?").upper()
            click.echo(f"    [{severity}] {a.get('message', 'N/A')}")
            click.echo(f"        Rule: {a.get('rule', 'N/A')}")
            click.echo(f"        Action: {a.get('suggested_action', 'N/A')}")

    # Show errors
    if show_errors or summary.get("total_errors", 0) > 0:
        errors_path = status_dir / "errors.json"
        if errors_path.exists():
            try:
                errors_data = json.loads(errors_path.read_text(encoding="utf-8"))
                if errors_data:
                    click.echo(f"\n  Errors ({len(errors_data)}):")
                    for err in errors_data[:10]:  # Limit to first 10
                        click.echo(f"    [{err.get('level', 'error')}] {err.get('component', '?')}: {err.get('message', 'N/A')}")
                        if err.get("file_path"):
                            click.echo(f"        File: {err.get('file_path')}")
                    if len(errors_data) > 10:
                        click.echo(f"    ... and {len(errors_data) - 10} more")
            except (json.JSONDecodeError, OSError):
                pass

    # Show decisions if no filters
    decisions = status.get("decisions", [])
    if decisions and not show_anomalies and not show_errors:
        decision_types = {}
        for d in decisions:
            dt = d.get("type", "unknown")
            decision_types[dt] = decision_types.get(dt, 0) + 1
        click.echo(f"\n  Decisions: {len(decisions)} total")
        for dt, count in decision_types.items():
            click.echo(f"    {dt}: {count}")

    click.echo(f"\n  Status files: {status_dir}")


if __name__ == "__main__":
    main()
