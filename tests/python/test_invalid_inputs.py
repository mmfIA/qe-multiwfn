"""Test invalid-input handling: bad dimensions, NULL pointers, etc."""
import numpy as np
import pytest

import qe_multiwfn as qe


def test_negative_ncenter():
    with pytest.raises(ValueError):
        qe.MolecularSystem(
            ncenter=0, nbasis=1, nprims=1, wfntype=0,
            atomic_numbers=np.array([], dtype=np.int32),
            coordinates=np.zeros((0, 3)),
            basis_center=np.array([], dtype=np.int32),
            basis_type=np.array([], dtype=np.int32),
            density_total=np.zeros((1, 1)),
            overlap=np.zeros((1, 1)),
        )


def test_nprims_less_than_nbasis():
    with pytest.raises(ValueError, match="nprims"):
        qe.MolecularSystem(
            ncenter=2, nbasis=3, nprims=2, wfntype=0,
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 2], dtype=np.int32),
            basis_type=np.array([0, 0], dtype=np.int32),
            density_total=np.zeros((3, 3)),
            overlap=np.zeros((3, 3)),
        )


def test_nan_in_density():
    with pytest.raises(ValueError, match="NaN/Inf"):
        qe.MolecularSystem(
            ncenter=2, nbasis=2, nprims=2, wfntype=0,
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 2], dtype=np.int32),
            basis_type=np.array([0, 0], dtype=np.int32),
            density_total=np.array([
                [np.nan, 0.4],
                [0.4, 0.8],
            ], dtype=np.float64),
            overlap=np.eye(2),
        )


def test_basis_center_out_of_range():
    with pytest.raises(ValueError, match="basis_center"):
        qe.MolecularSystem(
            ncenter=2, nbasis=2, nprims=2, wfntype=0,
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 5], dtype=np.int32),  # 5 > ncenter
            basis_type=np.array([0, 0], dtype=np.int32),
            density_total=np.diag([2.0, 0.0]),
            overlap=np.eye(2),
        )


def test_wrong_density_shape():
    with pytest.raises(ValueError, match="density_total"):
        qe.MolecularSystem(
            ncenter=2, nbasis=3, nprims=3, wfntype=0,
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 2, 1], dtype=np.int32),
            basis_type=np.array([0, 0, 0], dtype=np.int32),
            density_total=np.zeros((2, 2)),  # wrong shape
            overlap=np.zeros((3, 3)),
        )


def test_wrong_coordinates_unit():
    with pytest.raises(ValueError, match="coordinates_unit"):
        qe.MolecularSystem.from_arrays(
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 2], dtype=np.int32),
            basis_type=np.array([0, 0], dtype=np.int32),
            density_total=np.full((2, 2), 2.0/3.0),
            overlap=np.array([[1.0, 0.5], [0.5, 1.0]]),
            coordinates_unit="meters",  # invalid
        )


def test_engine_release_when_no_system_loaded():
    """Calling release_molecule when no system is loaded should not raise."""
    with qe.Engine() as eng:
        # Should be safe no-op
        eng.release_molecule()


def test_invalid_state_calculate_mayer():
    """Calling calculate_mayer without a loaded system should raise."""
    with qe.Engine() as eng:
        with pytest.raises(qe.QeError):
            eng.calculate_mayer()


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))


def test_contracted_basis_dimensions_are_independent():
    """Basis ownership is per basis function; primitive count may be larger."""
    system = qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=6, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([[0., 0., 0.], [0., 0., 1.4]]),
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.full((2, 2), 2.0/3.0),
        overlap=np.array([[1., .5], [.5, 1.]]),
        charge=0, multiplicity=1, nelectron=2,
    )
    with qe.Engine() as eng:
        eng.load_molecule(system)
        eng.prepare()
        result = eng.calculate_mayer()
    np.testing.assert_allclose(result.total, 1.0, atol=1e-9)


def test_noncontiguous_basis_centers_are_rejected_at_prepare():
    system = qe.MolecularSystem(
        ncenter=2, nbasis=3, nprims=3, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([2, 2], dtype=np.int32),
        coordinates=np.zeros((2, 3)),
        basis_center=np.array([1, 2, 1], dtype=np.int32),
        basis_type=np.array([0, 0, 0], dtype=np.int32),
        density_total=np.diag([2.0, 2.0, 0.0]),
        overlap=np.eye(3), charge=0, multiplicity=1, nelectron=4,
    )
    with qe.Engine() as eng:
        eng.load_molecule(system)
        with pytest.raises(qe.QeError, match="contiguous block"):
            eng.prepare()


def test_non_idempotent_rhf_density_is_rejected():
    with pytest.raises(ValueError, match="not idempotent"):
        qe.MolecularSystem(
            ncenter=2, nbasis=2, nprims=2, wfntype=0,
            atomic_numbers=np.array([1, 1], dtype=np.int32),
            coordinates=np.zeros((2, 3)),
            basis_center=np.array([1, 2], dtype=np.int32),
            basis_type=np.array([0, 0], dtype=np.int32),
            density_total=np.eye(2), overlap=np.eye(2),
            charge=0, multiplicity=1, nelectron=2,
        )
