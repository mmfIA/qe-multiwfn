# Phase 1 checkpoint — normalization

**Status: PASS**
- Added `normalization.py`: primitive normalization, same-center overlap,
  contraction self-overlap, convention inference, attach/report.
- Added 1.1 fields and schema `1.1.0`.
- Cartesian explicit/scaled and spherical source-normalized conventions.
- 12 normalization tests + 3 MDM tests pass.
- Known limitation: 5D/6D are different basis sets; no false equivalence.
