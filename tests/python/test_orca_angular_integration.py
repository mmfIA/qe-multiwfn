"""Phase 7C — ORCA → MDM 1.2 angular canonicalization."""
from pathlib import Path
import shutil
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    OrcaAdapterError, from_orca_directory, from_orca_uhf_directory,
    from_orca_rohf_directory,
)
from qe_multiwfn.angular import (
    AngularAlreadyCanonicalError, canonicalize_model_angular,
    known_source_convention,
)

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
_H2S = _ORCA / "df" / "h2s_def2tzvp"
_H2O_D = _ORCA / "df" / "h2o_631gstar"
if not _HERE.parents[3].joinpath("QE-Multiwfn-validation").exists():
    pytest.skip("validation fixtures unavailable", allow_module_level=True)


def _f_indices(model):
    return np.array([a.index - 1 for a in model.basis.aos if a.l == 3], dtype=int)


def _D_for(model):
    n = model.nbasis
    D = np.eye(n)
    f = _f_indices(model)
    D[f, f] = np.array([1, 1, 1, 1, 1, -1, -1])
    return D


def test_orca_f_default_remains_legacy_1_1():
    model = from_orca_directory(_H2S)
    assert model.schema_version == "1.1.0"
    assert all(sh.angular is None for sh in model.basis.shells)
    # existing compatibility path remains intact
    assert model.is_legacy_representable()
    assert model.to_legacy().nbasis == model.nbasis


def test_orca_f_canonicalization_is_1_2_and_preserves_invariants():
    src = from_orca_directory(_H2S)
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    assert src.schema_version == "1.1.0"
    assert can.schema_version == "1.2.0"
    assert can.basis.angular.state == "canonical"
    fsh = [sh for sh in can.basis.shells if sh.l == 3]
    assert fsh and all(sh.angular.state == "canonical" for sh in fsh)
    C0 = src.wavefunction.orbitals.coefficients
    C = can.wavefunction.orbitals.coefficients
    S0 = src.matrices.S.data; S = can.matrices.S.data
    P0 = src.matrices.P_total.data; P = can.matrices.P_total.data
    D = _D_for(can)
    np.testing.assert_allclose(C, D @ C0, atol=1e-12)
    np.testing.assert_allclose(S, D @ S0 @ D, atol=1e-12)
    np.testing.assert_allclose(P, D @ P0 @ D, atol=1e-12)
    np.testing.assert_allclose(C.T @ S @ C, C0.T @ S0 @ C0, atol=1e-10)
    np.testing.assert_allclose(np.trace(P @ S), np.trace(P0 @ S0), atol=1e-10)
    np.testing.assert_allclose(P @ S @ P, 2 * P, atol=1e-10)
    assert len(can.provenance.angular_transforms) == 1
    rec = can.provenance.angular_transforms[0]
    assert rec.phase_signs == (1, 1, 1, 1, 1, -1, -1)
    assert "orca" in rec.source_convention_id.lower()


def test_orca_f_canonicalization_changes_only_f_cross_blocks():
    src = from_orca_directory(_H2S)
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    f = _f_indices(can)
    D = _D_for(can)
    # The f block remains identity; cross-blocks change sign only where D has
    # opposite signs.  Compare the full matrices to the explicit D transform.
    S0 = src.matrices.S.data
    S = can.matrices.S.data
    diff = S - D @ S0 @ D
    assert np.max(np.abs(diff)) < 1e-12
    # Non-f rows/columns that are not cross-coupled to f are unchanged.
    other = np.setdiff1d(np.arange(can.nbasis), f)
    assert np.max(np.abs(S[np.ix_(other, other)] - S0[np.ix_(other, other)])) < 1e-12


def test_orca_f_second_canonicalization_rejected():
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    with pytest.raises(AngularAlreadyCanonicalError):
        canonicalize_model_angular(can, source={
            2: known_source_convention(2, "orca", "6.1.1"),
            3: known_source_convention(3, "orca", "6.1.1"),
        })


