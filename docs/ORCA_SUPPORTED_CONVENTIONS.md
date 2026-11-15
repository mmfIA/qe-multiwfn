# Supported ORCA angular conventions

## Validated source

| Item | Value |
|---|---|
| Program | ORCA |
| Version | 6.1.1 |
| Format | `sp.json` from `orca_2json` plus optional provenance files |
| Representation | Real spherical s/p/d/f |
| f order | `F0,F+1,F-1,F+2,F-2,F+3,F-3` |
| f phase signs | `(1,1,1,1,1,-1,-1)` |
| s/p/d phase | identity relative to canonical |
| Canonical target | MDM 1.2 `qe-mdm-real-spherical-1.0` |

The f convention was established in Phase 7A for the H₂S/def2-TZVP fixture
and independently checked against PySCF standard real f cross-blocks. The
source `sp.json` f coefficients and the ORCA-written Molden coefficients are
identical for that fixture.

## Coordinate units

`CoordinateUnits` is required in `sp.json`. Missing or unknown units fail
closed (no magnitude-based inference). Explicit `Angs` and `Bohr` are
converted to the internal Bohr representation exactly once.

## What is not supported

- ORCA versions other than 6.1.1 for f canonicalization. The adapter fails
  closed rather than extrapolating.
- Cartesian f from ORCA. ORCA's validated f path is spherical `[7F]`.
- g/h angular canonicalization. No convention is inferred.
- A standalone Molden file as a direct source. `sp.molden.input` is currently
  provenance-only in this adapter.
- Any source convention not in the registered Phase 7A/7C evidence.

## Choosing the path

```python
# Legacy/source path: MDM 1.1, no angular metadata
model = from_orca_directory(path)

# Canonical path: MDM 1.2, validated ORCA 6.1.1 convention
model = from_orca_directory(path, canonicalize_angular=True)
```

The canonical path is explicit because the legacy tests and 0.1.1/1.1
compatibility require the default to remain unchanged. Phase 7D may consider
making it the default after a compatibility decision.
