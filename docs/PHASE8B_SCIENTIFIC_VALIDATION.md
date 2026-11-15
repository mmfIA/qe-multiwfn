> **Historical Phase 8B report.** Phase 8C extends the validated scope to
> O₂/def2-TZVP UHF/ROHF and corrects the measured ABI inventory. The ABI
> counts in this report are historical; see `PHASE8C_ARCHITECTURE_AUDIT.md`
> and `checkpoints/PHASE8C_CHECKPOINT.md` for the current state.

# Phase 8B scientific validation

## Main case: H₂S/def2-TZVP, ORCA 6.1.1, RHF, spherical f

Source: ORCA 6.1.1 `sp.json`, canonicalized with MDM 1.2 (`D_f`).
Backend: original `genSbas_curr`, `genP`, `genPprim`, `matCar2curr`,
`calcMayerbndord`.

| Quantity | Value |
|---|---|
| `S` max vs canonical supplied S | `3.6136239972561768e-09` |
| `P` max vs canonical supplied P | `1.734723475976807e-18` |
| Mayer max vs direct supplied P/S | `7.543932811771015e-09` |
| Mayer max vs Multiwfn standalone | `8.449582811209666e-09` |
| `Tr(P S)` | `18.000000006302354` |
| `PSP − 2P` | `1.8250468913905138e-09` |
| Primitive `nprims` / shape | `85` / `(85,85)` |
| `Tr(Pprim Sprim)` | `18.000000006302354` |
| Primitive trace − Ne | `6.302354194076543e-09` |

The f block self-overlap is the identity; f–s/p cross-blocks are validated
through the canonicalization and the native S comparison. Pprim is separate
from the current-basis P and is not used as a Mayer density.

## Regression

- H₂/H₂O/C₆H₆ RHF/STO-3G: unchanged.
- O₂ UHF/ROHF: unchanged.
- H₂O/6-31G* d spherical and Cartesian: unchanged.
- 155 original tests: PASS.
- 18 Phase 7B angular tests: PASS.
- 19 Phase 7C ORCA tests: PASS.
- 6 Phase 8B native f tests: PASS.
- CTest: 6/6.

## Independent reference

- ORCA provides the source S/C/P and the direct reference.
- Multiwfn standalone `df_results/h2s_def2tzvp/multiwfn_bndmat.txt` is used
  only as an external comparison, never as a runtime backend.
- The Phase 7A PySCF cross-block evidence established the `D_f` phase.

## Not validated

- Cartesian f.
- g/h.
- UHF/ROHF f (no f open-shell fixture).
- PBC/post-HF/ECP/EDF.
- f in analyses other than Mayer.

No result is labeled PASS without an executed comparison.
