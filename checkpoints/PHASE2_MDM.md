# Phase 2 checkpoint — MDM consolidation

**Status: PASS**
- Atoms/geometry, charge/multiplicity, orbitals/occupations, coefficients,
  shells/primitives/contractions, S/Pα/Pβ, provenance, units and conventions
  are represented and validated.
- `normalization_convention` and per-AO normalization metadata added.
- Legacy `from_legacy`/`to_legacy` round-trip remains bit-for-bit.
- Tests: `test_mdm_1_1.py`, `test_model_v1.py`, `test_normalization.py`.
