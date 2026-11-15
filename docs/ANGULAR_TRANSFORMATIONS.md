# Angular transformations in MDM 1.2

## 1. Public API

`qe_multiwfn.angular` provides:

```text
canonical_convention(l)
canonical_cartesian_convention(l)
known_source_convention(l, program, version)
phase_matrix(l, source_phase_signs, target_phase_signs=None)
apply_phase_to_coefficients(C, ao_indices, D, layout)
apply_phase_to_matrix(M, ao_indices, D)
apply_phase_to_operator(O, ao_indices, D)
canonicalize_model_angular(model, source=..., shell_signs=None,
                           transform_id=None, strict=True)
validate_1_2_angular(model)
```

The functions are pure NumPy/data operations; they do not call the native
backend.

## 2. Phase matrix

For the same magnetic order,

\[
D=\operatorname{diag}(s^{src}_i s^{tgt}_i).
\]

`phase_matrix` rejects a magnetic-order change in Phase 7B:

```text
AngularUnsupportedError: magnetic-order reordering is not implemented
```

This is deliberate: changing the order also requires an AO-map update, which
is not part of the phase-only operation.

## 3. Coefficients

For a coefficient layout `ao_orbital` (shape `(nao,nmo)`):

\[
C' = D C
\]

applied to the AO index axis. For `orbital_ao` (shape `(nmo,nao))`:

\[
C' = C D^{T}.
\]

`apply_phase_to_coefficients` validates shape, layout, index range, duplicate
indices and phase entries.

## 4. Matrices

For S, P_total, P_alpha, P_beta and AO-basis operators:

\[
M' = D M D.
\]

`apply_phase_to_matrix` and `apply_phase_to_operator` implement the same
operation. Only `representation == "ao_current_basis"` is accepted for the
model-level canonicalization.

## 5. Invariants

Because \(D^T=D\) and \(D^2=I\):

\[
C'^T S' C' = C^T S C,
\]

\[
\operatorname{Tr}(P'S') = \operatorname{Tr}(P S),
\]

\[
P'S'P' = 2P' \quad\text{(RHF)}.
\]

For UHF/ROHF, the spin densities transform with the same \(D\), and the
separate traces/occupations are preserved. The tests validate these
relations on synthetic models without invoking the backend.

## 6. Canonicalization sequence

```text
1.1 model with source metadata
        │
        ├─ identify shells/AO blocks
        ├─ validate source convention/order/phases/normalization
        ├─ build D
        ├─ transform C, S, P, P_alpha, P_beta, AO operators
        ├─ update AngularConvention/AngularObjectMetadata
        ├─ record AngularTransformRecord in Provenance
        ▼
1.2 canonical model
```

A second canonicalization of the returned model raises
`AngularAlreadyCanonicalError`. If a `transform_id` is already present in
`Provenance.angular_transforms`, the operation raises
`AngularDoubleTransformError`.

## 7. Primitive matrices

`P_total_prim` is a primitive Cartesian-basis object. A spherical phase
transform is not defined for it by this API; canonicalization with
`P_total_prim` fails closed. Primitive-level transformation, if needed, must be
specified separately.

## 8. Example

```python
from qe_multiwfn.angular import (
    known_source_convention, canonicalize_model_angular,
)

source = {
    2: known_source_convention(2, "orca", "6.1.1"),
    3: known_source_convention(3, "orca", "6.1.1"),
}
canonical = canonicalize_model_angular(model, source=source)
# canonical is schema 1.2.0; model is unchanged.
```

This is an MDM operation only. It does not modify the ORCA adapter and did not
unblock f/g/h in the backend in Phase 7B. Phase 8B later enabled canonical
spherical f; g/h remains blocked.
