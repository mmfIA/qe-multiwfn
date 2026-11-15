"""Phase 6A — original Multiwfn genP integration."""
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


def _ref_mayer(model, allow_open_shell=False):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=allow_open_shell)
        eng.prepare()
        return eng.calculate_mayer()


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_genp_rhf_matches_reference(mol):
    model = from_orca_directory(_ORCA / mol)
    ref = _ref_mayer(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_density()
        P = eng.generated_density(0)
        res = eng.calculate_mayer()
    np.testing.assert_allclose(P, model.matrices.P_total.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-12, rtol=0.0)


def test_genp_uhf_and_rohf_match_reference():
    for fn, d, wfntype in (
        (from_orca_uhf_directory, "uhf", 1),
        (from_orca_rohf_directory, "rohf", 2),
    ):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        ref = _ref_mayer(model, allow_open_shell=True)
        with qe.Engine() as eng:
            eng.load_molecule_v1(model, allow_open_shell=True)
            eng.prepare()
            eng.generate_density()
            Pa = eng.generated_density(1)
            Pb = eng.generated_density(2)
            P = eng.generated_density(0)
            res = eng.calculate_mayer()
        np.testing.assert_allclose(Pa, model.matrices.P_alpha.data, atol=1e-10, rtol=0.0)
        np.testing.assert_allclose(Pb, model.matrices.P_beta.data, atol=1e-10, rtol=0.0)
        np.testing.assert_allclose(P, model.matrices.P_total.data, atol=1e-10, rtol=0.0)
        np.testing.assert_allclose(res.alpha, ref.alpha, atol=1e-12, rtol=0.0)
        np.testing.assert_allclose(res.beta, ref.beta, atol=1e-12, rtol=0.0)


def test_genp_spherical_d():
    model = from_orca_directory(_DF / "h2o_631gstar")
    ref = _ref_mayer(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_density()
        P = eng.generated_density(0)
        res = eng.calculate_mayer()
    np.testing.assert_allclose(P, model.matrices.P_total.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-12, rtol=0.0)


def test_genp_cartesian_d():
    model = from_orca_directory(_CART)
    ref = _ref_mayer(model)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        eng.generate_density()
        P = eng.generated_density(0)
        res = eng.calculate_mayer()
    np.testing.assert_allclose(P, model.matrices.P_total.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-12, rtol=0.0)
