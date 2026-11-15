"""Phase 8C — UHF/ROHF native f validation on O2/def2-TZVP."""
from pathlib import Path
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    from_orca_uhf_directory, from_orca_rohf_directory,
)

_HERE = Path(__file__).resolve()
_FIX = _HERE.parents[1] / "fixtures" / "phase8c"
if not _FIX.exists():
    pytest.skip("Phase 8C O2/def2-TZVP fixtures unavailable", allow_module_level=True)

_UHF = _FIX / "o2_uhf_def2tzvp"
_ROHF = _FIX / "o2_rohf_def2tzvp"


def _f_indices(model):
    return np.array([a.index - 1 for a in model.basis.aos if a.l == 3], dtype=int)


def _D(model):
    D = np.eye(model.nbasis)
    for sh in model.basis.shells:
        if sh.l != 3:
            continue
        idx = np.array([a.index - 1 for a in model.basis.aos if a.shell_index == sh.index])
        D[idx, idx] = [1, 1, 1, 1, 1, -1, -1]
    return D


def _reference(model):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=True)
        eng.prepare()
        return eng.calculate_mayer()


@pytest.mark.parametrize("name,fn", [("uhf", from_orca_uhf_directory), ("rohf", from_orca_rohf_directory)])
def test_open_shell_f_canonicalization_and_full_flow(name, fn):
    path = _UHF if name == "uhf" else _ROHF
    src = fn(path)
    can = fn(path, canonicalize_angular=True)
    assert src.schema_version == "1.1.0"
    assert can.schema_version == "1.2.0"
    fsh = [sh for sh in can.basis.shells if sh.l == 3]
    assert len(fsh) >= 2  # one f shell on each O atom
    assert all(sh.angular.state == "canonical" for sh in fsh)
    ref = _reference(can)
    with qe.Engine() as eng:
        eng.load_molecule_v1(can, allow_open_shell=True, prepare_from_orbitals=True)
        eng.prepare()
        S = eng.generated_overlap()
        P = eng.generated_density(0)
        Pa = eng.generated_density(1)
        Pb = eng.generated_density(2)
        res = eng.calculate_mayer()
    np.testing.assert_allclose(S, can.matrices.S.data, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(P, can.matrices.P_total.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(Pa, can.matrices.P_alpha.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(Pb, can.matrices.P_beta.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(np.trace(Pa @ S), 9.0, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(np.trace(Pb @ S), 7.0, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(np.trace(P @ S), 16.0, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(np.trace(res.alpha), np.trace(ref.alpha), atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(res.alpha, ref.alpha, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(res.beta, ref.beta, atol=1e-7, rtol=0.0)
    assert can.electronic.wfntype in (1, 2)


def test_open_shell_f_phase_and_primitive_density():
    for fn, path in ((from_orca_uhf_directory, _UHF),
                     (from_orca_rohf_directory, _ROHF)):
        src = fn(path)
        can = fn(path, canonicalize_angular=True)
        D = _D(can)
        C0 = src.wavefunction.orbitals.coefficients
        C = can.wavefunction.orbitals.coefficients
        S0 = src.matrices.S.data
        S = can.matrices.S.data
        np.testing.assert_allclose(C, D @ C0, atol=1e-12)
        np.testing.assert_allclose(S, D @ S0 @ D, atol=1e-12)
        with qe.Engine() as eng:
            eng.load_molecule_v1(can, allow_open_shell=True, prepare_from_orbitals=True)
            eng.prepare()
            eng.generate_primitive_density()
            n = eng._api.get_primitive_density_dimensions_v1()
            P = eng.generated_primitive_density(0)
            Pa = eng.generated_primitive_density(1)
            Pb = eng.generated_primitive_density(2)
            Sp = eng.generated_primitive_overlap()
        assert n > can.nbasis
        np.testing.assert_allclose(np.trace(P @ Sp), 16.0, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(np.trace(Pa @ Sp), 9.0, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(np.trace(Pb @ Sp), 7.0, atol=1e-6, rtol=0.0)
        np.testing.assert_allclose(P, Pa + Pb, atol=1e-14, rtol=0.0)


def test_open_shell_noncanonical_f_rejected():
    for fn, path in ((from_orca_uhf_directory, _UHF),
                     (from_orca_rohf_directory, _ROHF)):
        src = fn(path)
        with qe.Engine() as eng:
            eng.load_molecule_v1(src, allow_open_shell=True, prepare_from_orbitals=True)
            with pytest.raises(qe.QeUnsupported):
                eng.prepare()
