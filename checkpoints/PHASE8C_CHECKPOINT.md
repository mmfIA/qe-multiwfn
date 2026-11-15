# Phase 8C checkpoint — open-shell spherical f validation

**Status:** COMPLETE.
**Date:** 2026-11-14.
**Scope:** validation only; no production source, ABI, library, frozen artifact
or vendor change.

## Starting point

Phase 8B was preserved before Phase 8C changes:

- `../../MDM_1.1_work/PHASE8C/CHECKPOINT_PHASE8B/` (read-only)
- Initial hashes: `CHECKPOINT_PHASE8B/before_phase8c_hashes.txt`
- Initial library: `e9ac3a73…`; tests 198; CTest 6/6.

## Final state

| Item | Value |
|---|---|
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen 0.2.0 library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Python package | `0.3.0.dev0` |
| MDM | `1.2.0` supported; `1.1.0` default |
| Native ABI | `0.2.0`; **17 legacy + 27 additive = 44** |
| ABI delta in 8C | **0** |
| Python tests | **202 passed, 1 warning** |
| CTest | **6/6 passed** |
| Vendor diff | empty |
| Canonical validation results | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| Validation manifest | `6aff745e05feee71f9c2c9a6e47a854093353d50ad0dbcb059feaa1869fb97e6` |
| Frozen packages | `sha256sum -c` OK (`5e33f31f…`, `28811f71…`) |
| Rebuild | not required; no source change |

The historical "31 legacy + 15 additive = 46" count was a documentation error.
The measured inventory is 17 legacy + 27 additive = 44. The frozen baseline was
29 (17 legacy + 12 additive); 15 additive symbols have been added since, one of
them in Phase 8B. No legacy symbol was removed. See
`docs/PHASE8C_ARCHITECTURE_AUDIT.md`.

## Validated additions

### UHF: O₂/def2-TZVP, ORCA 6.1.1, canonical MDM 1.2 — PASS

- 62 basis functions, 102 primitives, two spherical f shells (14 f AOs).
- α = 9, β = 7; total 16.
- `S` max vs canonical ORCA: `5.93500075474207e-09`.
- `P_total` max: `0.0`; α/β max: `0.0`.
- `Tr(P S)/α/β`: `16.000000000000025 / 9.000000000000012 / 7.000000000000010`.
- `CᵀSC − I`: α `1.4654943925052066e-13`, β `1.3167245072054357e-13`.
- Mayer vs ORCA: total `1.160394980104229e-08`, α `1.845970043490297e-09`,
  β `6.4279244149645365e-09`.
- Mayer vs Multiwfn: α `2.933520426573466e-09`, β `4.926598240473368e-09`,
  mixed `2.451203018338788e-09`.
- Primitive trace: total `16.000000002734154`, α `8.999999997859856`,
  β `7.000000004874300`; `P_prim = P_alpha,prim + P_beta,prim` exactly.

### ROHF: O₂/def2-TZVP, ORCA 6.1.1, canonical MDM 1.2 — PASS

- Same basis/f shells; α = 9, β = 7.
- `S` max vs canonical ORCA: `5.93500075474207e-09`.
- `P_total` max: `1.1102230246251565e-16`; α/β max:
  `5.551115123125783e-17`.
- `Tr(P S)/α/β`: `16.000000000000010 / 9.000000000000005 / 7.000000000000006`.
- `CᵀSC − I`: `1.3633538742396922e-13` both channels.
- Mayer vs ORCA: total `1.161722051890024e-08`, α `2.378837404837242e-09`,
  β `6.076570802093784e-09`.
- Mayer vs Multiwfn: α `3.194906061931846e-09`, β `2.1216830514703133e-09`,
  mixed `1.073222399838869e-09`.
- Primitive trace: total `16.000000002448946`, α `8.999999998062659`,
  β `7.000000004386289`.

### f-specific checks

- Multiple f shells on different centers (AOs 25–31 and 56–62).
- Source f self-overlap minus identity ≤ `6.661338147750939e-16`; generated
  native f self-overlap minus identity ≤ `2.6645352591003757e-15`.
