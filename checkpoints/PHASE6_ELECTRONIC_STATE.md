# Phase 6 — electronic state with the original Multiwfn core

**Status:** IMPLEMENTED / VALIDATED in `qe_multiwfn_030_dev`.
**Frozen 0.2.0:** untouched (`9560c0fc…`; packages `5e33f31f…` / `28811f71…`).
**Vendor:** byte-identical to the frozen tree (`diff -qr` empty).

## 6A — genP

- Original `genP` compiled from `vendor/.../sub.f90`; no copy/reimplementation.
- Adapter builds `CObasa`/`CObasb`/`MOocc`/`MOtype`/`nmo`/`naelec`/`nbelec`
  from the canonical orbitals. RHF, UHF and ROHF are kept separate; ROHF is
  reordered as doubly → singly → empty because the original branch assumes it.
- Validated H2/H2O/C6H6 RHF, O2 UHF, O2 ROHF, H2O/6-31G* spherical d and
  Cartesian d. `Pmax` vs reference: 0 (RHF/UHF), 1.1e-16 (ROHF).

## 6B — genPprim

- `CO(nmo,nprims)` built in the Cartesian primitive representation:
  `CO(imo,ip)=C_cart(ao(ip),imo)*primconnorm(ip)`.
- Spherical current shells are expanded to Cartesian with the original
  `gensphcartab(2,...)` (Molden/ORCA order).
- Original `genPprim` produces `Ptot_prim/Palpha_prim/Pbeta_prim` (nprims²),
  stored separately. They never replace `Ptot/Palpha/Pbeta`.
- Validation uses the raw `doSint` overlap (the original `CO` already contains
  `primconnorm`): `Tr(Pprim·Sprim)=Ne`. Observed: 2.7e-9 (H2), 3.4e-9 (H2O),
  3.6e-8 (C6H6), 2.8e-9 (UHF/ROHF), 4.0e-9 (spherical d), 4.2e-7 (Cartesian d).
- UHF/ROHF α/β primitive traces: 9/7 electrons for O2.

## 6C — genSbas

- Cartesian primitive table built from shells/primitives: `b` types are the
  Multiwfn Cartesian codes (positive), `primconnorm = coeff*normgau*scale`.
- Original `genSbas` is called for the Cartesian intermediate and validated for
  Cartesian d against the PySCF reference (max 2.1e-7, source precision).
- `genSbas` is not separately exposed in the spherical final state; it is the
  first stage of `genSbas_curr`, which is compared to the ORCA/Multiwfn S.

## 6D — genSbas_curr

- Cartesian path: `genSbas` only; validated directly.
- Spherical path: `genSbas` + original `matCar2curr`.
  - `ifiletype` is set explicitly to **9** (Molden/ORCA conversion table).
  - `isphergau=1`; `shtype = -l` for d/f, `shtypeCar = +l`; `shcon`,
    `nshell`, `nbasisCar`, `primstart/end` are populated.
  - `matCar2curr` calls `gensphcartab(2,...)`; no `read`, `pause` or prompt
    is reachable on this path.
- `S` vs reference: 3.3e-9 (ORCA spherical d); 2.3e-9–3.4e-9 for s/p;
  2.1e-7 for PySCF Cartesian d. Symmetry exact; traces match.

## 6E — full flow

`Molecular Data Model → validation → basis → orbitals → genSbas_curr → genP →
Multiwfn state → Mayer`, with **no matrices.S / matrices.P_total** in the
input model. Tests strip both matrices and still pass for all seven cases.
Full-flow Mayer vs reference: 2.7e-9 (H2), 5.5e-9 (H2O), 1.1e-8 (C6H6),
1.0e-8 (UHF/ROHF), 4.7e-9 (spherical d), 4.1e-8 (Cartesian d).

## Dependency closure (compiled, untouched)

`define`, `util`, `Bspline`, `ext/2F2`, `libreta_hybrid/{boysfunc,hrr_012345,
blockhrr_012345,eanvrr_012345,ean,libreta,ryspoly,naiveeri}`, `function`,
`sub`, `integral`, `PBC`, `bondorder`, plus the documented `hyp2F2` stub.
`function` is required because `sub` has `use functions`; `libreta`/`PBC`/ERI
are needed by the whole-object link. They are not replaced.

## Fail-closed boundaries

- Missing atoms, basis, AO map, normalization metadata, or orbitals: error.
- f/g/h angular momentum: the original genSbas/genPprim path is validated
  only for s/p/d and **blocks f+ fail-closed**. The canonical model and the
  direct 0.2.0 P/S path still support f; only the original-routine state
  construction is blocked. Audit localized the H2S/def2-TZVP failure to the
  m=±3 spherical f functions (F0..F±2 match ~3e-9; F+3/F-3 give S max 0.3451,
  Mayer 0.00430), i.e. ORCA vs Molden/Multiwfn F±3 convention/normalization,
  not a general Cartesian order error. See `MDM_1.1_work/F_GH_DIAGNOSIS.md`.
- PBC (`ifPBC>0`), post-HF (wfntype 3/4), ECP/EDF: still rejected.
- No incomplete basis and no stale result is accepted; results are cleared
  whenever P/S are replaced.
- The 31 legacy exported symbols are all present; 14 new symbols are additive.

## Blockers / next

1. f/g/h support beyond s/p/d requires the F±3 convention/normalization
   mapping (the h2s_def2tzvp f shell exposed it); f+ is blocked fail-closed
   rather than accepted with a wrong permutation. Not needed for the
   requested validation (d).
2. cclib's ORCA parser remains the MDM 1.1 blocker (separate from Phase 6).
3. PBC/post-HF/ECP-EDF remain intentionally unstarted.
4. The fractional `2F2` C path remains a documented stub; unused by
   genP/genPprim/genSbas/genSbas_curr.

## Audit hardening (final)

- Derived `Sbas_cart_saved` and primitive-density caches are invalidated on a
  new system and on basis rebuild; getters require PREPARED/RESULT_AVAILABLE,
  validity flags and matching dimensions. Regression tests:
  `tests/python/test_cache_invalidation.py` (including a same-dimension
  reload, so dimension checks alone are not relied on).
- Early fail-closed returns now set exact status codes (UNSUPPORTED,
  INVALID_ARGUMENT, INCOMPLETE_STATE, INTERNAL).
- Final suite: **155 Python passed**, **CTest 6/6**; clean source build.
  Final dev library: `8885ae9e94671956bde79e217dddcda1d8c554465a8daab2316f53cb7662da38`.
