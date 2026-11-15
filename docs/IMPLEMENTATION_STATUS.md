# Implementation status — QE-Multiwfn 0.3.0

**Scope:** distribution tree after Phases 9A–10 and Phase 11 packaging.
**Python:** `0.3.0`. **MDM:** schema `1.1.0`.
**Native ABI:** `0.2.0`, intentionally preserved.
**Frozen release:** QE-Multiwfn 0.2.0 (`9560c0fc…`), unchanged.
**Dev library:** `python/libqe_multiwfn.so`, SHA-256 `e9ac3a73…`.
**ABI:** 17 legacy symbols + 27 additive symbols = **44**; 15 symbols added
since the frozen baseline; no legacy symbol removed. See
`PHASE8C_ARCHITECTURE_AUDIT.md` for the measured correction.

The 0.3.0 wheel/sdist have been produced and tested from an isolated environment; this status refers to the packaged library.

## Current capabilities

| Area | Status | Evidence / notes |
|---|---|---|
| Legacy C ABI and lifecycle | PASS | 17 legacy symbols; CTest 7/7 |
| P0 validation protocol | PASS (local) | versioned H₂/H₂O/C₆H₆ harness; external fixtures via `QE_P0_FIXTURES`; 223 historical external |
| RHF Mayer (`calcMayerbndord`) | PASS | P0 baseline bit-identical; QE × Multiwfn ≤ 4.98e-9 |
| UHF / ROHF (opt-in) | PASS | O₂/STO-3G; `allow_open_shell=True`; α/β validated |
| MDM 1.0/1.1 | IMPLEMENTED | schema 1.1.0; normalization metadata; provenance |
| MDM builder | PASS | `MolecularDataBuilder`, `build_molecular_system`; direct NumPy/Python/in-memory; full state without files |
| PySCF adapter | PASS | PySCF 2.15.0 RHF/UHF/ROHF; s/p/d/f spherical direct/full; Cartesian d direct; DFT/post-HF/ECP blocked |
| ASE adapter | PASS (structural) | `from_ase`/`from_ase_atoms`; geometry only; PBC fail-closed |
| Database protocol | PASS | `DatabaseRecord`, `from_database_record`, `DatabaseProvider`, `InMemoryDatabaseProvider`, `from_database_provider`; synthetic records converge |
| Strict Engine validation | PASS | direct S/P strict profile; full-state preflight + generated S/P checks |
| `MayerResult` semantics | PASS (additive) | `mixed`, `generalized_wiberg`, `mayer_total`, `alpha_plus_beta`, `total_semantics`; old fields preserved |
| Readiness ROHF | PASS | `analysis_ready["mayer"]` accepts wfntype 2 |
| ORCA 6.x JSON adapter | PASS (validated cases) | RHF/UHF/ROHF, s/p/d/f canonical opt-in; optimization geometry |
| cclib adapter | PARTIAL / fail-closed | synthetic conversion with explicit basis passes; real ORCA 6.1.1 parser blocked |
| `genP` | PASS (s/p/d/f) | RHF/UHF/ROHF; P exact vs reference |
| `genPprim` | PASS (s/p/d/f) | primitive density separate from AO density; trace=Ne |
| `genSbas` | PASS (s/p/d/f) | Cartesian d vs PySCF; spherical d/f via `genSbas_curr` |
| `genSbas_curr` | PASS (s/p/d/f) | spherical uses original `matCar2curr`, `ifiletype=9` |
| Full MDM → S/P → Mayer | PASS | `prepare_from_orbitals=True`; seven s/p/d cases + canonical H₂S f + O₂ UHF/ROHF f |
| f original-routine path | PASS (spherical) | canonical MDM 1.2; H₂S RHF and O₂ UHF/ROHF, def2-TZVP |
| g/h original-routine path | BLOCKED | fail-closed `l > 3` |
| Cartesian f native path | BLOCKED | not validated; native guard rejects |
| PBC / post-HF / ECP-EDF | NOT IMPLEMENTED | PBC/post-HF rejected; ECP/EDF modeled only |
| Thread safety / multiple engines | NOT SUPPORTED | process-global Multiwfn state |
| 0.3.0 package | PRODUCED | wheel/sdist tested in isolated venv; Linux x86_64/Python 3.12 |

## Test status (current)

| Suite | Result |
|---|---|
| Python | **256 passed, 1 warning** (local, with external P0 fixtures) |
| CTest | **7/7 passed** |
| Clean build | **PASS** (`build_audit`, same library hash) |
| Scientific flows | RHF/UHF/ROHF s/p/d/f **PASS**; Cartesian f not validated |
| RHF baseline | S/P/Mayer bit-identical |
| ABI symbols | 17 legacy + 27 additive = 44; no legacy removed |
| CI simulation (13C.4) | 109 passed, 50 skipped (build-test, no external fixtures); optional-dependency job 114/46; hosted CI pending publication authorization |
| `ldd -r` / RUNPATH | clean / `$ORIGIN` |

