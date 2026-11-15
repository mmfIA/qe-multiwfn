"""Phase 6E — full MDM -> original Multiwfn state -> Mayer flow.

The models are stripped of matrices.S and matrices.P_total before loading;
the engine must build S with genSbas_curr and P with genP from the
canonical basis/orbitals alone.
"""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn.model_v1 import MatrixBundle
from qe_multiwfn.adapters.orca import (
    from_orca_directory, from_orca_uhf_directory, from_orca_rohf_directory,
)

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
_DF = _ORCA / "df"
_CART = _VAL / "fixtures" / "cartesian" / "h2o_631gstar_cart"
if not _ORCA.exists():
    pytest.skip("fixtures unavailable", allow_module_level=True)


def _strip(model):
    m = deepcopy(model)
    m.matrices = MatrixBundle()
    assert m.matrices.S is None and m.matrices.P_total is None
    return m


def _reference(model, allow_open_shell=False):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=allow_open_shell)
        eng.prepare()
        return eng.calculate_mayer()


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_full_flow_rhf_without_matrices(mol):
    model = from_orca_directory(_ORCA / mol)
    ref = _reference(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(_strip(model), prepare_from_orbitals=True)
        eng.prepare()
        res = eng.calculate_mayer()
        P = eng.generated_density(0)
        S = eng.generated_overlap()
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)


def test_full_flow_uhf_and_rohf_without_matrices():
    for fn, d in ((from_orca_uhf_directory, "uhf"),
                  (from_orca_rohf_directory, "rohf")):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        ref = _reference(model, allow_open_shell=True)
        with qe.Engine() as eng:
            eng.load_molecule_v1(_strip(model), allow_open_shell=True,
                                 prepare_from_orbitals=True)
            eng.prepare()
            res = eng.calculate_mayer()
            P = eng.generated_density(0)
            S = eng.generated_overlap()
        np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                                   atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(res.alpha, ref.alpha, atol=1e-7, rtol=0.0)
        np.testing.assert_allclose(res.beta, ref.beta, atol=1e-7, rtol=0.0)
        np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)


def test_full_flow_spherical_d_without_matrices():
    model = from_orca_directory(_DF / "h2o_631gstar")
    ref = _reference(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(_strip(model), prepare_from_orbitals=True)
        eng.prepare()
        res = eng.calculate_mayer()
        P = eng.generated_density(0)
        S = eng.generated_overlap()
        # primitive density is optional in the final flow
        eng.generate_primitive_density()
        nprims = eng._api.get_primitive_density_dimensions_v1()
        Pprim = eng.generated_primitive_density(0)
        Sprim = eng.generated_primitive_overlap()
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(float(np.trace(Pprim @ Sprim)),
                               model.electronic.nelectron, atol=1e-6, rtol=0.0)
    assert nprims > P.shape[0]
    np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)


def test_full_flow_cartesian_d_without_matrices():
    model = from_orca_directory(_CART)
    ref = _reference(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(_strip(model), prepare_from_orbitals=True)
        eng.prepare()
        res = eng.calculate_mayer()
        P = eng.generated_density(0)
        S = eng.generated_overlap()
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-6, rtol=0.0)


def test_full_flow_requires_orbitals():
    model = from_orca_directory(_ORCA / "h2o")
    m = _strip(model)
    m.wavefunction = None
    with qe.Engine() as eng:
        eng.load_molecule_v1(m, prepare_from_orbitals=True)
        with pytest.raises(qe.QeIncompleteState):
            eng.prepare()


def test_full_flow_requires_normalization_metadata():
    model = from_orca_directory(_ORCA / "h2o")
    m = _strip(model)
    for ao in m.basis.aos:
        ao.source_self_overlap = None
        ao.contraction_normalization = None
        ao.normalization_convention = None
    with qe.Engine() as eng:
        eng.load_molecule_v1(m, prepare_from_orbitals=True)
        with pytest.raises(qe.QeIncompleteState):
            eng.prepare()


def test_missing_matrices_still_rejected_by_default():
    model = from_orca_directory(_ORCA / "h2o")
    with qe.Engine() as eng:
        with pytest.raises(qe.QeIncompleteState):
            eng.load_molecule_v1(_strip(model))


def test_f_original_path_fails_closed():
    # The canonical model and the direct 0.2.0 path still support f; the
    # original genSbas/genPprim path is deliberately limited to s/p/d until
    # the f Cartesian/spherical ordering is validated. It must fail closed.
    model = from_orca_directory(_DF / "h2s_def2tzvp")
    m = _strip(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(m, prepare_from_orbitals=True)
        with pytest.raises(qe.QeUnsupported):
            eng.prepare()
