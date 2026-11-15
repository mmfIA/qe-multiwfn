# Phase 10 — normalization audit

**Status:** COMPLETE; PySCF spherical-f full state released. Cartesian-d full
state remains blocked with a documented reason.

## 1. Initial limitation

Phase 9C observed:

1. PySCF spherical f with `include_overlap=False` failed the native full-state
   trace check (`Tr(PS)=18.23` vs `18` for H₂S/def2-TZVP);
2. PySCF Cartesian-d full state could not infer normalization without S.

The direct path (`include_overlap=True`) was already valid.

## 2. Root cause

PySCF `mol._basis` stores **raw contraction coefficients**. Some contractions
are not normalized against the standard Gaussian primitive convention used by
the native `genSbas`/`genP` path. PySCF applies an internal contraction
normalization when it builds its own integrals; the overlap returned by
`mol.intor('int1e_ovlp')` is unit-normalized, but the raw `_basis` row is not.

Example (H₂S/def2-TZVP, s shell):

```text
PySCF raw coefficients      [0.00054696, 0.00422972, ...]
standard contraction error  1.09038
normalized coefficients     raw / sqrt(1.09038)
```

The same applies to several p and d contractions. PySCF f coefficients in the
tested def2-TZVP case were already standard-normalized.

The source molecular orbitals correspond to PySCF's normalized basis. Scaling
the raw contraction coefficients to unit primitive-contraction self-overlap
therefore does not change the physical basis or the MO interpretation.

## 3. Correction

In `adapters/pyscf.py`, each s, p and d contraction is normalized by

```text
factor = 1 / sqrt(<contracted component | contracted component>)
```

using the existing `contracted_self_overlap` and `component_powers` helpers.
No new normalization algorithm was introduced. The source S and C are not
modified; full-state P is generated from the normalized basis and the same C.

This is a source-convention conversion, not a change to the MDM strict
validation profile.

## 4. Results

After the correction:

| Case | Path | Result |
|---|---|---|
| H₂O/STO-3G RHF | direct + full | PASS |
| H₂S/def2-TZVP RHF spherical f | direct + full | PASS |
| PySCF H₂S full CᵀSC | generated | `8.54e-14` |
| PySCF H₂S full Tr(PS) | generated | `18.000000000000018` |
| PySCF H₂S full Mayer vs ORCA | comparison | `~1.0e-6` |
| PySCF spherical d full | generated | PASS |
| PySCF Cartesian d full | blocked | explicit `PyscfAdapterError` |
| PySCF Cartesian d direct | S/P | PASS |

The earlier `18.23` trace failure was removed by normalizing the raw s/p/d
contractions. No native change was required.

## 5. Cartesian d

The PySCF Cartesian-d direct path is validated. Full state without S remains
blocked because the current shell/contraction representation does not safely
infer per-component Cartesian normalization for the native full path.
`from_pyscf(..., include_overlap=False)` now raises a specific
`PyscfAdapterError` rather than returning an invalid MDM. No normalization
value is invented.

## 6. Tolerances

- Source-supplied S/P/C: strict source profile remains
  `TOL_ORTHONORM=1e-10`, `TOL_ELECTRON_COUNT=1e-8`.
- Native generated S/P: generated checks use `1e-6` for electron count and
  `CᵀSC`; observed errors range from about `8e-9` to `2.1e-7`.
- The generated bound is not applied to source matrices and is not a universal
  scientific tolerance.
- The full PySCF f case now achieves generated `CᵀSC` around `5e-14`, well
  inside the generated bound.

Evidence: `MDM_1.1_work/PHASE9C/phase9c_p0_metrics.txt` and the Phase 10
checkpoint. The Phase 9C P0 measurements were retained; the new full-f
measurement is recorded in the Phase 10 checkpoint.
