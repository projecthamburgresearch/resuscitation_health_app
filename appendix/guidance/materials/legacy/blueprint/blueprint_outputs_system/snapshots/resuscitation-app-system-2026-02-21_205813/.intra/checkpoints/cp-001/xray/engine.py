"""X-Ray Engine — The static analysis orchestrator.

Discovers files, parses each with the appropriate language parser,
detects references, resolves cross-file relationships, computes
fan-in/out, and returns a unified AnalysisResult.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import BlueprintConfig
from src.core.domain import Domain
from src.core.graph import KnowledgeGraph
from src.core.io_utils import (
    iter_files,
    normalize_path,
    safe_read_text,
)
from src.core.models import (
    AnalysisResult,
    Edge,
    Entity,
    EntityType,
    RelationType,
)
from src.xray.parsers import get_parser_for_file, _auto_register
from src.xray.references import detect_references, resolve_request_endpoint_edges


class XRayEngine(Domain):
    """X-Ray v2 — Multi-language static analysis engine.

    Pipeline:
    1. Discover files (respecting config filters)
    2. Parse each file with the appropriate language parser
    3. Detect references (API calls, endpoints, SQL, URLs)
    4. Resolve cross-file references (request -> endpoint matching)
    5. Compute fan-in / fan-out metrics
    6. Optionally run git analysis
    7. Return AnalysisResult
    """

    def name(self) -> str:
        return "xray"

    def version(self) -> str:
        return "2.0.0"

    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        """Execute the X-Ray analysis pipeline."""
        t0 = time.time()

        # Ensure parsers are registered
        _auto_register()

        # Discover files
        files = iter_files(
            root=config.root_path,
            focus=config.focus_path,
            include_patterns=config.include_patterns,
            exclude_patterns=config.exclude_patterns,
            max_files=config.max_files,
            max_file_size=config.max_file_size,
        )

        all_entities: List[Entity] = []
        all_edges: List[Edge] = []
        errors: List[Dict[str, Any]] = []
        files_scanned = 0
        files_parsed = 0
        files_skipped = 0

        for file_path in files:
            files_scanned += 1
            rel_path = normalize_path(file_path, config.root_path)

            try:
                source, raw_bytes = safe_read_text(file_path, config.max_read_bytes)
            except Exception as exc:
                errors.append({
                    "file": rel_path,
                    "error": f"Read error: {exc}",
                    "phase": "read",
                })
                files_skipped += 1
                continue

            lines = source.splitlines(keepends=True)

            # Get parser for this file type
            parser = get_parser_for_file(rel_path)

            if parser and config.extract_symbols:
                try:
                    entities, edges = parser.parse_file(
                        rel_path, source,
                        extract_symbols=config.extract_symbols,
                    )
                    all_entities.extend(entities)
                    all_edges.extend(edges)
                    files_parsed += 1
                except Exception as exc:
                    errors.append({
                        "file": rel_path,
                        "error": f"Parse error: {exc}",
                        "phase": "parse",
                    })
                    # Still try references
            else:
                # No parser — still create a FILE entity
                file_entity = Entity(
                    id=f"FILE::{rel_path}",
                    type=EntityType.FILE,
                    name=file_path.name,
                    qualified_name=rel_path,
                    language=_guess_language(file_path.suffix),
                )
                all_entities.append(file_entity)

            # Reference detection (regex-based, works for all files)
            if config.extract_references:
                try:
                    ref_entities, ref_edges = detect_references(
                        source, rel_path, lines,
                    )
                    all_entities.extend(ref_entities)
                    all_edges.extend(ref_edges)
                except Exception as exc:
                    errors.append({
                        "file": rel_path,
                        "error": f"Reference detection error: {exc}",
                        "phase": "references",
                    })

        # Cross-file resolution
        if config.extract_references:
            try:
                match_edges = resolve_request_endpoint_edges(
                    all_entities, all_edges,
                )
                all_edges.extend(match_edges)
            except Exception as exc:
                errors.append({
                    "error": f"Cross-file resolution error: {exc}",
                    "phase": "resolve",
                })

        # Compute fan-in / fan-out
        graph = KnowledgeGraph.from_entities_and_edges(all_entities, all_edges)
        fan_data = graph.compute_fan_in_out()
        for ent in all_entities:
            if ent.id in fan_data and ent.metrics:
                fi, fo = fan_data[ent.id]
                ent.metrics.fan_in = fi
                ent.metrics.fan_out = fo

        # Git analysis (if enabled)
        if config.extract_git:
            try:
                from src.xray.git_analyzer import enrich_with_git
                enrich_with_git(config.root_path, all_entities)
            except ImportError:
                pass
            except Exception as exc:
                errors.append({
                    "error": f"Git analysis error: {exc}",
                    "phase": "git",
                })

        # Deduplicate entities by ID
        seen_ids: set = set()
        unique_entities: List[Entity] = []
        for ent in all_entities:
            if ent.id not in seen_ids:
                seen_ids.add(ent.id)
                unique_entities.append(ent)

        elapsed = round(time.time() - t0, 3)

        # Build stats
        entity_type_counts: Dict[str, int] = {}
        for ent in unique_entities:
            key = ent.type.value
            entity_type_counts[key] = entity_type_counts.get(key, 0) + 1

        stats: Dict[str, Any] = {
            "files_scanned": files_scanned,
            "files_parsed": files_parsed,
            "files_skipped": files_skipped,
            "entity_count": len(unique_entities),
            "edge_count": len(all_edges),
            "entity_types": entity_type_counts,
            "elapsed_seconds": elapsed,
            "error_count": len(errors),
        }

        return AnalysisResult(
            domain=self.name(),
            version=self.version(),
            root_path=str(config.root_path),
            entities=unique_entities,
            edges=all_edges,
            stats=stats,
            errors=errors,
        )


def _guess_language(ext: str) -> Optional[str]:
    """Guess language from file extension."""
    ext = ext.lower()
    LANG_MAP = {
        ".py": "python", ".pyw": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cs": "c_sharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin", ".kts": "kotlin",
        ".c": "c", ".h": "c",
        ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
        ".yml": "yaml", ".yaml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".html": "html", ".htm": "html",
        ".css": "css", ".scss": "scss",
        ".xml": "xml",
        ".sql": "sql",
        ".md": "markdown",
        ".sh": "bash", ".bash": "bash",
    }
    return LANG_MAP.get(ext)
