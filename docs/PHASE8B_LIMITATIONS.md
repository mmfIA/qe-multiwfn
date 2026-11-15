> **Historical Phase 8B report.** Phase 8C extends the validated scope to
> O₂/def2-TZVP UHF/ROHF and corrects the measured ABI inventory. The ABI
> counts in this report are historical; see `PHASE8C_ARCHITECTURE_AUDIT.md`
> and `checkpoints/PHASE8C_CHECKPOINT.md` for the current state.

# Phase 8B limitations

## Validated

- Spherical f, RHF, H₂S/def2-TZVP, ORCA 6.1.1 canonical MDM 1.2.
- Native `genSbas_curr`, `genP`, `genPprim`, `matCar2curr` and Mayer.

## Not validated / blocked

- Cartesian f native path: rejected by the basis builder.
- g/h: rejected (`l > 3`).
- UHF/ROHF f: no open-shell f fixture; not claimed.
- ORCA versions other than 6.1.1 for f canonicalization.
- ORCA adapter canonicalization remains opt-in (`canonicalize_angular=True`);
  default 1.1 paths are retained for compatibility.
- cclib ORCA 6.1.1 parser.
- PBC, post-HF, ECP/EDF.
- Thread safety / multiple engines.
- Other analyses.

## Backend numerical limits

- The canonical f model must be used; non-canonical 1.1 f is rejected for
  state/overlap building.
- Primitive matrices are not transformed by the spherical phase API.
- The f validation is for one RHF fixture; it is not a universal f claim.
