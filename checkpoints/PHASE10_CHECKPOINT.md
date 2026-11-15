# Phase 10 checkpoint — scientific hardening and adapter maturity

**Status:** COMPLETE.
**Global verdict:** **PASS** for the implemented and tested Phase 10 scope, with
documented limits (PySCF Cartesian-d full state, unsupported PBC/DFT/post-HF/
ECP, non-tested dependency versions and the not-yet-produced distribution
package).

## 1. Initial state

| Item | Value |
|---|---|
| Tree | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Python | `0.3.0.dev0` |
| MDM | `1.1.0` default; `1.2.0` opt-in |
| Native ABI | `0.2.0` |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Prior suite | 230 Python / CTest 6/6 |
| Environment | PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1 |

## 2. Normalization (P0)

Root cause: PySCF `mol._basis` stores raw contraction coefficients; several
s/p/d contractions are not normalized against the standard Gaussian primitive
convention used by native `genSbas`/`genP`. PySCF internally normalizes them
for its own integrals.

Correction in `adapters/pyscf.py`:

- s/p/d raw contraction coefficients are scaled by
  `1/sqrt(contracted_self_overlap)` using the existing normalization helpers;
- C and the physical basis are unchanged;
- f coefficients in the tested def2-TZVP case already follow the standard
  convention;
- no second normalization algorithm was introduced.

Results:

| Case | Generated CᵀSC | Generated Tr(PS) |
|---|---:|---:|
| PySCF H₂S/def2-TZVP f full | `8.54e-14` | `18.00000000000002` |
| PySCF H₂O/STO-3G | `2.00e-8` | `10.000000155` |
| PySCF H₂O/6-31G* spherical d | `2.11e-7` | `10.000000425` |
| PySCF O₂/STO-3G UHF | `2.62e-8` / `2.58e-8` | `16.000000328` |
| PySCF O₂/STO-3G ROHF | `2.60e-8` | `16.000000328` |

Generated-state bounds remain `1e-6` for electron count and orthonormality.
Source-supplied matrices retain `1e-8` electron count and `1e-10`
orthonormality. This is a differentiated validation profile, not a universal
relaxation.

PySCF spherical f with `include_overlap=False` is now supported. PySCF
Cartesian-d full state remains blocked because per-component Cartesian
normalization is not safely inferred without S; `from_pyscf(...,
include_overlap=False)` raises `PyscfAdapterError`.

## 3. PySCF (P1)

Tested version: **2.15.0**.

Supported:
- RHF, UHF, ROHF;
- STO-3G RHF/UHF/ROHF;
- H₂O/6-31G* spherical d, direct and full;
- H₂O/6-31G* Cartesian d, direct;
- H₂S/def2-TZVP spherical f, direct and full, MDM 1.2;
- canonical AO permutation and source-normalized full-state coefficients;
- explicit rejection of DFT, non-converged SCF, ECP, g/h, Cartesian f.

Version compatibility is documented but not claimed beyond 2.15.0.

## 4. ASE (P1)

Tested version: **3.29.0**.

- `from_ase`/`from_ase_atoms`;
- structural geometry only;
- Å → Bohr explicit;
- PBC fail-closed;
- no electronic data invented;
- ASE → PySCF composition documented.

## 5. Database protocol (P2)

Added:
- `DatabaseProvider` protocol (`get_record(record_id)`);
- `InMemoryDatabaseProvider` reference connector;
- `from_database_provider`;
- existing `DatabaseRecord`/`from_database_record`.

Synthetic records with different IDs/sources and identical arrays converge on
the same MDM and Engine result. No real database, network or credentials are
required.

## 6. Adapter audit (P3)

- Engine imports no adapters.
- No adapter imports native/Fortran, uses subprocess or requires a file.
- PySCF and DatabaseRecord converge through `MolecularDataBuilder`.
- ORCA/cclib retain their validated conversion paths and remain compatible.
- ASE is explicitly structural.
- Standard adapter exceptions: `PyscfAdapterError`, `AseAdapterError`,
  `OrcaAdapterError`, `CclibAdapterError`; builder contract errors remain
  `ValueError`/`QeIncompleteState`.
- No cross-source dependency was introduced.

## 7. Source equivalence (P4)

Validated cases include:

| System | Method | Sources | Max Mayer Δ |
|---|---|---|---:|
| H₂/STO-3G | RHF | ORCA/PySCF | `1.33e-15` |
| H₂O/STO-3G | RHF | ORCA/PySCF | `3.22e-8` |
| O₂/STO-3G | UHF | ORCA/PySCF | `2.53e-12` |
| O₂/STO-3G | ROHF | ORCA/PySCF | `2.22e-15` |
| H₂O/6-31G* | RHF spherical d | ORCA/PySCF | `3.78e-6` |
| H₂O/6-31G* | RHF Cartesian d | ORCA fixture/PySCF | `9.43e-7` |
| H₂S/def2-TZVP | RHF spherical f | ORCA/PySCF direct/full | `5.97e-7` / `1.02e-6` |
| Synthetic records | RHF | database A/B | exact |

