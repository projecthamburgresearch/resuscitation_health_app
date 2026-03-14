"""Registry Engine -- Domain orchestrator for the Registry.

Scans the project profile, partitions files into zones, and builds or
updates the master index from prior X-Ray results.  Produces an
AnalysisResult with registry-level statistics.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import BlueprintConfig
from src.core.domain import Domain
from src.core.models import AnalysisResult
from src.registry.index import (
    build_master_index,
    load_master_index,
    save_master_index,
    update_master_index,
)
from src.registry.partitioner import (
    detect_zone_dependencies,
    partition_into_zones,
)
from src.registry.scanner import scan_project_profile


# Default path for the persisted master index, relative to output_path
_INDEX_FILENAME = "master_index.json"


class RegistryEngine(Domain):
    """Registry domain engine.

    Pipeline:
    1. Scan the project to build a ProjectProfile.
    2. Partition discovered files into zones.
    3. If a prior xray result is available, build (or update) the
       master index from it.
    4. Detect cross-zone dependencies from xray edges.
    5. Persist the master index to disk.
    6. Return an AnalysisResult summarising the registry state.
    """

    def name(self) -> str:
        return "registry"

    def version(self) -> str:
        return "0.2.0"

    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        """Execute the Registry pipeline."""
        t0 = time.time()
        errors: List[Dict[str, Any]] = []
        run_id = uuid.uuid4().hex[:12]
        root = config.root_path

        # -----------------------------------------------------------
        # 1. Scan project profile
        # -----------------------------------------------------------
        try:
            profile = scan_project_profile(root, config)
        except Exception as exc:
            errors.append({
                "error": f"Profile scan failed: {exc}",
                "phase": "scan",
            })
            # Return a minimal result on critical failure
            return AnalysisResult(
                domain=self.name(),
                version=self.version(),
                root_path=str(root),
                stats={"error": "profile_scan_failed"},
                errors=errors,
            )

        # -----------------------------------------------------------
        # 2. Partition into zones
        # -----------------------------------------------------------
        try:
            zones = partition_into_zones(root, profile, config)
        except Exception as exc:
            errors.append({
                "error": f"Zone partitioning failed: {exc}",
                "phase": "partition",
            })
            zones = []

        # -----------------------------------------------------------
        # 3. Build or update the master index
        # -----------------------------------------------------------
        xray_result = self.find_prior_result("xray", prior_results)
        index_path = config.output_path / _INDEX_FILENAME
        master_index = None

        if xray_result is not None:
            # Detect zone dependencies from xray edges
            try:
                zones = detect_zone_dependencies(zones, xray_result.edges)
            except Exception as exc:
                errors.append({
                    "error": f"Zone dependency detection failed: {exc}",
                    "phase": "zone_deps",
                })

            # Try to load an existing index for incremental update
            if index_path.exists():
                try:
                    master_index = load_master_index(index_path)
                    master_index.profile = profile
                    master_index.zones = zones
                    master_index = update_master_index(
                        master_index, xray_result, run_id,
                    )
                except Exception as exc:
                    errors.append({
                        "error": f"Incremental update failed, rebuilding: {exc}",
                        "phase": "update",
                    })
                    master_index = None

            # Build from scratch if no existing index or update failed
            if master_index is None:
                project_name = root.name
                try:
                    master_index = build_master_index(
                        project_name=project_name,
                        root=root,
                        profile=profile,
                        zones=zones,
                        result=xray_result,
                        run_id=run_id,
                    )
                except Exception as exc:
                    errors.append({
                        "error": f"Master index build failed: {exc}",
                        "phase": "build",
                    })

        # -----------------------------------------------------------
        # 4. Persist the master index
        # -----------------------------------------------------------
        if master_index is not None:
            try:
                save_master_index(master_index, index_path)
            except Exception as exc:
                errors.append({
                    "error": f"Failed to save master index: {exc}",
                    "phase": "save",
                })

        # -----------------------------------------------------------
        # 5. Build stats and return
        # -----------------------------------------------------------
        elapsed = round(time.time() - t0, 3)

        stats: Dict[str, Any] = {
            "run_id": run_id,
            "elapsed_seconds": elapsed,
            "profile": {
                "total_files": profile.total_files,
                "total_size_bytes": profile.total_size_bytes,
                "estimated_entities": profile.estimated_entities,
                "directory_count": profile.directory_count,
                "languages": len(profile.language_distribution),
            },
            "zones": {
                "count": len(zones),
                "names": [z.name for z in zones],
            },
            "index": {},
            "error_count": len(errors),
        }

        if master_index is not None:
            stats["index"] = {
                "total_entries": len(master_index.entries),
                "total_runs": len(master_index.run_history),
                "version": master_index.version,
            }

        # The registry itself does not produce new entities/edges --
        # it catalogues those from prior domains.  We return an empty
        # entity/edge list but rich stats.
        return AnalysisResult(
            domain=self.name(),
            version=self.version(),
            root_path=str(root),
            entities=[],
            edges=[],
            stats=stats,
            errors=errors,
        )
