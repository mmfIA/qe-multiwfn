"""UHF (opt-in) scientific verification.

Fixtures live in the validation project (ORCA 6.1.1 O2/STO-3G UHF and a
fresh Multiwfn standalone bndmat). Tests are skipped when absent, so the
library package remains self-contained.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    OrcaAdapterError,
    from_orca_uhf_directory,
)

_HERE = Path(__file__).resolve()
_VALIDATION = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VALIDATION / "orca"
_UHF_DIR = _ORCA / "uhf" / "o2_uhf_sto3g"
_RESULTS = _VALIDATION / "uhf_results" / "o2_uhf_sto3g"

if not _UHF_DIR.exists():
    pytest.skip(f"UHF fixtures not available: {_UHF_DIR}", allow_module_level=True)


def _model():
    return from_orca_uhf_directory(_UHF_DIR)


def test_uhf_model_builds_and_validates():
    model = _model()
    assert model.electronic.wfntype == 1
    assert model.electronic.nelectron == 16
    assert model.electronic.naelectron == 9
    assert model.electronic.nbelectron == 7
    assert model.nbasis == 10 and model.nprims == 30
    assert model.matrices.P_alpha is not None
    assert model.matrices.P_beta is not None
    assert model.matrices.P_total.data.shape == (10, 10)
    model.validate(strict=True)
    assert model.is_legacy_representable() is False
    from qe_multiwfn import model_v1 as m1
    rep = m1.wavefunction_report(model)
    assert rep["status"] == "PASS"
    for key in ("electron_count_TrPS_alpha", "electron_count_TrPS_beta",
                "idempotency_PSP_alpha", "idempotency_PSP_beta",
                "total_vs_spin_sum"):
        assert rep[key]["passed"] is True


def test_uhf_requires_explicit_open_shell_flag():
    model = _model()
    with pytest.raises(qe.QeUnsupported):
        with qe.Engine() as eng:
            eng.load_molecule_v1(model)


def test_uhf_v1_mayer_matches_multiwfn_and_orca():
    import sys
    sys.path.insert(0, str(_VALIDATION))
    from validation.multiwfn_parser import read_multiwfn_bndmat_uhf

    model = _model()
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=True)
        eng.prepare()
        res = eng.calculate_mayer()
    assert res.has_spin_components
    assert res.alpha is not None and res.beta is not None

    # Stored regression matrices (bitwise).
    if (_RESULTS / "qe_mayer_total.npy").exists():
        assert np.array_equal(res.total, np.load(_RESULTS / "qe_mayer_total.npy"))
        assert np.array_equal(res.alpha, np.load(_RESULTS / "qe_mayer_alpha.npy"))
        assert np.array_equal(res.beta, np.load(_RESULTS / "qe_mayer_beta.npy"))

    # Independent Multiwfn blocks.
    bnd = _RESULTS / "multiwfn_bndmat.txt"
    if bnd.exists():
        blocks = read_multiwfn_bndmat_uhf(bnd, expected_n=model.ncenter)
        assert np.max(np.abs(res.alpha - blocks["alpha"])) <= 1e-6
        assert np.max(np.abs(res.beta - blocks["beta"])) <= 1e-6
        # QE total is the generalized Wiberg (mixed density) block.
        assert np.max(np.abs(res.total - blocks["mixed"])) <= 1e-6
        assert np.max(np.abs((res.alpha + res.beta) - blocks["total"])) <= 1e-6

    # ORCA property: all-electron Mayer value.
    text = (_UHF_DIR / "sp.property.txt").read_text()
    m = re.search(r"&BondOrders.*?\n(.*?)(?:\$|&ATNO|&VA)", text, re.S)
    vals = []
    for line in m.group(1).strip().splitlines():
        p = line.split()
        if len(p) >= 2:
            try:
                vals.append(float(p[1]))
            except ValueError:
                pass
    assert vals
    assert abs((res.alpha + res.beta)[0, 1] - vals[0]) < 1e-4


def test_uhf_flag_is_reset_after_release():
    model = _model()
    with qe.Engine() as eng:
        eng.load_molecule_v1(model, allow_open_shell=True)
        eng.prepare()
        eng.calculate_mayer()
    # A new engine must still require the explicit flag.
    with pytest.raises(qe.QeUnsupported):
        with qe.Engine() as eng:
            eng.load_molecule_v1(model)


def test_uhf_adapter_rejects_rhf_input():
    with pytest.raises(OrcaAdapterError, match="UHF"):
        from_orca_uhf_directory(_ORCA / "h2")