Test breakdown: 121 MDM/M1 + 6 genP + 10 genSbas + 6 genPprim +
10 full-flow/fail-closed + 2 cache-invalidation + 19 Phase 7C ORCA +
6 Phase 8B native f + 4 Phase 8C open-shell f + 13 Phase 9B builder +
12 Phase 9C/10 PySCF + 2 ASE + 4 database (plus 18 Phase 7B angular),
10 unit-contract tests, 6 versioned P0 harness tests and 2 skip-inventory tests in 13C.4.

## Blocked / not implemented

### Native angular support

- **Spherical f:** supported for canonical MDM 1.2. H₂S/def2-TZVP RHF full
  flow gives S max `3.61e-9`, P max `1.7e-18`, Mayer max `7.54e-9` vs the
  direct reference; Multiwfn standalone max `8.45e-9`. O₂/def2-TZVP UHF and
  ROHF full flow gives S max `5.94e-9`; Mayer vs ORCA `≤1.17e-8`; α/β vs
  Multiwfn `≤4.93e-9`. Primitive traces are 16/9/7 within `3e-9`.
- **Cartesian f:** not validated; the native basis builder rejects it.
- **g/h:** fail-closed (`l > 3`); not generalized.
- **Guard:** non-canonical MDM 1.1 f is rejected for overlap/state building;
  the direct P/S path remains available.

### cclib / ORCA 6.1.1

cclib 1.8.1 fails in `orcaparser.py:2799 _append_scfvalues_scftargets`
(`IndexError`; last line read: RMS-density tolerance). The project adapter
`from_cclib` fails closed. `from_cclib_data` with an explicit canonical basis
is tested for RHF/UHF/ROHF. Details:
`../../MDM_1.1_work/CCLIB_ORCA_DIAGNOSIS.md`.

### Other limitations

- PBC not implemented; `ifPBC > 0` is rejected.
- Post-HF (`wfntype` 3/4) not implemented/rejected.
- ECP/EDF modeled but not executed.
- One active system/process; no thread safety or simultaneous engines.
- RHF assumes `nmo == nbasis`; linear-dependence cases
  (`nindbasis < nbasis`) still require validation.
- `hyp2F2` remains a documented stub; unused by the validated s/p/d path.
- Native FCH/WFN/WFX/Molden/MWFN readers are not exposed as core readers.
- 0.3.0 wheel/sdist built; platform is Linux x86_64 with Python 3.12 and system BLAS/gfortran.
- Full-state builder requires explicit normalization metadata; unknown
  conventions fail closed rather than being inferred.
- Builder f support is for canonical MDM 1.2 spherical f; Cartesian f/g/h
  remain blocked.
- PySCF spherical f is validated on both direct and full-state paths for the
  tested H₂S/def2-TZVP case. PySCF Cartesian-d full-state normalization is
  still blocked without S.
- ASE supplies only structural geometry; no electronic state.
- The database protocol is generic; no real DB connector is implemented.

## Historical snapshots (not current counts)

The following documents are retained for provenance and describe earlier
frozen states. Their counts must not be read as current:

- `M1_IMPLEMENTATION_REPORT.md` — 0.2.0/M1, schema 1.0, 94 Python tests,
  6/6 CTest, 223 validation tests. Symbol counts in that historical report
  are not current; the measured current library exports 17 legacy + 27
  additive = 44 (15 additive since the 29-symbol frozen baseline).
- `BUILD_VERIFICATION_0.1.1.md` — 0.1.1, 29 symbols, 4/4 CTest, 29/29 Python.
- `RELEASE_NOTES_0.1.1.md` — historical 0.1.1 and 0.2.0 notes.
- `FINAL_REPORT_0.1.0.md`, `SOURCE_AUDIT.md` — 0.1.0 scope.
- `MOLECULAR_DATA_MODEL_1.0.md` — historical 1.0 specification; the model has
  since been implemented and extended to 1.1.
- `EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md` — original plan; UHF/ROHF are now
  implemented, while PBC/post-HF/ECP/EDF remain pending.

Current evidence lives in `../../MDM_1.1_work/PHASE6_REPORT.md`,
`../../MDM_1.1_work/PHASE6_RESIDUALS.md`,
`../../MDM_1.1_work/AUDIT_PHASE6_FINAL.md` and
`../../MDM_1.1_work/TRANSFER_TO_OPENCODE_GO.md`.
