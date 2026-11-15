# Compatibility matrix — Phase 12

| Component | Version | Platform | Status | Evidence |
|---|---|---|---|---|
| Python | 3.12.16 | Linux x86_64 | **tested/supported** | wheel/sdist install, suite |
| Python | other 3.x | — | not tested | no wheel |
| NumPy | 2.5.4 | Linux x86_64 | **tested/supported** | reference install/suite |
| NumPy | 2.4.6 | Linux x86_64 | **tested** | matrix venv + adapter tests |
| NumPy | other | — | not tested | no claim |
| PySCF | 2.15.0 | Linux x86_64 | **tested/supported reference** | full PySCF adapter suite |
| PySCF | 2.14.0 | Linux x86_64 | **tested** | 18 PySCF/ASE tests in matrix venv |
| PySCF | other | — | not tested | no claim |
| ASE | 3.29.0 | Linux x86_64 | **tested/supported reference** | structural tests |
| ASE | 3.28.0 | Linux x86_64 | **tested** | structural tests in matrix venv |
| ASE | other | — | not tested | no claim |
| cclib | 1.8.1 | Linux x86_64 | **partial** | synthetic conversion; ORCA parser blocked |
| Native ABI | 0.2.0 | Linux x86_64 | **preserved** | 44 symbols |
| OpenBLAS | system `libopenblas.so.0` | Linux x86_64 | required | `ldd -r` |
| gfortran runtime | system `libgfortran.so.5` | Linux x86_64 | required | `ldd -r` |
| DatabaseProvider | in-memory protocol | — | **tested** | conformance tests |

The optional extras in the wheel declare `pyscf>=2.14,<2.16` and
`ase>=3.28,<3.30`; only the versions above were tested. cclib remains pinned
to 1.8.1.

PyPI availability is not a compatibility claim.
