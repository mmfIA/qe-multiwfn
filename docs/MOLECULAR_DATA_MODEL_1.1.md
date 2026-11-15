# Molecular Data Model 1.1 — normalization and consolidation

**Status:** development for QE-Multiwfn 0.3.0
**Schema:** `1.1.0` (additive over 1.0.0)
**Frozen base:** QE-Multiwfn 0.2.0 (`9560c0fc…`)

## 1. Purpose

Resolve the 0.2.0 closing-audit INCOMPLETE: explicit normalization
metadata, conventions and validation for molecular basis functions. The
frozen 0.2.0 package is not modified; this is the development tree for the
next release.

## 2. New fields (additive)

| Type | Field | Meaning |
|---|---|---|
| `BasisSet` | `normalization_convention` | global convention: `unknown`, `source_normalized`, `cartesian_explicit`, `cartesian_source_scaled`, `cartesian_source_unnormalized`, `mixed` |
| `AOFunction` | `contraction_normalization` | per-AO contraction normalization factor |
| `AOFunction` | `source_self_overlap` | source `S_ii` used to validate the convention |
| `AOFunction` | `normalization_convention` | per-AO convention |

`PrimitiveTable.normalization` is populated per primitive row for Cartesian
components. The source `S`, `C`, `P` matrices are never modified.

## 3. Conventions

- **source_normalized** — the source S/C are already normalized; `S_ii = 1`.
  Used for spherical d/f from ORCA. Verified by `S_ii`.
- **cartesian_explicit** — standard Cartesian primitive normalization
  factors are computed and stored; the contraction factor is stored per AO;
  `S_ii = 1`.
- **cartesian_source_scaled** — the source Cartesian AO has `S_ii != 1`
  (e.g., PySCF Cartesian d). Primitive factors are stored and
  `1/sqrt(S_ii)` records the per-AO normalization.
- **cartesian_source_unnormalized** — source coefficients behave as
  unnormalized primitives; the per-AO factor is stored.
- **unknown** — legacy 0.1.1 models or incomplete data; explicitly
  INCOMPLETE, never silently accepted as normalized.

## 4. Cartesian normalization formulas

For a primitive Gaussian with exponent α and powers `(lx,ly,lz)`:

```
N(α,lx,ly,lz) = (2α/π)^(3/4) · (4α)^((lx+ly+lz)/2)
                / sqrt((2lx−1)!! (2ly−1)!! (2lz−1)!!)
```

The same-center 1-D Gaussian overlap is used to compute the contracted shell
self-overlap and to validate the source `S_ii`. A source coefficient set that
does not match a known convention is rejected.

## 5. Representation equivalence

- s/p Cartesian and spherical functions are the same physical basis; the
  model supports both conventions and the Mayer result is bit-identical
  (tested).
- d/f 5D (spherical) and 6D (Cartesian) are **different basis sets**, not
  merely different orderings. They are not claimed equivalent; both are
  represented and validated independently.
- Cartesian↔spherical component mappings are label-based (Multiwfn codes
  5..10 and 11..20) and verified against the vendor `GTFtype2name` table.

## 6. Compatibility

- `MolecularSystem` 0.1.1 remains the legacy input; `from_legacy`/`to_legacy`
  round-trip is bit-for-bit.
- 1.0 models are upgraded conceptually to 1.1; normalization is `unknown`
  until an adapter attaches it.
- The current development library exports **17 legacy + 27 additive ABI
  symbols (44 total; Phase 8C)**; 15 symbols were added since the 29-symbol
  frozen baseline and no legacy symbol was removed. The frozen 0.2.0 artifact
  and its original 0.1.1/0.2.0 symbol set remain untouched.
- The frozen 0.2.0 package remains untouched.

## 7. Tests

- Normalization formulas and known shells.
- ORCA RHF/UHF/ROHF normalization reports PASS.
- ORCA spherical d/f (`source_normalized`) and PySCF Cartesian
  (`cartesian_source_scaled`) PASS.
- s/p Cartesian/spherical equivalence.
- 5D/6D distinction.
- Legacy models report INCOMPLETE (honest).
- Phase 6 original-routine flow (`genSbas_curr`/`genP`) on s/p/d; f/g/h is
  fail-closed in that path (see `../../MDM_1.1_work/F_GH_DIAGNOSIS.md`).
