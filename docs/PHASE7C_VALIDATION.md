> **Historical Phase 7C note.** This document describes the state before
> Phase 8B. Phase 8B subsequently lifted the native spherical-f guard for
> canonical MDM 1.2 data; see `PHASE8B_*` docs.

# Phase 7C validation summary

## Mathematical checks

For H₂S/def2-TZVP (ORCA 6.1.1, f present), the canonical path was compared to
the source path:

| Quantity | Source | Canonical |
|---|---|---|
| schema | 1.1.0 | 1.2.0 |
| `max|S_can − D S_src D|` | — | `0.0` |
| `max|P_can − D P_src D|` | — | `0.0` |
| `max|C_can − D C_src|` | — | `0.0` |
| `CᵀSC − I` | `1.89e-14` | `1.89e-14` |
| `Tr(PS)` | `17.999999999999993` | `17.999999999999993` |
| `PSP − 2P` | `1.33e-14` | `1.33e-14` |

The numerical maximum is zero; bitwise equality is not claimed because the
phase transform can change the sign of zero entries. The f block self-overlap
is invariant; f–s/p cross-blocks carry the phase.

For H₂O/6-31G* (d, no f):

- canonical d phase is identity;
- C/S/P are bitwise identical to the source;
- direct backend Mayer is bitwise identical.

UHF/ROHF O₂/STO-3G (s/p only) remain 1.1 with or without the flag; matrices
are unchanged.

## Backend boundary

The canonical f model is MDM-only in Phase 7C. Loading it with
`prepare_from_orbitals=True` still fails with `QeUnsupported` from the
original genSbas guard (`l > 2`). No f Mayer result is produced or claimed.

## Independent evidence

The ORCA-to-canonical f phase is the Phase 7A artifact-confirmed result:
independent ORCA vs PySCF f–H s/p cross-blocks reduce to ~1e-9 after
\(D_f\). Phase 7C applies exactly that phase and records its provenance.
See `MDM_1.1_work/PHASE7A/EVIDENCE_AND_REFERENCES.md`.

## Not validated

- native backend f/g/h execution;
- ORCA versions other than 6.1.1;
- g/h angular conventions;
- full f Mayer/Multiwfn comparison.
