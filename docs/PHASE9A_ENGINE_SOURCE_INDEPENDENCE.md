# Phase 9A — Engine source independence

**Verdict:** **PASS for origin independence; PARTIAL for contract
enforcement.**
**Scope:** audit only; no executable code was changed.

## 1. Execution flow

### Direct P/S path

```text
MDM (atoms, geometry, electronic, basis.aos, matrices.S/P)
  -> Engine.load_molecule_v1(model, prepare_from_orbitals=False)
  -> model.validate(strict=False)
  -> NativeAPI.begin_system_v1 / set_atoms_v1 / set_shells_v1 /
     set_primitives_v1 / set_ao_map_v1 / set_density_v1 / set_overlap_v1
  -> Engine.prepare() -> NativeAPI.commit_v1()
  -> NativeAPI.calculate_mayer()
  -> MayerResult
```

No adapter call is made by `Engine`; the model is only duck-typed and
consumed through its attributes.

### Full MDM-to-original-routines path

```text
MDM (canonical basis + orbitals, optionally without S/P)
  -> Engine.load_molecule_v1(..., prepare_from_orbitals=True)
  -> NativeAPI.begin_system_v1 / atoms / shells / primitives / AO map /
     normalization / orbitals
  -> Engine.prepare() -> NativeAPI.build_electronic_state_v1()
  -> original genSbas_curr + genP
  -> NativeAPI.calculate_mayer()
  -> MayerResult
```

## 2. Dependency inventory

| Location | Dependency | Classification | Finding |
|---|---|---|---|
| `engine.py:import` | `MolecularSystem` (legacy) | legitimate compatibility | Legacy `load_molecule` remains RHF/P/S-only; it does not affect v1. |
| `engine.py` | NumPy | legitimate scientific library | Array conversion only. |
| `engine.py:load_molecule_v1` | MDM attributes | legitimate contract | No ORCA/adapters/files. |
| `engine.py:load_molecule_v1` | `system.validate(strict=False)` | contract validation | Less strict than the model's strict profile; see §4. |
| `engine.py:load_molecule_v1` | `system.basis.angular.state` | legitimate angular metadata | Used only to set the additive canonical flag. |
| `engine.py` | no import from `adapters` | independent | Fresh-process probe confirmed no ORCA/ASE/cclib module is imported. |
| `native.py` | `libqe_multiwfn.so` discovery via env/package/build paths | legitimate native-library dependency | It locates the shared library, not scientific input files. |
| `native.py` | ctypes/NumPy | legitimate | C ABI boundary. |
| `results.py` | NumPy/dataclass | legitimate | Result container. |
| `analysis/bond_order.py` | legacy `MolecularSystem` | limitation | The convenience `calculate_mayer` does not accept `MolecularSystemV1`; callers must use `Engine` directly. |
| `Engine` bodies | paths, filenames, parsers, subprocesses | none found | No `subprocess`, `Popen`, `os.system`, JSON/Molden reader, or working-directory logic. |
| `NativeAPI` | environment variable `QE_MULTIWFN_LIBRARY` | legitimate configuration | Library path only; no scientific data. |
| Fortran wrappers | MDM state only | legitimate | No ORCA/JSON/Molden/file parser; `readinfile`, `bondorder_main`, `init_PBC` are not called by the exposed path. |

## 3. Fresh-process import probe

Executed in the development tree:

```text
orca_adapter_loaded False
ase_adapter_loaded False
cclib_adapter_loaded False
engine_loaded True
```

This confirms that importing/using the Engine does not import an adapter.
`source_program`, `source_format`, `FileRecord`, ORCA names and provenance are
not read by Engine.

## 4. Contract enforcement gaps

1. **Non-strict validation:** `Engine.load_molecule_v1` calls
   `system.validate(strict=False)`. It does not require positive-definite S,
   strict `Tr(PS)=Ne`, RHF idempotency, C^TSC, spin traces or
   `P_total=P_alpha+P_beta`; these are only in `validate(strict=True)`. The
   native layer may reject some cases later, but the Python contract is weaker
   than advertised.
2. **Normalization is not automatic:** the full state requires per-AO
   normalization metadata. `attach_normalization` is an explicit model
   operation and is currently called by the ORCA/cclib adapters, not by
   Engine. A direct in-memory full-state model must call it or supply
   equivalent metadata.
3. **Missing AO component metadata:** `Engine` substitutes `0` for
   `AOFunction.multiwfn_type` when absent. This is a metadata gap, not an
   ORCA dependency; the full-state Fortran path mainly checks
   center/shell/l/angular consistency.
4. **Legacy convenience API:** `analysis.calculate_mayer` accepts only the
   legacy RHF container. This does not compromise Engine independence, but it
   fragments the public entry point.
5. **Minor duplication:** `Engine.__init__` assigns
   `self._prepare_from_orbitals = False` twice. Harmless, but should be
   cleaned in a later phase.

## 5. In-memory feasibility

### Direct P/S path — verified conceptually by a non-destructive probe

A synthetic one-center MDM built entirely from Python dataclasses/NumPy was
passed to `Engine.load_molecule_v1` without any file. It completed the direct
P/S path and returned a `1x1` Mayer result. This demonstrates that no input
file or adapter is required when S/P and the AO map are already present.

The probe is an architectural check, not scientific validation: the synthetic
matrices are not a physical test case.

### Full state path — viable but currently manual

A full-state MDM can be built in memory only if the caller supplies:

- shells and primitive table;
- AO map with shell/center/l/angular types;
- per-AO normalization metadata (or attaches it);
- orbitals with coefficients/occupations/spin;
- consistent electronic counts.

The dataclasses permit this, and `from_legacy`/adapter code shows the required
shape, but there is **no public high-level builder** for arbitrary NumPy
input. A caller currently has to assemble many nested dataclasses manually.
The full-state integration tests use ORCA-derived models with matrices
stripped; they do not prove a file-free, arbitrary-source full-state build.

## 6. What would block a universal in-memory call today

| Requirement | Status |
|---|---|
| Engine accepts a Python MDM object | PASS |
| Engine accepts S/P arrays and AO map without a file | PASS (direct path probe) |
| Engine accepts arbitrary basis/orbitals without a file | PARTIAL: possible manually, no builder |
| Engine auto-normalizes a raw basis | NO: metadata must be supplied/attached |
| Engine enforces strict scientific invariants | PARTIAL: strict validation exists but is not used by `load_molecule_v1` |
| Engine knows ORCA | NO |
| Engine reads ORCA/JSON/Molden | NO |
| Engine runs subprocesses | NO |

## 7. Conclusion

The Engine is **origin-independent**: it consumes MDM attributes and the
native ABI, not an adapter or a file format. The architectural rule is already
satisfied.

It is not yet a complete **self-validating universal entry**: raw basis input
needs a builder/normalization contract and the Engine should eventually invoke
the strict validation profile (or a documented equivalent) before the native
call. Those are Phase 9B tasks, not defects to fix in this audit.

## 8. Evidence

- `python/qe_multiwfn/engine.py:144-326`
- `python/qe_multiwfn/native.py:57-90, 312-645`
- `python/qe_multiwfn/results.py:14-69`
- `python/qe_multiwfn/analysis/bond_order.py:12-27`
- `python/qe_multiwfn/model_v1.py:887-1022`
- Fresh-process import probe in this audit (no adapter modules loaded)
- Synthetic direct P/S probe (no files; `1x1` result)
- `tests/python/test_full_flow_mdm.py` (full state uses ORCA-derived basis)
