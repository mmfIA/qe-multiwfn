# Source equivalence — Phase 11

Phase 11 preserves the Phase 10 scientific comparisons:

| System | Method | Sources | Mayer max Δ |
|---|---|---|---:|
| H₂/STO-3G | RHF | ORCA/PySCF | `1.33e-15` |
| H₂O/STO-3G | RHF | ORCA/PySCF | `3.22e-8` |
| O₂/STO-3G | UHF | ORCA/PySCF | `2.53e-12` |
| O₂/STO-3G | ROHF | ORCA/PySCF | `2.22e-15` |
| H₂O/6-31G* | RHF spherical d | ORCA/PySCF | `3.78e-6` |
| H₂O/6-31G* | RHF Cartesian d | fixture/PySCF | `9.43e-7` |
| H₂S/def2-TZVP | RHF spherical f | ORCA/PySCF direct | `5.97e-7` |
| H₂S/def2-TZVP | RHF spherical f | ORCA/PySCF full | `1.02e-6` |
| synthetic H₂ | RHF | database A/B | exact |

The H₂S difference was investigated: S differs by `3.64e-9` with diagonal
agreement within `4.4e-16`; P differs by `2.86e-6`; C differs by SCF orbital
signs/rotations; the Mayer difference is distributed across the matrix and is
not concentrated in an f component. It is a cross-backend SCF numerical
difference, not a normalization or angular failure.

No reference geometry, basis, matrix, tolerance or result was changed.
