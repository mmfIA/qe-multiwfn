"""cclib adapter: fail-closed parsing and canonical conversion."""
import copy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn.adapters.cclib import (
    CclibAdapterError, from_cclib, from_cclib_data,
)
from qe_multiwfn.adapters.orca import (
    from_orca_directory, from_orca_uhf_directory, from_orca_rohf_directory,
)
from qe_multiwfn.normalization import normalization_report
from qe_multiwfn.molecular import BOHR_TO_ANGSTROM

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
if not _ORCA.exists():
    pytest.skip("fixtures unavailable", allow_module_level=True)


def _cclib_like(model, hf):
    mo = model.wavefunction.orbitals
    if model.electronic.wfntype == 0:
        mocoeffs = [mo.coefficients]
        moocc = [mo.occupations]
        enes = [mo.energies]
    elif model.electronic.wfntype == 1:
        n = mo.coefficients.shape[1] // 2
        mocoeffs = [mo.coefficients[:, :n], mo.coefficients[:, n:]]
        moocc = [mo.occupations[:n], mo.occupations[n:]]
        enes = [mo.energies[:n], mo.energies[n:]]
    else:
        mocoeffs = [mo.coefficients]
        moocc = [mo.occupations]
        enes = [mo.energies]
    return SimpleNamespace(
        atomnos=model.atoms.z.copy(),
        atomcoords=np.array(model.geometry.coordinates * BOHR_TO_ANGSTROM),
        charge=model.electronic.charge,
        mult=model.electronic.multiplicity,
        aooverlaps=model.matrices.S.data.copy(),
        mocoeffs=mocoeffs,
        moocc=moocc,
        moenergies=enes,
        metadata={"package": "ORCA", "package_version": "6.1.1", "hf": hf},
    )


def test_cclib_fails_closed_on_orca_output():
    with pytest.raises(CclibAdapterError, match="cclib could not parse"):
        from_cclib(_ORCA / "h2o" / "sp.out")


@pytest.mark.parametrize("mol,hf,fn", [
    ("h2o", "RHF", from_orca_directory),
])
def test_cclib_rhf_conversion_with_basis(mol, hf, fn):
    ref = fn(_ORCA / mol)
    data = _cclib_like(ref, hf)
    model = from_cclib_data(data, basis=copy.deepcopy(ref.basis))
    assert model.electronic.wfntype == 0
    assert np.allclose(model.geometry.coordinates, ref.geometry.coordinates)
    assert normalization_report(model)["status"] == "PASS"
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        B = eng.calculate_mayer().total
    with qe.Engine() as eng:
        eng.load_molecule_v1(ref)
        eng.prepare()
        Bref = eng.calculate_mayer().total
    np.testing.assert_allclose(B, Bref, atol=0.0, rtol=0.0)


def test_cclib_uhf_and_rohf_conversion_with_basis():
    for hf, fn, d in (("UHF", from_orca_uhf_directory, "uhf"),
                      ("ROHF", from_orca_rohf_directory, "rohf")):
        ref = fn(_ORCA / d / f"o2_{d}_sto3g")
        data = _cclib_like(ref, hf)
        model = from_cclib_data(data, basis=copy.deepcopy(ref.basis))
        assert model.electronic.wfntype == ref.electronic.wfntype
        assert normalization_report(model)["status"] == "PASS"
        with qe.Engine() as eng:
            eng.load_molecule_v1(model, allow_open_shell=True)
            eng.prepare()
            res = eng.calculate_mayer()
        with qe.Engine() as eng:
            eng.load_molecule_v1(ref, allow_open_shell=True)
            eng.prepare()
            ref_res = eng.calculate_mayer()
        np.testing.assert_allclose(res.alpha, ref_res.alpha, atol=0.0, rtol=0.0)
        np.testing.assert_allclose(res.beta, ref_res.beta, atol=0.0, rtol=0.0)


def test_cclib_without_basis_is_partial_and_fails_closed():
    ref = from_orca_directory(_ORCA / "h2o")
    data = _cclib_like(ref, "RHF")
    model = from_cclib_data(data)
    assert model.basis.aos == []
    assert normalization_report(model)["status"] == "INCOMPLETE"
    with pytest.raises(qe.QeError):
        with qe.Engine() as eng:
            eng.load_molecule_v1(model)
