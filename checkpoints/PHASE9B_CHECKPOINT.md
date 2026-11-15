# Phase 9B checkpoint — universal MDM builder

**Status:** COMPLETE.
**Global verdict:** **PASS** for the Phase 9B acceptance scope, with documented
non-blocking limits.
**Phase 9C:** not started.

## 1. Initial state

| Item | Value |
|---|---|
| Tree | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Previous checkpoint | `checkpoints/PHASE9A_CHECKPOINT.md` |
| Python | `0.3.0.dev0` |
| MDM | `1.1.0` default; `1.2.0` opt-in |
| Native ABI | `0.2.0` |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Pre-9B test state | 202 Python / CTest 6/6 |
| Phase 9B initial evidence | `MDM_1.1_work/PHASE9B/` (Phase 9A checkpoint, logs, hashes) |

## 2. What was implemented

### 2.1 Public builder

New module: `python/qe_multiwfn/builder.py`.

- `MolecularDataBuilder`
  - `set_geometry`
  - `set_electronic_state`
  - `set_basis`
  - `set_orbitals`
  - `set_overlap`
  - `set_density`
  - `set_matrix`
  - `set_angular`
  - `build`
- `ShellInput`
- `BasisInput`
- `build_molecular_system`
- `from_numpy` alias

The builder supports:

- atomic numbers or symbols, explicit Angstrom/Bohr units;
- charge, multiplicity, Ne and alpha/beta counts;
- shell/primitive/AO map construction from arrays;
- spherical/Cartesian component names and Multiwfn component codes;
- source-normalized full-state normalization;
- `attach_normalization` reuse when S is available;
- RHF/UHF/ROHF occupation and density derivation;
- direct S/P matrices and extra AO operators;
- MDM 1.1 default and explicit 1.2 canonical angular metadata;
- array copies so later caller mutation does not change the MDM.

### 2.2 Engine integration

`Engine.load_molecule_v1`:

- direct S/P path now applies `validate(strict=True)`;
- UHF/ROHF explicit/full behavior preserved;
- full path has a preflight for orbitals/shells/primitives/AO map/component
  codes/normalization/coefficient dimensions;
- generated S/P is checked for dimensions, finiteness, symmetry, trace,
  method-specific idempotency and open-shell total/spin consistency.

`Engine.calculate_mayer(system=None, *, allow_open_shell=None)`:

- accepts an MDM directly;
- automatically selects UHF/ROHF when the model requires it;
- automatically uses the full path when S/P are absent;
- preserves the no-argument behavior.

`analysis.calculate_mayer` now accepts `MolecularSystemV1` as well as the
legacy `MolecularSystem`.

### 2.3 Mayer semantics

`MayerResult` gained additive properties:

- `mixed` — mixed-density/generalized-Wiberg matrix (`total` for open shell);
- `generalized_wiberg` — alias of `mixed`;
- `mayer_total` — `alpha + beta` for open shell, `total` for RHF;
- `alpha_plus_beta` — alias of `mayer_total`;
- `total_semantics` — explicit semantic string.

`Engine.calculate_mayer` metadata now includes `wavefunction_type_name` and
`total_semantics`. `total`, `alpha`, `beta` retain their prior values.

### 2.4 Readiness

`ReadinessFlags.analysis_ready["mayer"]` now accepts RHF, UHF and ROHF
(`wfntype` 0/1/2) when geometry, basis, densities, overlap and non-PBC
requirements are satisfied.

### 2.5 ABI/documentation correction

`include/qe_multiwfn_v1.h` comment corrected from the historical “31 legacy +
14 additive = 45” to the measured **17 legacy + 27 additive = 44**. No
declaration, symbol, signature or shared library changed.

## 3. Tests

| Suite | Result |
|---|---|
| Python | **215 passed, 1 warning** |
| CTest | **6/6 passed** |
| New builder tests | 13 |
| Previous suite | 202 |

Builder tests cover:

- direct NumPy/Python P/S path;
- explicit units and open-shell method selection;
- bad shapes and non-finite input;
- non-contiguous and integer/float input arrays;
- array copy/ownership;
- full-state RHF without files;
- full-state UHF/ROHF without matrices;
- canonical f MDM 1.2 metadata;
- unknown normalization rejection;
- ROHF readiness and analysis wrapper;
- strict direct Engine rejection;
- Mayer mixed/mayer-total semantics.

The one warning is the pre-existing ASE/NumPy deprecation warning.

## 4. ABI, frozen, vendor and science integrity

| Item | Result |
|---|---|
| ABI symbols | 17 legacy + 27 additive = **44** |
| Removed legacy symbols | **0** |
| New ABI symbols in 9B | **0** |
| Dev library | `e9ac3a73…` unchanged |
| Frozen library | `9560c0fc…` unchanged |
| Frozen packages | `sha256sum -c` OK |
| Vendor diff | 0 lines |
| Canonical results | `6fb8b315…` unchanged |
| Validation manifest | `6aff745e…` unchanged |
| Native rebuild | not required; no native source/library change |
| `include/qe_multiwfn_v1.h` | comment-only update |

The existing scientific routines, canonicalization, f phase, tolerances,
fixtures, frozen tree and vendor tree were not modified.

## 5. Files created/modified

Created:

- `python/qe_multiwfn/builder.py`
- `tests/python/test_builder.py`
- `docs/MDM_BUILDER.md`
- `docs/MDM_VALIDATION.md`
- `docs/PUBLIC_API.md`
- `checkpoints/PHASE9B_CHECKPOINT.md`

