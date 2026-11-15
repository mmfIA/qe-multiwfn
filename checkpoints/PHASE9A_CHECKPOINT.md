# Phase 9A checkpoint — MDM contract audit

**Status:** AUDIT COMPLETE.
**Global verdict:** **PARTIAL** — architecture is origin-neutral and the
validated scientific scope is intact, but universal direct construction still
needs the Phase 9B builder and stricter contract enforcement.
**Gate:** **AUTHORIZED for Phase 9B implementation under the specification**,
not started automatically.

## 1. Initial state

| Item | Value |
|---|---|
| Tree | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Python | `0.3.0.dev0` |
| MDM | `1.1.0` default; `1.2.0` opt-in |
| Native ABI | `0.2.0` |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Previous checkpoint | `MDM_1.1_work/PHASE9A/CHECKPOINT_PHASE8C/` (read-only) |
| Initial hashes | `MDM_1.1_work/PHASE9A/before_phase9a_hashes.txt` |
| Source/ABI changes in 9A | **none** |

## 2. Tools and evidence

| Tool | Use |
|---|---|
| `grep`/file reads | MDM, Engine, adapters, headers and Fortran audit |
| `nm -D --defined-only` | frozen/current ABI inventory |
| `diff -u` | legacy/v1 header comparison |
| `pytest -q -p no:cacheprovider` | existing 202-test suite |
| `ctest --output-on-failure` | native 6-test suite |
| Python fresh-process import | adapter independence |
| Synthetic in-memory MDM probe | direct P/S path without files |
| Existing ORCA O₂/def2-TZVP fixture | ROHF readiness probe only (no scientific run change) |

Evidence files:

- `phase9a_abi_symbols.txt`, `phase9a_abi_counts.txt`
- `phase9a_removed_symbols.txt`, `phase9a_added_symbols.txt`
- `phase9a_legacy_header.diff` (empty)
- `phase9a_v1_header.diff` (additions/comment changes)
- `phase9a_import_probe.txt`
- `phase9a_memory_probe.txt`
- `phase9a_readiness_probe.txt`
- `phase9a_pytest.log`, `phase9a_ctest.log`

## 3. Executed verification

| Check | Result |
|---|---|
| Python | **202 passed, 1 warning** |
| CTest | **6/6 passed** |
| Frozen reference result | `6fb8b315…` unchanged |
| Validation manifest | `6aff745e…` unchanged |
| Vendor diff | empty |
| Frozen library | `9560c0fc…` unchanged |
| Current library | `e9ac3a73…` unchanged |
| ABI | 17 legacy + 27 additive = 44; 0 removed; 15 added since frozen |
| Direct in-memory P/S | synthetic `1x1` Mayer result; no files |
| Adapter import from Engine | ORCA/ASE/cclib not imported |
| ROHF readiness probe | `wfntype=2`, `density_ready=True`, `analysis_ready["mayer"]=False` (finding MDM-1) |

No tolerance, fixture, reference, canonicalization, vendor or frozen file was
changed. No rebuild was performed.

## 4. Problems found

| ID | Severity | Finding | Proposed action |
|---|---|---|---|
| MDM-1 | High | `ReadinessFlags.analysis_ready["mayer"]` excludes ROHF (`wfntype=2`) despite validated ROHF. | Include 2 in 9B; add regression test. |
| MDM-2 | High | `AOFunction.shell_index`/`multiwfn_type` are optional; Engine substitutes `0` for missing component code. | Make required for full-state builder; validate AO map. |
| MDM-3 | High | `Engine.load_molecule_v1` uses `validate(strict=False)`; fails to enforce S positive definiteness, strict traces/idempotency/C^TSC or P_total=Pa+Pb before native. | Add `strict="auto"`/strict validation in 9B. |
| MDM-4 | Medium | Shell/BasisSet do not cross-check shell_type/l, primitive ownership, or shell/AO agreement. | Builder-level structural validation. |
| MDM-5 | Medium | Primitive `type` is not range-validated; `shell_index` optional. | Builder/AO-map validation. |
| MDM-6 | Medium | Orbital occupations/coefficient row count are not checked against Ne/nbasis at construction. | Builder/orbital validation. |
| MDM-7 | Medium | Normalization metadata is manual; Engine does not attach it for full-state input. | Builder attaches/validates; explicit failure otherwise. |
| MDM-8 | Medium | `MatrixRecord.layout` is unvalidated; `symmetric=False` bypasses symmetry. | Restrict layout; require symmetry for S/P. |
| MDM-9 | Low | `with_ao_order` does not preserve angular metadata (1.2 rejects; 1.1 only). | Document; keep 1.2 permutation out of scope. |
| MDM-10 | Medium | `validate_1_2_angular` does not cross-check matrix convention IDs/basis representation. | Strengthen 1.2 validation in 9B. |
| API-1 | High | `MayerResult.total` for UHF/ROHF is generalized Wiberg/mixed density, not alpha+beta. | Add explicit semantics/metadata and additive `mixed`/`mayer_total` API. |
| API-2 | Medium | `analysis.calculate_mayer` is legacy-only; no one-shot v1 helper. | Add overload/router using Engine. |
| API-3 | Medium | Public submodels are only under `qe.model_v1`, not top-level. | Optional re-exports/documentation. |
| API-4 | Low | `Engine` duplicate `_prepare_from_orbitals` assignment; some state checks rely on native. | Clean up in 9B. |
| ABI-DOC-1 | High (documentation) | Current `include/qe_multiwfn_v1.h` comment still says 31 legacy + 14 additive =45. | Correct comment to 17+27=44 (no ABI change). |
| ABI-DOC-2 | Medium | Historical docs say 31+15=46; measured baseline is 29 (31 is +2). | Correct current docs; keep historical checkpoints marked historical. |

