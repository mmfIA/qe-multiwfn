"""Cartesian d/f data-path verification.

ORCA 6.1.1 does not emit Cartesian d/f. The fixture is a real PySCF
RHF/6-31G* wavefunction with mol.cart=True, converted to the canonical
ORCA-like JSON schema. Scientific comparison uses a fresh Multiwfn run on
the PySCF Cartesian Molden.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import OrcaAdapterError, from_orca_directory

_HERE = Path(__file__).resolve()
_VALIDATION = _HERE.parents[3] / "QE-Multiwfn-validation"
_FIXTURE = _VALIDATION / "fixtures" / "cartesian" / "h2o_631gstar_cart"
_RESULTS = _VALIDATION / "cartesian_results" / "h2o_631gstar_cart"

if not _FIXTURE.exists():
    pytest.skip(f"Cartesian fixture not available: {_FIXTURE}", allow_module_level=True)


def test_cartesian_model_and_mapping():
    model = from_orca_directory(_FIXTURE)
    assert model.nbasis == 19
    assert model.nprims == 36
    assert model.basis.representation == "cartesian"
    d_codes = [a.multiwfn_type for a in model.basis.aos if a.angular_type == 2]
    assert sorted(d_codes) == [5, 6, 7, 8, 9, 10]
    model.validate(strict=True)
    assert model.is_legacy_representable()
    legacy = model.to_legacy()
    assert legacy.nbasis == 19


def test_cartesian_v1_mayer_matches_multiwfn():
    import sys
    sys.path.insert(0, str(_VALIDATION))
    from validation.multiwfn_parser import read_multiwfn_bndmat

    model = from_orca_directory(_FIXTURE)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        B = eng.calculate_mayer().total
    if (_RESULTS / "qe_mayer.npy").exists():
        assert np.array_equal(B, np.load(_RESULTS / "qe_mayer.npy"))
    bnd = _RESULTS / "multiwfn_bndmat.txt"
    if bnd.exists():
        Bmw = read_multiwfn_bndmat(bnd, expected_n=model.ncenter)
        assert np.max(np.abs(B - Bmw)) <= 1e-6


def test_cartesian_unknown_component_rejected(tmp_path):
    import json
    data = json.loads((_FIXTURE / "sp.json").read_text())
    # Corrupt one d label with an unknown component suffix.
    for i, lab in enumerate(data["Molecule"]["MolecularOrbitals"]["OrbitalLabels"]):
        if "d" in lab:
            data["Molecule"]["MolecularOrbitals"]["OrbitalLabels"][i] = lab[:-2] + "q1"
            break
    (tmp_path / "sp.json").write_text(json.dumps(data))
    with pytest.raises(OrcaAdapterError):
        from_orca_directory(tmp_path)
