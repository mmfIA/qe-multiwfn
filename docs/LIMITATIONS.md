# Limitations and scope — QE-Multiwfn 0.3.0

**Current tree:** Python `0.3.0`, MDM `1.1.0`, native ABI `0.2.0`.
**Frozen base:** QE-Multiwfn 0.2.0 (`9560c0fc…`), not modified.
**Dev library (Phase 9C):** `e9ac3a73…`; 17 legacy + 27 additive ABI symbols
(44 total; 15 additive since the 29-symbol frozen baseline).

This document describes the current development scope. Historical 0.1.x,
0.2.0 and M1 counts are not current; see the scope labels in the relevant
documents.

## Implemented and validated

- Legacy C ABI lifecycle, state transfer, error handling and Mayer pipeline.
- Original `calcMayerbndord` for Mayer; not replaced by a Python formula.
- RHF Mayer; UHF and ROHF as explicit opt-ins (`allow_open_shell=True`).
- Public in-memory MDM builder (`MolecularDataBuilder`, `build_molecular_system`)
  for NumPy/Python input, with no file or adapter dependency.
- PySCF 2.15.0 in-memory adapter for RHF/UHF/ROHF, s/p/d/f spherical and
  Cartesian d on the direct path.
- ASE structural adapter (`from_ase`/`from_ase_atoms`), with PBC fail-closed.
- Generic `DatabaseRecord` protocol and synthetic source-equivalence tests.
- MDM 1.1: atoms, geometry, shells, primitives, AO map, normalization
  metadata, orbital data, S/P, provenance and readiness.
- ORCA 6.x JSON adapter for the validated RHF/UHF/ROHF s/p/d cases and the
  canonical H₂S/O₂ f fixtures.
- cclib conversion from cclib-like data with an explicit canonical basis.
- Original-routine electronic state on the validated s/p/d scope:
  `genP`, `genPprim`, `genSbas`, `genSbas_curr`, and the full
  `MDM → basis → orbitals → genSbas_curr → genP → Mayer` flow.
- Fail-closed missing-data handling, state-gated getters and invalidation of
  derived Cartesian overlap/primitive-density caches.
- Strict direct S/P validation and full-state preflight/generated S/P checks.
- Additive `MayerResult` semantics: `mixed`, `generalized_wiberg`,
  `mayer_total`, `alpha_plus_beta` and `total_semantics`; old fields/results
  preserved.
- Non-interactive exposed paths: `ifiletype=9`, `ifPBC=0`; no public setter
  for either global. `matCar2curr`'s only `read(*,*)` is in its unsupported
  `ifiletype` branch and is unreachable from the API.

## Not implemented / blocked

| Capability | Status | Notes |
|---|---|---|
| f spherical native path | **PASS (canonical MDM 1.2)** | H₂S/def2-TZVP RHF; O₂/def2-TZVP UHF/ROHF. S≤5.94e-9; Mayer vs ORCA≤1.17e-8; α/β vs Multiwfn≤4.93e-9. |
| f Cartesian native path | **BLOCKED** | not validated; basis builder rejects Cartesian f. |
| g/h native path | **BLOCKED** | fail-closed `l > 3`; no generalization. |
| ORCA/Molden m=±3 f convention | **RESOLVED for validated fixture** | ORCA 6.1.1 phase corrected by MDM 1.2 canonicalization; see Phase 7A/8B. |
| cclib + ORCA 6.1.1 text parser | **BLOCKED** | cclib 1.8.1 `orcaparser.py:2799` `IndexError`; adapter fails closed. Synthetic conversion with explicit basis passes. |
| ASE independent Mayer | **NOT AVAILABLE** | Geometry-only; no basis/orbitals from ASE input. |
| PBC | **NOT IMPLEMENTED** | `ifPBC > 0` rejected; no periodic integrals/Mayer path. |
| Post-HF (`wfntype` 3/4) | **NOT IMPLEMENTED** | Rejected by the open-shell boundary. |
| ECP / EDF execution | **NOT IMPLEMENTED** | Modeled in MDM; no validated execution path. |
| Thread safety / multiple engines | **NOT SUPPORTED** | Multiwfn state is process-global; one active system per process. |
| OpenMP | **DISABLED** | Not enabled until state isolation is proven. |
| 0.3.0 package | **PRODUCED** | Wheel/sdist in `dist-phase12/`; Linux x86_64/Python 3.12 only; system BLAS/gfortran required. |
| RHF `nmo == nbasis` | **UNVALIDATED EDGE** | The current RHF/ROHF adapter assumes one spatial set of size `nbasis`; bases with linear dependence (`nindbasis < nbasis`) require an explicit test. |
| `hyp2F2` | **STUB** | Fractional 2F2 path is a documented stub; unused by the validated s/p/d routines. |
| Native FCH/WFN/WFX/Molden/MWFN readers | **NOT EXPOSED** | Core readers are not exposed; adapters are separate and format-specific. |
| Analyses other than Mayer | **NOT EXPOSED** | Future work. |
| Full-state normalization inference | **PARTIAL** | Source-normalized input is supported; other conventions require S or explicit AO metadata. |
| PySCF full-state f | **PASS (tested)** | H₂S/def2-TZVP f full state validated after unit contraction normalization. |
| PySCF Cartesian d full state | **BLOCKED** | Direct path with S is validated; full state without S lacks safe per-component normalization. |
| ASE electronic state | **NOT AVAILABLE** | ASE is structural only; PBC fails closed. |
| Database connectors | **NOT IMPLEMENTED** | Generic protocol only; no network/credentials. |
| Builder Cartesian f/g/h | **BLOCKED** | Same native scope as Engine; canonical spherical f only. |

