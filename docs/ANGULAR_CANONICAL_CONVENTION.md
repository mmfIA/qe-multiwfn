# Angular canonical convention

## 1. Canonical real-spherical basis

The canonical MDM representation is **real spherical** with the component
order

\[
m=0,+1,-1,+2,-2,\ldots,+l,-l.
\]

For `l=3` (f) this is

```text
F0, F+1, F-1, F+2, F-2, F+3, F-3.
```

The canonical phase is the standard normalized real-spherical phase used by
the validated Multiwfn `matf` path and by PySCF `cart2sph`. Its phase signs
are all `+1`.

Canonical metadata id: `qe-mdm-real-spherical-1.0`.

## 2. Phase signs

A source convention is described by a signed tuple of length `2l+1`. For the
ORCA 6.1.1 f convention established in Phase 7A:

\[
\text{signs}_{ORCA}=(1,1,1,1,1,-1,-1).
\]

The conversion to canonical is

\[
D_f=\operatorname{diag}(1,1,1,1,1,-1,-1)
\]

in the canonical order. This is a **phase** convention, not a magnetic-label
permutation. It leaves the f-only block invariant and changes the f–s/p
cross-blocks.

## 3. Cartesian order

The canonical Cartesian order is explicit and format-independent:

```text
l=0: s
l=1: px, py, pz
l=2: xx, yy, zz, xy, xz, yz
l=3: xxx, yyy, zzz, xyy, xxy, xxz, xzz, yzz, yyz, xyz
```

The f order is the Multiwfn `s2f(3)` order
`11,12,13,17,14,15,18,19,16,20`; the exact mapping is in
`CARTESIAN_SPHERICAL_TRANSFORMS.md` of Phase 7A.

## 4. Normalization

- Canonical spherical functions are unit-normalized.
- Primitive/contraction normalization is stored separately
  (`normalization_convention`, `source_self_overlap`,
  `contraction_normalization`).
- A phase transform is only accepted when the source is normalized
  (`source_normalized` or `unit_spherical`); it does not absorb or invent a
  normalization factor.

## 5. Source identification

Every source convention records:

```text
representation, order, phase_signs, normalization,
source_program, source_version, source_format, convention_id
```

A program-specific convention is resolved in the import layer. The backend
never receives `ifiletype`, `source_program` or a source-format switch.

## 6. What is not canonical

- ORCA's f phase is not silently assumed to be canonical.
- A 1.1 model without angular metadata is `unknown`.
- A source `f` convention does not imply g/h conventions.
- A f phase transform does not imply anything about g/h.
- A change of magnetic order is not implemented in Phase 7B; it must be
  rejected rather than guessed.

## 7. Fail-closed rules

Reject, rather than guess, when:

- `l > 3` is requested for canonical metadata;
- the source representation is unknown;
- the source order differs from the canonical order;
- phase signs have the wrong length or value;
- the source normalization is not normalized;
- the object is already canonical;
- the same transform id was already recorded;
- an AO has no shell/angular metadata where required;
- a primitive-basis matrix would need a spherical transform.
