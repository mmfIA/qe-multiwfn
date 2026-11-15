"""
qe_multiwfn.results — Python wrappers for analysis results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict

import numpy as np


@dataclass
class MayerResult:
    """Result of a Mayer bond-order analysis.

    Attributes:
        total        : (ncenter, ncenter) float64 — the native total slot.
                   For RHF this is the closed-shell Mayer matrix. For
                   UHF/ROHF this is the generalized Wiberg/mixed-density
                   matrix returned by ``calcMayerbndord``; it is not
                   necessarily ``alpha + beta``.
        alpha        : (ncenter, ncenter) float64 or None — alpha-spin Mayer
                        matrix (only when has_spin_components is True).
        beta         : (ncenter, ncenter) float64 or None — beta-spin Mayer
                        matrix (only when has_spin_components is True).
        metadata     : dict with keys:
                            wavefunction_type : int
                            wavefunction_type_name : str
                            total_semantics : str
                            has_spin_components : bool
                            ncenter           : int
    """
    total: np.ndarray
    alpha: Optional[np.ndarray] = None
    beta:  Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)

    @property
    def has_spin_components(self) -> bool:
        return self.alpha is not None and self.beta is not None

    @property
    def ncenter(self) -> int:
        return int(self.total.shape[0])

    @property
    def total_semantics(self) -> str:
        """Explicit meaning of ``total`` for this wavefunction type."""
        return self.metadata.get(
            "total_semantics",
            "generalized_wiberg_mixed" if self.has_spin_components else "closed_shell_mayer",
        )

    @property
    def mixed(self):
        """Mixed-density/generalized-Wiberg matrix, or None for RHF."""
        return self.total if self.has_spin_components else None

    @property
    def generalized_wiberg(self):
        """Alias for ``mixed`` with the original Multiwfn terminology."""
        return self.mixed

    @property
    def mayer_total(self):
        """All-electron Mayer matrix: alpha+beta for open shell, total for RHF."""
        if self.has_spin_components:
            return self.alpha + self.beta
        return self.total

    @property
    def alpha_plus_beta(self):
        """Alias for ``mayer_total``."""
        return self.mayer_total

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "alpha": self.alpha,
            "beta":  self.beta,
            "mixed": self.mixed,
            "mayer_total": self.mayer_total,
            "metadata": dict(self.metadata),
            "has_spin_components": self.has_spin_components,
            "total_semantics": self.total_semantics,
        }

    def __repr__(self) -> str:
        return (
            f"MayerResult(ncenter={self.ncenter}, "
            f"wfntype={self.metadata.get('wavefunction_type','?')}, "
            f"has_spin={self.has_spin_components})"
        )
