# Phase 8B checkpoint — native spherical f

**Status:** COMPLETE for canonical spherical f; g/h and Cartesian f blocked.

## Final state

| Item | Value |
|---|---|
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Python tests | 198 passed, 1 warning |
| CTest | 6/6 |
| ABI | 31 legacy + 15 additive = 46; no legacy removed |
| New ABI | `qe_v1_set_angular_canonical` |
| f guard | spherical f allowed only with canonical MDM 1.2; g/h rejected (`l > 3`); Cartesian f rejected |
| Scientific references | `6fb8b315…`; H₂/H₂O/C₆H₆ bitwise |
| Validation manifest | `6aff745e…` |
| Vendor | `diff -qr` empty |
| Frozen packages | `sha256sum -c` OK |
| Rebuild | dev library rebuilt; frozen 0.2.0 untouched |

## Native f validation

H₂S/def2-TZVP, RHF, canonical ORCA 6.1.1 f:

- `S` max vs canonical: `3.613623997e-9`
- `P` max: `1.734723476e-18`
- Mayer max vs direct: `7.543932812e-9`
- Mayer max vs Multiwfn standalone: `8.449582811e-9`
- `Tr(PS)`: `18.0000000063`
- `PSP−2P`: `1.825046891e-9`
- `Pprim` `(85,85)`, `Tr(Pprim Sprim)`: `18.0000000063`

## Files

- Fortran wrappers/state: `src/state/qe_molecular_state.f90`,
  `src/state/qe_state_builder.f90`, `src/state/qe_gensbas.f90`,
  `src/state/qe_genpprim.f90`, `src/bridge/qe_c_api.f90`
- Header: `include/qe_multiwfn_v1.h`
- Python: `python/qe_multiwfn/native.py`, `python/qe_multiwfn/engine.py`
- Tests: `tests/python/test_native_f_support.py`;
  `tests/python/test_orca_angular_integration.py` expectation updated
- Docs: `docs/PHASE8B_*`
- Evidence: `MDM_1.1_work/PHASE8B/`

No `vendor/`, frozen 0.2.0, original Fortran/C scientific core or reference
result was modified.
