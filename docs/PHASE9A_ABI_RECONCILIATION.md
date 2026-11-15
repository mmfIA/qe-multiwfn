# Phase 9A — ABI reconciliation

**Verdict:** **PASS for binary compatibility; documentation count was wrong.**
**Scope:** audit only. No ABI, header, library or build file was changed.

## 1. Objective evidence

Tools:

```bash
nm -D --defined-only <library> | awk '{print $3}' | sed 's/@@.*//' | grep '^qe_'
diff -u include/qe_multiwfn.h include/qe_multiwfn_v1.h   # frozen vs current
```

Measured inventories:

| Artifact | Legacy `QE_MULTIWFN_0.1.1` | Additive `QE_MULTIWFN_0.2.0` | Total |
|---|---:|---:|---:|
| Frozen 0.2.0 `9560c0fc…` | 17 | 12 | **29** |
| Before Phase 8B `8885ae9e…` | 17 | 26 | **43** |
| Current dev `e9ac3a73…` | 17 | 27 | **44** |

No non-`qe_*` function is exported; only the two version nodes appear in
`nm -D`. No duplicate symbol names were found.

## 2. Symbol-by-symbol table

`Frozen` means present in the frozen 0.2.0 library; `Dev` means present in
the current development library. Signatures are the public C declarations.

| Symbol | Frozen | Dev | Class | Signature | Compatibility |
|---|---|---|---|---|---|
| `qe_initialize` | yes | yes | legacy | `int qe_initialize(void)` | unchanged |
| `qe_finalize` | yes | yes | legacy | `int qe_finalize(void)` | unchanged |
| `qe_get_engine_state` | yes | yes | legacy | `int qe_get_engine_state(int*)` | unchanged |
| `qe_get_last_error` | yes | yes | legacy | `int qe_get_last_error(char*, int)` | unchanged |
| `qe_begin_system` | yes | yes | legacy | `int qe_begin_system(int,int,int,int)` | unchanged |
| `qe_set_atomic_data` | yes | yes | legacy | `int qe_set_atomic_data(int,const int*,const double*)` | unchanged |
| `qe_set_electronic_metadata` | yes | yes | legacy | `int qe_set_electronic_metadata(int,int,int)` | unchanged |
| `qe_set_basis_data` | yes | yes | legacy | `int qe_set_basis_data(int,int,const int*,const int*)` | unchanged |
| `qe_set_density` | yes | yes | legacy | `int qe_set_density(int,const double*,const double*,const double*)` | unchanged |
| `qe_set_overlap` | yes | yes | legacy | `int qe_set_overlap(int,const double*)` | unchanged |
| `qe_prepare_system` | yes | yes | legacy | `int qe_prepare_system(void)` | unchanged |
| `qe_release_system` | yes | yes | legacy | `int qe_release_system(void)` | unchanged |
| `qe_calculate_mayer` | yes | yes | legacy | `int qe_calculate_mayer(void)` | unchanged |
| `qe_get_mayer_dimensions` | yes | yes | legacy | `int qe_get_mayer_dimensions(int*)` | unchanged |
| `qe_get_mayer_metadata` | yes | yes | legacy | `int qe_get_mayer_metadata(int*,int*)` | unchanged |
| `qe_get_mayer_result` | yes | yes | legacy | `int qe_get_mayer_result(int,double*,int)` | unchanged |
| `qe_get_version` | yes | yes | legacy | `const char *qe_get_version(void)` | unchanged |
| `qe_v1_enable_open_shell` | yes | yes | additive | `int qe_v1_enable_open_shell(int)` | same signature; ROHF now allowed when enabled |
| `qe_v1_model_begin` | yes | yes | additive | `int qe_v1_model_begin(int,int,int,int)` | unchanged |
| `qe_v1_model_commit` | yes | yes | additive | `int qe_v1_model_commit(void)` | unchanged |
| `qe_v1_model_release` | yes | yes | additive | `int qe_v1_model_release(void)` | unchanged |
| `qe_v1_set_atoms` | yes | yes | additive | `int qe_v1_set_atoms(int,const int*,const double*,int)` | unchanged |
| `qe_v1_set_shells` | yes | yes | additive | `int qe_v1_set_shells(int,const int*,const int*,const int*,const int*,const int*)` | unchanged |
| `qe_v1_set_primitives` | yes | yes | additive | `int qe_v1_set_primitives(int,const int*,const int*,const double*,const double*,const double*,const int*)` | unchanged |
| `qe_v1_set_ao_map` | yes | yes | additive | `int qe_v1_set_ao_map(int,const int*,const int*,const int*,const int*,const int*)` | unchanged |
| `qe_v1_set_density` | yes | yes | additive | `int qe_v1_set_density(int,int,const double*,const double*,const double*)` | unchanged |
| `qe_v1_set_overlap` | yes | yes | additive | `int qe_v1_set_overlap(int,int,const double*)` | unchanged |
| `qe_v1_set_orbitals` | yes | yes | additive | `int qe_v1_set_orbitals(int,int,int,int,const double*,const double*,const double*,const int*)` | unchanged |
| `qe_v1_get_readiness` | yes | yes | additive | `int qe_v1_get_readiness(int*)` | unchanged |
| `qe_v1_set_ao_normalization` | no | yes | additive/new | `int qe_v1_set_ao_normalization(int,const double*,const double*,const int*)` | new additive |
| `qe_v1_set_angular_canonical` | no | yes | additive/new | `int qe_v1_set_angular_canonical(int)` | new additive |
| `qe_v1_generate_density` | no | yes | additive/new | `int qe_v1_generate_density(void)` | new additive |
| `qe_v1_get_generated_density_dimensions` | no | yes | additive/new | `int qe_v1_get_generated_density_dimensions(int*)` | new additive |
| `qe_v1_get_generated_density` | no | yes | additive/new | `int qe_v1_get_generated_density(int,double*,int)` | new additive |
| `qe_v1_generate_overlap` | no | yes | additive/new | `int qe_v1_generate_overlap(void)` | new additive |
| `qe_v1_generate_cartesian_overlap` | no | yes | additive/new | `int qe_v1_generate_cartesian_overlap(void)` | new additive |
| `qe_v1_get_overlap_dimensions` | no | yes | additive/new | `int qe_v1_get_overlap_dimensions(int*,int*,int*)` | new additive |
| `qe_v1_get_generated_overlap` | no | yes | additive/new | `int qe_v1_get_generated_overlap(double*,int)` | new additive |
| `qe_v1_get_generated_cartesian_overlap` | no | yes | additive/new | `int qe_v1_get_generated_cartesian_overlap(double*,int)` | new additive |
| `qe_v1_build_electronic_state` | no | yes | additive/new | `int qe_v1_build_electronic_state(void)` | new additive |
| `qe_v1_generate_primitive_density` | no | yes | additive/new | `int qe_v1_generate_primitive_density(void)` | new additive |
| `qe_v1_get_primitive_density_dimensions` | no | yes | additive/new | `int qe_v1_get_primitive_density_dimensions(int*)` | new additive |
| `qe_v1_get_generated_primitive_density` | no | yes | additive/new | `int qe_v1_get_generated_primitive_density(int,double*,int)` | new additive |
| `qe_v1_get_primitive_overlap` | no | yes | additive/new | `int qe_v1_get_primitive_overlap(double*,int)` | new additive |