AO order, units, angular convention and normalization are aligned before
comparison. Provenance differs; scientific results do not.

## 8. Quality and optional dependencies (P5)

- `import qe_multiwfn` does not import PySCF, ASE or cclib.
- Optional imports are local to adapters.
- Core builder/MDM/Engine path works with NumPy only.
- `phase10_optional_import_probe.txt` confirms core import with optional
  packages blocked.
- A distribution package is still not produced; source-tree/PYTHONPATH usage
  remains the tested installation mode.

## 9. Tests

| Suite | Result |
|---|---|
| Python | **231 passed, 1 warning** |
| CTest | **6/6 passed** |
| Prior suite | 230 passed |
| New Phase 10 test | 1 database provider test |
| Existing warning | pre-existing ASE/NumPy deprecation |

Evidence:

- `MDM_1.1_work/PHASE10/phase10_pytest.log`
- `MDM_1.1_work/PHASE10/phase10_ctest.log`
- `MDM_1.1_work/PHASE10/phase10_p0_metrics.txt`
- `MDM_1.1_work/PHASE10/phase10_optional_import_probe.txt`

## 10. Files

Created:
- `docs/PHASE10_NORMALIZATION_AUDIT.md`
- `docs/PYSCF_COMPATIBILITY.md`
- `docs/ASE_COMPATIBILITY.md`
- `docs/DATABASE_CONNECTOR_ARCHITECTURE.md`
- `docs/ADAPTER_CONTRACT_AUDIT.md`
- `docs/SOURCE_EQUIVALENCE_PHASE10.md`
- `checkpoints/PHASE10_CHECKPOINT.md`
- `docs/PHASE10_CHECKPOINT.md` (checkpoint copy)

Modified:
- `python/qe_multiwfn/adapters/pyscf.py`
- `python/qe_multiwfn/adapters/database.py`
- `python/qe_multiwfn/engine.py` (generated CᵀSC check; carried from Phase 9C)
- `python/qe_multiwfn/adapters/ase.py` (PBC/alias; Phase 9C contract)
- `tests/python/test_pyscf_adapter.py`
- `tests/python/test_database_adapter.py`
- `docs/MDM_VALIDATION.md`
- `docs/PUBLIC_API.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/LIMITATIONS.md`
- `docs/ARCHITECTURE.md`
- `README.md`

No native Fortran, C ABI, shared library, vendor or frozen artifact was
changed.

## 11. Integrity

| Item | Value |
|---|---|
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | **44** = 17 legacy + 27 additive; no change |
| Vendor diff | 0 |
| Frozen packages | `sha256sum -c` OK |
| Canonical results | `6fb8b315…` |
| Manifest | `6aff745e…` |
| Native rebuild | not required |

## 12. Acceptance matrix

| Area | Result |
|---|---|
| Normalization full state | **PASS**; Cartesian-d full blocked explicitly |
| PySCF RHF/UHF/ROHF | **PASS** |
| PySCF spherical f full | **PASS** |
| PySCF Cartesian d direct | **PASS** |
| AO ordering | **PASS** |
| Angular conventions | **PASS** for supported cases |
| ASE structural | **PASS** |
| ASE PBC | **FAIL-CLOSED** |
| Database protocol | **PASS** |
| In-memory connector | **PASS** |
| Adapter contract | **PASS** |
| Source equivalence | **PASS** on validated cases |
| ORCA compatibility | **PASS** |
| Prior tests | **PASS** |
| ABI | **PASS** |
| Frozen | **PASS** |
| Vendor | **PASS** |
| Documentation | **PASS** |

## 13. Remaining limits / pending

- PySCF Cartesian-d full state without S remains blocked.
- PBC, DFT, post-HF and ECP execution remain out of scope.
- g/h and Cartesian f remain blocked.
- cclib real ORCA 6.1.1 parser remains blocked.
- Only PySCF 2.15.0 and ASE 3.29.0 were tested; no other versions are
  claimed.
- A distribution package/installation test is not produced.
- No real database connector is implemented; provider protocol is tested with
  in-memory records only.

## 14. Gate

Phase 10 is complete. Phase 11 is not started. Recommended next step: package
installation testing, optional-version CI, PySCF Cartesian-d full-state
normalization research, and a real connector behind the provider protocol,
without changing the native core or ABI.
