# Phase 3 checkpoint — ORCA adapter

**Status: PASS**
- RHF/UHF/ROHF reading from `sp.json` + `sp.out` + `sp.property.txt` +
  `sp.molden.input`.
- Complete basis extraction (shells, primitives, AO map), S/C/occupations,
  Pα/Pβ/Ptotal and provenance.
- Optimization geometry: `from_orca_optimization` validates `opt.xyz` against
  `sp.json` and fails closed on mismatch.
- Normalization attached and reported.
- Cartesian d/f validated with a PySCF-generated canonical fixture (ORCA
  does not emit Cartesian); spherical d/f with real ORCA.
- Tests: `test_orca_adapter.py`, `test_orca_optimization.py`,
  `test_normalization.py`, `test_mdm_1_1.py`.
