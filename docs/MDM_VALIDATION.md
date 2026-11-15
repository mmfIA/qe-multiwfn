# MDM validation — builder and Engine contract

**Scope:** Phase 9B validation contract for `MolecularSystemV1`, the public
builder and the Engine. This document distinguishes structural readiness,
strict source-matrix validation and generated-state validation.

## 1. Validation layers

```text
builder input
  -> structural validation
  -> electronic/spin validation
  -> normalization metadata
  -> strict MDM validation (when S/P are supplied)
  -> Engine direct path: strict validation at load
  -> Engine full path: full-state preflight + generated S/P validation
  -> native scientific routines
```

No layer asserts that an unavailable scientific reference is a PASS.

## 2. Structural validation

Performed by `MolecularDataBuilder` and `MolecularSystemV1.validate`

- atom count matches geometry rows;
- atomic numbers 1..118 and symbol/Z consistency;
- coordinates finite and shaped `(ncenter, 3)`;
- electronic wfntype, charge, multiplicity and Ne;
- basis dimensions, AO indexes, primitive table size, shell primitive ranges;
- AO centers and `angular_type`;
- square finite matrices;
- S/P dimensions match nbasis;
- PBC metadata consistency (PBC execution still rejected by Engine).

Error: `ValueError` for malformed data; `QeIncompleteState` for missing
scientific components.

## 3. Electronic and spin validation

| Method | Required checks |
|---|---|
| RHF | multiplicity 1, even Ne, doubly occupied orbitals, `P S P = 2P` |
| UHF | `Na+Nb=Ne`, `Na−Nb=mult−1`, alpha/beta occupations 0/1, `Tr(PσS)=Nσ`, `PσSPσ=Pσ` |
| ROHF | one spatial set, occupations 2/1/0, `Pα/Pβ` from occupancy thresholds, same trace/idempotency checks |
| post-HF | represented but rejected by the native execution boundary |

`P_total = P_alpha + P_beta` is required for open shell. The total density is
not assumed to be a Mayer matrix.

## 4. Orbital validation

- coefficient layout and shape match the declared `orbital_ao`/`ao_orbital`;
- coefficient rows/columns span nbasis;
- occupations are finite, nonnegative and match nmo;
- spin labels match nmo;
- supplied S permits `CᵀSC` per spin group;
- RHF/ROHF spatial sets and UHF alpha/beta sets are kept distinct.

If S is not supplied, C^TSC cannot be checked before native S generation; the
full-state path documents this and validates the generated S/P traces and
idempotency instead.

## 5. Normalization validation

- S supplied and shells/primitives available: existing
  `attach_normalization` classifies the source convention and fills AO
  metadata.
- No S but `source_normalized`: per-AO normalization metadata is set to 1 and
  primitive normalization to 1.
- Unknown or non-determinable convention: full state fails with
  `QeIncompleteState`; it is never guessed.
- `normalization_report` can inspect the resulting metadata.
- `P_total_prim` is not transformed by angular phase operations.

## 6. Strict MDM profile

`MolecularSystemV1.validate(strict=True)` enforces, when S/P are present:

- S and P are `ao_current_basis`;
- `Tr(P S)=Ne` within the existing `TOL_ELECTRON_COUNT`;
- RHF `PSP−2P` idempotency;
- UHF/ROHF alpha/beta traces and idempotency;
- `P_total=Pα+Pβ`;
- per-spin `CᵀSC` orthonormality when coefficients span nbasis.

The Engine applies this profile to the direct S/P path before native
execution. The full path cannot apply source C^TSC without S; it applies a
structural/full-state preflight and validates the generated matrices.

## 7. Full-state preflight and generated checks

Before `build_electronic_state_v1`, the Engine checks:

- wavefunction and orbitals present;
- shells, primitive table and AO map present;
- primitive count matches;
- every AO has a valid shell index, component code and normalization
  metadata;
- coefficient dimensions span nbasis.

After native `genSbas_curr`/`genP`, it checks:

- generated S/P dimensions and finiteness;
- symmetry;
- `Tr(P S)=Ne`;
- `CᵀSC` per spin group at the generated-state tolerance;
- method-specific idempotency;
- open-shell `P=Pα+Pβ` and alpha/beta traces.

Generated state uses documented native-integration bounds of `1e-6` for
electron count and orthonormality. These are separate from the strict
source-matrix tolerances (`TOL_ELECTRON_COUNT=1e-8`, `TOL_ORTHONORM=1e-10`) and
do not relax source validation. Generated S/C^TSC is not asserted at the
source tolerance because the native integrals have their own numerical
precision; the P0 audit records the observed errors.

## 8. ReadinessFlags

`analysis_ready["mayer"]` is true only when:

- geometry is ready;
- basis/AO map is valid;
- S and P (or the method-required spin densities) are present;
- the system is non-periodic;
- wfntype is RHF, UHF or ROHF.

ROHF is now included (Phase 9B). Readiness is a summary flag, not a substitute
for strict validation.

## 9. Fail-closed policy

| Missing/invalid | Result |
|---|---|
| geometry/electronic/basis | `QeIncompleteState`/`ValueError` |
| direct S/P inconsistent | `ValueError` before native |
| full-state normalization missing | `QeIncompleteState` before native |
| PBC/post-HF/ECP-EDF execution | `QeUnsupported` |
| g/h, Cartesian f | `QeUnsupported`/`ValueError` |
| unknown angular convention | angular exception |
| native failure | typed `QeError` |

No path returns a “valid-looking” result when a required scientific invariant
or reference is unavailable.

## 10. Tested matrix

The builder tests cover structural failures, units, spin, direct P/S, full
state without files, canonical 1.2 f metadata, UHF/ROHF semantics and strict
Engine rejection. The existing 202-test suite remains green; the Phase 9B
The combined suite is 233 Python tests; CTest remains 6/6.
