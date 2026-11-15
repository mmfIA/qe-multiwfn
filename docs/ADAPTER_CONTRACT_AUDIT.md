# Adapter contract audit — Phase 10

**Scope:** PySCF, ASE, ORCA, cclib, NumPy/Python/builder, DatabaseRecord.
**Status:** adapters converge on the same MDM/Engine; no cross dependency or
subprocess.

## 1. Contract matrix

| Adapter | Source | Geometry/units | Electronic method | Basis/AO | Normalization | S/P | Standard exception | Fail-closed |
|---|---|---|---|---|---|---|---|---|
| PySCF | live `Mole`/SCF | Bohr; explicit | RHF/UHF/ROHF; DFT/post-HF rejected | `_basis` + AO permutation | s/p/d raw contraction normalization; source-normalized full | direct and full | `PyscfAdapterError` | yes |
| ASE | `Atoms` | Å → Bohr explicit | none (structural) | none | not applicable | none | `AseAdapterError` | PBC/absent electronic data |
| ORCA | JSON/text files | required source unit → Bohr; missing/unknown fail-closed | RHF/UHF/ROHF | shell/primitive/AO map | existing `attach_normalization` | direct/full | `OrcaAdapterError` | ECP/g-h/Cartesian-f unsupported |
| cclib | cclib object/file | Å → Bohr | RHF/UHF/ROHF synthetic | optional explicit basis | existing normalization | direct | `CclibAdapterError` | real ORCA 6.1.1 parser |
| NumPy/builder | arrays/objects | explicit unit | RHF/UHF/ROHF | `BasisInput`/`ShellInput` | builder + `attach_normalization` | direct/full | `ValueError`/`QeIncompleteState` | yes |
| DatabaseRecord | provider record | explicit unit | explicit method | source basis | builder | direct/full | `ValueError`/key errors | no record invention |

## 2. Contract details

### PySCF

- **Units:** `atom_coords(unit="Bohr")`, explicit.
- **Geometry/charge/spin:** extracted and validated.
- **Method:** class-based RHF/UHF/ROHF; DFT rejected.
- **Basis:** `mol._basis`; raw s/p/d contraction normalization handled.
- **AO order:** deterministic canonical permutation; S/C same permutation.
- **Angular:** p `pz,px,py`, spherical d/f canonical; f MDM 1.2.
- **Matrices:** direct S/P or full generated S/P.
- **Exceptions:** `PyscfAdapterError`.
- **Independence:** imports builder/model/angular/normalization only; no Engine,
  native, subprocess or file requirement.

### ASE

- Structural only; no method, basis, orbitals or matrices.
- PBC fail-closed.
- No PySCF dependency.
- It does not claim Mayer readiness.

### ORCA

- Existing validated adapter preserved.
- File-based entry remains optional; always returns MDM.
- Canonical f opt-in behavior preserved.
- No builder rewrite: its scientific conversion path remains unchanged.

### cclib

- Existing synthetic conversion with explicit basis preserved.
- Real ORCA 6.1.1 text parser remains blocked.
- Fail-closed; no invented data.

### NumPy / builder

- The central path.
- Same builder, normalization and validation as PySCF/DatabaseRecord.
- Direct P/S and full-state runs tested.

### DatabaseRecord

- Provider supplies `DatabaseRecord`; conversion uses the builder.
- Record ID/source remain provenance metadata.
- Structural records are not marked ready.

## 3. Standardized error categories

| Category | Existing representation |
|---|---|
| missing scientific data | `QeIncompleteState`, `ValueError` |
| unsupported method | adapter-specific `*AdapterError`, `QeUnsupported` |
| unsupported basis/angular | `Angular*Error`, `QeUnsupported` |
| unknown normalization | `QeIncompleteState`/`ValueError` |
| unknown unit | `ValueError` |
| inconsistent matrix | `ValueError`/`QeInvalidState` |
| missing provider record | `KeyError` |

Adapters use specific subclasses (`PyscfAdapterError`, `AseAdapterError`,
`OrcaAdapterError`, `CclibAdapterError`) and do not replace them with generic
messages.

## 4. Cross-dependency checks

- `Engine` does not import any adapter.
- No adapter imports `qe_multiwfn.native` or calls Fortran directly.
- No adapter uses `subprocess`, `Popen` or `os.system`.
- PySCF and ASE imports are local to their adapters; core import works without
  them.
- Builder imports no adapter.
- Database protocol imports no database engine/network.
- All scientific paths converge on `MolecularDataBuilder` or the preserved
  existing validated adapter path that produces the same MDM.

## 5. Known divergences

- ASE is geometry-only and does not use the builder for a full state.
- ORCA/cclib retain their validated legacy conversion path rather than being
  rewritten through the builder; this is intentional compatibility.
- cclib ORCA text parsing is blocked.
- PBC/DFT/post-HF/ECP are outside the native scope.
