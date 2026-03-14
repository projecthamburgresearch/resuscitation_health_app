"""Synapse domain data models.

Synapse analyzes caller/callee chains, execution sequences,
and routing formations (loops, conditionals, branching paths).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChainDirection(str, Enum):
    """Direction of a call chain traversal."""
    UPSTREAM = "upstream"      # Who calls this (callers of callers)
    DOWNSTREAM = "downstream"  # What this calls (callees of callees)


class CallChain(BaseModel):
    """A single caller/callee chain from a root entity."""
    root_entity_id: str
    root_name: str
    direction: ChainDirection
    depth: int
    chain: List[str]  # Ordered list of entity IDs in the chain
    names: List[str]  # Parallel list of human-readable names
    files: List[str]  # Parallel list of file paths


class CallGraph(BaseModel):
    """Full call graph for an entity: both upstream and downstream."""
    entity_id: str
    entity_name: str
    file_path: str
    upstream_chains: List[CallChain] = Field(default_factory=list)
    downstream_chains: List[CallChain] = Field(default_factory=list)
    upstream_depth: int = 0
    downstream_depth: int = 0
    total_callers: int = 0
    total_callees: int = 0


class SequenceStep(BaseModel):
    """One step in an execution sequence."""
    order: int
    entity_id: str
    entity_name: str
    file_path: str
    call_type: str = "direct"  # direct, conditional, loop, callback


class ExecutionSequence(BaseModel):
    """An execution sequence starting from an entry point."""
    entry_point_id: str
    entry_point_name: str
    steps: List[SequenceStep] = Field(default_factory=list)
    branches: int = 0  # Number of conditional branches encountered
    loops: int = 0     # Number of loops encountered
    max_depth: int = 0


class HotspotType(str, Enum):
    """Types of structural hotspots."""
    HIGH_FAN_IN = "high_fan_in"    # Called by many
    HIGH_FAN_OUT = "high_fan_out"  # Calls many
    BOTTLENECK = "bottleneck"      # High fan-in AND fan-out
    HUB = "hub"                    # Central to many chains
    LEAF = "leaf"                  # End of chains (no outgoing calls)
    ORPHAN = "orphan"              # No callers, no callees


class Hotspot(BaseModel):
    """A structural hotspot in the call graph."""
    entity_id: str
    entity_name: str
    file_path: str
    hotspot_type: HotspotType
    fan_in: int = 0
    fan_out: int = 0
    chain_count: int = 0  # How many chains pass through this entity
    severity: str = "info"  # info, warning, critical


class SynapseReport(BaseModel):
    """Complete Synapse analysis report."""
    call_graphs: List[CallGraph] = Field(default_factory=list)
    sequences: List[ExecutionSequence] = Field(default_factory=list)
    hotspots: List[Hotspot] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
