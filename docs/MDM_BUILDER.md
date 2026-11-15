# MDM Builder — public in-memory construction

**Module:** `qe_multiwfn.builder`
**Status:** implemented in `0.3.0.dev0` (Phase 9B)
**Scope:** RHF/UHF/ROHF, s/p/d/f spherical (canonical MDM 1.2 for f),
Mayer; PBC/post-HF/ECP-EDF and Cartesian f remain outside the validated scope.

## 1. Purpose

`MolecularDataBuilder` converts NumPy arrays and Python objects into a
validated `MolecularSystemV1` without reading files, importing an adapter or
calling the native library. The resulting MDM is handed directly to the
existing `Engine`:

```text
NumPy / Python objects
        -> MolecularDataBuilder
        -> MolecularSystemV1
        -> Engine.load_molecule_v1
        -> ctypes / C ABI / Fortran
        -> MayerResult
```

The Engine never learns which source produced the MDM.

## 2. Public objects

| Object | Role |
|---|---|
| `MolecularDataBuilder` | stateful builder with `set_*` methods and `build()` |
| `ShellInput` | one shell: center, l, exponents, contraction, representation, components |
| `BasisInput` | shell list (or a complete AO map), representation and normalization convention |
| `build_molecular_system(...)` | one-call constructor for arrays |
| `from_numpy` | alias of `build_molecular_system` |

All are available from `qe_multiwfn`:

```python
import qe_multiwfn as qe
```

## 3. Geometry and units

`set_geometry` accepts atomic numbers or symbols and requires an explicit
unit:

```python
builder = qe.MolecularDataBuilder()
builder.set_geometry(
    atomic_numbers=[1, 1],
    coordinates=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]],
    unit="angstrom",
)
```

- `unit` is mandatory; there is no Angstrom/Bohr guess.
- Internal `Geometry.coordinates` are always Bohr.
- The source unit and conversion factor are recorded in geometry/provenance.
- `symbols` is checked against `atomic_numbers` when both are supplied.

Electronic state:

```python
builder.set_electronic_state(
    wfntype="RHF", charge=0, multiplicity=1,
)  # UHF/ROHF require an explicit wfntype for multiplicity > 1
```

`nelectron` defaults to `sum(Z) - charge`; if supplied it is validated by the
MDM. Alpha/beta counts are derived for UHF/ROHF when omitted and checked
against Ne and multiplicity.

## 4. Basis

### 4.1 Shell input

```python
basis = qe.BasisInput(
    shells=[
        qe.ShellInput(
            center=1, l=0,
            exponents=[3.42525091, 0.62391373, 0.16885540],
            coefficients=[0.15432897, 0.53532814, 0.44463454],
            representation="cartesian",
        ),
        qe.ShellInput(
            center=2, l=0,
            exponents=[3.42525091, 0.62391373, 0.16885540],
            coefficients=[0.15432897, 0.53532814, 0.44463454],
            representation="cartesian",
        ),
    ],
    normalization_convention="source_normalized",
)
```

The builder creates:

- the global `PrimitiveTable`, one row per component per primitive;
- `Shell` records with valid primitive ranges;
- `AOFunction` records with center, shell, l, component, Multiwfn component
  code, angular type and representation;
- `BasisSet.nbasis`, `nprims` and representation.

Default component orders:

| l | spherical | Cartesian |
|---|---|---|
| 0 | `s` | `s` |
| 1 | `px, py, pz` | `px, py, pz` |
| 2 | `dz2, dxz, dyz, dx2-y2, dxy` | `xx, yy, zz, xy, xz, yz` |
| 3 | `f0, f+1, f-1, f+2, f-2, f+3, f-3` | `xxx, yyy, zzz, xyy, xxy, xxz, xzz, yzz, yyz, xyz` |

`component_order` can preserve a source order (for example ORCA's
`pz, px, py`) because the AO map, S/P/C and matrices must stay aligned.
Cartesian f and g/h are rejected; spherical f requires canonical MDM 1.2
metadata.

### 4.2 Complete AO map (direct P/S)

For a direct P/S calculation a minimal basis description is enough:

```python
basis = qe.BasisInput(
    aos=[
        qe.model_v1.AOFunction(index=1, center=1, l=0, component="s",
                               angular_type=0, multiwfn_type=1),
        qe.model_v1.AOFunction(index=2, center=2, l=0, component="s",
                               angular_type=0, multiwfn_type=1),
    ],
    nbasis=2, nprims=2,
)
```

No shells or primitives are required on this path; the Engine only needs the
AO map plus S/P. For `prepare_from_orbitals=True`, shells, primitives,
AO-shell links, component codes and normalization metadata are required.

### 4.3 Normalization

- If S is supplied and shells/primitives exist, the builder calls the existing
  `attach_normalization` implementation.
- With no S, `normalization_convention="source_normalized"` sets per-AO
  source self-overlap/contraction metadata to 1 and primitive normalization
  to 1.
