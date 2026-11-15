"""Versioned P0 validation protocol (H2/H2O/C6H6 RHF/STO-3G).

The external P0 fixtures are not redistributed. This test verifies their
SHA-256 manifest and, when the fixture root is available, reproduces the
historical P0 scientific checks with the current library.

Set ``QE_P0_FIXTURES`` to the external ``QE-Multiwfn-validation`` directory.
Without it the three system tests are skipped with an explicit reason; the
manifest-format test still runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import from_orca_directory

_HERE = Path(__file__).resolve()
_DEFAULT_ROOT = _HERE.parents[3] / "QE-Multiwfn-validation"
_P0_ROOT = Path(os.environ.get("QE_P0_FIXTURES", str(_DEFAULT_ROOT)))
_MANIFEST = json.loads((_HERE.parent / "p0_fixtures.json").read_text())
_HAS_FIXTURES = _P0_ROOT.exists()

_SYSTEMS = {
    "h2": {"name": "H2", "nbasis": 2, "nelec": 2,
           "energy": -1.117505885114},
    "h2o": {"name": "H2O", "nbasis": 7, "nelec": 10,
            "energy": -74.965901192193},
    "benzene": {"name": "C6H6", "nbasis": 36, "nelec": 42,
                "energy": -227.891360374421},
}

_FINAL_SP_RE = re.compile(r"FINAL SINGLE POINT ENERGY\s+([-+0-9.]+)", re.I)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_files_for(mol: str):
    return [
        f"orca/{mol}/sp.json",
        f"orca/{mol}/sp.out",
        f"orca/{mol}/sp.property.txt",
        f"orca/{mol}/sp.molden.input",
        f"qe_results/{mol}/mayer.npy",
        "comparisons/validation_results.json",
    ]


def test_p0_manifest_is_complete_and_well_formed():
    required = set()
    for mol in _SYSTEMS:
        required.update(_manifest_files_for(mol))
    files = _MANIFEST.get("files", {})
    assert required.issubset(files)
    for rel in required:
        entry = files[rel]
        assert len(entry["sha256"]) == 64
        assert entry["size"] > 0


@pytest.mark.skipif(not _HAS_FIXTURES,
                    reason="P0 external fixtures unavailable; set QE_P0_FIXTURES")
@pytest.mark.parametrize("mol", list(_SYSTEMS))
def test_p0_system(mol):
    info = _SYSTEMS[mol]
    files = _MANIFEST["files"]
    for rel in _manifest_files_for(mol):
        path = _P0_ROOT / rel
        assert path.exists(), f"missing P0 fixture: {path}"
        assert _sha256(path) == files[rel]["sha256"], f"P0 fixture hash mismatch: {rel}"

    model = from_orca_directory(_P0_ROOT / "orca" / mol)
    assert model.geometry.unit_source == "angstrom"
    assert model.provenance.coordinate_unit_source == "angstrom"
    assert model.nbasis == info["nbasis"]
    assert model.electronic.nelectron == info["nelec"]

    C = model.wavefunction.orbitals.coefficients
    S = model.matrices.S.data
    P = model.matrices.P_total.data
    assert C.shape[0] == S.shape[0] == S.shape[1] == info["nbasis"]
    assert C.shape[1] == info["nbasis"]

    ctc_err = float(np.max(np.abs(C.T @ S @ C - np.eye(C.shape[1]))))
    trps_err = abs(float(np.trace(P @ S)) - info["nelec"])
    scale = max(1.0, float(np.max(np.abs(2.0 * P))))
    psp_err = float(np.max(np.abs(P @ S @ P - 2.0 * P)))
    assert ctc_err < 1e-10
    assert trps_err < 1e-8
    assert psp_err <= 1e-6 * scale
    assert float(np.max(np.abs(P - P.T))) < 1e-10
    assert float(np.min(np.linalg.eigvalsh(S))) > 0.0

    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        B = np.asarray(eng.calculate_mayer().total, dtype=np.float64)

    baseline = np.load(_P0_ROOT / "qe_results" / mol / "mayer.npy")
    assert B.shape == baseline.shape
    np.testing.assert_allclose(B, baseline, atol=1e-12, rtol=0.0)

    hist_all = json.loads(
        (_P0_ROOT / "comparisons" / "validation_results.json").read_text()
    )
    hist = hist_all["molecules"][info["name"]]
    np.testing.assert_allclose(B, np.asarray(hist["qe_mayer"]),
                               atol=1e-12, rtol=0.0)
    np.testing.assert_allclose(B, np.asarray(hist["multiwfn_mayer"]),
                               atol=1e-6, rtol=0.0)
    assert hist["comparison"]["max_abs_diff"] <= 1e-6

    text = (_P0_ROOT / "orca" / mol / "sp.out").read_text(errors="replace")
    match = _FINAL_SP_RE.search(text)
    assert match is not None
    energy = float(match.group(1))
    assert abs(energy - info["energy"]) < 1e-9
    assert abs(energy - hist["orca_energies"]["sp_final_energy"]) < 1e-9


@pytest.mark.skipif(not _HAS_FIXTURES,
                    reason="P0 external fixtures unavailable; set QE_P0_FIXTURES")
@pytest.mark.parametrize("mol", ["h2o", "benzene"])
def test_p0_p_component_order(mol):
    model = from_orca_directory(_P0_ROOT / "orca" / mol)
    for atom in sorted({ao.center for ao in model.basis.aos}):
        p = [ao for ao in model.basis.aos
             if ao.center == atom and ao.l == 1]
        if not p:
            continue
        assert [ao.component for ao in p[:3]] == ["pz", "px", "py"]
        assert [ao.multiwfn_type for ao in p[:3]] == [4, 2, 3]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
