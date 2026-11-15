"""Phase 9C — PySCF in-memory adapter and source equivalence."""
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pyscf")
from pyscf import dft, gto, scf

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    from_orca_directory, from_orca_rohf_directory, from_orca_uhf_directory,
)
from qe_multiwfn.adapters.pyscf import PyscfAdapterError, from_pyscf
from qe_multiwfn.model_v1 import symbol_from_z

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
if not _ORCA.exists():
    pytest.skip("scientific fixtures unavailable", allow_module_level=True)


def _atom(model):
    z = model.atoms.z
    c = model.geometry.coordinates * 0.529177210903
    return "; ".join(
        f"{symbol_from_z(int(zz))} {x:.12f} {y:.12f} {z:.12f}"
        for zz, (x, y, z) in zip(z, c)
    )


def _make(mol, mf_type):
    mf = mf_type(mol)
    mf.conv_tol = 1e-10
    mf.kernel()
    assert mf.converged
    return mf


def _pyscf(model, basis, mf_type, cart=False):
    mol = gto.M(atom=_atom(model), basis=basis,
                charge=model.electronic.charge,
                spin=model.electronic.multiplicity - 1,
                cart=cart, verbose=0)
    return mol, _make(mol, mf_type)


def _mayer(mdm):
    with qe.Engine() as eng:
        return eng.calculate_mayer(mdm)


@pytest.mark.parametrize("name", ["h2", "h2o"])
def test_pyscf_rhf_matches_orca(name):
    ref = from_orca_directory(_ORCA / name)
    mol, mf = _pyscf(ref, "sto-3g", scf.RHF)
    mdm = from_pyscf(mol, mf)
    assert mdm.electronic.wfntype == 0
    assert np.max(np.abs(mdm.matrices.S.data - ref.matrices.S.data)) < 1e-7
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-6, rtol=0.0)


@pytest.mark.parametrize("name,fn,mf_type", [
    ("uhf", from_orca_uhf_directory, scf.UHF),
    ("rohf", from_orca_rohf_directory, scf.ROHF),
])
def test_pyscf_open_shell_matches_orca(name, fn, mf_type):
    ref = fn(_ORCA / name / f"o2_{name}_sto3g")
    mol, mf = _pyscf(ref, "sto-3g", mf_type)
    mdm = from_pyscf(mol, mf)
    assert mdm.electronic.wfntype == ref.electronic.wfntype
    assert mdm.matrices.P_alpha is not None and mdm.matrices.P_beta is not None
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(res.alpha, ref_res.alpha, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(res.beta, ref_res.beta, atol=1e-6, rtol=0.0)


@pytest.mark.parametrize("name,basis,mf_type", [
    ("h2o", "sto-3g", scf.RHF),
    ("uhf", "sto-3g", scf.UHF),
    ("rohf", "sto-3g", scf.ROHF),
])
def test_pyscf_full_state_without_matrices(name, basis, mf_type):
    if name == "h2o":
        ref = from_orca_directory(_ORCA / "h2o")
    elif name == "uhf":
        ref = from_orca_uhf_directory(_ORCA / "uhf" / "o2_uhf_sto3g")
    else:
        ref = from_orca_rohf_directory(_ORCA / "rohf" / "o2_rohf_sto3g")
    model_ref = ref
    mol, mf = _pyscf(model_ref, basis, mf_type)
    mdm = from_pyscf(mol, mf, include_overlap=False)
    assert mdm.matrices.S is None and mdm.matrices.P_total is None
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-6, rtol=0.0)
    if ref.electronic.wfntype in (1, 2):
        np.testing.assert_allclose(res.alpha, ref_res.alpha, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(res.beta, ref_res.beta, atol=1e-6, rtol=0.0)


def test_pyscf_spherical_f_direct_and_full():
    ref = from_orca_directory(_ORCA / "df" / "h2s_def2tzvp",
                              canonicalize_angular=True)
    mol, mf = _pyscf(ref, "def2-tzvp", scf.RHF)
    mdm = from_pyscf(mol, mf)
    assert mdm.schema_version == "1.2.0"
    assert np.max(np.abs(mdm.matrices.S.data - ref.matrices.S.data)) < 1e-7
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-5, rtol=0.0)
    full = from_pyscf(mol, mf, include_overlap=False)
    assert full.matrices.S is None and full.matrices.P_total is None
    full_res = _mayer(full)
    np.testing.assert_allclose(full_res.total, ref_res.total, atol=1e-5, rtol=0.0)


def test_pyscf_cartesian_d_matches_cartesian_fixture():
    ref = from_orca_directory(_VAL / "fixtures" / "cartesian" / "h2o_631gstar_cart")
    mol, mf = _pyscf(ref, "6-31g*", scf.RHF, cart=True)
    mdm = from_pyscf(mol, mf)
    assert mdm.basis.representation == "cartesian"
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-6, rtol=0.0)
    with pytest.raises(PyscfAdapterError, match="Cartesian-d"):
        from_pyscf(mol, mf, include_overlap=False)


def test_pyscf_rejects_dft_and_nonconverged():
    ref = from_orca_directory(_ORCA / "h2o")
    mol = gto.M(atom=_atom(ref), basis="sto-3g", verbose=0)
    mf = dft.RKS(mol)
    mf.converged = True
    with pytest.raises(PyscfAdapterError, match="DFT"):
        from_pyscf(mol, mf)
    mf = scf.RHF(mol)
    mf.converged = False
    with pytest.raises(PyscfAdapterError, match="converged"):
        from_pyscf(mol, mf)


def test_pyscf_spherical_d_matches_orca():
    ref = from_orca_directory(_ORCA / "df" / "h2o_631gstar")
    mol, mf = _pyscf(ref, "6-31g*", scf.RHF, cart=False)
    mdm = from_pyscf(mol, mf)
    assert mdm.basis.representation == "spherical"
    res = _mayer(mdm)
    ref_res = _mayer(ref)
    np.testing.assert_allclose(res.total, ref_res.total, atol=1e-5, rtol=0.0)
    full = from_pyscf(mol, mf, include_overlap=False)
    np.testing.assert_allclose(_mayer(full).total, ref_res.total,
                               atol=1e-5, rtol=0.0)


def test_pyscf_p_components_are_distinct_and_ordered():
    ref = from_orca_directory(_ORCA / "h2o")
    mol, mf = _pyscf(ref, "sto-3g", scf.RHF)
    mdm = from_pyscf(mol, mf)
    p_aos = [a for a in mdm.basis.aos if a.l == 1]
    assert [a.component for a in p_aos[:3]] == ["pz", "px", "py"]
    assert [a.multiwfn_type for a in p_aos[:3]] == [4, 2, 3]
    assert len({a.component for a in p_aos}) == 3
