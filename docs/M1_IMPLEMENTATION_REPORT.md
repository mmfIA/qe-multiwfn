# M1 — Molecular Data Model 1.0 — Implementation report

> **Historical snapshot (0.2.0/M1, schema 1.0).** This report records the
> frozen M1 state. It is not the current 0.3.0-dev status: the current tree
> has MDM 1.1, Phase 6, 45 ABI symbols, 155 Python tests and 6/6 CTest.
> Current status: `docs/IMPLEMENTATION_STATUS.md`.

**Date (UTC):** 2026-11-14
**Status:** **PASS** for the implemented scope (RHF s/p Mayer path)
**Library:** QE-Multiwfn 0.2.0 + v1 layer (schema `1.0.0`)
**Library artifact SHA-256:** `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72`
**Host:** Ubuntu 26.04.1, GNU Fortran/GCC 15.2.0, CMake 4.2.3,
OpenBLAS, Python 3.12.16, NumPy 2.5.4.

This report covers Phases 1–8 of the execution plan. It distinguishes what
was **implemented and tested**, what was **rejected intentionally**, and what
remains **planned**.

---

## 1. Executive summary

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Critical audit/correction of the Model 1.0 specification | PASS |
| 2 | Python `MolecularSystemV1` + 0.1.1 compatibility | PASS |
| 3 | Fortran v1 storage + additive `qe_v1_*` ABI | PASS |
| 4 | Shells, primitives, exponents, contraction coefficients, AO map | PASS (s/p + spherical/Cartesian d/f) |
| 5 | Wavefunction, S/P validation and adapter-side P preparation | PASS |
| 6 | ORCA 6.1.1 JSON adapter | PASS (RHF, s/p) |
| 7 | Scientific verification H₂/H₂O/C₆H₆ | PASS (bit-for-bit) |
| 8 | UHF/ROHF opt-in + preparation for post-HF/other analyses | PASS (UHF/ROHF validated; post-HF planned) |

The v1 path reproduces the previously validated Mayer matrices **bit-for-bit**.
Spherical d/f support was added and validated with H₂O/6-31G* and
H₂S/def2-TZVP (QE × Multiwfn ≤ 4.55e−9; QE × ORCA ≤ 8.88e−16).
UHF and ROHF are available as explicit opt-ins and were validated with
O₂/STO-3G (UHF: QE α/β × Multiwfn α/β ≤ 2.89e−15, QE (α+β) × ORCA ≤
1.33e−15; ROHF: QE α/β × Multiwfn α/β ≤ 2.22e−15, QE (α+β) × ORCA ≤
6.66e−16).
The legacy 0.1.1 API, the original `calcMayerbndord` call and all scientific
tolerances are unchanged.

---

## 2. What was implemented

### 2.1 Python canonical model — `python/qe_multiwfn/model_v1.py`

- `MolecularSystemV1` with `Provenance`, `Atoms`, `Geometry`,
  `ElectronicState`, `Shell`, `PrimitiveTable`, `AOFunction`, `BasisSet`,
  `OrbitalSet`, `Wavefunction`, `MatrixRecord`, `MatrixBundle`,
  `CoreCorrection`, `Periodicity`, `ReadinessFlags`.
- `from_legacy` / `to_legacy`: exact 0.1.1 compatibility (arrays bit-for-bit).
- Strict validation: `CᵀSC`, `Tr(PS)`, `PSP=2P`, symmetry, positivity;
  `PASS/FAIL/INCOMPLETE` report via `wavefunction_report`.
- AO permutation (`with_ao_order`) applied consistently to S/P/C and AO map.
- Adapter-side `derive_rhf_density` with explicit provenance.
- Explicit rejection of states not representable in 0.1.1.

### 2.2 Fortran v1 storage — `qe_molecular_state.f90`, `qe_state_builder.f90`

- Optional shell table, primitive table (center, component type, exponent,
  contraction coefficient, normalization, shell index), AO map (center,
  shell, Multiwfn component code, angular type, source index) and orbital
  data.
- Consistency checks that are additive: missing v1 data never blocks Mayer.
- The AO map also fills the legacy `basis_center`/`basis_type` arrays.
- `Tr(PS)`, `PSP=2P`, symmetry and completeness checks preserved.

### 2.3 Additive C ABI — `include/qe_multiwfn_v1.h`, `qe_c_api.f90`

11 new symbols:

