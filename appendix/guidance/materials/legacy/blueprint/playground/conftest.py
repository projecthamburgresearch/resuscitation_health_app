"""Shared pytest fixtures for Blueprint tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import BlueprintConfig
from src.core.models import (
    AnalysisResult,
    Edge,
    Entity,
    EntityType,
    Evidence,
    Location,
    Metrics,
    RelationType,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_config(tmp_path: Path) -> BlueprintConfig:
    return BlueprintConfig(
        root_path=FIXTURES_DIR,
        output_path=tmp_path / "output",
    )


@pytest.fixture
def sample_entity() -> Entity:
    return Entity(
        id="FUNC::src/auth.py::login",
        type=EntityType.FUNCTION,
        name="login",
        qualified_name="auth.login",
        location=Location(file="src/auth.py", start_line=10, end_line=25),
        language="python",
        signature="def login(username: str, password: str) -> bool",
        return_type="bool",
        parameters=["username: str", "password: str"],
        metrics=Metrics(cyclomatic_complexity=5, loc_code=15),
    )


@pytest.fixture
def sample_edge() -> Edge:
    return Edge(
        source="FUNC::src/auth.py::login",
        target="FUNC::src/db.py::get_user",
        relation=RelationType.CALLS,
        confidence=1.0,
        evidence=[Evidence(file="src/auth.py", start_line=15, end_line=15, snippet="user = get_user(username)")],
    )


@pytest.fixture
def sample_analysis_result(sample_entity: Entity, sample_edge: Edge) -> AnalysisResult:
    return AnalysisResult(
        domain="xray",
        version="2.0.0",
        root_path=str(FIXTURES_DIR),
        entities=[sample_entity],
        edges=[sample_edge],
        stats={"files_scanned": 1},
    )
