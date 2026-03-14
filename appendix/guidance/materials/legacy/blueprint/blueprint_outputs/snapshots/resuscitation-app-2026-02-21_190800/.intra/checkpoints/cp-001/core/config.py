"""Blueprint configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BlueprintConfig(BaseSettings):
    """Central configuration for all Blueprint domains.

    Values can be set via:
    1. Constructor arguments
    2. Environment variables prefixed with BLUEPRINT_
    3. .env file
    """

    model_config = {"env_prefix": "BLUEPRINT_"}

    # Paths
    root_path: Path = Field(default_factory=lambda: Path(".").resolve())
    output_path: Path = Field(default_factory=lambda: Path("./blueprint_out").resolve())

    # File scanning
    focus_path: Optional[Path] = None
    max_files: int = 0  # 0 = unlimited
    max_file_size: int = 1_500_000
    max_read_bytes: int = 1_500_000
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "**/node_modules/**",
        "**/.git/**",
        "**/dist/**",
        "**/build/**",
        "**/__pycache__/**",
        "**/.next/**",
        "**/.venv/**",
        "**/venv/**",
        "**/.history/**",
    ])
    include_patterns: List[str] = Field(default_factory=list)

    # X-Ray
    xray_preset: str = "standard"  # quick, standard, deep
    extract_symbols: bool = True
    extract_references: bool = True
    extract_git: bool = False

    # Cortex
    cortex_dry_run: bool = True  # Default: never modify files without opt-in
    cortex_overwrite: bool = False

    # Manifest
    manifest_format: str = "yaml"  # yaml or json

    # Output / LLM caps
    emit: List[str] = Field(default_factory=lambda: ["bundle"])
    llm_max_nodes: int = 600
    llm_max_edges: int = 1200
    llm_max_evidence: int = 1
    llm_max_snippet_chars: int = 900

    def apply_preset(self, preset: str | None = None) -> None:
        """Apply a scanning preset to adjust settings."""
        p = preset or self.xray_preset
        if p == "quick":
            self.extract_symbols = False
            self.llm_max_nodes = min(self.llm_max_nodes, 400)
            self.llm_max_edges = min(self.llm_max_edges, 800)
        elif p == "standard":
            self.extract_symbols = True
        elif p == "deep":
            self.extract_symbols = True
            self.extract_git = True
            self.llm_max_nodes = max(self.llm_max_nodes, 900)
            self.llm_max_edges = max(self.llm_max_edges, 1800)
