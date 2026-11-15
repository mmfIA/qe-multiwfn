# Dependencies — QE-Multiwfn 0.3.0

## Required Python

- Python 3.12 (tested);
- NumPy >=2.0 (2.4.6 and 2.5.4 tested).

## Optional Python extras

| Extra | Pins | Purpose |
|---|---|---|
| `pyscf` | `>=2.14,<2.16` | in-memory electronic data |
| `ase` | `>=3.28,<3.30` | structural geometry |
| `cclib` | `1.8.1` | cclib conversion; ORCA text parser remains blocked |
| `full` | all above | full optional profile |

None is required for `import qe_multiwfn`, NumPy MDM construction, Engine or
Mayer.

## Native runtime

`libqe_multiwfn.so` is bundled. External runtime dependencies:

- OpenBLAS;
- libgfortran;
- libgcc_s;
- libm/libmvec;
- libc/loader.

The wheel does not bundle these system libraries. `ldd -r` and `ldd` are
recorded in the Phase 12 evidence. A machine without compatible OpenBLAS and
gfortran runtime is not supported.
