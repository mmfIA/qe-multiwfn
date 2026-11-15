"""ORCA → Molecular Data Model 1.0 adapter tests (Phases 4/6/7).

The fixtures live in the validation project. Tests are skipped when the
fixtures are not present, so the library test suite stays self-contained.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    OrcaAdapterError,
    from_orca_directory,
    from_orca_json,
)

_HERE = Path(__file__).resolve()
_VALIDATION = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VALIDATION / "orca"
_QE_RESULTS = _VALIDATION / "qe_results"
_EXTRACTED = _VALIDATION / "extracted"

if not _ORCA.exists():
    pytest.skip(f"ORCA fixtures not available: {_ORCA}", allow_module_level=True)

EXPECTED = {
    "h2": dict(ncenter=2, nbasis=2, nprims=6, nelectron=2, nshell=2),
    "h2o": dict(ncenter=3, nbasis=7, nprims=21, nelectron=10, nshell=5),
    "benzene": dict(ncenter=12, nbasis=36, nprims=108, nelectron=42, nshell=24),
}


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_model_metadata(mol):
    model = from_orca_directory(_ORCA / mol)
    exp = EXPECTED[mol]
    assert model.ncenter == exp["ncenter"]
    assert model.nbasis == exp["nbasis"]
    assert model.nprims == exp["nprims"]
    assert model.electronic.nelectron == exp["nelectron"]
    assert model.electronic.wfntype == qe.molecular.WFNTYPE_RHF
    assert len(model.basis.shells) == exp["nshell"]
    assert len(model.basis.aos) == exp["nbasis"]
    assert model.basis.primitives.nprims == exp["nprims"]
    assert model.basis.contiguity_ok()
    model.validate(strict=True)
    assert model.is_legacy_representable()


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_ao_map_matches_legacy_arrays(mol):
    model = from_orca_directory(_ORCA / mol)
    legacy = model.to_legacy()
    np.testing.assert_array_equal(model.basis.center_array(), legacy.basis_center)
    np.testing.assert_array_equal(
        model.basis.angular_type_array(), legacy.basis_type
    )
    # Every AO must carry a Multiwfn component code.
    assert all(ao.multiwfn_type is not None and ao.multiwfn_type >= 1
               for ao in model.basis.aos)
    # s/p component codes: s=1, pz=4, px=2, py=3.
    for ao in model.basis.aos:
        if ao.angular_type == 0:
            assert ao.multiwfn_type == 1
        elif ao.angular_type == 1:
            assert ao.multiwfn_type in (2, 3, 4)


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_matrices_are_bitwise_reproducible(mol):
    model = from_orca_directory(_ORCA / mol)
    p_path = _EXTRACTED / mol / "P.npy"
    s_path = _EXTRACTED / mol / "S.npy"
    if p_path.exists():
        assert np.array_equal(model.matrices.P_total.data, np.load(p_path))
    if s_path.exists():
        assert np.array_equal(model.matrices.S.data, np.load(s_path))


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_v1_engine_reproduces_baseline_mayer(mol):
    baseline_path = _QE_RESULTS / mol / "mayer.npy"
    if not baseline_path.exists():
        pytest.skip(f"baseline Mayer matrix missing: {baseline_path}")
    model = from_orca_directory(_ORCA / mol)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        result = eng.calculate_mayer().total
        flags = eng._api.get_readiness_v1()
    baseline = np.load(baseline_path)
    assert np.array_equal(result, baseline), (
        f"{mol}: max|delta|={np.max(np.abs(result - baseline)):.3e}"
    )
    assert flags & qe.native.QE_V1_READY_MAYER


def test_orca_provenance_records_version_and_hashes():
    model = from_orca_directory(_ORCA / "h2")
    prov = model.provenance
    assert prov.source_program == "ORCA"
    assert prov.source_version == "6.1.1"
    assert prov.source_format == "orca_json"
    assert prov.coordinate_unit_source == "angstrom"
    assert prov.conversion_factor > 0
    assert prov.input_files
    assert all(len(f.sha256) == 64 for f in prov.input_files)
    assert set(("S", "C", "P_total", "coordinates")).issubset(prov.hashes)


def test_from_orca_json_wrapper():
    model = from_orca_json(_ORCA / "h2o" / "sp.json")
    assert model.nbasis == 7


def test_orca_rejects_non_rhf(tmp_path):
    data = json.loads((_ORCA / "h2" / "sp.json").read_text())
    data["Molecule"]["HFTyp"] = "UHF"
    (tmp_path / "sp.json").write_text(json.dumps(data))
    with pytest.raises(OrcaAdapterError, match="RHF"):
        from_orca_directory(tmp_path)


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_legacy_engine_still_reproduces_baseline(mol):
    """Backward compatibility: the 0.1.1 engine path with real ORCA data."""
    baseline_path = _QE_RESULTS / mol / "mayer.npy"
    if not baseline_path.exists():
        pytest.skip(f"baseline Mayer matrix missing: {baseline_path}")
    model = from_orca_directory(_ORCA / mol)
    legacy = model.to_legacy()
    with qe.Engine() as eng:
        eng.load_molecule(legacy)
        eng.prepare()
        result = eng.calculate_mayer().total
    baseline = np.load(baseline_path)
    assert np.array_equal(result, baseline)


def test_orca_rejects_inconsistent_shell_labels(tmp_path):
    """A d shell without matching d labels must fail closed."""
    data = json.loads((_ORCA / "h2" / "sp.json").read_text())
    data["Molecule"]["Atoms"][0]["Basis"][0]["Shell"] = "d"
    (tmp_path / "sp.json").write_text(json.dumps(data))
    with pytest.raises(OrcaAdapterError):
        from_orca_directory(tmp_path)


# ----------------------------------------------------------------------
# Spherical d/f fixtures (H2O/6-31G* and H2S/def2-TZVP)
# ----------------------------------------------------------------------
_ORCA_DF = _ORCA / "df"
_DF_RESULTS = _VALIDATION / "df_results"


@pytest.mark.parametrize("mol", ["h2o_631gstar", "h2s_def2tzvp"])
def test_orca_spherical_df_model(mol):
    if not (_ORCA_DF / mol).exists():
        pytest.skip(f"d/f fixture missing: {_ORCA_DF / mol}")
    model = from_orca_directory(_ORCA_DF / mol)
    assert model.basis.representation == "spherical"
    assert any(ao.angular_type == 2 for ao in model.basis.aos)
    d_codes = [ao.multiwfn_type for ao in model.basis.aos if ao.angular_type == 2]
    assert d_codes and all(-5 <= c <= -1 for c in d_codes)
    if mol == "h2s_def2tzvp":
        assert any(ao.angular_type == 3 for ao in model.basis.aos)
        f_codes = [ao.multiwfn_type for ao in model.basis.aos if ao.angular_type == 3]
        assert f_codes and all(-12 <= c <= -6 for c in f_codes)
    model.validate(strict=True)
    assert model.is_legacy_representable()
    legacy = model.to_legacy()
    assert legacy.nbasis == model.nbasis and legacy.nprims == model.nprims


@pytest.mark.parametrize("mol", ["h2o_631gstar", "h2s_def2tzvp"])
def test_orca_df_v1_mayer_vs_multiwfn(mol):
    if not (_ORCA_DF / mol).exists():
        pytest.skip(f"d/f fixture missing: {_ORCA_DF / mol}")
    import sys
    sys.path.insert(0, str(_VALIDATION))
    from validation.multiwfn_parser import read_multiwfn_bndmat

    model = from_orca_directory(_ORCA_DF / mol)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        B = eng.calculate_mayer().total
    baseline = _DF_RESULTS / mol / "qe_mayer.npy"
    if baseline.exists():
        assert np.array_equal(B, np.load(baseline))
    bnd = _DF_RESULTS / mol / "multiwfn_bndmat.txt"
    if bnd.exists():
        Bmw = read_multiwfn_bndmat(bnd, expected_n=model.ncenter)
        assert np.max(np.abs(B - Bmw)) <= 1e-6


@pytest.mark.parametrize("mol", ["h2o_631gstar", "h2s_def2tzvp"])
def test_orca_df_vs_orca_bondorders(mol):
    if not (_ORCA_DF / mol).exists():
        pytest.skip(f"d/f fixture missing: {_ORCA_DF / mol}")
    import re
    model = from_orca_directory(_ORCA_DF / mol)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        B = eng.calculate_mayer().total
    text = (_ORCA_DF / mol / "sp.property.txt").read_text()
    mc = re.search(r"&components.*?\n(.*?)&BondOrders", text, re.S)
    mb = re.search(r"&BondOrders.*?\n(.*?)(?:\$|&ATNO|&VA)", text, re.S)
    pairs = []
    for line in mc.group(1).strip().splitlines():
        p = line.split()
        if len(p) >= 5:
            try:
                pairs.append((int(p[1]), int(p[3])))
            except ValueError:
                pass
    vals = []
    for line in mb.group(1).strip().splitlines():
        p = line.split()
        if len(p) >= 2:
            try:
                vals.append(float(p[1]))
            except ValueError:
                pass
    assert len(pairs) == len(vals) and pairs
    assert max(abs(B[i, j] - v) for (i, j), v in zip(pairs, vals)) < 1e-4


def test_orca_cartesian_df_request_is_rejected():
    if not (_ORCA_DF / "h2o_631gstar").exists():
        pytest.skip("d/f fixture missing")
    with pytest.raises(OrcaAdapterError, match="Cartesian"):
        from_orca_directory(_ORCA_DF / "h2o_631gstar", representation="cartesian")