def test_orca_non_f_remains_1_1_by_default():
    model = from_orca_directory(_H2O_D)
    assert model.schema_version == "1.1.0"
    assert all(sh.angular is None for sh in model.basis.shells)


def test_orca_d_canonicalization_identity_phase():
    src = from_orca_directory(_H2O_D)
    can = from_orca_directory(_H2O_D, canonicalize_angular=True)
    assert can.schema_version == "1.2.0"
    dsh = [sh for sh in can.basis.shells if sh.l == 2]
    assert dsh and all(sh.angular.state == "canonical" for sh in dsh)
    np.testing.assert_allclose(can.matrices.S.data, src.matrices.S.data, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(can.matrices.P_total.data, src.matrices.P_total.data, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(
        can.wavefunction.orbitals.coefficients,
        src.wavefunction.orbitals.coefficients, atol=0.0, rtol=0.0
    )


def test_orca_canonical_model_deltas_are_consistent_with_mdm_1_2():
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    assert can.schema_version == "1.2.0"
    can.validate(strict=True)
    with pytest.raises(ValueError):
        can.to_legacy()
    with pytest.raises(ValueError):
        can.with_ao_order(list(range(can.nbasis)))


def test_orca_f_version_unvalidated_fails_closed(tmp_path):
    src = _H2S
    dst = tmp_path / "h2s"
    shutil.copytree(src, dst)
    out = dst / "sp.out"
    text = out.read_text()
    text = text.replace("Program Version 6.1.1", "Program Version 6.2.0")
    out.write_text(text)
    with pytest.raises(OrcaAdapterError, match="6.1.1|version"):
        from_orca_directory(dst, canonicalize_angular=True)
    # The legacy path remains available and unchanged.
    legacy = from_orca_directory(dst)
    assert legacy.schema_version == "1.1.0"


def test_orca_f_missing_version_fails_closed(tmp_path):
    dst = tmp_path / "h2s_no_out"
    dst.mkdir()
    shutil.copy2(_H2S / "sp.json", dst / "sp.json")
    with pytest.raises(OrcaAdapterError, match="6.1.1|version"):
        from_orca_directory(dst, canonicalize_angular=True)


def test_orca_f_backend_original_path_supported_in_phase8b():
    # Phase 8B lifts the native f guard for canonical MDM 1.2 data. The
    # non-canonical 1.1 f path remains fail-closed (tested in Phase 7C and 8B).
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    with qe.Engine() as eng:
        eng.load_molecule_v1(can, prepare_from_orbitals=True)
        eng.prepare()
        S = eng.generated_overlap()
        P = eng.generated_density(0)
    assert S.shape == can.matrices.S.data.shape
    assert P.shape == can.matrices.P_total.data.shape
    np.testing.assert_allclose(S, can.matrices.S.data, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(P, can.matrices.P_total.data, atol=1e-10, rtol=0.0)


def test_orca_uhf_rohf_legacy_paths_remain_1_1():
    for fn, d in ((from_orca_uhf_directory, "uhf"),
                  (from_orca_rohf_directory, "rohf")):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        assert model.schema_version == "1.1.0"
        # s/p-only: the opt-in canonicalizer leaves the model as 1.1.
        same = fn(_ORCA / d / f"o2_{d}_sto3g", canonicalize_angular=True)
        assert same.schema_version == "1.1.0"
        np.testing.assert_allclose(same.matrices.S.data, model.matrices.S.data)
        np.testing.assert_allclose(same.matrices.P_total.data, model.matrices.P_total.data)


def test_orca_d_canonical_backend_mayer_matches_source():
    src = from_orca_directory(_H2O_D)
    can = from_orca_directory(_H2O_D, canonicalize_angular=True)
    with qe.Engine() as eng:
        eng.load_molecule_v1(src)
        eng.prepare()
        Bsrc = eng.calculate_mayer().total
    with qe.Engine() as eng:
        eng.load_molecule_v1(can)
        eng.prepare()
        Bcan = eng.calculate_mayer().total
    np.testing.assert_array_equal(Bcan, Bsrc)
