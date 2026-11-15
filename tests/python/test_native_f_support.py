"""Phase 8B — native f support through canonical MDM 1.2."""
from pathlib import Path
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import from_orca_directory

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_H2S = _VAL / "orca" / "df" / "h2s_def2tzvp"
if not _H2S.exists():
    pytest.skip("H2S fixture unavailable", allow_module_level=True)


def _canonical():
    return from_orca_directory(_H2S, canonicalize_angular=True)


def _reference_mayer(model):
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        return eng.calculate_mayer().total


def test_f_full_flow_matches_supplied_reference():
    can = _canonical()
    ref = _reference_mayer(can)
    with qe.Engine() as eng:
        eng.load_molecule_v1(can, prepare_from_orbitals=True)
        eng.prepare()
        S = eng.generated_overlap()
        P = eng.generated_density(0)
        res = eng.calculate_mayer().total
    np.testing.assert_allclose(S, can.matrices.S.data, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(P, can.matrices.P_total.data, atol=1e-10, rtol=0.0)
    np.testing.assert_allclose(res, ref, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(float(np.trace(P @ S)), can.electronic.nelectron,
                               atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(P @ S @ P, 2.0 * P, atol=1e-6, rtol=0.0)


def test_f_full_flow_matches_multiwfn_standalone():
    import sys
    sys.path.insert(0, str(_VAL))
    from validation.multiwfn_parser import read_multiwfn_bndmat
    can = _canonical()
    with qe.Engine() as eng:
        eng.load_molecule_v1(can, prepare_from_orbitals=True)
        eng.prepare()
        B = eng.calculate_mayer().total
    bnd = _VAL / "df_results" / "h2s_def2tzvp" / "multiwfn_bndmat.txt"
    if not bnd.exists():
        pytest.skip("Multiwfn f reference unavailable")
    Bmw = read_multiwfn_bndmat(bnd, expected_n=can.ncenter)
    assert np.max(np.abs(B - Bmw)) <= 1e-6
    baseline = _VAL / "df_results" / "h2s_def2tzvp" / "qe_mayer.npy"
    if baseline.exists():
        assert np.max(np.abs(B - np.load(baseline))) <= 1e-6


def test_f_primitive_density_is_separate_and_has_correct_trace():
    can = _canonical()
    with qe.Engine() as eng:
        eng.load_molecule_v1(can, prepare_from_orbitals=True)
        eng.prepare()
        Pcur = eng.generated_density(0).copy()
        eng.generate_primitive_density()
        n = eng._api.get_primitive_density_dimensions_v1()
        Pprim = eng.generated_primitive_density(0)
        Sprim = eng.generated_primitive_overlap()
        Pcur_after = eng.generated_density(0)
    assert n > can.nbasis
    assert Pprim.shape == (n, n)
    np.testing.assert_allclose(Pprim, Pprim.T, atol=1e-14, rtol=0.0)
    np.testing.assert_allclose(float(np.trace(Pprim @ Sprim)),
                               can.electronic.nelectron, atol=1e-6, rtol=0.0)
    np.testing.assert_allclose(Pcur_after, Pcur, atol=1e-12, rtol=0.0)


def test_noncanonical_f_original_path_rejected():
    src = from_orca_directory(_H2S)  # MDM 1.1, no angular metadata
    with qe.Engine() as eng:
        eng.load_molecule_v1(src, prepare_from_orbitals=True)
        with pytest.raises(qe.QeUnsupported):
            eng.prepare()


def test_noncanonical_f_overlap_generation_rejected():
    src = from_orca_directory(_H2S)
    with qe.Engine() as eng:
        eng.load_molecule_v1(src)
        eng.prepare()
        with pytest.raises(qe.QeUnsupported):
            eng.generate_overlap()


def test_canonical_f_overlap_generation_allowed():
    can = _canonical()
    with qe.Engine() as eng:
        eng.load_molecule_v1(can)
        eng.prepare()
        eng.generate_overlap()
        S = eng.generated_overlap()
    np.testing.assert_allclose(S, can.matrices.S.data, atol=1e-7, rtol=0.0)
