"""Export X-Ray analysis results in multiple formats.

Formats: JSON, CSV, Markdown, and LLM-friendly bundle.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.io_utils import ensure_dir
from src.core.models import AnalysisResult, Entity, EntityType


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(
    result: AnalysisResult,
    output_path: Path,
    *,
    indent: int = 2,
    max_nodes: int = 0,
    max_edges: int = 0,
    max_snippet_chars: int = 900,
) -> Path:
    """Export analysis result as JSON.

    Args:
        result: The AnalysisResult to export.
        output_path: Directory to write to.
        indent: JSON indent level.
        max_nodes: Limit entities (0 = unlimited).
        max_edges: Limit edges (0 = unlimited).
        max_snippet_chars: Truncate evidence snippets.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)
    data = _result_to_dict(result, max_nodes, max_edges, max_snippet_chars)
    out_file = output_path / "xray_result.json"
    out_file.write_text(json.dumps(data, indent=indent, default=str), encoding="utf-8")
    return out_file


# ---------------------------------------------------------------------------
# LLM-friendly bundle (condensed)
# ---------------------------------------------------------------------------

def export_llm_bundle(
    result: AnalysisResult,
    output_path: Path,
    *,
    max_nodes: int = 600,
    max_edges: int = 1200,
    max_evidence: int = 1,
    max_snippet_chars: int = 900,
) -> Path:
    """Export a condensed LLM-friendly JSON bundle.

    Prioritizes entities with metrics, reduces evidence to essentials.

    Args:
        result: AnalysisResult.
        output_path: Output directory.
        max_nodes: Max entities to include.
        max_edges: Max edges to include.
        max_evidence: Max evidence items per edge.
        max_snippet_chars: Max chars per snippet.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)

    # Sort entities: prioritize those with metrics/complexity
    entities = sorted(
        result.entities,
        key=lambda e: (
            -(e.metrics.cyclomatic_complexity or 0) if e.metrics else 0,
            e.type.value,
            e.name,
        ),
    )
    if max_nodes > 0:
        entities = entities[:max_nodes]

    entity_ids = {e.id for e in entities}

    # Filter edges to only include ones with at least one known entity
    edges = [
        e for e in result.edges
        if e.source in entity_ids or e.target in entity_ids
    ]
    if max_edges > 0:
        edges = edges[:max_edges]

    # Build compact node representation
    nodes = []
    for ent in entities:
        node: Dict[str, Any] = {
            "id": ent.id,
            "type": ent.type.value,
            "name": ent.name,
        }
        if ent.location:
            node["file"] = ent.location.file
            node["line"] = ent.location.start_line
        if ent.signature:
            node["sig"] = ent.signature[:200]
        if ent.metrics:
            m = {}
            if ent.metrics.cyclomatic_complexity is not None:
                m["cc"] = ent.metrics.cyclomatic_complexity
            if ent.metrics.loc_code is not None:
                m["loc"] = ent.metrics.loc_code
            if ent.metrics.fan_in is not None:
                m["fi"] = ent.metrics.fan_in
            if ent.metrics.fan_out is not None:
                m["fo"] = ent.metrics.fan_out
            if m:
                node["metrics"] = m
        if ent.meta:
            node["meta"] = ent.meta
        nodes.append(node)

    # Build compact edge representation
    edge_list = []
    for edge in edges:
        e: Dict[str, Any] = {
            "src": edge.source,
            "tgt": edge.target,
            "rel": edge.relation.value,
        }
        if edge.confidence < 1.0:
            e["conf"] = edge.confidence
        if edge.evidence:
            ev_items = edge.evidence[:max_evidence]
            e["ev"] = [
                {
                    "file": ev.file,
                    "line": ev.start_line,
                    "snip": ev.snippet[:max_snippet_chars] if ev.snippet else "",
                }
                for ev in ev_items
            ]
        edge_list.append(e)

    bundle = {
        "scope": {
            "domain": result.domain,
            "version": result.version,
            "root": result.root_path,
        },
        "stats": result.stats,
        "nodes": nodes,
        "edges": edge_list,
    }

    out_file = output_path / "llm_context.json"
    out_file.write_text(
        json.dumps(bundle, indent=2, default=str),
        encoding="utf-8",
    )
    return out_file


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(
    result: AnalysisResult,
    output_path: Path,
) -> Dict[str, Path]:
    """Export entities and edges as CSV files.

    Returns:
        Dict with 'entities' and 'edges' keys pointing to file paths.
    """
    ensure_dir(output_path)
    files = {}

    # Entities CSV
    entities_file = output_path / "entities.csv"
    with entities_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "type", "name", "qualified_name", "file",
            "start_line", "end_line", "language", "signature",
            "cyclomatic_complexity", "loc_code", "fan_in", "fan_out",
        ])
        for ent in result.entities:
            writer.writerow([
                ent.id,
                ent.type.value,
                ent.name,
                ent.qualified_name or "",
                ent.location.file if ent.location else "",
                ent.location.start_line if ent.location else "",
                ent.location.end_line if ent.location else "",
                ent.language or "",
                ent.signature or "",
                ent.metrics.cyclomatic_complexity if ent.metrics else "",
                ent.metrics.loc_code if ent.metrics else "",
                ent.metrics.fan_in if ent.metrics else "",
                ent.metrics.fan_out if ent.metrics else "",
            ])
    files["entities"] = entities_file

    # Edges CSV
    edges_file = output_path / "edges.csv"
    with edges_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "relation", "confidence"])
        for edge in result.edges:
            writer.writerow([
                edge.source,
                edge.target,
                edge.relation.value,
                edge.confidence,
            ])
    files["edges"] = edges_file

    return files


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def export_markdown(
    result: AnalysisResult,
    output_path: Path,
    *,
    max_entities: int = 50,
) -> Path:
    """Export a human-readable Markdown report.

    Args:
        result: AnalysisResult.
        output_path: Output directory.
        max_entities: Max entities to list per type.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)
    lines: List[str] = []

    lines.append(f"# X-Ray Analysis Report\n")
    lines.append(f"**Root:** `{result.root_path}`  \n")
    lines.append(f"**Domain:** {result.domain} v{result.version}  \n")
    lines.append(f"**Timestamp:** {result.timestamp}  \n")
    lines.append("")

    # Stats
    lines.append("## Statistics\n")
    for key, val in result.stats.items():
        if isinstance(val, dict):
            lines.append(f"- **{key}:**")
            for k2, v2 in val.items():
                lines.append(f"  - {k2}: {v2}")
        else:
            lines.append(f"- **{key}:** {val}")
    lines.append("")

    # Entity summary by type
    lines.append("## Entities by Type\n")
    type_groups: Dict[str, List[Entity]] = {}
    for ent in result.entities:
        type_groups.setdefault(ent.type.value, []).append(ent)

    for etype, ents in sorted(type_groups.items()):
        lines.append(f"### {etype.title()} ({len(ents)})\n")
        display = ents[:max_entities]
        lines.append("| Name | File | Line | Complexity |")
        lines.append("|------|------|------|------------|")
        for ent in display:
            file_str = ent.location.file if ent.location else "-"
            line_str = str(ent.location.start_line) if ent.location else "-"
            cc = str(ent.metrics.cyclomatic_complexity) if ent.metrics and ent.metrics.cyclomatic_complexity else "-"
            lines.append(f"| {ent.name} | {file_str} | {line_str} | {cc} |")
        if len(ents) > max_entities:
            lines.append(f"\n*... and {len(ents) - max_entities} more*\n")
        lines.append("")

    # Complexity hotspots
    lines.append("## Complexity Hotspots\n")
    hotspots = sorted(
        [e for e in result.entities if e.metrics and e.metrics.cyclomatic_complexity],
        key=lambda e: -(e.metrics.cyclomatic_complexity or 0),
    )[:20]
    if hotspots:
        lines.append("| Entity | File | CC | LOC |")
        lines.append("|--------|------|----|-----|")
        for ent in hotspots:
            file_str = ent.location.file if ent.location else "-"
            cc = ent.metrics.cyclomatic_complexity if ent.metrics else 0
            loc = ent.metrics.loc_code if ent.metrics else 0
            lines.append(f"| {ent.qualified_name or ent.name} | {file_str} | {cc} | {loc} |")
    else:
        lines.append("*No complexity data available.*\n")
    lines.append("")

    # Errors
    if result.errors:
        lines.append("## Errors\n")
        for err in result.errors:
            lines.append(f"- **{err.get('file', 'unknown')}**: {err.get('error', 'unknown')}")
        lines.append("")

    out_file = output_path / "xray_report.md"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