```
qe_v1_model_begin      qe_v1_model_commit     qe_v1_model_release
qe_v1_set_atoms        qe_v1_set_shells       qe_v1_set_primitives
qe_v1_set_ao_map       qe_v1_set_density      qe_v1_set_overlap
qe_v1_set_orbitals     qe_v1_get_readiness
```

The 17 original `qe_*` symbols are unchanged. `ldd -r` is clean; the
library exports 28 `qe_*`/`qe_v1_*` symbols and RUNPATH `$ORIGIN`.

### 2.4 Python v1 execution — `Engine.load_molecule_v1`

- Sends atoms/geometry, electronic metadata, shells, primitives, AO map,
  S/P, and optional orbitals through the v1 ABI.
- `prepare()` calls `qe_v1_model_commit`; `release_molecule()` calls the v1
  release. The legacy path is untouched.
- Readiness bitmask exposed by the native API.

### 2.5 ORCA adapter — `python/qe_multiwfn/adapters/orca.py`

- Reads ORCA 6.x `sp.json` (with `sp.json.conf` requesting S, MOs and 1e
  integrals) and optional `sp.out`/`sp.molden.input`/`sp.property.txt`.
- Builds shells, primitive table (component-level), AO map with Multiwfn
  component codes for s/p, S and C/occupations/energies.
- Derives `P = 2 C_occ C_occᵀ` for closed-shell RHF, records provenance.
- Rejects non-RHF and d/f explicitly (no silent conversion).

### 2.6 Scientific verification — `QE-Multiwfn-validation/verify_model_v1_flow.py`

Runs ORCA → v1 model → v1 ABI → `calcMayerbndord` and compares against the
P0 baseline without modifying canonical artifacts.

---

## 3. Test results

| Suite | Result |
|---|---|
| CTest | **6/6 PASS** (4 legacy + `v1_abi_c` + `uhf_abi_c`) |
| Python library | **94/94 PASS** (29 legacy + 27 model + 26 ORCA/d-f + 5 UHF + 4 ROHF + 3 Cartesian) |
| Validation pipeline | **223/223 PASS** |
| Examples | 3/3 PASS |
| v1 scientific flow | **PASS** for H₂, H₂O, C₆H₆ |
| Vendor integrity | **74/74** byte-identical |

### 3.1 Scientific results (v1 path)

| Molecule | `max|QE − baseline|` | `max|QE − Multiwfn|` | Mayer bitwise |
|---|---|---|---|
| H₂ | 0.0 | 1.33e−15 | yes |
| H₂O | 0.0 | 3.61e−9 | yes |
| C₆H₆ | 0.0 | 4.98e−9 | yes |

The S and P matrices from the adapter are also bit-identical to the P0
baseline. The legacy engine path (`model.to_legacy()` → `Engine`) reproduces
the same matrices with the new build.

### 3.1.1 Spherical d/f verification

Two new reference systems were generated with ORCA 6.1.1 and validated
against a fresh Multiwfn 2026.11.3 standalone run:

| System | nbasis | nprims | d/f | QE × Multiwfn | QE × ORCA |
|---|---|---|---|---|---|
| H₂O / 6-31G* | 18 | 35 | 5D | 2.90e−9 | 4.44e−16 |
| H₂S / def2-TZVP | 49 | 79 | 5D + 7F | 4.55e−9 | 8.88e−16 |

ORCA's spherical component order matches the Multiwfn internal order
(d: dz2,dxz,dyz,dx2y2,dxy → −5..−1; f: f0,f+1,f−1,f+2,f−2,f+3,f−3 → −12..−6).
Cartesian d/f is also implemented. ORCA 6.1.1 cannot emit Cartesian 6D/10F,
so the Cartesian path was validated with a real PySCF 2.15.0 RHF/6-31G*
wavefunction (`mol.cart=True`) converted to the canonical ORCA-like schema:
19 basis functions, 36 GTFs, d codes `5,8,9,6,10,7`, QE × Multiwfn
`1.20e−9`. Evidence:
`QE-Multiwfn-validation/verify_df_flow.py`,
`QE-Multiwfn-validation/verify_cartesian_flow.py`,
`M1_work_20261114_160216/df_flow_final/` and
`M1_work_20261114_160216/cartesian_flow_final/`.

### 3.1.2 UHF verification (opt-in)

The UHF path is **disabled by default**. `load_molecule_v1(..., allow_open_shell=True)`
(or `qe_v1_enable_open_shell(1)`) enables only UHF (`wfntype=1`); ROHF and
post-HF remain rejected. The O₂/STO-3G reference was generated with ORCA 6.1.1
and compared with a fresh Multiwfn 2026.11.3 standalone run:

