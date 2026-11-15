"""Example 3: full Mayer RHF pipeline.

A 3-atom system where we compute the Mayer bond order and verify it
matches an independent NumPy reference implementation.
"""
import numpy as np
import qe_multiwfn as qe


def reference_mayer(P, S, basstart, basend, ncenter):
    """Independent NumPy Mayer implementation (see test_mayer_reference.py)."""
    PS = P @ S
    BO = np.zeros((ncenter, ncenter), dtype=np.float64)
    for i in range(ncenter):
        if basstart[i] == 0:
            continue
        i_lo, i_hi = basstart[i] - 1, basend[i] - 1
        for j in range(i + 1, ncenter):
            if basstart[j] == 0:
                continue
            j_lo, j_hi = basstart[j] - 1, basend[j] - 1
            block = PS[i_lo:i_hi+1, j_lo:j_hi+1]
            rev   = PS[j_lo:j_hi+1, i_lo:i_hi+1]
            val = float(np.sum(block * rev.T))
            BO[i, j] = val
            BO[j, i] = val
    for i in range(ncenter):
        BO[i, i] = float(np.sum(BO[:, i]))
    return BO


def main():
    # Three centers, three basis functions, and four electrons (closed-shell RHF).
    # Build two occupied orbitals orthonormal in the supplied overlap metric.
    S = np.array([
        [1.0, 0.4, 0.3],
        [0.4, 1.0, 0.5],
        [0.3, 0.5, 1.0],
    ], dtype=np.float64)
    L = np.linalg.cholesky(S)
    C = np.linalg.solve(L.T, np.eye(3)[:, :2])
    P = 2.0 * C @ C.T

    system = qe.MolecularSystem(
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

    print(f"System: {system}")
    print(f"Tr(P*S) = {np.trace(P @ S):.6f}")
    print()

    with qe.Engine() as eng:
        eng.load_molecule(system)
        eng.prepare()
        result = eng.calculate_mayer()

    print("Mayer total bond-order matrix (Fortran backend):")
    print(result.total)
    print()

    # Independent reference
    basstart = np.array([1, 2, 3])
    basend   = np.array([1, 2, 3])
    ref = reference_mayer(P, S, basstart, basend, 3)
    print("Independent NumPy reference:")
    print(ref)
    print()

    diff = np.abs(result.total - ref).max()
    print(f"Max abs diff: {diff:.2e}")
    print()
    print(f"Has spin components: {result.has_spin_components}")
    print(f"Wavefunction type: {result.metadata['wavefunction_type']}")


if __name__ == "__main__":
    main()