# ---------------------------------------------------------------------------
# Sitemap (file tree)
# ---------------------------------------------------------------------------

def export_sitemap(
    result: AnalysisResult,
    output_path: Path,
) -> Path:
    """Export a file tree sitemap.

    Returns:
        Path to the written file.
    """
    ensure_dir(output_path)

    file_entities = sorted(
        [e for e in result.entities if e.type == EntityType.FILE],
        key=lambda e: e.qualified_name or e.name,
    )

    lines = ["# Sitemap\n"]
    for ent in file_entities:
        path = ent.qualified_name or ent.name
        lines.append(f"- `{path}`")

    out_file = output_path / "sitemap.md"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _result_to_dict(
    result: AnalysisResult,
    max_nodes: int,
    max_edges: int,
    max_snippet_chars: int,
) -> Dict[str, Any]:
    """Convert AnalysisResult to a JSON-serializable dict with optional limits."""
    entities = result.entities
    if max_nodes > 0:
        entities = entities[:max_nodes]

    edges = result.edges
    if max_edges > 0:
        edges = edges[:max_edges]

    return {
        "domain": result.domain,
        "version": result.version,
        "timestamp": str(result.timestamp),
        "root_path": result.root_path,
        "stats": result.stats,
        "entities": [e.model_dump(exclude_none=True) for e in entities],
        "edges": [
            {
                **e.model_dump(exclude_none=True),
                "evidence": [
                    {**ev.model_dump(), "snippet": ev.snippet[:max_snippet_chars]}
                    for ev in (e.evidence or [])
                ] if e.evidence else None,
            }
            for e in edges
        ],
        "errors": result.errors,
    }
