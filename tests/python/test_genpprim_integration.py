"""Phase 6B — original Multiwfn genPprim integration (primitive basis)."""
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


def _run(model, allow_open_shell=False):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=allow_open_shell)
        eng.prepare()
        Pcur = eng.generated_density(0).copy()
        ncur = Pcur.shape[0]
        eng.generate_primitive_density()
        nprims = eng._api.get_primitive_density_dimensions_v1()
        Pprim = eng.generated_primitive_density(0)
        Sprim = eng.generated_primitive_overlap()
        Pcur_after = eng.generated_density(0)
        out = {
            "nprims": nprims, "Pprim": Pprim, "Sprim": Sprim,
            "Pcur": Pcur, "Pcur_after": Pcur_after,
        }
        if allow_open_shell:
            out["Pa"] = eng.generated_primitive_density(1)
            out["Pb"] = eng.generated_primitive_density(2)
    return out


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_genpprim_rhf(mol):
    model = from_orca_directory(_ORCA / mol)
    out = _run(model)
    P, S = out["Pprim"], out["Sprim"]
    assert P.shape == S.shape == (out["nprims"], out["nprims"])
    np.testing.assert_allclose(P, P.T, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(S, S.T, atol=1e-14, rtol=0.0)
    # The original genPprim CO already contains primconnorm, so the
    # matching overlap is the raw unnormalized primitive doSint.
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    # Primitive density must not replace the current-basis density.
    np.testing.assert_allclose(out["Pcur_after"], out["Pcur"], atol=1e-12, rtol=0.0)
    assert out["nprims"] != P.shape[0] or out["nprims"] > 0
    assert out["nprims"] != out["Pcur"].shape[0]


def test_genpprim_uhf_and_rohf():
    for fn, d in ((from_orca_uhf_directory, "uhf"),
                  (from_orca_rohf_directory, "rohf")):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        out = _run(model, allow_open_shell=True)
        P, S = out["Pprim"], out["Sprim"]
        assert P.shape == S.shape == (out["nprims"], out["nprims"])
        np.testing.assert_allclose(P, P.T, atol=0.0, rtol=0.0)
        np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                                   atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(float(np.trace(out["Pa"] @ S)),
                                   model.electronic.naelectron, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(float(np.trace(out["Pb"] @ S)),
                                   model.electronic.nbelectron, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(out["Pprim"], out["Pa"] + out["Pb"], atol=1e-14, rtol=0.0)
        np.testing.assert_allclose(out["Pcur_after"], out["Pcur"], atol=1e-12, rtol=0.0)


def test_genpprim_spherical_d():
    model = from_orca_directory(_DF / "h2o_631gstar")
    out = _run(model)
    P, S = out["Pprim"], out["Sprim"]
    assert out["nprims"] > out["Pcur"].shape[0]
    assert P.shape == S.shape == (out["nprims"], out["nprims"])
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(P, P.T, atol=0.0, rtol=0.0)


def test_genpprim_cartesian_d():
    model = from_orca_directory(_CART)
    out = _run(model)
    P, S = out["Pprim"], out["Sprim"]
    assert out["nprims"] > out["Pcur"].shape[0]
    np.testing.assert_allclose(float(np.trace(P @ S)), model.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(P, P.T, atol=0.0, rtol=0.0)
