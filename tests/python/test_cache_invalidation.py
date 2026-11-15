"""Fail-closed stale-cache checks for the Phase 6 getters."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn.model_v1 import MatrixBundle
from qe_multiwfn.adapters.orca import from_orca_directory

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
if not _ORCA.exists():
    pytest.skip("fixtures unavailable", allow_module_level=True)


def _stripped(model):
    m = deepcopy(model); m.matrices = MatrixBundle(); return m


def test_new_system_invalidates_derived_caches():
    h2o = _stripped(from_orca_directory(_ORCA / "h2o"))
    h2_ref = from_orca_directory(_ORCA / "h2")
    h2 = _stripped(h2_ref)
    with qe.Engine() as eng:
        eng.load_molecule_v1(h2o, prepare_from_orbitals=True)
        eng.prepare()
        eng.generate_overlap()
        # genPprim/ genSbas rebuild the basis; generate the diagnostic
        # Cartesian overlap last so both derived caches are current.
        eng.generate_primitive_density()
        eng.generate_cartesian_overlap()
        assert eng.generated_overlap().shape == (7, 7)
        assert eng.generated_cartesian_overlap().shape == (7, 7)
        assert eng.generated_primitive_density().shape[0] > 7

        # Same engine, new (smaller) system: release+begin must invalidate.
        eng.load_molecule_v1(h2, prepare_from_orbitals=True)
        with pytest.raises(qe.QeInvalidState):
            eng.generated_overlap()
        with pytest.raises(qe.QeInvalidState):
            eng.generated_cartesian_overlap()
        with pytest.raises(qe.QeInvalidState):
            eng.generated_primitive_density()

        eng.prepare()
        # Current S is valid for H2; diagnostic caches were cleared.
        np.testing.assert_allclose(eng.generated_overlap(),
                                   h2_ref.matrices.S.data, atol=1e-6, rtol=0.0)
        with pytest.raises(qe.QeNotAvailable):
            eng.generated_cartesian_overlap()
        with pytest.raises(qe.QeNotAvailable):
            eng.generated_primitive_density()

        eng.generate_primitive_density()
        eng.generate_cartesian_overlap()
        assert eng.generated_cartesian_overlap().shape == (2, 2)
        assert eng.generated_primitive_density().shape[0] > 2


def test_same_dimension_new_system_still_invalidates_primary_cache():
    model = from_orca_directory(_ORCA / "h2o")
    stripped = _stripped(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(stripped, prepare_from_orbitals=True)
        eng.prepare()
        eng.generate_primitive_density()
        P1 = eng.generated_primitive_density().copy()
        # Reload the same molecule: dimensions are identical, so only the
        # explicit invalidation can prevent a stale Pprim.
        eng.load_molecule_v1(_stripped(model), prepare_from_orbitals=True)
        eng.prepare()
        with pytest.raises(qe.QeNotAvailable):
            eng.generated_primitive_density()
        eng.generate_primitive_density()
        P2 = eng.generated_primitive_density()
        np.testing.assert_allclose(P2, P1, atol=1e-14, rtol=0.0)
