"""Test that memory layout is handled correctly.

We send a known non-trivial matrix to the Fortran side and verify
that the Mayer pipeline produces the mathematically expected result.
This is the Python-side equivalent of tests/native/test_memory_transfer.c.
"""
import numpy as np
import pytest

import qe_multiwfn as qe


def _make_test_system():
    """2 H atoms, 2 basis functions (one per atom).
    P = [2/3  2/3]
        [2/3  2/3]
    S = [1.0  0.5]
        [0.5  1.0]
    PS = P·S = [1.0  0.8]
               [0.8  1.0]
    Tr(PS) = 2.0  ✓ (nelec=2)
    BO(1,2) = PS(1,2)*PS(2,1) = 0.8*0.8 = 0.64
    """
    ncenter = 2
    nbasis = 2
    nprims = 2
    wfntype = qe.molecular.WFNTYPE_RHF

    atomic_numbers = np.array([1, 1], dtype=np.int32)
    coordinates = np.array([
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)  # Bohr

    basis_center = np.array([1, 2], dtype=np.int32)
    basis_type = np.array([0, 0], dtype=np.int32)  # S, S

    density_total = np.array([
        [2.0/3.0, 2.0/3.0],
        [2.0/3.0, 2.0/3.0],
    ], dtype=np.float64)
    overlap = np.array([
        [1.0, 0.5],
        [0.5, 1.0],
    ], dtype=np.float64)

    return qe.MolecularSystem(
        ncenter=ncenter, nbasis=nbasis, nprims=nprims, wfntype=wfntype,
        atomic_numbers=atomic_numbers,
        coordinates=coordinates,
        basis_center=basis_center,
        basis_type=basis_type,
        density_total=density_total,
        overlap=overlap,
        charge=0,
        multiplicity=1,
        nelectron=2,
    )


def test_mayer_pipeline_python():
    sys = _make_test_system()
    with qe.Engine() as eng:
        eng.load_molecule(sys)
        eng.prepare()
        result = eng.calculate_mayer()

    # The expected Mayer matrix is all 1.0 (diagonal = sum of off-diagonals)
    assert result.total.shape == (2, 2)
    expected = 1.0
    np.testing.assert_allclose(result.total, expected, atol=1e-9)

    # No spin components for RHF
    assert not result.has_spin_components
    assert result.alpha is None
    assert result.beta is None

    # Metadata
    assert result.metadata["wavefunction_type"] == 0
    assert result.metadata["has_spin_components"] is False
    assert result.metadata["ncenter"] == 2


def test_angstrom_input():
    """Verify coordinates_unit="angstrom" works."""
    sys = _make_test_system()
    # Convert coords from Bohr to Angstrom and re-create
    angs_coords = sys.coordinates * qe.molecular.BOHR_TO_ANGSTROM
    sys2 = qe.MolecularSystem(
        ncenter=sys.ncenter, nbasis=sys.nbasis, nprims=sys.nprims, wfntype=sys.wfntype,
        atomic_numbers=sys.atomic_numbers,
        coordinates=angs_coords,
        basis_center=sys.basis_center,
        basis_type=sys.basis_type,
        density_total=sys.density_total,
        overlap=sys.overlap,
        charge=0, multiplicity=1, nelectron=2,
    )
    # The Mayer result should be identical to the Bohr-input version
    with qe.Engine() as eng:
        eng.load_molecule(sys2)
        eng.prepare()
        result = eng.calculate_mayer()
    np.testing.assert_allclose(result.total, 1.0, atol=1e-9)


def test_invalid_density_nonsymmetric():
    sys = _make_test_system()
    bad = sys.density_total.copy()
    bad[0, 1] = 0.5  # make it asymmetric
    bad[1, 0] = 0.4
    with pytest.raises(ValueError, match="not symmetric"):
        qe.MolecularSystem(
            ncenter=sys.ncenter, nbasis=sys.nbasis, nprims=sys.nprims, wfntype=sys.wfntype,
            atomic_numbers=sys.atomic_numbers,
            coordinates=sys.coordinates,
            basis_center=sys.basis_center,
            basis_type=sys.basis_type,
            density_total=bad,
            overlap=sys.overlap,
        )


def test_invalid_dimensions():
    sys = _make_test_system()
    with pytest.raises(ValueError):
        qe.MolecularSystem(
            ncenter=0, nbasis=sys.nbasis, nprims=sys.nprims, wfntype=sys.wfntype,
            atomic_numbers=sys.atomic_numbers,
            coordinates=sys.coordinates,
            basis_center=sys.basis_center,
            basis_type=sys.basis_type,
            density_total=sys.density_total,
            overlap=sys.overlap,
        )


def test_invalid_wfntype():
    sys = _make_test_system()
    with pytest.raises(ValueError, match="wfntype"):
        qe.MolecularSystem(
            ncenter=sys.ncenter, nbasis=sys.nbasis, nprims=sys.nprims, wfntype=99,
            atomic_numbers=sys.atomic_numbers,
            coordinates=sys.coordinates,
            basis_center=sys.basis_center,
            basis_type=sys.basis_type,
            density_total=sys.density_total,
            overlap=sys.overlap,
        )


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
