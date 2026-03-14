"""Cortex Engine — Comment metadata orchestrator.

Requires X-Ray results. Reads analysis data and injects @blueprint:cortex
blocks into source files. Defaults to dry-run mode.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import BlueprintConfig
from src.core.domain import Domain
from src.core.io_utils import normalize_path, safe_read_text
from src.core.models import (
    AnalysisResult,
    Entity,
    EntityType,
    RelationType,
)
from src.cortex.injector import inject_cortex_blocks, InjectionResult


class CortexEngine(Domain):
    """Cortex — Comment metadata injection engine.

    Pipeline:
    1. Consume X-Ray results (required)
    2. Group entities by file
    3. Build calls/uses maps from edges
    4. Inject @blueprint:cortex blocks into each file
    5. Optionally write modified files
    """

    def name(self) -> str:
        return "cortex"

    def version(self) -> str:
        return "1.0.0"

    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        """Execute the Cortex injection pipeline."""
        t0 = time.time()

        # Find X-Ray result
        xray_result = self.find_prior_result("xray", prior_results)
        if not xray_result:
            return AnalysisResult(
                domain=self.name(),
                version=self.version(),
                root_path=str(config.root_path),
                errors=[{"error": "No X-Ray result available", "phase": "init"}],
            )

        # Build relationship maps
        calls_map: Dict[str, List[str]] = {}
        uses_map: Dict[str, List[str]] = {}
        for edge in xray_result.edges:
            if edge.relation == RelationType.CALLS:
                calls_map.setdefault(edge.source, []).append(edge.target)
            elif edge.relation == RelationType.USES:
                uses_map.setdefault(edge.source, []).append(edge.target)

        # Group entities by file
        entities_by_file: Dict[str, List[Entity]] = {}
        for ent in xray_result.entities:
            if ent.location:
                entities_by_file.setdefault(ent.location.file, []).append(ent)

        # Process each file
        results: List[InjectionResult] = []
        errors: List[Dict[str, Any]] = []
        files_modified = 0

        for file_path, entities in entities_by_file.items():
            full_path = config.root_path / file_path
            if not full_path.exists():
                continue

            try:
                source = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                errors.append({
                    "file": file_path,
                    "error": str(exc),
                    "phase": "read",
                })
                continue

            try:
                inj_result = inject_cortex_blocks(
                    file_path=file_path,
                    source=source,
                    entities=entities,
                    calls_map=calls_map,
                    uses_map=uses_map,
                    dry_run=config.cortex_dry_run,
                    overwrite=config.cortex_overwrite,
                )
                results.append(inj_result)

                # Write back if not dry run and there are changes
                if not config.cortex_dry_run and inj_result.new_source:
                    full_path.write_text(inj_result.new_source, encoding="utf-8")
                    files_modified += 1

            except Exception as exc:
                errors.append({
                    "file": file_path,
                    "error": str(exc),
                    "phase": "inject",
                })

        elapsed = round(time.time() - t0, 3)

        total_inserted = sum(r.blocks_inserted for r in results)
        total_updated = sum(r.blocks_updated for r in results)
        total_skipped = sum(r.blocks_skipped for r in results)

        stats: Dict[str, Any] = {
            "dry_run": config.cortex_dry_run,
            "files_processed": len(results),
            "files_modified": files_modified,
            "blocks_inserted": total_inserted,
            "blocks_updated": total_updated,
            "blocks_skipped": total_skipped,
            "elapsed_seconds": elapsed,
            "error_count": len(errors),
        }

        return AnalysisResult(
            domain=self.name(),
            version=self.version(),
            root_path=str(config.root_path),
            entities=xray_result.entities,  # Pass through entities
            edges=xray_result.edges,
            stats=stats,
            errors=errors,
        )