- `unknown` or a non-determinable convention blocks a full-state build with
  `QeIncompleteState`; it is never guessed.
- `attach_normalization`/`normalization_report` are reused; no algorithm is
  duplicated.
- Primitive matrices are not phase-transformed.

## 5. Orbitals

```python
builder.set_orbitals(
    coefficients=C,       # (nmo, nbasis) or (nbasis, nmo)
    occupations=occ,      # (nmo,)
    energies=energies,    # optional; zeros are used as placeholders
    spins=spins,          # RHF/ROHF default "both"; UHF can infer 2*nbasis blocks
    layout="ao_orbital",  # "ao_orbital" or "orbital_ao"
)
```

- RHF: one spatial set, occupied orbitals exactly 2.0.
- UHF: alpha/beta blocks, occupations 0/1; `spins` may be explicit or
  inferred from a `2*nbasis` block.
- ROHF: one spatial set, occupations 2/1/0; Pa/Pb are derived from the
  occupancy thresholds used by the existing adapter.
- Energies are optional metadata; the current Mayer path does not use them.
- The builder copies input arrays. Mutating the original arrays after
  `build()` does not mutate the MDM.

## 6. Matrices

```python
builder.set_overlap(S)
builder.set_density(total=P, alpha=Pa, beta=Pb)
builder.set_matrix("operator", M, representation="ao_current_basis")
```

Checks:

- square shapes matching `nbasis`;
- finite values;
- symmetry (the MDM strict profile checks S/P symmetry);
- direct/open-shell consistency (`P_total = P_alpha + P_beta`);
- trace and idempotency through the strict MDM profile;
- no automatic symmetrization.

If C/occupations and S are supplied but P is absent, the builder derives the
method-appropriate density and records its origin. It does not overwrite a
caller-supplied P.

## 7. Build and Engine

```python
mdm = builder.build()

with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

`Engine.calculate_mayer(mdm)`:

- loads the MDM through `load_molecule_v1`;
- automatically enables UHF/ROHF for wfntype 1/2;
- uses `prepare_from_orbitals=True` when S/P are absent;
- applies strict validation for the direct S/P path;
- applies a full-state preflight and generated-state validation for the
  basis/orbital path.

The no-argument `engine.calculate_mayer()` is unchanged.

## 8. Executable direct example

```python
import numpy as np
import qe_multiwfn as qe
from qe_multiwfn.model_v1 import AOFunction

S = np.array([[1.0, 0.5], [0.5, 1.0]])
P = np.full((2, 2), 2.0 / 3.0)
basis = qe.BasisInput(
    aos=[
        AOFunction(index=1, center=1, l=0, component="s",
                   angular_type=0, multiwfn_type=1),
        AOFunction(index=2, center=2, l=0, component="s",
                   angular_type=0, multiwfn_type=1),
    ],
    nbasis=2, nprims=2, normalization_convention="source_normalized",
)

builder = qe.MolecularDataBuilder()
builder.set_geometry(
    atomic_numbers=[1, 1],
    coordinates=[[0, 0, 0], [0, 0, 1.4]],
    unit="bohr",
)
builder.set_electronic_state(wfntype="RHF", charge=0, multiplicity=1)
builder.set_basis(basis)
builder.set_overlap(S)
builder.set_density(total=P)
mdm = builder.build()

with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
assert result.total.shape == (2, 2)
```

## 9. Full-state example

```python
import numpy as np
import qe_multiwfn as qe

mdm = qe.build_molecular_system(
    atomic_numbers=[2],
    coordinates=[[0, 0, 0]],
    coordinate_unit="bohr",
    wfntype="RHF",
    multiplicity=1,
    basis=qe.BasisInput(
        shells=[qe.ShellInput(center=1, l=0,
                              exponents=[1.0], coefficients=[1.0])],
        normalization_convention="source_normalized",
    ),
    coefficients=np.array([[1.0]]),
    occupations=np.array([2.0]),
)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

This executes the complete `basis -> genSbas_curr -> genP -> Mayer` path with
no input file. It is an architectural example, not a scientific reference
calculation.

## 10. Errors

| Situation | Exception |
|---|---|
| missing geometry/electronic/basis | `QeIncompleteState` |
| ambiguous/missing unit | `ValueError` |
| bad shapes, non-finite arrays, spin/electron mismatch | `ValueError` |
| full-state missing shells/primitives/orbitals/normalization | `QeIncompleteState` |
| Cartesian f / g/h / post-HF / PBC | `ValueError` or `QeUnsupported` |
| direct-path scientific invariant failure | `ValueError` from strict MDM validation |
| native failure | typed `QeError` subclasses |

No invalid matrix is silently symmetrized and no unknown convention is
assumed.

## 11. Related documentation

- `MDM_VALIDATION.md`
- `PUBLIC_API.md`
- `MOLECULAR_DATA_MODEL_1.1.md`
- `MOLECULAR_DATA_MODEL_1.2.md`
- `LIMITATIONS.md`
