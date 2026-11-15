# Phase 9B — implementation specification for direct MDM construction

**Status:** SPECIFICATION ONLY. Do not implement in Phase 9A.
**Goal:** make `MolecularSystemV1` directly constructible from NumPy/Python
objects and scientific libraries, without files or adapters, while preserving
legacy compatibility and all validated science.

## 1. Design principles

1. `MolecularSystemV1` remains the universal contract; do not replace it with
   an adapter-specific object.
2. A builder converts heterogeneous input into the same validated MDM that
   adapters produce.
3. File input remains supported but is only one producer of the MDM.
4. No ORCA/Molden/JSON/provenance field is mandatory for calculation.
5. The Engine consumes the MDM only; it never imports an adapter.
6. Default schema remains `1.1.0`; `1.2.0` is explicit for canonical angular
   data.
7. Missing or ambiguous data fail closed; no silent unit, order, phase or
   density assumption.
8. No ABI change is required for the first 9B increment.

## 2. Proposed public API

### 2.1 High-level builder

Add an additive module (name is a proposal, not implemented here):

```python
qe_multiwfn.build.build_molecular_system(...) -> MolecularSystemV1
```

Recommended public signature:

```python
def build_molecular_system(
    *,
    atomic_numbers=None,          # int[ncenter] or symbols
    symbols=None,                 # alternative to atomic_numbers
    coordinates,                  # (ncenter, 3)
    coordinate_unit="angstrom",  # "angstrom" or "bohr"
    charge=0,
    multiplicity=1,
    nelectron=None,
    wfntype=None,                 # "RHF" | "UHF" | "ROHF" or 0/1/2
    basis=None,                   # BasisInput/BasisSet
    overlap=None,                 # (nbasis, nbasis), optional for full state
    coefficients=None,            # orbital coefficients
    occupations=None,             # orbital occupations
    spins=None,                   # "both" or per-orbital labels
    coefficient_layout="ao_orbital",
    coefficient_representation="contracted_basis",
    density_total=None,
    density_alpha=None,
    density_beta=None,
    derive_density=True,          # only if C/occupations supplied and P absent
    angular=None,                 # explicit 1.2 source/canonical contract
    schema_version="1.1.0",
    provenance=None,              # optional; defaults to python/arrays
    strict="auto",                # auto -> strict when S/P are present
    attach_normalization=True,    # when S is available
) -> MolecularSystemV1:
    ...
```

Equivalent convenience method:

```python
MolecularSystemV1.from_arrays(..., **same_keywords) -> MolecularSystemV1
```

`build_molecular_system` and `from_arrays` must use the same implementation;
no duplicate scientific path.

### 2.2 Basis input

Proposed immutable specs:

```python
@dataclass(frozen=True)
class ShellInput:
    center: int                 # 1-based
    l: int
    exponents: Sequence[float]
    coefficients: Sequence[float]
    representation: str         # "spherical" | "cartesian"
    component_order: Sequence[str] = ()  # standard names; optional canonical default
    normalization: Sequence[float] | None = None
    contraction_normalization: float | None = None
    source_label: str | None = None

@dataclass(frozen=True)
class BasisInput:
    shells: Sequence[ShellInput]
    primitives: PrimitiveTable | array-like | None = None
    ao_map: Sequence[AOFunction] | None = None
    representation: str = "unspecified"
    ao_order: str = "canonical"
    normalization_convention: str = "source_normalized"
    nindbasis: int | None = None
```

Builder responsibilities:

- build the global `PrimitiveTable` from shells unless supplied;
- generate AOs in center/shell/component order; every AO gets a standard
  component name, `multiwfn_type`, `angular_type`, `shell_index` and
  `source_index`;
- reject mixed/unknown component codes without an explicit AO map;
- split `sp` shells explicitly (the caller supplies the s and p contractions);
- enforce one shell representation (Cartesian or spherical);
- reject `l > 3`, Cartesian f, and g/h fail-closed for the current backend;
- for full-state builds, require shells + primitives + AO map +
  normalization metadata;
- for direct P/S builds, allow a minimal basis (nbasis/nprims/AO map) as the
  current Engine does.

### 2.3 Orbital input

Accept either a fully built `OrbitalSet` or arrays:

```python
C: (nmo, nbasis) for layout="orbital_ao"
   or (nbasis, nmo) for layout="ao_orbital"
occupations: (nmo,)
spins: "both" | sequence of "both"/"alpha"/"beta"
```

Rules:

- `nmo` and coefficient shape must match the declared layout and nbasis.
- RHF: occupied orbitals exactly 2.0; all spin labels `"both"`.
- UHF: alpha and beta blocks separately or concatenated with explicit spin
  labels; occupations 0/1 per block.
