"""Snapshot executor - runs Blueprint analysis from a snapshot's src/.

This module is the entry point for subprocess execution. When a snapshot
is "booted", this script is invoked with the snapshot's src/ prepended
to sys.path, ensuring all imports come from the snapshot copy.

Usage (from parent process):
    subprocess.run([
        sys.executable,
        "-m", "src.core.snapshot_executor",
        "--snapshot-dir", "/path/to/snapshot",
        "--workspace", "/path/to/workspace",
        "--config", "/path/to/run_config.json",
    ])

The run_config.json contains:
{
    "project_root": "/path/to/project",
    "project_name": "myapp",
    "run_id": "2025-02-05_150000",
    "domains": ["xray", "sonar", ...],
    "preset": "standard",
    "output_config": {...},
    "bpignore_patterns": [...],
    "focus_path": null,
    "include_patterns": [],
    "exclude_patterns": [],
}

Results are written to workspace/results/<project>/<run_id>/
Status is written to workspace/status/runs/<run_id>/
The snapshot manifest is updated with run outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def main() -> int:
    """Main entry point for snapshot execution."""
    parser = argparse.ArgumentParser(description="Execute Blueprint from a snapshot")
    parser.add_argument("--snapshot-dir", required=True, help="Path to snapshot directory")
    parser.add_argument("--workspace", required=True, help="Path to workspace root")
    parser.add_argument("--config", required=True, help="Path to run config JSON")
    parser.add_argument("--intra-run", action="store_true", help="This is an intra-run (re-run within same snapshot)")
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot_dir)
    workspace_root = Path(args.workspace)
    config_path = Path(args.config)

    # Validate paths
    if not snapshot_dir.is_dir():
        print(f"ERROR: Snapshot directory not found: {snapshot_dir}", file=sys.stderr)
        return 1
    if not (snapshot_dir / "src").is_dir():
        print(f"ERROR: Snapshot src/ not found: {snapshot_dir / 'src'}", file=sys.stderr)
        return 1
    if not config_path.is_file():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1

    # Load run config
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        return 1

    # Prepend snapshot's src to sys.path so all imports come from snapshot
    snapshot_src = str(snapshot_dir / "src")
    snapshot_parent = str(snapshot_dir)  # For "from src.xxx" imports

    # Remove only non-snapshot Blueprint source paths.
    # Keep site-packages/dist-packages entries (venv deps such as pydantic live there).
    def _should_prune_path(entry: str) -> bool:
        norm = entry.replace("\\", "/").lower()
        if "site-packages" in norm or "dist-packages" in norm:
            return False
        has_blueprint = "blueprint" in norm
        is_snapshot = "/snapshots/" in norm
        return has_blueprint and not is_snapshot

    sys.path = [p for p in sys.path if not _should_prune_path(p)]

    # Insert snapshot paths at the front
    sys.path.insert(0, snapshot_parent)
    sys.path.insert(0, snapshot_src)

    # Now import from snapshot's src
    try:
        from src import __version__
        from src.core.config import BlueprintConfig
        from src.core.io_utils import ensure_dir
        from src.core.models import AnalysisResult
        from src.core.snapshot import load_manifest, record_run, save_manifest
        from src.core.status import create_status_reporter
    except ImportError as e:
        print(f"ERROR: Failed to import from snapshot: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    # Extract config values
    project_root = Path(config["project_root"])
    project_name = config["project_name"]
    run_id = config.get("run_id") or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    domains = config.get("domains", ["xray", "manifest", "sonar"])
    preset = config.get("preset", "standard")
    output_config = config.get("output_config", {})
    bpignore_patterns = config.get("bpignore_patterns", [])
    focus_path = Path(config["focus_path"]) if config.get("focus_path") else None
    include_patterns = config.get("include_patterns", [])
    exclude_patterns = config.get("exclude_patterns", [])

    # Create results directory
    results_dir = workspace_root / "results" / project_name / run_id
    ensure_dir(results_dir)

    # Create status reporter
    reporter = create_status_reporter(project_name)
    reporter.start_run({
        "target_name": project_name,
        "snapshot_id": snapshot_dir.name,
        "snapshot_dir": str(snapshot_dir),
        "domains": domains,
        "preset": preset,
        "is_intra_run": args.intra_run,
    })

    # Update snapshot manifest status
    manifest = load_manifest(snapshot_dir)
    if manifest:
        manifest.status = "running"
        save_manifest(manifest, snapshot_dir)

    t0 = time.time()
    all_errors: List[Dict[str, Any]] = []

    try:
        # Build BlueprintConfig
        bp_config = BlueprintConfig(
            root_path=project_root,
            output_path=results_dir,
            xray_preset=preset,
            extract_git=output_config.get("git_analysis", False),
            manifest_format=output_config.get("manifest_format", "yaml"),
            exclude_patterns=exclude_patterns,
            include_patterns=include_patterns,
            focus_path=focus_path,
            cortex_dry_run=True,
        )
        bp_config.apply_preset(preset)

        # Run domains
        all_results: List[AnalysisResult] = []
        xray_result: Optional[AnalysisResult] = None

        domain_order = ["xray", "manifest", "cortex", "registry", "sonar", "synapse"]
        domains_to_run = [d for d in domain_order if d in domains]

        for domain_name in domains_to_run:
            try:
                reporter.start_domain(domain_name, __version__)
                result = _run_domain(
                    domain_name, bp_config, all_results, xray_result,
                    results_dir, output_config,
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
                    "traceback": traceback.format_exc(),
                })

        # Build run metadata
        elapsed = round(time.time() - t0, 3)
        files_scanned = xray_result.stats.get("files_scanned", 0) if xray_result else 0
        entities_found = xray_result.entity_count() if xray_result else 0
        edges_found = xray_result.edge_count() if xray_result else 0

        run_meta = {
            "run_id": run_id,
            "project_name": project_name,
            "snapshot_id": snapshot_dir.name,
            "source_path": str(project_root),
            "domains_run": domains_to_run,
            "preset": preset,
            "duration_seconds": elapsed,
            "blueprint_version": __version__,
            "bpignore_patterns": bpignore_patterns,
            "files_scanned": files_scanned,
            "entities_found": entities_found,
            "edges_found": edges_found,
            "errors": all_errors,
            "is_intra_run": args.intra_run,
        }

        # Save run metadata
        meta_path = results_dir / "run_meta.json"
        meta_path.write_text(
            json.dumps(run_meta, indent=2, default=str),
            encoding="utf-8",
        )

        # End run and save status
        success = len(all_errors) == 0
        reporter.end_run(success=success)
        reporter.save(workspace_root)

        # Update snapshot manifest with run result (record_run also updates status)
        record_run(snapshot_dir, run_id, success, {
            "files_scanned": files_scanned,
            "entities_found": entities_found,
            "edges_found": edges_found,
            "errors": len(all_errors),
            "duration_seconds": elapsed,
        })

        # Print summary to stdout for parent process
        print(json.dumps({
            "success": success,
            "run_id": run_id,
            "snapshot_id": snapshot_dir.name,
            "results_dir": str(results_dir),
            "files_scanned": files_scanned,
            "entities_found": entities_found,
            "edges_found": edges_found,
            "errors": len(all_errors),
            "duration_seconds": elapsed,
        }))

        return 0 if success else 1

    except Exception as e:
        # Catastrophic failure
        reporter.log_error("executor", f"Catastrophic failure: {e}", exception=e)
        reporter.end_run(success=False)
        reporter.save(workspace_root)

        if manifest:
            manifest.status = "failed"
            save_manifest(manifest, snapshot_dir)

        print(json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), file=sys.stderr)

        return 1


def _run_domain(
    domain_name: str,
    config: Any,  # BlueprintConfig
    prior_results: list,
    xray_result: Any,
    results_dir: Path,
    output_config: dict,
) -> Any:
    """Run a single domain and save its output."""
    # Import dynamically from snapshot's src
    if domain_name == "manifest":
        if xray_result is None:
            return None
        from src.manifest.builder import build_manifest, save_manifest
        from src.core.models import AnalysisResult
        m = build_manifest(xray_result)
        fmt = output_config.get("manifest_format", "yaml")
        save_manifest(m, results_dir, fmt=fmt)
        return AnalysisResult(
            domain="manifest",
            version="1.0.0",
            root_path=str(config.root_path),
            stats={
                "entities_indexed": len(m.entities),
                "relationships": len(m.relationships),
            },
        )

    # Get domain engine
    engine = _get_domain_engine(domain_name)

    if domain_name == "xray":
        result = engine.run(config)
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

    # Save result
    import json as json_module
    output_path = results_dir / f"{domain_name}_report.json"
    output_path.write_text(
        json_module.dumps(result.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8",
    )

    return result


def _get_domain_engine(domain_name: str):
    """Get a domain engine instance."""
    if domain_name == "xray":
        from src.xray.engine import XRayEngine
        return XRayEngine()
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


if __name__ == "__main__":
    sys.exit(main())
