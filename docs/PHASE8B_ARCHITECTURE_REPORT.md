> **Historical Phase 8B report.** Phase 8C extends the validated scope to
> O₂/def2-TZVP UHF/ROHF and corrects the measured ABI inventory. The ABI
> counts in this report are historical; see `PHASE8C_ARCHITECTURE_AUDIT.md`
> and `checkpoints/PHASE8C_CHECKPOINT.md` for the current state.

# Phase 8B architecture report

## Pure Python scientific library

The implementation remains a Python-importable library:

```text
Python adapters / MDM / Engine
          |
          v
C ABI (ctypes)
          |
          v
Fortran wrappers + original Multiwfn routines
```

No subprocess execution of Multiwfn, no terminal simulation, no GUI and no
menu parsing were introduced.

## Boundary

- MDM 1.1 remains the legacy/default schema.
- MDM 1.2 carries canonical angular metadata.
- The Python Engine sets the new additive C flag
  `qe_v1_set_angular_canonical` from the model's angular state.
- The Fortran basis builder accepts spherical f only for canonical data.
- g/h and Cartesian f are rejected by the basis builder.
- The direct P/S path remains available for legacy data.
- Vendor routines remain unmodified.

## C ABI

Legacy symbols: **31** (unchanged).
Additive symbols: **15** (Phase 8B adds `qe_v1_set_angular_canonical`).
Total: **46**; no legacy symbol removed.

The native library version remains `0.2.0`; the Python package remains
`0.3.0.dev0`.

## State and cache

- Canonical flag is reset with the molecular state.
- Derived overlap/primitive caches keep validity flags and are invalidated on
  a new system or basis rebuild.
- f full-flow state is built only from canonical MDM 1.2 data.
