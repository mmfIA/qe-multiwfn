# Phase 8C — limitations

## Validated in Phase 8C

- Spherical f (`l = 3`), canonical MDM 1.2, O₂/def2-TZVP.
- UHF: 62 basis functions, 102 primitives, 9 α + 7 β electrons; f shells on
  both O atoms; native S/P/α/β/primitive density/Mayer PASS.
- ROHF: same fixture and checks PASS.
- Multiple f shells, f–s/p/d cross-blocks, `D_f` source-to-canonical
  transformation, channel idempotency, and `CᵀSC` PASS.
- ORCA 6.1.1 direct matrices and Multiwfn 2026.11.3 standalone are external
  references only; neither is a runtime backend.

## Not validated / blocked

| Item | Status |
|---|---|
| Cartesian f native path | **BLOCKED / NOT VALIDATED**; basis builder rejects Cartesian f |
| g/h | **BLOCKED** (`l > 3`) |
| Other f bases/molecules/multiplicities | **NOT VALIDATED** |
| f in analyses other than Mayer | **NOT EXPOSED / NOT VALIDATED** |
| `generate_cartesian_overlap()` with f | **NOT VALIDATED**; it returns a 72×72 object for O₂ f but has no independent reference |
| ORCA versions other than 6.1.1 for the f convention | **NOT VALIDATED** |
| cclib ORCA 6.1.1 text parser | **BLOCKED / fail-closed** |
| PBC, post-HF, ECP/EDF | **NOT IMPLEMENTED / rejected** |
| Thread safety, multiple simultaneous engines | **NOT SUPPORTED** |
| RHF linear-dependence case (`nindbasis < nbasis`) | **NOT VALIDATED** |

## Semantics caveat

For UHF/ROHF, `MayerResult.total` is the mixed-density matrix; it is not the
α+β all-electron matrix. Multiwfn prints a separate all-electron "total" and a
"mixed density" matrix; only the latter is the correct comparison for native
`total`. The separate `.alpha` and `.beta` matrices are compared directly.

## ABI count caveat

The current library exports 44 `qe_*` symbols: 17 legacy and 27 additive v1.
The frozen baseline was 29 (17 legacy + 12 v1); 15 symbols have been added
since, and Phase 8B added one. Earlier documents that state "31 legacy + 15
additive = 46" are a counting error; no legacy symbol is missing, and Phase 8C
made no ABI change. The measured inventory is authoritative.

## Scientific boundary

Phase 8B established H₂S/def2-TZVP RHF spherical f. Phase 8C adds only
O₂/def2-TZVP UHF and ROHF. Together they are strong fixture evidence, not a
universal statement about all f basis sets or all open-shell wavefunctions.
No tolerance was relaxed, and no unavailable reference is reported as PASS.