Modified:

- `python/qe_multiwfn/engine.py`
- `python/qe_multiwfn/results.py`
- `python/qe_multiwfn/model_v1.py` (ROHF readiness only)
- `python/qe_multiwfn/analysis/bond_order.py`
- `python/qe_multiwfn/__init__.py`
- `include/qe_multiwfn_v1.h` (comment/count only)
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/LIMITATIONS.md`
- `README.md`
- `docs/PHASE9A_ABI_RECONCILIATION.md` (note that 9B corrected the header comment)

No Fortran, C ABI implementation, native library, vendor or frozen file was
changed.

## 6. Hashes

Source/tests:

| File | SHA-256 |
|---|---|
| `python/qe_multiwfn/builder.py` | `d824c6fe057c57c68d138a48037e8ca4a29794fedafe2d442068e98cf0c2d0db` |
| `python/qe_multiwfn/engine.py` | `27d5eb3a8ff3662fc6ce1f07fb3d8de88c7fd94afa58d4395451f54ff8a96ae5` |
| `python/qe_multiwfn/results.py` | `6160a58027a2114ff1cd66645bd17d217b0b235707591bdcce09316599b4d292` |
| `python/qe_multiwfn/model_v1.py` | `ae654f1b5272ed4cef464e3b244fd33eb52622dd5b7ff81894b067c699efbebf` |
| `python/qe_multiwfn/analysis/bond_order.py` | `9798744ac0c1ebcf6e81b5716ca1ee2dbce0d279659ec7798a4e218e13f5a4c4` |
| `python/qe_multiwfn/__init__.py` | `00801456764e69250dedd28c93d753c332449c8d5bba0c01c79ccb9615e3edde` |
| `include/qe_multiwfn_v1.h` | `d99b67d41e701be9e3a41d1879011618685fe43e4cbd6d1ee1fc094b8559fb17` |
| `tests/python/test_builder.py` | `f47eb7bfaebe594a40bc7421b76d38efd11df48fd8b55508b8acb8d3600179a3` |

Documentation:

| File | SHA-256 |
|---|---|
| `docs/MDM_BUILDER.md` | `4748d3882a75d3c67511e259ffb8c2127ea0f7219ed794c410038e903683656d` |
| `docs/MDM_VALIDATION.md` | `9fce2d96a5619d2ebc725c2c262e791b35efc9b544c1398b8dee2519a26fcc58` |
| `docs/PUBLIC_API.md` | `71d4b3a2231e06de736e81777d2cc570aeaba734e3749917fe302d96df8a3167` |
| `docs/IMPLEMENTATION_STATUS.md` | `2e0bbe81eb35a16c22f5f42de4f937d6aa19a55d714a23418263b6fc92a4e87e` |
| `docs/LIMITATIONS.md` | `70f7915fd74c5e5978ba3c9980c1edc8f8267b5238170b942b4e74eb87011248` |
| `README.md` | `02513f2351af4ccc80a8799f7ea4250d6a0b2ffb9f5e0f93367dea54294bc056` |

Final artifacts:

| Item | SHA-256 |
|---|---|
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Canonical results | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| Manifest | `6aff745e05feee71f9c2c9a6e47a854093353d50ad0dbcb059feaa1869fb97e6` |

## 7. Remaining limitations

- Full-state generated S/C^TSC is not re-checked at the strict source
  `TOL_ORTHONORM`; the generated S/P trace, symmetry and idempotency checks
  use a documented native-integration electron tolerance of `1e-6`.
  Source strict validation remains `1e-8`.
- Only `source_normalized` is inferred for full state without S; Cartesian
  scaled/unnormalized conventions require S or explicit AO metadata and fail
  closed otherwise.
- PySCF/database adapters are not implemented; they are future producers of
  the same builder/MDM.
- Cartesian f, g/h, PBC, post-HF and ECP/EDF execution remain out of scope.
- No native rebuild or ABI change was needed.
- Full scientific regression remains the existing 202 tests + 13 builder
  tests; all green.

## 8. Acceptance matrix

| Criterion | Result |
|---|---|
| Public builder | **PASS** |
| Direct NumPy construction | **PASS** |
| Direct Python construction | **PASS** |
| Geometry in memory | **PASS** |
| Basis in memory | **PASS** |
| Orbitals in memory | **PASS** |
| Matrices in memory | **PASS** |
| RHF/UHF/ROHF | **PASS** |
| Integrated normalization | **PASS** (source-normalized/explicit; unknown fail-closed) |
| Strict validation | **PASS** (source direct; generated checks for full path) |
| Fail-closed policy | **PASS** |
| Engine without files | **PASS** |
| Engine origin-independent | **PASS** |
| Mayer semantics explicit | **PASS** (additive) |
| ReadinessFlags ROHF | **PASS** |
| Scientific regression | **PASS** |
| ABI compatibility | **PASS** (44 symbols; no removal) |
| Frozen preserved | **PASS** |
| `vendor/` preserved | **PASS** |
| Documentation | **PASS** |

## 9. Gate

Phase 9B is complete. Phase 9C is not started. Recommended next step: implement
PySCF/ASE/database adapters as thin producers of the already-tested builder,
then extend the same validation pattern; do not change the ABI or original
scientific routines without a new approved scope.
