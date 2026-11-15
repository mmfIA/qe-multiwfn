"""Geometry-unit contract tests.

These tests are independent of the external P0 fixtures: they use a minimal
synthetic ORCA JSON and synthetic adapter data, so unit handling is exercised
in the regular CI suite.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.adapters.cclib import from_cclib_data
from qe_multiwfn.adapters.database import DatabaseRecord, from_database_record
from qe_multiwfn.adapters.orca import OrcaAdapterError, from_orca_directory
from qe_multiwfn.builder import build_molecular_system
from qe_multiwfn.molecular import ANGSTROM_TO_BOHR


def _synthetic_sp(tmp_path, units, coords):
    data = {
        "Molecule": {
            "Atoms": [
                {
                    "Basis": [{"Shell": "s", "Exponents": [1.0],
                               "Coefficients": [1.0]}],
                    "Coords": list(coords[0]),
                    "ElementLabel": "H",
                    "ElementNumber": 1,
                    "Idx": 0,
                    "NuclearCharge": 1,
                },
                {
                    "Basis": [{"Shell": "s", "Exponents": [1.0],
                               "Coefficients": [1.0]}],
                    "Coords": list(coords[1]),
                    "ElementLabel": "H",
                    "ElementNumber": 1,
                    "Idx": 1,
                    "NuclearCharge": 1,
                },
            ],
            "MolecularOrbitals": {
                "OrbitalLabels": ["0H   1s", "1H   1s"],
                "MOs": [
                    {"MOCoefficients": [1.0, 0.0], "Occupancy": 2.0,
                     "OrbitalEnergy": -0.5, "OrbitalSymLabel": "1",
                     "OrbitalSymmetry": "A1"},
                    {"MOCoefficients": [0.0, 1.0], "Occupancy": 0.0,
                     "OrbitalEnergy": 0.2, "OrbitalSymLabel": "2",
                     "OrbitalSymmetry": "A1"},
                ],
            },
            "Multiplicity": 1,
            "Charge": 0,
            "HFTyp": "RHF",
            "S-Matrix": [[1.0, 0.0], [0.0, 1.0]],
            "BaseName": "H2",
            "PointGroup": "Dinfh",
            "Origin": "synthetic",
        }
    }
    if units is not None:
        data["Molecule"]["CoordinateUnits"] = units
    path = tmp_path / "sp.json"
    path.write_text(json.dumps(data))
    return path


def test_orca_explicit_angstrom_converts_once(tmp_path):
    _synthetic_sp(tmp_path, "Angs", [[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]])
    model = from_orca_directory(tmp_path)
    expected = 0.74 * ANGSTROM_TO_BOHR
    assert model.geometry.unit_source == "angstrom"
    assert model.provenance.coordinate_unit_source == "angstrom"
    assert model.provenance.conversion_factor == ANGSTROM_TO_BOHR
    assert abs(model.geometry.coordinates[1, 2] - expected) < 1e-12


def test_orca_explicit_bohr_no_double_conversion(tmp_path):
    _synthetic_sp(tmp_path, "Bohr",
                  [[0.0, 0.0, 0.0], [0.0, 0.0, 0.74 * ANGSTROM_TO_BOHR]])
    model = from_orca_directory(tmp_path)
    expected = 0.74 * ANGSTROM_TO_BOHR
    assert model.geometry.unit_source == "bohr"
    assert model.provenance.conversion_factor == 1.0
    assert abs(model.geometry.coordinates[1, 2] - expected) < 1e-12


def test_orca_missing_unit_fails_closed(tmp_path):
    _synthetic_sp(tmp_path, None, [[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]])
    with pytest.raises(OrcaAdapterError, match="CoordinateUnits"):
        from_orca_directory(tmp_path)


def test_orca_unknown_unit_fails_closed(tmp_path):
    _synthetic_sp(tmp_path, "furlong", [[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]])
    with pytest.raises(OrcaAdapterError, match="unsupported ORCA coordinate unit"):
        from_orca_directory(tmp_path)


def test_builder_missing_or_unknown_unit_rejected():
    with pytest.raises(ValueError, match="unit"):
        build_molecular_system(atomic_numbers=[1], coordinates=[[0, 0, 0]],
                               coordinate_unit=None)
    with pytest.raises(ValueError, match="unit"):
        build_molecular_system(atomic_numbers=[1], coordinates=[[0, 0, 0]],
                               coordinate_unit="furlong")


def test_database_record_missing_or_unknown_unit_rejected():
    for unit in (None, "furlong"):
        record = DatabaseRecord(
            record_id="r1", source="synthetic", atomic_numbers=[1],
            coordinates=[[0, 0, 0]], coordinate_unit=unit,
        )
        with pytest.raises(ValueError, match="coordinate_unit"):
            from_database_record(record)


def test_legacy_explicit_bohr_and_angstrom_equivalent():
    S = np.array([[1.0, 0.5], [0.5, 1.0]])
    P = np.full((2, 2), 2.0 / 3.0)
    kwargs = dict(atomic_numbers=[1, 1], basis_center=[1, 2],
                  basis_type=[0, 0], density_total=P, overlap=S,
                  charge=0, multiplicity=1, nelectron=2)
    bohr = qe.MolecularSystem.from_arrays(
        coordinates=[[0, 0, 0], [0, 0, 1.4]],
        coordinates_unit="bohr", **kwargs,
    )
    ang = qe.MolecularSystem.from_arrays(
        coordinates=[[0, 0, 0], [0, 0, 1.4 * 0.529177210903]],
        coordinates_unit="angstrom", **kwargs,
    )
    default = qe.MolecularSystem.from_arrays(
        coordinates=[[0, 0, 0], [0, 0, 1.4]], **kwargs,
    )
    np.testing.assert_allclose(ang.coordinates, bohr.coordinates, atol=1e-12)
    np.testing.assert_allclose(default.coordinates, bohr.coordinates, atol=1e-12)


def test_cclib_angstrom_to_bohr():
    data = SimpleNamespace(
        atomnos=np.array([1, 1]),
        atomcoords=np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]]),
        charge=0, mult=1,
        aooverlaps=np.eye(2),
        mocoeffs=[np.eye(2)],
        moocc=[np.array([2.0, 0.0])],
        moenergies=[np.array([-0.5, 0.2])],
        metadata={"hf": "RHF", "package": "synthetic"},
    )
    model = from_cclib_data(data)
    expected = 0.74 * ANGSTROM_TO_BOHR
    assert model.geometry.unit_source == "angstrom"
    assert model.provenance.coordinate_unit_source == "angstrom"
    assert abs(model.geometry.coordinates[1, 2] - expected) < 1e-12


def test_pyscf_explicit_bohr_no_conversion():
    pytest.importorskip("pyscf")
    from pyscf import gto, scf
    from qe_multiwfn.adapters.pyscf import from_pyscf

    mol = gto.M(atom="H 0 0 0; H 0 0 1.4", basis="sto-3g",
                unit="Bohr", verbose=0)
    mf = scf.RHF(mol)
    mf.conv_tol = 1e-10
    mf.kernel()
    assert mf.converged
    model = from_pyscf(mol, mf)
    assert model.geometry.unit_source == "bohr"
    assert abs(model.geometry.coordinates[1, 2] - 1.4) < 1e-12


def test_ase_angstrom_to_bohr():
    ase = pytest.importorskip("ase")
    from ase import Atoms
    from qe_multiwfn.adapters.ase import from_ase_atoms

    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]])
    model = from_ase_atoms(atoms)
    expected = 0.74 * ANGSTROM_TO_BOHR
    assert model.geometry.unit_source == "angstrom"
    assert abs(model.geometry.coordinates[1, 2] - expected) < 1e-12


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
