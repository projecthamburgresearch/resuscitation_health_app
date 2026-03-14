"""Abstract base class for all Blueprint domains."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.config import BlueprintConfig
from src.core.models import AnalysisResult


class Domain(ABC):
    """Base class for Blueprint domains (X-Ray, Cortex, Manifest, etc.).

    Each domain:
    - Has a name and version
    - Takes a BlueprintConfig
    - Can consume prior domain results
    - Produces an AnalysisResult
    """

    @abstractmethod
    def name(self) -> str:
        """Domain identifier (e.g., 'xray', 'cortex', 'manifest')."""
        ...

    @abstractmethod
    def version(self) -> str:
        """Domain version string."""
        ...

    @abstractmethod
    def run(
        self,
        config: BlueprintConfig,
        prior_results: Optional[List[AnalysisResult]] = None,
    ) -> AnalysisResult:
        """Execute this domain's analysis.

        Args:
            config: Blueprint configuration.
            prior_results: Results from domains that ran before this one.

        Returns:
            AnalysisResult with entities, edges, stats.
        """
        ...

    def validate_config(self, config: BlueprintConfig) -> List[str]:
        """Validate configuration for this domain. Returns list of error messages."""
        errors = []
        if not config.root_path.exists():
            errors.append(f"Root path does not exist: {config.root_path}")
        return errors

    def find_prior_result(
        self,
        domain_name: str,
        prior_results: Optional[List[AnalysisResult]],
    ) -> Optional[AnalysisResult]:
        """Find a specific domain's result from prior_results list."""
        if not prior_results:
            return None
        for r in prior_results:
            if r.domain == domain_name:
                return r
        return None
