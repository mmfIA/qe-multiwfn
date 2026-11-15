# Phase 5 checkpoint — genP / genSbas_curr audit

> **Historical Phase 5 checkpoint.** The “no integration yet” statements below
> describe the audit phase only. Phase 6 subsequently integrated `genP`,
> `genPprim`, `genSbas` and `genSbas_curr` for s/p/d; f/g/h remains blocked.
> Current checkpoint: `PHASE6_ELECTRONIC_STATE.md`.

**Status at the time: AUDIT COMPLETE (no integration yet)**

## genP / genPprim
- `sub.f90`; no terminal `read`/`stop` in the routines.
- Dependencies: `defvar` globals (`CObasa`, `CObasb`, `MOocc`, `MOtype`,
  `wfntype`, `imodwfn`, `nbasis`, `nmo`, `naelec`, `nbelec`), `matmul_blas`
  (BLAS), `allocatable` arrays.
- `genPprim` uses `CO`, `MOtype`, `MOocc`, `nprims`; OpenMP directives are
  present but OpenMP is disabled in the library.
- **Conclusion:** can likely be integrated non-interactively once the
  molecular/basis/orbital state is complete. Not implemented in this phase.

## genSbas / genSbas_curr
- `integral.f90`; `genSbas` for non-PBC has no terminal interaction.
- `genSbas` depends on `primstart/end`, `primconnorm`, `nbasisCar`,
  `doSint`/`doSintactual` (util `Rhm/Whm`, `type2ix/iy/iz`), BLAS-free
  quadrature.
- `genSbas_curr`: if `isphergau==0` calls `genSbas` directly (Cartesian,
  safe); if spherical calls `matCar2curr` (`sub.f90`).
- **Critical:** `matCar2curr` has an interactive fallback:
  `write(*,*) ... ; read(*,*)` when `ifiletype` is not FCH/MWFN/Molden
  (`ifiletype` 1/14/9). It also calls `gensphcartab` with program-specific
  conversion tables.
- **Conclusion:** Cartesian `genSbas_curr` can likely be integrated
  non-interactively. Spherical integration requires setting `ifiletype` to a
  supported value (Molden=9, FCH=1, MWFN=14) and validating the conversion;
  vendor sources must not be modified. Dependency closure is larger:
  `define`, `util`, `sub`, `integral` (and whatever `sub.f90`/`integral.f90`
  pull in as whole objects). A linker-map audit is required before
  integration.

## Decision
No Fortran integration in MDM 1.1/0.3.0 preparation. `genP`/`genSbas_curr`
will be integrated in a dedicated phase after the MDM/ORCA consolidation and
with non-interactive preconditions proven by tests.