Count check: 17 legacy + 12 frozen additive + 15 new additive = **44**.
Current additive total: 12 + 15 = **27**.

## 3. Symbol versions and compatibility

- All 17 legacy symbols are exported under `QE_MULTIWFN_0.1.1`.
- All 27 additive symbols are exported under `QE_MULTIWFN_0.2.0`.
- The legacy header (`include/qe_multiwfn.h`) has no diff between frozen and
  current trees; its 17 declarations and memory-layout contract are identical.
- Common v1 declarations have unchanged parameter lists and calling
  convention (`bind(C)`/C ABI). The frozen-to-current v1 header diff consists
  of added declarations and comments.
- No symbol was renamed, removed or re-signatured.
- No internal Fortran/Multiwfn symbol leaked into the dynamic table; only the
  two version nodes are non-`qe_*` exports.
- `qe_v1_enable_open_shell` has the same signature but extended behavior:
  ROHF is now accepted when enabled. This is source-compatible with frozen
  callers that only used RHF/UHF.

## 4. Why 44, 45 and 46 appeared

Historical arithmetic is inconsistent with the artifacts:

| Claim | Arithmetic | Measured reality |
|---|---|---|
| Frozen baseline | 17 + 12 = 29 | 29 |
| Before Phase 8B | “31 legacy + 14 additive = 45” | 17 + 26 = 43 |
| After Phase 8B | “31 legacy + 15 additive = 46” | 17 + 27 = 44 |

The **15 additive since frozen** is correct (12 existing + 14 added before
8B + 1 added in 8B = 27; 27 − 12 = 15). The **31 legacy** is not a measured
class: it is two greater than the measured 29-symbol frozen baseline. No
third symbol class, alias, duplicate or hidden export accounts for those two
symbols in either the frozen library, the current library or the headers.
Thus:

```text
correct baseline 29 + additive since baseline 15 = 44
historical 31 + additive 15 = 46  (31 is a +2 baseline miscount)
```

The “45” value has the same constant +2 error against the pre-8B 43. This is
a documentation/counting defect, not a missing ABI.

A separate documentation defect was present in the Phase 9A snapshot:
`include/qe_multiwfn_v1.h` said “31 legacy + 14 additive (45 total)”. The
declarations were correct; only the comment was stale. Phase 9B corrected
that comment to 17 + 27 = 44; no ABI declaration or library symbol changed.

## 5. Closure decision

- **All 17 legacy symbols present:** PASS.
- **All legacy signatures unchanged:** PASS.
- **All common additive signatures unchanged:** PASS.
- **New additive symbols:** 15, all declared and exported.
- **Removed/renamed/altered symbols:** none.
- **ABI change in Phase 9A:** none.
- **Recommendation:** do not change the ABI in Phase 9B merely to satisfy the
  old 46 count. Fix the header comment and documentation count to 17 + 27 =
  44, and add an automated symbol-inventory test so future counts come from
  `nm` plus headers, not prose.

## 6. Evidence

- `MDM_1.1_work/PHASE8C/phase8c_abi_symbols.txt`
- `MDM_1.1_work/PHASE8C/phase8c_abi_counts.txt`
- `MDM_1.1_work/PHASE8C/frozen_abi_symbols.txt`
- `MDM_1.1_work/PHASE8C/frozen_abi_counts.txt`
- `include/qe_multiwfn.h`, `include/qe_multiwfn_v1.h` (current and frozen)
- `cmake/qe_multiwfn.map`
- `nm -D --defined-only` on frozen and current libraries