- ROHF: one spatial set with occupations 2/1/0; derive Pa from occ>0.5 and Pb
  from occ>1.5, matching the ORCA adapter.
- Reject fractional occupations unless the wfntype explicitly permits them;
  current backend accepts only RHF/UHF/ROHF for Mayer.
- Never infer `multiplicity` silently from occupations if the caller supplied
  it; validate consistency.

### 2.4 Density input

Accepted combinations:

| Input | Behavior |
|---|---|
| `overlap` and `density_total` only | direct RHF/ROHF path; strict checks |
| `overlap`, `P_total`, `P_alpha`, `P_beta` | direct open-shell path; enforce P_total=Pa+Pb |
| `overlap` + orbitals/occupations, no P | derive P (RHF/UHF/ROHF) with explicit formula and `origin="derived_from_orbitals"` |
| orbitals/occupations, no S/P, full basis | full native path via `prepare_from_orbitals=True` |
| S/P plus orbitals | both stored; S/P remain authoritative for direct path |

Derivation formulas:

- RHF: `P = 2 * C_occ C_occ^T`.
- UHF: `P_alpha = C_alpha occ_alpha C_alpha^T`; beta analogous;
  `P_total = P_alpha + P_beta`.
- ROHF: `P_alpha = sum_{occ>0.5} C_i C_i^T`;
  `P_beta = sum_{occ>1.5} C_i C_i^T`; `P_total = P_alpha + P_beta`.

Checks before accepting derived P:

- `Tr(P S)=Ne`, `Tr(P_sigma S)=N_sigma`;
- RHF `P S P = 2P`; UHF/ROHF `P_sigma S P_sigma = P_sigma`;
- `P_total=Pa+Pb` for open-shell;
- symmetry and finite values;
- `C^T S C` per spin group.

Do not silently replace caller-supplied P; require an explicit `overwrite` or
omit P.

### 2.5 Normalization

- If S is supplied, `attach_normalization` must be available as a
  non-mutating or explicitly documented step.
- Builder should attach normalization automatically for supported conventions
  when `attach_normalization=True`.
- If S is not supplied but the full native path will generate it, the caller
  must provide enough normalization metadata (`source_normalized` and per-AO
  source self-overlap/contraction data) or explicitly request a
  source-normalized basis.
- Unknown convention remains `unknown` and blocks the full native path; it
  does not silently guess.
- `P_total_prim` is never phase-transformed and is not used for Mayer.

## 3. Units and ordering

- Coordinates: input Angstrom or Bohr; builder stores Bohr, records source
  unit and conversion factor in `Geometry`/`Provenance`.
- No implicit unit inference from numbers.
- Energies: `total_energy` remains optional provenance; no energy unit is used
  by Mayer. If added, record an explicit `energy_unit` and do not convert
  silently.
- AO order: builder produces a documented canonical center/shell/component
  order. If the caller supplies an AO map/order, it is authoritative; do not
  silently permute S/P/C.
- Primitive order: builder assigns shell links; `primitive_start/end` must
  match the generated table.
- Matrices are Python `(nbasis, nbasis)` in the MDM; the ABI converts to
  Fortran order.

## 4. RHF/UHF/ROHF contract

| Method | Multiplicity | Spin densities | Orbital layout |
|---|---|---|---|
| RHF | 1 | total only | one spatial set, occupancy 2 |
| UHF | ≥1, consistent with `Na−Nb` | Pa and Pb required | alpha/beta sets |
| ROHF | ≥1, consistent with `Na−Nb` | Pa and Pb required | one spatial set, occupancy 2/1/0 |
| post-HF | 3/4 | represented but rejected | not supported |

`Na = (Ne + mult − 1)//2`, `Nb = Ne − Na` only when the model is spin-resolved
and the caller did not provide counts; validate `Na−Nb = mult−1`.

## 5. Angular contract

- Default 1.1: s/p/d data can use source ordering; f is not accepted by the
  native original-routine path without canonical metadata.
- Explicit 1.2: caller supplies `AngularConvention` per relevant shell (or a
  complete canonical model). The builder must not guess ORCA phase from a file
  format.
- `known_source_convention(..., "orca", "6.1.1")` remains an optional helper;
  it is not required for other sources.
- A generic source may provide a canonical `AngularConvention` directly.
- `canonicalize_angular=True` remains explicit.
- g/h and Cartesian f remain fail-closed.
- `P_total_prim` cannot be transformed by spherical phase; fail closed.
- A 1.2 model must be fully canonical (basis, shells, orbitals, matrices) and
  pass `validate_1_2_angular`.

## 6. Provenance and source independence

- `provenance` is optional in the builder; default:
  `source_program="python"`, `source_format="arrays"`, current UTC,
  adapter `qe_multiwfn.build`.
