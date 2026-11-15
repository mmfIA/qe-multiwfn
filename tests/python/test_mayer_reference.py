"""Validate Mayer result against an independent NumPy reference implementation."""
import numpy as np
import pytest

import qe_multiwfn as qe


def reference_mayer(P, S, basstart, basend, ncenter):
    """Independent NumPy implementation of Mayer bond order.

    Mirrors the formula in calcMayerbndord (bondorder.f90):
        PS = P · S
        for atoms A != B (with A having basis indices [basstart[A], basend[A]]):
            BO(A,B) = sum_{i in A} sum_{j in B} PS[i,j] * PS[j,i]
        BO is symmetric.
        BO(A,A) = sum_{B != A} BO(A,B)  (diagonal = sum of off-diagonal)
    """
    nbasis = P.shape[0]
    PS = P @ S

    BO = np.zeros((ncenter, ncenter), dtype=np.float64)
    # Multiwfn uses 1-based indexing for basstart/basend. Here we receive
    # them as Python ints with the same convention.
    for i in range(ncenter):
        if basstart[i] == 0:
            continue
        i_lo = basstart[i] - 1
        i_hi = basend[i] - 1   # inclusive
        for j in range(i + 1, ncenter):
            if basstart[j] == 0:
                continue
            j_lo = basstart[j] - 1
            j_hi = basend[j] - 1
            block = PS[i_lo:i_hi+1, j_lo:j_hi+1]
            rev   = PS[j_lo:j_hi+1, i_lo:i_hi+1]
            val = float(np.sum(block * rev.T))
            BO[i, j] = val
            BO[j, i] = val

    # Diagonal: sum of off-diagonal of each column
    for i in range(ncenter):
        BO[i, i] = float(np.sum(BO[:, i]))

    return BO


def _make_test_system_H2():
    """Two H atoms, each with one basis function (the canonical H2 test)."""
    return qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=2, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.4],
        ], dtype=np.float64),
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.array([
            [2.0/3.0, 2.0/3.0],
            [2.0/3.0, 2.0/3.0],
        ], dtype=np.float64),
        overlap=np.array([
            [1.0, 0.5],
            [0.5, 1.0],
        ], dtype=np.float64),
        charge=0, multiplicity=1, nelectron=2,
    )


def _make_test_system_3atom():
    """Three-center, four-electron RHF fixture with two occupied MOs."""
    S = np.array([
        [1.0, 0.4, 0.3],
        [0.4, 1.0, 0.5],
        [0.3, 0.5, 1.0],
    ], dtype=np.float64)
    # Construct two S-orthonormal occupied orbitals, then P=2*C*C.T.
    L = np.linalg.cholesky(S)
    C = np.linalg.solve(L.T, np.eye(3)[:, :2])
    P = 2.0 * C @ C.T
    return qe.MolecularSystem(
        ncenter=3, nbasis=3, nprims=3, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1, 2], dtype=np.int32),
        coordinates=np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 2.0],
        ], dtype=np.float64),
        basis_center=np.array([1, 2, 3], dtype=np.int32),
        basis_type=np.array([0, 0, 0], dtype=np.int32),
        density_total=P,
        overlap=S,
        charge=0, multiplicity=1, nelectron=4,
    )


def test_mayer_matches_reference_2atom():
    sys = _make_test_system_H2()
    with qe.Engine() as eng:
        eng.load_molecule(sys)
        eng.prepare()
        result = eng.calculate_mayer()

    # Manual basstart/basend (1-based, Multiwfn convention)
    basstart = np.array([1, 2], dtype=np.int32)
    basend   = np.array([1, 2], dtype=np.int32)
    ref = reference_mayer(sys.density_total, sys.overlap, basstart, basend, sys.ncenter)
    np.testing.assert_allclose(result.total, ref, atol=1e-10)
    # Symmetry
    np.testing.assert_allclose(result.total, result.total.T, atol=1e-12)


def test_mayer_matches_reference_3atom():
    sys = _make_test_system_3atom()
    with qe.Engine() as eng:
        eng.load_molecule(sys)
        eng.prepare()
        result = eng.calculate_mayer()

    basstart = np.array([1, 2, 3], dtype=np.int32)
    basend   = np.array([1, 2, 3], dtype=np.int32)
    ref = reference_mayer(sys.density_total, sys.overlap, basstart, basend, sys.ncenter)
    np.testing.assert_allclose(result.total, ref, atol=1e-10)
    # Symmetry
    np.testing.assert_allclose(result.total, result.total.T, atol=1e-12)


def test_mayer_two_systems_sequential():
    """Verify that loading a second system does NOT leave residual state
    from the first."""
    sys1 = _make_test_system_H2()
    sys2 = _make_test_system_3atom()

    with qe.Engine() as eng:
        # First system
        eng.load_molecule(sys1)
        eng.prepare()
        result1 = eng.calculate_mayer()
        ref1 = reference_mayer(
            sys1.density_total, sys1.overlap,
            np.array([1, 2]), np.array([1, 2]), sys1.ncenter,
        )
        np.testing.assert_allclose(result1.total, ref1, atol=1e-10)

        # Release and load second system
        eng.release_molecule()
        eng.load_molecule(sys2)
        eng.prepare()
        result2 = eng.calculate_mayer()
        ref2 = reference_mayer(
            sys2.density_total, sys2.overlap,
            np.array([1, 2, 3]), np.array([1, 2, 3]), sys2.ncenter,
        )
        np.testing.assert_allclose(result2.total, ref2, atol=1e-10)

        # Run sys1 again to verify clean state
        eng.release_molecule()
        eng.load_molecule(sys1)
        eng.prepare()
        result1b = eng.calculate_mayer()
        np.testing.assert_allclose(result1b.total, result1.total, atol=1e-12)


def test_mayer_3_then_2_atoms():
    """Loading a smaller system after a larger one — verify no leftover
    data leaks into the smaller system's result."""
    sys_big = _make_test_system_3atom()
    sys_small = _make_test_system_H2()

    with qe.Engine() as eng:
        eng.load_molecule(sys_big)
        eng.prepare()
        big = eng.calculate_mayer()
        assert big.total.shape == (3, 3)

        eng.release_molecule()
        eng.load_molecule(sys_small)
        eng.prepare()
        small = eng.calculate_mayer()
        assert small.total.shape == (2, 2)

        # The 2x2 small result must NOT contain the 3x3 big result's data
        # and must match the independent reference.
        ref_small = reference_mayer(
            sys_small.density_total, sys_small.overlap,
            np.array([1, 2]), np.array([1, 2]), sys_small.ncenter,
        )
        np.testing.assert_allclose(small.total, ref_small, atol=1e-10)


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