| Quantity | Result |
|---|---|
| QE α × Multiwfn α | 1.22e−15 |
| QE β × Multiwfn β | 2.89e−15 |
| QE total (Wiberg/mixed) × Multiwfn mixed | 3.16e−9 |
| QE (α+β) × Multiwfn all-electron | 4.00e−15 |
| QE (α+β) × ORCA `&BondOrders` | 1.33e−15 |

UHF without the explicit flag is rejected with `QE_ERROR_UNSUPPORTED`.
Evidence: `QE-Multiwfn-validation/verify_uhf_flow.py` and
`M1_work_20261114_160216/uhf_flow_final/`.

### 3.1.3 ROHF verification (opt-in)

ROHF uses the same explicit flag (`allow_open_shell=True` /
`qe_v1_enable_open_shell(1)`). Densities follow the Multiwfn convention:
P_alpha = Σ_{occ>0} C_i C_iᵀ and P_beta = Σ_{occ=2} C_i C_iᵀ. O₂/STO-3G:

| Quantity | Result |
|---|---|
| QE α × Multiwfn α | 2.22e−16 |
| QE β × Multiwfn β | 2.22e−15 |
| QE total (Wiberg/mixed) × Multiwfn mixed | 2.22e−15 |
| QE (α+β) × Multiwfn all-electron | 2.44e−15 |
| QE (α+β) × ORCA `&BondOrders` | 6.66e−16 |

Post-HF remains rejected even with the flag. Evidence:
`QE-Multiwfn-validation/verify_rohf_flow.py` and
`M1_work_20261114_160216/rohf_flow_final/`.

### 3.2 Legacy pipeline with the final build

The full validation pipeline (`run_validation.py`) was re-run for H₂, H₂O and
C₆H₆ with the final v1-enabled build and fresh Multiwfn executions:

- Global status: **PASS**; per molecule 34/34 required checks PASS;
- Mayer matrices are **bitwise identical** to the P0 baseline;
- QE × Multiwfn `max|Δ|`: 1.33e−15 / 3.61e−9 / 4.98e−9.

### 3.3 Packaged build verification

The `qe_multiwfn-0.2.0-fullsource.tar.gz` package was extracted into a clean
temporary directory and built from scratch:

- `scripts/clean.sh`, `scripts/configure.sh`, `scripts/build.sh`: OK;
- CTest: **6/6**;
- Python: **56 passed, 4 skipped** (the ORCA/d-f, UHF, ROHF and Cartesian
  test modules are skipped when the validation fixtures are not present in
  the package; the full 94-test run was executed in the project tree with the
  fixtures);
- the temporary build `.so` hash is path-dependent and differs from the
  in-tree artifact (`9560c0fc…`); functionality and tests are identical. The
  exact clean-build hash is recorded in the 0.2.0 closing audit report. No
  claim of bit-reproducible binaries across different build directories is
  made.

---

## 4. Corrections made during Phase 1 audit

| # | Finding | Correction |
|---|---|---|
| A1 | `basis_type` ambiguity (header vs adapter vs Multiwfn) | Model separates `multiwfn_type` (component: 1=S, 2..4=p) from `angular_type` (0=s, 1=p, ...); adapter uses the real codes |
| A2 | Tolerance table did not match the code | Aligned to the strict audit profile (1e−10 / 1e−8 / 1e−6·scale / 1e−10) |
| A3 | AO ordering unspecified | Preserve source order within contiguous center blocks; `source_index` recorded; permutation helper provided |
| A4 | Compatibility asserted without checklist | Added the 7-point compatibility demonstration |
| A5 | Risk of `to_legacy` accepting non-representable states | Explicit blockers and `ValueError` |
| A6 | Mayer dependency closure | Confirmed in the original source: P, S, basstart, basend, ncenter, nbasis, wfntype |

---

## 5. Files added / modified

### Added

