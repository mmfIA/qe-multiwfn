# Phase 8C — analysis and routine support matrix for spherical f

**Scope:** canonical MDM 1.2 spherical f (`l = 3`). A `PASS` below means an
executed comparison, not merely that a routine accepts an f matrix.

## Exposed scientific paths

| Public API / path | Underlying routine(s) | RHF f | UHF f | ROHF f | Status |
|---|---|---|---|---|---|
| `load_molecule_v1(..., prepare_from_orbitals=True)` + `prepare()` | basis builder, `genSbas_curr` | PASS (H₂S) | PASS (O₂) | PASS (O₂) | Validated only for canonical MDM 1.2 |
| `generate_overlap()` | `genSbas_curr` / `matCar2curr` | PASS | PASS | PASS | Generated `S` compared with canonical ORCA S |
| `generate_density()` | `genP` | PASS | PASS | PASS | `P_total`, `P_alpha`, `P_beta` validated |
| `generate_primitive_density()` | `genPprim` | PASS | PASS | PASS | Separate primitive basis; traces equal `N_e`, α/β traces equal 9/7 |
| `calculate_mayer()` | `calcMayerbndord` | PASS | PASS | PASS | α/β/mixed compared with ORCA and Multiwfn |
| direct `load_molecule_v1(model)` + `calculate_mayer()` | `calcMayerbndord` on supplied P/S | PASS | PASS | PASS | Matrix-only path; does not process f basis, so it is not f-integral evidence |
| `generate_cartesian_overlap()` | Cartesian overlap / `matCar2curr` | NOT VALIDATED | NOT VALIDATED | NOT VALIDATED | Returns a 72×72 object for O₂ f, but no independent f reference; do not claim correctness |
| `analysis.calculate_mayer()` convenience wrapper | same Mayer path | PASS | PASS | PASS | Delegates to `Engine.calculate_mayer()` |
| Mulliken, Wiberg, Fuzzy, LBO, IBSI, other analyses | not exposed by this ABI | NOT EXPOSED | NOT EXPOSED | NOT EXPOSED | No support claim |

## Native guards

| Case | Behavior | Status |
|---|---|---|
| canonical MDM 1.2 spherical f | accepted | VALIDATED (RHF/UHF/ROHF fixtures) |
| non-canonical MDM 1.1 f, original-routine state | rejected | FAIL-CLOSED |
| Cartesian f | rejected by the basis builder | BLOCKED |
| g/h (`l > 3`) | rejected | BLOCKED |
| canonical spherical f with `l > 3` | rejected | BLOCKED |
| PBC / post-HF / ECP-EDF | rejected or not implemented | NOT SUPPORTED |

## Open-shell density semantics

- `P_total = P_alpha + P_beta`; this identity was checked to `0.0`.
- `MayerResult.alpha` and `.beta` are separate matrices.
- `MayerResult.total` is the mixed-density Mayer matrix for UHF/ROHF, not the
  α+β all-electron matrix. Multiwfn prints both; comparisons must use its
  mixed-density matrix for the native `total`.

## Validation boundary

The only executed f cases are:

- H₂S/def2-TZVP, RHF, spherical f (Phase 8B);
- O₂/def2-TZVP, UHF and ROHF, spherical f (Phase 8C).

No other f basis, molecule, multiplicity, analysis or angular momentum is
validated. `generate_cartesian_overlap()` accepting an f model is not evidence
of Cartesian-f correctness.
