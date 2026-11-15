# Phase 4 checkpoint — cclib and ASE adapters

**Status: PASS (with documented cclib limitation)**
- ASE adapter: geometry-only canonical model, readiness marks Mayer false;
  geometry matches ORCA `opt.xyz` for H2/H2O/benzene.
- cclib adapter: independent extraction, fail-closed on ORCA 6.1.1 parser
  errors; canonical conversion tested with cclib-like data and an explicit
  basis; without basis it is a partial model (INCOMPLETE).
- Tests: `test_ase_adapter.py`, `test_cclib_adapter.py`.
- Limitation: cclib 1.8.1 cannot parse the current ORCA 6.1.1 outputs; the
  adapter rejects rather than guessing. Matrix equivalence with cclib for
  ORCA remains pending until a parsable output/version is available.
