"""Phase 6C/6D — original Multiwfn genSbas / genSbas_curr integration."""
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
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


def _invariants(S, model):
    """Internal checks independent of the printed reference precision."""
    assert S.shape == model.matrices.S.data.shape
    np.testing.assert_allclose(S, S.T, atol=1e-13, rtol=0.0)
    assert np.all(np.linalg.eigvalsh(S) > -1e-10)
    # For normalized (s/p and spherical) bases Tr(S)=nbasis. Cartesian
    # PySCF d uses a non-unit source normalization, so compare to the
    # reference trace instead with the same 1e-6 source-precision bound.
    ref_trace = float(np.trace(model.matrices.S.data))
    np.testing.assert_allclose(float(np.trace(S)), ref_trace, atol=1e-6, rtol=0.0)


def _ref_mayer(model, allow_open_shell=False, generate=False):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=allow_open_shell)
        eng.prepare()
        if generate:
            eng.generate_overlap()
            eng.generate_density()
        return eng.calculate_mayer()


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_gensbas_curr_rhf_matches_reference(mol):
    model = from_orca_directory(_ORCA / mol)
    ref = _ref_mayer(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_overlap()
        S = eng.generated_overlap()
        eng.generate_density()
        res = eng.calculate_mayer()
    np.testing.assert_allclose(S, model.matrices.S.data, atol=1e-6, rtol=0.0)
    _invariants(S, model)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)


def test_gensbas_curr_uhf_and_rohf():
    for fn, d in ((from_orca_uhf_directory, "uhf"),
                  (from_orca_rohf_directory, "rohf")):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        ref = _ref_mayer(model, allow_open_shell=True)
        with qe.Engine() as eng:
            eng.load_molecule_v1(model, allow_open_shell=True)
            eng.prepare()
            eng.generate_overlap()
            S = eng.generated_overlap()
            eng.generate_density()
            res = eng.calculate_mayer()
        np.testing.assert_allclose(S, model.matrices.S.data, atol=1e-6, rtol=0.0)
        _invariants(S, model)
        np.testing.assert_allclose(res.alpha, ref.alpha, atol=1e-7, rtol=0.0)
        np.testing.assert_allclose(res.beta, ref.beta, atol=1e-7, rtol=0.0)


def test_gensbas_curr_spherical_d():
    model = from_orca_directory(_DF / "h2o_631gstar")
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_overlap()
        S = eng.generated_overlap()
    np.testing.assert_allclose(S, model.matrices.S.data, atol=1e-6, rtol=0.0)
    _invariants(S, model)
    assert S.shape == model.matrices.S.data.shape
    np.testing.assert_allclose(S, S.T, atol=1e-13, rtol=0.0)
    assert np.all(np.linalg.eigvalsh(S) > -1e-10)


def test_gensbas_cartesian_d_intermediate():
    model = from_orca_directory(_CART)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_cartesian_overlap()
        S = eng.generated_cartesian_overlap()
        Scur = eng.generated_overlap()
    np.testing.assert_allclose(S, model.matrices.S.data, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(Scur, model.matrices.S.data, atol=1e-6, rtol=0.0)
    assert S.shape == Scur.shape


def test_gensbas_full_flow_spherical_d_mayer():
    model = from_orca_directory(_DF / "h2o_631gstar")
    ref = _ref_mayer(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_overlap()
        eng.generate_density()
        res = eng.calculate_mayer()
    np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_gensbas_curr_matches_multiwfn_extracted(mol):
    model = from_orca_directory(_ORCA / mol)
    extracted = _VAL / "extracted" / mol / "S.npy"
    if not extracted.exists():
        pytest.skip("Multiwfn extracted S unavailable")
    ref = np.load(extracted)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_overlap()
        S = eng.generated_overlap()
    # The Multiwfn-extracted S and the ORCA S carry the same printed
    # precision; the original genSbas matches both to ~3e-9.
    np.testing.assert_allclose(S, ref, atol=1e-8, rtol=0.0)
