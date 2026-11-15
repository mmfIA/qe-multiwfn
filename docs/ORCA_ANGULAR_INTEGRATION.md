# ORCA angular integration (Phase 7C)

## 1. Entry point

The ORCA JSON adapter now exposes an explicit canonicalization option:

```python
from qe_multiwfn.adapters.orca import from_orca_directory

source = from_orca_directory("orca/df/h2s_def2tzvp")                       # MDM 1.1
canonical = from_orca_directory(
    "orca/df/h2s_def2tzvp", canonicalize_angular=True
)                                                                         # MDM 1.2
```

The same keyword is available on:

- `from_orca_directory`
- `from_orca_json`
- `from_orca_uhf_directory`
- `from_orca_uhf_json`
- `from_orca_rohf_directory`
- `from_orca_rohf_json`
- `from_orca_optimization`

`canonicalize_angular=False` is the default for backward compatibility with
the 0.3.0-dev legacy paths. The canonical path is explicit and returns a new
MDM 1.2 model; the source model is not mutated.

## 2. When canonicalization happens

The adapter performs it:

1. after reading geometry, basis, AO labels, S and MO coefficients;
2. after constructing and validating the source MDM;
3. after `attach_normalization`;
4. before the final strict validation and before returning the model.

No phase/sign rule is inserted into Fortran, the C ABI or the backend.

## 3. Source conventions

The only registered source convention is the ORCA JSON convention validated
in Phase 7A for ORCA **6.1.1**:

| l | ORCA source order | Source phase |
|---|---|---|
| 0 | canonical | `+1` |
| 1 | `m=0,+1,-1` | `+1,+1,+1` |
| 2 | `m=0,+1,-1,+2,-2` | all `+1` |
| 3 | `m=0,+1,-1,+2,-2,+3,-3` | `+1,+1,+1,+1,+1,-1,-1` |

The f phase is the Phase 7A result. The source `sp.json` f coefficients and
the ORCA-written Molden f coefficients were found to be identical; the phase
difference is with the standard/Multiwfn representation used by the MDM.

## 4. Canonical result

With `canonicalize_angular=True`, the returned model has:

- `schema_version == "1.2.0"`;
- `basis.angular` and per-shell `angular` metadata in canonical state;
- `OrbitalSet.angular`, `MatrixRecord.angular` for S/P;
- `Provenance.angular_transforms` with the applied transform.

The f phase is applied consistently to C, S, P_total, P_alpha and P_beta:

\[
C'=D_f C,\qquad S'=D_f S D_f,\qquad P'=D_f P D_f.
\]

## 5. Fail-closed behavior

`canonicalize_angular=True` fails with `OrcaAdapterError` when:

- the source version is not ORCA 6.1.1;
- an f shell is present but `sp.out` is absent/unknown;
- f is Cartesian (the validated convention is spherical f);
- a g/h shell is present (not generalized);
- the canonicalization API rejects the source metadata.

The legacy default path (`canonicalize_angular=False`) remains available and
returns the source MDM 1.1 model unchanged.

## 6. Backend boundary

Canonicalization is an MDM operation. Phase 8B allows the original-routine
backend to consume canonical spherical f; g/h remains blocked and Cartesian
f is rejected. The non-canonical 1.1 f path remains fail-closed for overlap
generation.

See `ORCA_SUPPORTED_CONVENTIONS.md` and `PHASE7C_VALIDATION.md`.
