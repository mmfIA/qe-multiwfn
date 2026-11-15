"""Example 2: RAM-to-RAM matrix transfer.

Demonstrates that:
  - a NumPy matrix is passed via ctypes to Fortran-owned memory,
  - the data is preserved (verified by computing Mayer BO),
  - the result is returned to NumPy in the right layout.
"""
import numpy as np
import qe_multiwfn as qe


def main():
    # A 2-atom, 2-basis RHF system. See test_mayer_reference.py for
    # the derivation of the expected result.
    system = qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=2, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.4],
        ], dtype=np.float64),  # Bohr
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.full((2, 2), 2.0/3.0, dtype=np.float64),
        overlap=np.array([
            [1.0, 0.5],
            [0.5, 1.0],
        ], dtype=np.float64),
        charge=0, multiplicity=1, nelectron=2,
    )

    with qe.Engine() as eng:
        eng.load_molecule(system)
        eng.prepare()
        result = eng.calculate_mayer()

    print("Loaded system:")
    print(f"  {system}")
    print()
    print("Mayer total bond-order matrix:")
    print(result.total)
    print()
    print(f"Expected: all entries = 1.00")
    print(f"Result:   all entries = {result.total[0,0]:.6f}")
    print()
    print(f"Result object: {result}")


if __name__ == "__main__":
    main()