- Complete 7×7 f self-overlap matrices and all l-pair blocks are in
  `phase8c_angular_blocks.json`.
- All l-pair blocks are checked: `S` range `2.43e-9`–`5.94e-9`; f–f
  `3.94e-9`; `P` ≤ `1.11e-16` (UHF `P=0`).
- f–s/p/d cross-block max `0.21302211385097844` (nonzero; validated as part
  of S).
- `D_f` source-to-canonical `C` and `S` transformations exact (`0.0`).
- Non-canonical MDM 1.1 f remains rejected by the original-routine state path.

### Open-shell semantics

`MayerResult.total` is the mixed-density Mayer matrix for UHF/ROHF, not the
α+β all-electron matrix. Multiwfn's "mixed density" matrix is the correct
comparison; its "total" matrix is a different quantity. This is documented in
the Phase 8C reports.

## Tests

- `tests/python/test_open_shell_f_support.py` (new, 4 tests):
  - canonical UHF/ROHF f full flow;
  - phase/primitive density;
  - non-canonical f rejection.
- Full suite: **202 passed, 1 warning** (pre-existing ASE/NumPy warning).
- CTest: **6/6 passed**.

## Fixtures

Test fixtures:

- `tests/fixtures/phase8c/o2_uhf_def2tzvp/`
- `tests/fixtures/phase8c/o2_rohf_def2tzvp/`

Full evidence:

- `../../MDM_1.1_work/PHASE8C/fixtures/` (ORCA inputs, outputs, JSON, Molden,
  Multiwfn logs and `bndmat.txt`)
- `../../MDM_1.1_work/PHASE8C/fixture_hashes.sha256`
- `../../MDM_1.1_work/PHASE8C/phase8c_open_shell_metrics.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_angular_blocks.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_multiwfn_comparison.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_abi_symbols.txt`
- `../../MDM_1.1_work/PHASE8C/phase8c_abi_counts.txt`
- `../../MDM_1.1_work/PHASE8C/frozen_abi_symbols.txt`
- `../../MDM_1.1_work/PHASE8C/frozen_abi_counts.txt`
- `../../MDM_1.1_work/PHASE8C/phase8c_pytest.log`
- `../../MDM_1.1_work/PHASE8C/phase8c_ctest.log`
- `../../MDM_1.1_work/PHASE8C/final_hashes.txt`

## Reproduction commands

```bash
# ORCA (fixtures were generated with ORCA 6.1.1)
cd MDM_1.1_work/PHASE8C/fixtures/o2_uhf_def2tzvp
orca sp.inp > sp.out
orca_2json sp.gbw
orca_2mkl sp -molden
# Multiwfn external comparison
printf "9\n1\ny\n0\nq\n" | Multiwfn_noGUI sp.molden.input

# Tests
cd qe_multiwfn_030_dev
PYTHONPATH="$PWD/python" QE_MULTIWFN_LIBRARY="$PWD/python/libqe_multiwfn.so" \
  python3 -m pytest -q
(cd build && ctest --output-on-failure)
```

The ROHF fixture is the same commands with its own directory and `ROHF` input.

## Files changed in Phase 8C

- New tests: `tests/python/test_open_shell_f_support.py`;
  `tests/fixtures/phase8c/`.
- New docs: `docs/PHASE8C_*`.
- Current docs: `README.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`,
  `docs/IMPLEMENTATION_STATUS.md`, `docs/MOLECULAR_DATA_MODEL_1.1.md`,
  `docs/MOLECULAR_DATA_MODEL_1.2.md`,
  `docs/MDM_MIGRATION_1.1_TO_1.2.md`, and historical Phase 8B reports
  annotated as superseded.
- No Fortran, C header, Python production module, ABI, vendor, frozen artifact
  or reference result changed.

## Remaining limits

- Cartesian f and g/h remain unvalidated/blocked.
- Only the two executed f fixtures are covered.
- Other analyses are not exposed.
- PBC, post-HF, ECP/EDF, cclib ORCA 6.1.1 and thread safety remain out of
  scope.
- `generate_cartesian_overlap()` accepting f is not a correctness claim.
- `MayerResult.total` is mixed-density for open-shell systems.