## Important boundary notes

- **Two P/S paths:** the direct 0.2.0 path consumes caller-supplied S/P; the
  Phase 6/8 path generates S/P from MDM basis/orbitals. Spherical f is now
  validated on the canonical MDM 1.2 path; g/h and Cartesian f are not.
- **Angular-order coupling:** the original path fixes `ifiletype=9` and relies
  on the ORCA/Molden component convention. The ORCA f phase is corrected in
  the import layer by `D_f`; g/h remains outside the validated convention.
- **No stale results:** derived Cartesian overlap and primitive density have
  validity flags; a new system/basis invalidates them. Getters require
  PREPARED/RESULT_AVAILABLE and matching dimensions.
- **Memory:** input buffers are copied into Fortran; no Python pointers are
  retained after a call. Matrices are column-major at the C ABI.
- **Units:** coordinates are explicitly Angstrom or Bohr; the canonical model
  stores Bohr. Do not infer units silently.
- **Numerical policy:** do not relax tolerances to force PASS. Missing
  evidence or an unavailable external executable is `INCOMPLETE`, not `PASS`.

## Scientific validation boundary

Current tests (233 Python, 6/6 CTest) cover the RAM-to-RAM bridge, state
transitions, MDM validation, the original Mayer path, UHF/ROHF, s/p/d
spherical/Cartesian cases, the Phase 6 full flow without input matrices,
canonical spherical f on H₂S/def2-TZVP (RHF) and O₂/def2-TZVP (UHF/ROHF),
the in-memory builder/direct/full paths, PySCF RHF/UHF/ROHF, ASE structural
input and synthetic database records. Generated full-state validation checks
orthonormality and electron-count with a documented native-integration bound
of `1e-6`; strict source-matrix validation remains `10^-10`/`10^-8`.
They do not establish PBC, post-HF, ECP/EDF, g/h, cclib ORCA 6.1.1 parsing,
or thread safety. Spherical f is established for the canonical H₂S RHF and
O₂ UHF/ROHF fixtures; Cartesian f is not. The builder is tested for RHF,
UHF and ROHF, direct S/P and full-state in-memory execution.

The canonical validation artifacts are unchanged
(`comparisons/validation_results.json = 6fb8b315…`; H₂/H₂O/C₆H₆ Mayer
bit-identical). The derived validation manifest remains `6aff745e…` under
the existing post-freeze addendum.

## Build dependencies

CMake requires a Fortran and C compiler, BLAS and LAPACK. The dev library
compiles the Phase 6 upstream closure (17 files): `define`, `util`, `Bspline`,
`2F2`, LIBRETA helpers, `function`, `sub`, `integral`, `PBC` and `bondorder`.
`vendor/` remains byte-identical to the frozen source. `hyp2F2` is resolved
by the documented stub; flint/arb is not required for the validated path.

Tested configuration: Ubuntu, GNU Fortran/GCC, CMake, OpenBLAS, Python 3.12,
NumPy and pytest. Other compilers/BLAS implementations must be validated
independently.

## P0 validation fixtures and skipped tests

The historical P0 validation suite (223 tests) and its ORCA/Multiwfn
artifacts live in the external `QE-Multiwfn-validation` tree. They are not
redistributed in this repository because their provenance/redistribution
conditions have not been audited. The versioned protocol is
`tests/python/test_p0_validation.py`, using the SHA-256 manifest
`tests/python/p0_fixtures.json`; set `QE_P0_FIXTURES` to the external tree to
execute it. Without fixtures the three system tests skip explicitly. The external P0
pipeline now also requires `CoordinateUnits` and fails closed (13C.5).
The external validation tree is not a Git repository and its
`SHA256SUMS.txt` is stale relative to the 13C.5 changes; see
`docs/PHASE13C5_1_PRECOMMIT_AUDIT.md`.

The regular CI suite no longer uses module-level skips where independent unit
tests exist. In the no-fixture simulation the build-test suite executes
109 tests and skips 50; the optional-dependency job executes 114 and skips 46.
The remaining skips are fixture-dependent (ORCA/Multiwfn datasets), not
silent PASSes. Of the 115 test functions formerly hidden by 20 module-level
skips, 14 are executable without external fixtures (11 without optional
packages; 3 additional ASE tests with ASE installed) and 101 remain
fixture-dependent. Hosted CI must be run after publication authorization; the
local simulation is not a substitute.

## Historical documents

The following are historical and not current status:
`RELEASE_NOTES_0.1.1.md`, `BUILD_VERIFICATION_0.1.1.md`,
`FINAL_REPORT_0.1.0.md`, `SOURCE_AUDIT.md`, `M1_IMPLEMENTATION_REPORT.md`,
`MOLECULAR_DATA_MODEL_1.0.md`, and `EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md`.
See their scope banners.
