# Source equivalence — Phase 9C

**Scope:** cross-source MDM/Engine comparisons on the validated RHF/UHF/ROHF
scope. All adapters converge on the same `MolecularDataBuilder` and
`Engine`.

## 1. Tested sources

| Source | Path | Output |
|---|---|---|
| ORCA 6.1.1 fixtures | `QE-Multiwfn-validation/orca` | MDM via `adapters.orca` |
| PySCF 2.15.0 | in-memory `Molecule`/SCF | MDM via `adapters.pyscf` |
| ASE 3.29.0 | in-memory `Atoms` | structural MDM only |
| Synthetic database records | in-memory `DatabaseRecord` | MDM via `adapters.database` |
| cclib 1.8.1 | existing adapter | synthetic/partial; ORCA text parser blocked |

## 2. PySCF vs ORCA

The same geometry/basis/state was computed in PySCF and compared with the
existing ORCA fixture after AO/angular normalization.

| Case | Method | Basis | Max |S_PySCF − S_ORCA| | Mayer max Δ |
|---|---|---|---:|---:|
| H₂ | RHF | STO-3G | `2.31e-9` | `1.33e-15` |
| H₂O | RHF | STO-3G | `3.14e-9` | `3.22e-8` |
| O₂ | UHF | STO-3G | `3.33e-9` | `2.53e-12` (α `3.3e-16`, β `2.0e-15`) |
| O₂ | ROHF | STO-3G | `3.33e-9` | `2.22e-15` (α `5.0e-16`, β `2.44e-15`) |
| H₂O | RHF | 6-31G* spherical d | — | `3.78e-6` |
| H₂O | RHF | 6-31G* Cartesian d | — | `5.71e-13` |
| H₂S | RHF | def2-TZVP spherical f | `3.64e-9` | direct `5.97e-7`; full `1.02e-6` |

PySCF AO order is explicitly mapped to the MDM order (p `pz,px,py`; spherical
d/f canonical; Cartesian d retains the PySCF order). S and C receive the
same permutation. The f block agrees with the ORCA canonical S to `4e-16`
after mapping, so no extra f phase is applied.

Tolerance policy:

- S comparison: `1e-7` (`2e-7` only for Cartesian d when the reference is a
  different SCF/integral path).
- Mayer comparison: `1e-6` for matched RHF/UHF/ROHF; `1e-5` for spherical f
  and the `6-31G*` d SCF/basis difference.
- Database synthetic records: exact equality for identical arrays.
- No tolerance is used to hide a source-specific convention.

## 3. P0 generated-state audit

The full path builds S with the native `genSbas_curr` and P with `genP`.
Observed generated `CᵀSC` errors and traces:

| Source/case | Generated CᵀSC max | Generated Tr(PS) error |
|---|---:|---:|
| ORCA H₂O/STO-3G | `7.78e-9` | `3.43e-9` |
| ORCA H₂O/6-31G* d | `1.08e-8` | `4.01e-9` |
| ORCA H₂O/6-31G* Cartesian d | `2.11e-7` | `4.24e-7` |
| ORCA H₂S/def2-TZVP f | `2.06e-8` | `6.30e-9` |
| ORCA O₂/STO-3G UHF | α `1.02e-8`, β `1.09e-8` | `2.80e-9` |
| ORCA O₂/STO-3G ROHF | `1.05e-8` | `2.78e-9` |
| PySCF H₂O/STO-3G | `2.00e-8` | `1.55e-7` |
| PySCF H₂O/6-31G* d | `2.11e-7` | `4.25e-7` |
| PySCF O₂/STO-3G UHF | α `2.62e-8`, β `2.58e-8` | `3.28e-7` |
| PySCF O₂/STO-3G ROHF | `2.60e-8` | `3.28e-7` |

The generated-state validation uses `1e-6` for electron count and
orthonormality. Source-supplied matrices retain the strict
`TOL_ELECTRON_COUNT=1e-8` and `TOL_ORTHONORM=1e-10` profile. The distinction is
documented in `MDM_VALIDATION.md`; it is not a relaxation of source
validation.

## 4. ASE

ASE contributes only geometry. Existing tests compare ASE geometry with the
ORCA optimized fixtures within `1e-6` Bohr and verify that the model is not
Mayer-ready without basis/orbitals. PBC is fail-closed.

## 5. Database protocol

Two synthetic records with different IDs/source labels and identical
scientific arrays produce identical MDMs and identical Engine Mayer results.
No real database or network is used.

## 6. cclib

The existing cclib adapter remains fail-closed for the real ORCA 6.1.1 text
parser (`orcaparser.py:2799`, cclib 1.8.1). Synthetic cclib-like data with an
explicit canonical basis passes RHF/UHF/ROHF and is preserved. No missing
data is invented.

## 7. Evidence

- `tests/python/test_pyscf_adapter.py`
- `tests/python/test_ase_adapter_phase9c.py`
- `tests/python/test_database_adapter.py`
- `tests/python/test_ase_adapter.py`
- `tests/python/test_cclib_adapter.py`
- `MDM_1.1_work/PHASE9C/phase9c_p0_metrics.txt`
- Existing 233-test regression suite.
