# Phase 8C — final report

**Status:** COMPLETE.
**Phase objective:** validate native spherical f beyond the closed-shell
H₂S/def2-TZVP case, with open-shell UHF/ROHF fixtures and an independent
analysis/routine audit.

## 1. What was done

1. Preserved the complete Phase 8B state before any Phase 8C work in
   `../../MDM_1.1_work/PHASE8C/CHECKPOINT_PHASE8B/` (read-only).
2. Audited the native f path, canonical angular gate, ABI, vendor/frozen
   integrity and MDM independence.
3. Built O₂/def2-TZVP open-shell fixtures with ORCA 6.1.1:
   - UHF, multiplicity 3;
   - ROHF, multiplicity 3;
   - 62 basis functions, 102 primitives, two spherical f shells.
4. Canonicalized both to MDM 1.2 and ran the complete native flow:
   `basis → genSbas_curr → genP → Mayer`, plus `genPprim`.
5. Compared alpha, beta and mixed Mayer matrices against ORCA direct matrices
   and Multiwfn 2026.11.3 standalone.
6. Added four backend tests and compact canonical fixtures to the test suite.
7. Audited all exposed scientific paths and documented the support matrix.
8. Corrected the ABI inventory documentation using measured dynamic symbols.

No Fortran, C ABI, native library, frozen artifact, vendor source, or
scientific reference result was changed. The dev library remains `e9ac…`.

## 2. Scientific verdict

| Case | Result |
|---|---|
| UHF spherical f, O₂/def2-TZVP | **PASS** |
| ROHF spherical f, O₂/def2-TZVP | **PASS** |
| S vs canonical ORCA | `5.935e-9` UHF/ROHF |
| P_total / P_alpha / P_beta | UHF `0 / 0 / 0`; ROHF `1.11e-16 / 5.55e-17 / 5.55e-17` |
| Tr(P S), α, β | 16, 9, 7 (within `3e-9`) |
| CᵀSC | `≤1.47e-13` |
| Channel idempotency | `≤1.73e-15` |
| Mayer vs ORCA (total/α/β) | UHF `1.16e-8 / 1.85e-9 / 6.43e-9`; ROHF `1.16e-8 / 2.38e-9 / 6.08e-9` |
| Mayer vs Multiwfn (α/β/mixed) | UHF `2.93e-9 / 4.93e-9 / 2.45e-9`; ROHF `3.19e-9 / 2.12e-9 / 1.07e-9` |
| Primitive trace | UHF `16.0000000027`; ROHF `16.0000000024` |
| f self-overlap / f–other cross | source `≤6.66e-16`; generated `≤2.66e-15` / `0.2130` (nonzero) |

`MayerResult.total` is the mixed-density matrix for open-shell systems; this
semantic is documented so that it is not confused with Multiwfn's all-electron
α+β total matrix.

## 3. Tests

Commands:

```bash
PYTHONPATH="$PWD/python" QE_MULTIWFN_LIBRARY="$PWD/python/libqe_multiwfn.so" \
  python3 -m pytest -q
(cd build && ctest --output-on-failure)
```

| Suite | Result |
|---|---|
| Python | **202 passed, 1 warning** |
| Previous suite | 198 passed |
| New Phase 8C tests | 4 passed |
| CTest | **6/6 passed** |
| New C ABI symbols | **none** |

The one warning is the pre-existing ASE/NumPy deprecation warning; it is not
from the new f path.

## 4. Fixtures and evidence

- `tests/fixtures/phase8c/o2_uhf_def2tzvp/`
- `tests/fixtures/phase8c/o2_rohf_def2tzvp/`
- `../../MDM_1.1_work/PHASE8C/fixtures/` (full ORCA inputs, JSON, outputs,
  Molden, Multiwfn logs and `bndmat.txt`)
- `../../MDM_1.1_work/PHASE8C/phase8c_open_shell_metrics.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_angular_blocks.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_multiwfn_comparison.json`
- `../../MDM_1.1_work/PHASE8C/fixture_hashes.sha256`
- `../../MDM_1.1_work/PHASE8C/phase8c_pytest.log`
- `../../MDM_1.1_work/PHASE8C/phase8c_ctest.log`

## 5. ABI audit result

Measured with `nm -D`:

| Class | Count |
|---|---|
| Legacy `QE_MULTIWFN_0.1.1` | 17 |
| Additive `qe_v1_*` (`QE_MULTIWFN_0.2.0`) | 27 |
| Total | **44** |

The frozen baseline is 29 (17 + 12), and 15 additive symbols have been added
since; Phase 8B added one. Earlier “31 legacy + 15 additive = 46” statements
are a counting error, not a missing symbol set. All legacy symbols are present
and Phase 8C introduced no ABI change. See `PHASE8C_ARCHITECTURE_AUDIT.md`.

## 6. Support boundary

- Validated: spherical f for canonical MDM 1.2, H₂S RHF/def2-TZVP and
  O₂ UHF/ROHF/def2-TZVP; generated S/P/α/β/primitive density/Mayer.
- Not validated: Cartesian f, g/h, other f bases/molecules/multiplicities,
  other analyses, ORCA versions other than 6.1.1 for this convention,
  PBC/post-HF/ECP/EDF, cclib ORCA parser, thread safety.
- `generate_cartesian_overlap()` accepting f is not a correctness claim; it is
  not validated against an f reference.

## 7. Integrity

| Item | Value |
|---|---|
| Phase 8B checkpoint | preserved read-only |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Vendor diff | empty |
| Canonical refs | `6fb8b315…`; validation manifest `6aff745e…` |
| ABI | 17 legacy + 27 additive = 44; 0 legacy removed |
| Source/Fortran changes | none in Phase 8C |
| Rebuild | not required; library unchanged |

## 8. Deliverables

- `PHASE8C_SCIENTIFIC_VALIDATION.md`
- `PHASE8C_UHF_F_VALIDATION.md`
- `PHASE8C_ROHF_F_VALIDATION.md`
- `PHASE8C_ANALYSIS_SUPPORT_MATRIX.md`
- `PHASE8C_ARCHITECTURE_AUDIT.md`
- `PHASE8C_LIMITATIONS.md`
- `checkpoints/PHASE8C_CHECKPOINT.md`
- Test: `tests/python/test_open_shell_f_support.py`
- Fixtures: `tests/fixtures/phase8c/`

See the checkpoint for the exact final hashes and reproduction commands.
