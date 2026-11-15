# PySCF compatibility — Phase 10

**Tested version:** PySCF 2.15.0
**Python:** 3.12
**Status:** tested matrix PASS; other versions are not claimed.

## 1. Version matrix

| PySCF version | Status | Notes |
|---|---|---|
| 2.15.0 | **tested PASS** | RHF/UHF/ROHF, s/p/d/f spherical, Cartesian d direct, full spherical f |
| other 2.x | **NOT TESTED** | no compatibility claim; APIs may differ |
| 1.x | **NOT SUPPORTED** | not tested; no compatibility layer |

The adapter stores `pyscf.__version__` in provenance but does not infer
compatibility from a successful import.

## 2. API requirements

The adapter requires:

- `mol.nao_nr()`, `mol.natm`, `mol.atom_symbol()`, `mol.atom_charges()`,
  `mol.atom_coords(unit="Bohr")`;
- `mol._basis` with raw shell/contraction rows;
- `mol.cart`, `mol.charge`, `mol.spin`, `mol.nelectron`;
- `scf.hf.RHF`, `scf.uhf.UHF`, `scf.rohf.ROHF`;
- `mf.converged`, `mf.mo_coeff`, `mf.mo_occ`, `mf.mo_energy`;
- `mol.intor("int1e_ovlp")` when overlap is requested.

Missing attributes produce `PyscfAdapterError`; no silent fallback is used.

## 3. Methods

| Method | Status |
|---|---|
| RHF | PASS |
| UHF | PASS (array or tuple alpha/beta layout) |
| ROHF | PASS (one spatial set, occupations 2/1/0) |
| DFT (`RKS/UKS/ROKS`) | BLOCKED explicitly |
| post-HF | BLOCKED |
| non-converged SCF | BLOCKED |
| ECP basis | BLOCKED |

## 4. Basis and angular behavior

- s/p: raw PySCF contraction coefficients are converted to unit primitive
  contraction normalization before the full-state build.
- spherical d: converted to MDM canonical component order.
- spherical f: converted to MDM canonical f order; MDM 1.2 canonical metadata.
- Cartesian d: accepted on the direct S/P path. The full path is blocked
  because per-component normalization is not inferred without S.
- Cartesian f and g/h: blocked.
- p order is mapped from PySCF `px,py,pz` to MDM `pz,px,py`.
- S and C receive the same AO permutation.

See `PHASE10_NORMALIZATION_AUDIT.md` for the coefficient-normalization cause
and measurements.

## 5. Tested cases

| Case | Method | Basis | Path |
|---|---|---|---|
| H₂ | RHF | STO-3G | direct/full |
| H₂O | RHF | STO-3G | direct/full |
| O₂ | UHF/ROHF | STO-3G | direct/full |
| H₂O | RHF | 6-31G* spherical d | direct/full |
| H₂O | RHF | 6-31G* Cartesian d | direct |
| H₂S | RHF | def2-TZVP spherical f | direct/full |

## 6. Compatibility policy

- Only the matrix above is declared tested.
- Any future version needs its own test run; import success alone is not
  evidence.
- The adapter uses explicit class checks and fails closed on unknown SCF
  classes.
- No version-specific fallback is implemented until a real API difference is
  demonstrated.