- No ORCA fields required.
- `input_files=[]` is valid for memory/database input.
- If a source library provides version/name, store it; do not require it.
- File adapters continue to build the same model and may attach `FileRecord`
  metadata.

## 7. Engine integration

- Builder returns a fully validated `MolecularSystemV1`.
- `Engine.load_molecule_v1` remains the only Engine entry for MDM.
- Direct path: require `S/P` and `basis.aos`; call strict validation before
  native commit.
- Full path: require basis/orbitals/normalization; `prepare_from_orbitals=True`.
- Recommended additive Engine option:
  `validate="strict"|"structural"|"auto"`; default `"auto"` strict when S/P
  are supplied, structural for full-state prebuild.
- `analysis.calculate_mayer` should accept `MolecularSystemV1` and route to
  `Engine.load_molecule_v1`; keep legacy overload.
- No adapter import in Engine/build.

## 8. Error policy

| Situation | Error |
|---|---|
| Missing geometry/basis/AO map | `QeIncompleteState` / `ValueError` |
| Shape/unit/occupation inconsistency | `ValueError` (builder) |
| P/S not symmetric or wrong trace | `ValueError` / `QeInvalidState` |
| P_total != Pa+Pb | `ValueError` / `QeInvalidState` |
| Missing normalization for full state | `QeIncompleteState` |
| g/h, Cartesian f | `QeUnsupported` |
| PBC/post-HF/ECP-EDF execution | `QeUnsupported` |
| Unknown angular convention | `AngularStateError`/`AngularUnsupportedError` |
| Missing native library | existing native error |

Never infer a convention or silently coerce a matrix to make validation pass.

## 9. Compatibility

- Existing `MolecularSystem` 0.1.1 API remains unchanged.
- `MolecularSystemV1.from_legacy`/`to_legacy` remain bitwise compatible.
- Default schema remains `1.1.0`; `1.2.0` is opt-in.
- Existing ORCA/ASE/cclib adapters must be refactorable to call the builder,
  but no adapter rewrite is required in the first 9B increment.
- No ABI change is required; 9B is Python-only unless a later approved scope
  requires native support.

## 10. Test plan

### Unit tests

- coordinates Angstrom/Bohr and unit metadata;
- atomic numbers/symbols and nuclear charge;
- shell/primitive/AO map generation for s/p/d/f spherical;
- component codes and ordering;
- RHF/UHF/ROHF electronic counts and spin validation;
- C/occupation layout and density derivation;
- P/Pa/Pb trace, idempotency, P_total=Pa+Pb;
- normalization conventions and failure modes;
- angular 1.1 vs explicit 1.2; phase transform;
- provenance defaults and no-ORCA requirement;
- direct NumPy construction without files;
- fail-closed g/h, Cartesian f, PBC, post-HF, unknown conventions.

### Integration tests

- build H₂/H₂O/C₆H₆ from arrays; run direct Engine path; compare to canonical;
- build O₂ UHF/ROHF from arrays; run direct and full paths;
- build H₂S/def2-TZVP f canonical from arrays; compare to ORCA reference;
- build a geometry-only ASE-like object, then attach basis/orbitals from a
  separate source; no file;
- confirm no adapter module is imported by builder/Engine;
- file adapter output and arrays builder produce the same MDM fields for the
  same data; no separate scientific path.

### Scientific regression

- Existing 202 Python tests and CTest 6/6 remain green.
- Preserve canonical references `6fb8b315…` and manifest `6aff745e…`.
- No tolerance relaxation; no fixture/result mutation.
- `MayerResult` semantics test: RHF total, UHF/ROHF mixed/GWBO and
  alpha+beta are distinct and documented.

## 11. Acceptance criteria

1. A complete MDM can be built from NumPy/Python objects with no file and no
   adapter import.
2. `Engine.load_molecule_v1` executes direct and full paths from that MDM.
3. RHF/UHF/ROHF traces, idempotency, total/spin densities and Mayer matrices
   match existing validated fixtures.
4. Canonical spherical f and the phase transform remain opt-in and
   fail-closed.
5. Provenance is optional; no ORCA-specific field is required.
6. The same builder can be used by file adapters; no duplicated scientific
   path.
7. All existing tests and scientific references remain unchanged.
8. The public API documents `MayerResult.total` versus alpha+beta and
   mixed/GWBO without silently changing old results.
9. No ABI change and no rebuild are required for the Python-only increment.

## 12. Non-goals for 9B

- Full PySCF/ASE/cclib/database adapters.
- g/h, Cartesian f, PBC, post-HF, ECP/EDF execution.
- New analyses.
- ABI changes, native rebuild, or Multiwfn subprocess/terminal/GUI.
- Changing the already validated scientific formulas or tolerances.