## 5. Final conformance matrix

| Area | Status | Evidence | Problem | Action |
|---|---|---|---|---|
| MDM universal | **PARTIAL** | Root model covers atoms/geometry/electronic/basis/orbitals/matrices/angular/provenance | No high-level builder; validation gaps | Phase 9B builder |
| Engine independence | **PASS** | No adapter imports; fresh probe; Engine consumes MDM | Strict validation not used | 9B strict policy |
| Memory entry | **PARTIAL** | Direct P/S probe passed without files | Full-state basis/normalization manual | 9B builder |
| NumPy entry | **PARTIAL** | Dataclasses accept arrays; direct path works | No single public array constructor | 9B API |
| Scientific-library integration | **PARTIAL** | ASE geometry-only; cclib synthetic; ORCA adapter | No PySCF adapter; cclib ORCA blocked | later adapters |
| Database entry | **PARTIAL** | MDM can be populated from arrays | No DB adapter; no test | independent adapter later |
| File entry | **PASS** | ORCA JSON/text adapters; file provenance | File is not core dependency | preserve |
| Normalization | **PARTIAL** | `attach_normalization`/report; ORCA uses it | Not automatic for arbitrary full-state MDM | 9B |
| RHF/UHF/ROHF | **PASS** | 202 tests; Phase 8C scientific PASS | none | preserve |
| Angular conventions | **PASS** | MDM 1.1 default; 1.2 f canonical RHF/UHF/ROHF | g/h and Cartesian f blocked | preserve |
| Public API | **PARTIAL** | Engine/exceptions/result classes | Legacy-only one-shot; discoverability | 9B |
| MayerResult | **PARTIAL** | Values validated in Phase 8C | `total` semantics mislabeled for open shell | 9B additive API |
| ABI | **PASS** | 17+27=44; no removed; header diff only additive | Header/comment count stale; historical 46 wrong | docs fix, no ABI change |
| Frozen compatibility | **PASS** | 17 legacy symbols; legacy header diff empty; frozen hash | none | preserve |
| Scientific integrity | **PASS** | 202/6; refs unchanged; no source change | none in 9A | preserve |

## 6. Authorization decision

**Authorized to start Phase 9B**, subject to its specification:

- implement the direct MDM builder and validation contract;
- fix/document the `MayerResult.total` open-shell semantics additively;
- correct the stale ABI count documentation;
- preserve all scientific formulas, fixtures, tolerances, ABI symbols and
  frozen artifacts;
- keep g/h, Cartesian f, PBC, post-HF, ECP/EDF and full external adapters out
  of the first 9B increment.

Phase 9B is **not started** by this checkpoint.

## 7. Hashes

Current documents:

| File | SHA-256 |
|---|---|
| `docs/PHASE9A_MDM_CONTRACT_AUDIT.md` | `b921e30dfd6b295dceb27d5a837f080cae944224df0c6ce7af077a932f34b310` |
| `docs/PHASE9A_ENGINE_SOURCE_INDEPENDENCE.md` | `71d7c56895309fbb4c3cce7d343fe598af604197ae9c9e3981ed394f3fb00c03` |
| `docs/PHASE9A_PUBLIC_API_SEMANTICS.md` | `6fe1b657c0858d288933aa3cfe7e0c08b0199692a039988cc4f5f2c3717393f6` |
| `docs/PHASE9A_ABI_RECONCILIATION.md` | `52ae8de7f6eb8b98a46a7f76cda0329782d192cac5f96363b4dff7e2fd59ab8d` |
| `docs/PHASE9A_IMPLEMENTATION_SPEC_9B.md` | `c9985fee57677db379f29945168b34ee6fd69bc1f577e5f5ef1d647cb6f2bb16` |

Artifacts:

| Item | SHA-256 |
|---|---|
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Canonical results | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| Validation manifest | `6aff745e05feee71f9c2c9a6e47a854093353d50ad0dbcb059feaa1869fb97e6` |
| ABI total | 44 = 17 legacy + 27 additive |
| Removed symbols | 0 |
| Added since frozen | 15 |

The final hash file is
`MDM_1.1_work/PHASE9A/phase9a_final_hashes.txt`.

## 8. Scope limitations

- This is an audit/specification, not an implementation.
- No high-level direct builder exists yet.
- No full-state, file-free, arbitrary-basis execution was performed; only the
  direct P/S memory probe was executed.
- PySCF/database adapters were assessed architecturally, not implemented.
- g/h, Cartesian f, PBC, post-HF, ECP/EDF and other analyses remain outside
  the validated scope.
- Historical 31/45/46 documents remain historical evidence; current measured
  counts are 17/27/44.
