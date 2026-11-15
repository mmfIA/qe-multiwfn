# Molecular Data Model 1.2 — angular metadata

**Status:** implemented in the 0.3.0-dev Python MDM.
**Python:** `0.3.0.dev0`. **Native ABI:** `0.2.0` (unchanged).
**Default schema:** `1.1.0` (legacy-compatible).
**Canonical schema:** `1.2.0` (explicit).

## 1. Purpose

MDM 1.2 adds a traceable angular contract to the canonical model:

- real-spherical vs Cartesian representation;
- angular momentum `l`;
- magnetic-component order;
- phase signs;
- normalization convention;
- source program/version/format;
- transform state and history;
- per-object angular state (`unknown`, `source`, `canonical`).

The backend accepts canonical spherical f for RHF (Phase 8B) and UHF/ROHF
(Phase 8C); g/h remains blocked. The frozen 0.2.0 artifact is unchanged; the
ABI has one additive symbol for the canonical-angular flag.

## 2. Compatibility

`SCHEMA_VERSION` remains `1.1.0` as the constructor default. Existing 1.1
models, adapters, tests and legacy 0.1.1 paths continue unchanged.

A model is moved to `1.2.0` only by an explicit canonicalization operation:

```python
from qe_multiwfn.angular import known_source_convention, canonicalize_model_angular

source = {
    2: known_source_convention(2, "orca", "6.1.1"),
    3: known_source_convention(3, "orca", "6.1.1"),
}
canonical = canonicalize_model_angular(model, source=source)
assert canonical.schema_version == "1.2.0"
```

A 1.1 model without angular metadata is **not** silently assigned a
convention. `canonicalize_model_angular` requires an explicit source for
spherical shells with `l >= 2`.

A 1.2 model cannot be converted back with `to_legacy()` because 0.1.1 has no
place for angular phase/order metadata. `with_ao_order()` is also rejected for
1.2, to avoid changing a canonical AO order without updating all angular
metadata.

## 3. New public objects

### AngularConvention (per shell)

Located in `qe_multiwfn.angular`:

```text
l, representation, magnetic_order, phase_signs, normalization,
cartesian_order, convention_id, source_program, source_version,
source_format, state, transform_id
```

`state` is one of `unknown`, `source`, `canonical`.

### AngularBasisMetadata

Global basis-level contract: representation (`spherical_real`, `cartesian`,
`mixed`, `unknown`), magnetic-order policy, phase convention, normalization,
convention id, state and last transform id.

### AngularObjectMetadata

State/provenance attached to coefficients and matrices:

```text
state, convention_id, source_convention_id, transform_id
```

### AngularTransformRecord

Immutable history entry stored in `Provenance.angular_transforms`:

```text
transform_id, source_convention_id, canonical_convention_id, l,
shell_indices, phase_signs, applied_to, input_hashes, output_hashes
```

## 4. Fields added to existing objects

| Object | New optional field | Meaning |
|---|---|---|
| `Shell` | `angular: AngularConvention` | authoritative per-shell angular convention |
| `BasisSet` | `angular: AngularBasisMetadata` | global basis angular contract |
| `OrbitalSet` | `angular: AngularObjectMetadata` | state of MO coefficients |
| `MatrixRecord` | `angular: AngularObjectMetadata` | state of S, P or operator matrix |
| `Provenance` | `angular_transforms: list[AngularTransformRecord]` | immutable transform history |

`AOFunction` deliberately has no duplicated phase field: the shell metadata is
authoritative, while `component`, `multiwfn_type`, `source_label` and
`source_index` continue to describe the AO map. After canonicalization,
`component`/`multiwfn_type` are the canonical labels; source labels remain in
`source_label`/`source_index`.

## 5. Canonical convention

The canonical spherical convention is:

- representation: `spherical_real`;
- order: `m=0,+1,-1,+2,-2,...`;
- phase signs: all `+1`;
- normalization: `unit_spherical`;
- convention id: `qe-mdm-real-spherical-1.0`.

The canonical Cartesian order is:

```text
s; px,py,pz; xx,yy,zz,xy,xz,yz;
xxx,yyy,zzz,xyy,xxy,xxz,xzz,yzz,yyz,xyz
```

The f reference phase is compatible with Multiwfn's `matf`/PySCF standard
real harmonics. ORCA's Phase 7A f source is represented by the explicit phase
signs `(1,1,1,1,1,-1,-1)`; this is metadata, not a backend hard-code.

## 6. Validation

- `1.1.0` models: existing validation unchanged; angular metadata is optional
  and, if present, is checked for internal consistency.
- `1.2.0` models: require `basis.angular` in canonical state, canonical
  metadata for every shell, and canonical metadata for orbitals/S/P when
  those objects are present.
- Unknown representation/order/phase/state is rejected.
- `l > 3` is unsupported in Phase 7B; no g/h generalization.
- Primitive-basis matrices (`P_total_prim`) are not transformed by the
  spherical phase operation; canonicalization with such a matrix fails closed.

## 7. Serialization

The existing `summary()` exposes the angular block. `Provenance.to_dict()`
includes `angular_transforms`. No new file serialization format is introduced.

## 8. Limitations

- The ORCA/cclib adapters are **not** modified in Phase 7B; they do not yet
  emit 1.2 angular metadata.
- The native backend supports canonical spherical f for RHF/UHF/ROHF on the
  executed fixtures; g/h remains blocked and Cartesian f is rejected.
- Magnetic-order changes are declared in the contract but rejected by the
  Phase 7B transform implementation; only phase changes in the same order are
  implemented.
- g/h angular conventions are not investigated or generalized.
