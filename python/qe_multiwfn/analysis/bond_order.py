"""
qe_multiwfn.analysis.bond_order — convenience functions for bond order analyses.
"""

from __future__ import annotations

from ..engine import Engine
from ..molecular import MolecularSystem
from ..results import MayerResult
from ..model_v1 import MolecularSystemV1


def calculate_mayer(system: MolecularSystem, *, engine: Engine = None) -> MayerResult:
    """One-shot convenience: load + prepare + calculate Mayer.

    If `engine` is None, a fresh engine is created, used, and finalized.
    If `engine` is provided, it must already be initialized (or not yet
    initialized; in that case it will be initialized here).
    """
    if isinstance(system, MolecularSystemV1):
        if engine is None:
            with Engine() as e:
                return e.calculate_mayer(system)
        return engine.calculate_mayer(system)
    if engine is None:
        with Engine() as e:
            e.load_molecule(system)
            e.prepare()
            return e.calculate_mayer()
    else:
        engine.load_molecule(system)
        engine.prepare()
        return engine.calculate_mayer()