- `docs/MOLECULAR_DATA_MODEL_1.0.md`
- `docs/EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md`
- `docs/M1_IMPLEMENTATION_REPORT.md`
- `RELEASE_MANIFEST_0.2.0.txt`
- `include/qe_multiwfn_v1.h`
- `python/qe_multiwfn/model_v1.py`
- `python/qe_multiwfn/adapters/__init__.py`
- `python/qe_multiwfn/adapters/orca.py`
- `tests/native/test_v1_abi.c`
- `tests/python/test_model_v1.py`
- `tests/python/test_orca_adapter.py` (s/p + spherical d/f)
- `tests/python/test_uhf.py` (UHF opt-in)
- `tests/python/test_rohf.py` (ROHF opt-in)
- `tests/python/test_cartesian_df.py` (Cartesian d/f)
- `tests/native/test_uhf_abi.c` (open-shell flag semantics)
- `QE-Multiwfn-validation/verify_model_v1_flow.py`
- `QE-Multiwfn-validation/verify_df_flow.py`
- `QE-Multiwfn-validation/verify_uhf_flow.py`
- `QE-Multiwfn-validation/verify_rohf_flow.py`
- `QE-Multiwfn-validation/verify_cartesian_flow.py`
- `QE-Multiwfn-validation/fixtures/cartesian/` and `cartesian_results/`
- `QE-Multiwfn-validation/orca/rohf/` and `rohf_results/` (ROHF fixtures)
- `QE-Multiwfn-validation/orca/uhf/` and `uhf_results/` (UHF fixtures)
- `QE-Multiwfn-validation/orca/df/` and `df_results/` (d/f fixtures)

### Modified (additive)

- `python/qe_multiwfn/__init__.py` (exports)
- `python/qe_multiwfn/native.py` (v1 ctypes bindings)
- `python/qe_multiwfn/engine.py` (`load_molecule_v1`, v1 lifecycle)
- `src/state/qe_molecular_state.f90` (v1 fields)
- `src/state/qe_state_builder.f90` (v1 setters/validation)
- `src/bridge/qe_c_api.f90` (v1 ABI)
- `src/bridge/qe_memory.f90` (real 1-D pointer/finite helpers)
- `tests/CMakeLists.txt` (v1 C test)
- `docs/IMPLEMENTATION_STATUS.md`, `docs/LIMITATIONS.md`,
  `docs/RELEASE_NOTES_0.1.1.md`, `docs/BUILD_VERIFICATION_0.1.1.md`,
  `README.md`

`vendor/` was not modified.

---

## 6. Reproduction commands

```bash
cd qe_multiwfn_src
./scripts/clean.sh
./scripts/configure.sh Release build
./scripts/build.sh build 4
./scripts/test.sh build

cd ../QE-Multiwfn-validation
export QE_ROOT=../qe_multiwfn_src
export QE_MULTIWFN_LIBRARY=../qe_multiwfn_src/build/libqe_multiwfn.so
python3 verify_model_v1_flow.py \
  --qe-root "$QE_ROOT" --orca-data ./orca \
  --output ../M1_work_20261114_160216/v1_flow_final
```

---

## 7. Real limitations and pending items

| Item | Status | Required work |
|---|---|---|
| Cartesian d/f from ORCA | N/A | ORCA does not emit Cartesian; adapter path validated with PySCF fixture |
| Post-HF execution | REJECTED (planned) | Audit `genP`; add multiconfigurational reference data |
| PBC | NOT IMPLEMENTED | Modeled only; v1 engine rejects ifPBC>0 |
| ECP/EDF execution | NOT IMPLEMENTED | Modeled only; v1 engine rejects incomplete ECP/EDF |
| `genP`/`genSbas_curr` | NOT CALLED | S/P are supplied/derived by adapters with provenance |
| Native readers (FCH/WFN/WFX/Molden/MWFN) | NOT IMPLEMENTED | Separate adapters with per-format tests |
| Multiple engines/thread safety | NOT IMPLEMENTED | Global Multiwfn state |
| Other analyses (Hirshfeld, MBIS, ...) | NOT IMPLEMENTED | See extension plan |
| Library version bump (0.1.1 → 0.2.0) | DONE (D7) | New SONAME/symbol node; legacy 0.1.1 symbols preserved |

No functionality above is claimed as implemented. The implemented scope is
the RHF s/p Mayer path with the canonical model and the additive ABI.

---

## 8. Definition of done (checked)

- [x] code and documentation updated;
- [x] clean build works on the target host;
- [x] applicable tests pass (6 C, 94 Python, 223 pipeline);
- [x] reproducible evidence (hashes, logs, bitwise comparisons);
- [x] remaining limitations listed;
- [x] original Multiwfn sources intact (74/74);
- [x] no tolerance relaxed;
- [x] PASS/FAIL/INCOMPLETE distinguished.
