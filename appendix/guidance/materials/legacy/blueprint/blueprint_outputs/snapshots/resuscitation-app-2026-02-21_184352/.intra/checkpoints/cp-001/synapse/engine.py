"""Synapse domain engine - call chain analysis, execution tracing, hotspot detection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.config import BlueprintConfig
from src.core.domain import Domain
from src.core.models import AnalysisResult
from src.synapse.chains import build_all_call_graphs
from src.synapse.hotspots import detect_hotspots
from src.synapse.sequences import detect_entry_points, trace_all_sequences


class SynapseEngine(Domain):
    """Synapse domain: caller/callee chain analysis, execution sequences, hotspots.

    Requires a prior X-Ray result. Reads entities and edges to build
    call graphs, trace execution sequences, and detect structural hotspots.
    """

    def name(self) -> str:
        return "synapse"

    def version(self) -> str:
        return "0.2.0"

    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        xray_result = self.find_prior_result("xray", prior_results)
        if not xray_result:
            return AnalysisResult(
                domain=self.name(),
                version=self.version(),
                root_path=str(config.root_path),
                errors=[{"error": "Synapse requires a prior X-Ray result"}],
            )

        entities = xray_result.entities
        edges = xray_result.edges

        # 1. Build call graphs for all callable entities
        call_graphs = build_all_call_graphs(
            entities, edges, max_depth=10,
        )

        # 2. Detect entry points and trace execution sequences
        entry_points = detect_entry_points(entities)
        sequences = trace_all_sequences(
            entities, edges, max_depth=50,
            entry_points=entry_points,
        )

        # 3. Detect structural hotspots
        hotspots = detect_hotspots(entities, edges)

        # Serialize results into stats
        stats: Dict[str, Any] = {
            "call_graphs_count": len(call_graphs),
            "entry_points_count": len(entry_points),
            "sequences_count": len(sequences),
            "hotspots_count": len(hotspots),
            "hotspots_by_type": {},
            "hotspots_by_severity": {},
            "max_upstream_depth": 0,
            "max_downstream_depth": 0,
            "max_sequence_length": 0,
            "call_graphs": [g.model_dump() for g in call_graphs[:100]],
            "sequences": [s.model_dump() for s in sequences[:50]],
            "hotspots": [h.model_dump() for h in hotspots[:200]],
            "entry_points": [
                {
                    "id": ep.id,
                    "name": ep.qualified_name or ep.name,
                    "file": ep.location.file if ep.location else "",
                }
                for ep in entry_points
            ],
        }

        # Aggregate stats
        for h in hotspots:
            stats["hotspots_by_type"][h.hotspot_type.value] = (
                stats["hotspots_by_type"].get(h.hotspot_type.value, 0) + 1
            )
            stats["hotspots_by_severity"][h.severity] = (
                stats["hotspots_by_severity"].get(h.severity, 0) + 1
            )

        if call_graphs:
            stats["max_upstream_depth"] = max(g.upstream_depth for g in call_graphs)
            stats["max_downstream_depth"] = max(g.downstream_depth for g in call_graphs)

        if sequences:
            stats["max_sequence_length"] = max(len(s.steps) for s in sequences)

        return AnalysisResult(
            domain=self.name(),
            version=self.version(),
            root_path=str(config.root_path),
            stats=stats,
        )
