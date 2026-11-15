# Phase 8C — architecture and independence audit

**Status:** PASS for the audit. No production source or ABI change was required
in Phase 8C.

## 1. Core does not depend on ORCA or file formats

Verified by code inspection and import tracing:

| Layer | Dependency | Result |
|---|---|---|
| `qe_multiwfn.Engine` | `model_v1.MolecularSystemV1`, exceptions, native API | No ORCA/Molden/JSON import |
| `qe_multiwfn.native` | C ABI via ctypes | No parser, subprocess or file reader |
| `qe_multiwfn.model_v1` | Python dataclasses and NumPy arrays | Format-agnostic |
| `qe_multiwfn.angular` | explicit convention catalog and phase transforms | Contains the known ORCA 6.1.1 convention, but no ORCA I/O |
| `qe_multiwfn.adapters.orca` | ORCA JSON/text import only | Import boundary; not imported by Engine/core |
| Fortran wrappers | `the_mol` state and original Multiwfn routines | No JSON/Molden/ORCA parsing; no subprocess |

The `angular.py` ORCA convention is metadata, not a runtime dependency. A
producer can construct a canonical MDM from any program and pass it to
`Engine.load_molecule_v1`; the backend consumes the model, not a program name
or an input file.

The Fortran state builder explicitly does not call `readinfile`,
`init_PBC`, `init_func` or the interactive `bondorder_main`. The C ABI is the
only Python boundary. No `subprocess`, `Popen`, `os.system` or Multiwfn menu
call exists in the library path.

## 2. Angular gate

- `Engine.load_molecule_v1` sets the additive flag
  `qe_v1_set_angular_canonical` only when the model is MDM 1.2 with canonical
  `basis.angular`.
- `qe_gensbas_build` accepts spherical f only with that flag, `l = 3` and a
  spherical shell; it rejects `l > 3` and Cartesian f.
- The direct supplied-P/S path remains available and is independent of the
  basis builder.

## 3. ABI inventory — verified correction

Phase 8C re-ran the dynamic symbol inventory because the historical reports
did not agree with the built library. The verified current inventory is:

| Class | Count |
|---|---|
| Legacy `QE_MULTIWFN_0.1.1` symbols | **17** |
| Additive `QE_MULTIWFN_0.2.0` / `qe_v1_*` symbols | **27** |
| Total exported `qe_*` symbols | **44** |

Evidence:

- `nm -D --defined-only python/libqe_multiwfn.so` → 44 `qe_*` symbols;
- 17 match the legacy map node, 27 match `qe_v1_*`;
- `qe_v1_set_angular_canonical` is present;
- all 44 declarations are accounted for by `include/qe_multiwfn.h` and
  `include/qe_multiwfn_v1.h`.

Baseline comparison:

| State | Legacy / baseline | Additive v1 | Total |
|---|---|---|---|
| Frozen 0.2.0 (`9560…`) | 17 legacy | 12 | 29 |
| Before Phase 8B (`8885…`) | 17 legacy | 26 | 43 |
| Phase 8B / Phase 8C (`e9ac…`) | 17 legacy | 27 | 44 |

Thus Phase 8B added exactly one symbol (`qe_v1_set_angular_canonical`) and
removed none. The "31 legacy + 15 additive = 46" statement in earlier Phase
6/7/8 reports is **not** the measured symbol count: 15 symbols were added
since the frozen baseline, but the baseline is 29 (17 legacy + 12 v1), so the
current total is 44, not 46. This is a documentation/counting correction, not a
missing ABI symbol; all 17 legacy symbols are present.

## 4. Current ABI surface

- Version node `QE_MULTIWFN_0.1.1`: unchanged 17 legacy functions.
- Version node `QE_MULTIWFN_0.2.0`: 27 additive `qe_v1_*` functions.
- No legacy symbol removed, renamed or signature-changed.
- No new symbol was introduced in Phase 8C.
- CTest `v1_abi_c`, `mayer_c`, `uhf_abi_c`, lifecycle/memory/error tests: 6/6.

## 5. Phase 9 preparation

Phase 9 can add analyses or adapters without coupling the core to ORCA:

1. Keep `MolecularSystemV1` as the engine input contract; new producers
   should emit canonical MDM, not call backend internals.
2. Keep angular convention adaptation in `angular.py`/adapters, not in
   Fortran.
3. Add new analysis routines behind new additive `qe_v1_*` symbols only after
   a support/validation matrix entry exists.
4. Do not assume that accepting an f matrix equals validating f integrals or
   f-dependent analysis; require an executed reference comparison.

## 6. Integrity

- `vendor/` diff against the frozen source: empty.
- Frozen 0.2.0 library and packages: unchanged.
- Canonical validation results: `6fb8b315…`; manifest `6aff745e…`.
- Dev library: `e9ac3a73…` (unchanged in Phase 8C).
