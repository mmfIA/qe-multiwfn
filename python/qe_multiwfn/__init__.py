"""
QE-Multiwfn — QuantumEngine-Multiwfn
=====================================

A Python wrapper around libqe_multiwfn.so, exposing the Multiwfn
scientific core as an in-memory Fortran-backed library.

Quickstart
----------

    import qe_multiwfn as qe

    with qe.Engine() as engine:
        engine.load_molecule(my_system)
        result = engine.calculate_mayer()
        print(result.total)

See docs/MOLECULAR_STATE.md for the canonical molecular data model.
"""

from .exceptions import (
    QeError,
    QeInvalidArgument,
    QeInvalidState,
    QeInvalidDimension,
    QeNullPointer,
    QeAllocation,
    QeIncompleteState,
    QeUnsupported,
    QeCalculation,
    QeInternal,
    QeCompatibility,
    QeMemoryLayout,
    QeNotAvailable,
    STATUS_TO_EXCEPTION,
)
from .molecular import MolecularSystem
from .engine import Engine
from .results import MayerResult
from .native import NATIVE_LIBRARY_PATH, NATIVE_LIBRARY_VERSION
from . import model_v1
from . import analysis
from .model_v1 import MolecularSystemV1
from .normalization import attach_normalization, normalization_report
from .builder import (
    BasisInput,
    MolecularDataBuilder,
    ShellInput,
    build_molecular_system,
    from_numpy,
)
from . import angular
from .angular import (
    AngularConvention,
    AngularBasisMetadata,
    AngularObjectMetadata,
    AngularTransformRecord,
    AngularError,
    AngularConventionError,
    AngularUnsupportedError,
    AngularStateError,
    AngularAlreadyCanonicalError,
    AngularDoubleTransformError,
    canonical_convention,
    canonical_cartesian_convention,
    known_source_convention,
    phase_matrix,
    apply_phase_to_coefficients,
    apply_phase_to_matrix,
    apply_phase_to_operator,
    canonicalize_model_angular,
)

__version__ = "0.3.0"
__all__ = [
    "Engine",
    "MolecularSystem",
    "MolecularSystemV1",
    "attach_normalization",
    "normalization_report",
    "BasisInput",
    "ShellInput",
    "MolecularDataBuilder",
    "build_molecular_system",
    "from_numpy",
    "model_v1",
    "analysis",
    "MayerResult",
    "QeError",
    "QeInvalidArgument",
    "QeInvalidState",
    "QeInvalidDimension",
    "QeNullPointer",
    "QeAllocation",
    "QeIncompleteState",
    "QeUnsupported",
    "QeCalculation",
    "QeInternal",
    "QeCompatibility",
    "QeMemoryLayout",
    "QeNotAvailable",
    "NATIVE_LIBRARY_PATH",
    "NATIVE_LIBRARY_VERSION",
    "angular",
    "AngularConvention",
    "AngularBasisMetadata",
    "AngularObjectMetadata",
    "AngularTransformRecord",
    "AngularError",
    "AngularConventionError",
    "AngularUnsupportedError",
    "AngularStateError",
    "AngularAlreadyCanonicalError",
    "AngularDoubleTransformError",
    "canonical_convention",
    "canonical_cartesian_convention",
    "known_source_convention",
    "phase_matrix",
    "apply_phase_to_coefficients",
    "apply_phase_to_matrix",
    "apply_phase_to_operator",
    "canonicalize_model_angular",
]
