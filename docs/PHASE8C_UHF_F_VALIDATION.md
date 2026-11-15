# Phase 8C — UHF spherical f validation

**Verdict:** **PASS** for O₂/def2-TZVP, ORCA 6.1.1, canonical MDM 1.2.
This is a validated fixture, not a general UHF-f claim.

## Fixture

- O₂, O–O `1.207 Å`, charge `0`, multiplicity `3`.
- `def2-TZVP`: 62 basis functions, 102 primitives.
- Two canonical spherical f shells (one per O; 14 f AOs total).
- UHF: 9 α and 7 β electrons; 16 total.
- Source: ORCA 6.1.1 `sp.json` / `sp.out`; source model MDM `1.1.0`; native
  execution from canonical MDM `1.2.0`.

## Native full flow

`prepare_from_orbitals=True` reconstructs S/P α/β from the canonical basis and
orbitals, then calls the original Mayer routine.

| Check | Result |
|---|---|
| `S` max vs canonical ORCA S | `5.93500075474207e-09` |
| `P_total` max | `0.0` |
| `P_alpha` / `P_beta` max | `0.0` / `0.0` |
| `Tr(P S)` | `16.000000000000025` |
| `Tr(P_alpha S)` / `Tr(P_beta S)` | `9.000000000000012` / `7.000000000000010` |
| `C_alphaᵀ S C_alpha − I` | `1.4654943925052066e-13` |
| `C_betaᵀ S C_beta − I` | `1.3167245072054357e-13` |
| `P_alpha S P_alpha − P_alpha` | `1.7208456881689926e-15` |
| `P_beta S P_beta − P_beta` | `1.0547118733938987e-15` |
| `P_total − (P_alpha + P_beta)` | `0.0` |
| Primitive trace | `16.000000002734154` |
| Primitive α / β trace | `8.999999997859856` / `7.000000004874300` |

## Mayer comparison

`MayerResult.total` is the mixed-density matrix; α and β are separate.

| Matrix | Max vs ORCA direct | Max vs Multiwfn 2026.11.3 |
|---|---|---|
| `total` (mixed) | `1.160394980104229e-08` | `2.451203018338788e-09` |
| `alpha` | `1.845970043490297e-09` | `2.933520426573466e-09` |
| `beta` | `6.4279244149645365e-09` | `4.926598240473368e-09` |

The Multiwfn comparison is against its printed 8-decimal alpha/beta and
mixed-density matrices, so the `~3–5e-9` floor is the print precision plus
the native/ORCA difference. Multiwfn is a standalone external reference, not a
runtime backend.

## f behavior

- Source-to-canonical `D_f` transformation is exact:
  `max|C − D_f C_source| = 0`, `max|S − D_f S_source D_f| = 0`.
- Source f self-overlap differs from identity by at most `6.66e-16`; the
  generated native f self-overlap differs by at most `2.66e-15` (7×7 matrix
  in `phase8c_angular_blocks.json`).
- f–s/p/d cross blocks are nonzero (max `0.2130`), so the validation exercises
  f mixing and not only f self-overlap. All l-pair blocks are checked
  (`s–s` through `f–f`), not only the global maximum.
- The two f shells are on different centers.

## Rejection check

Loading the same UHF source without canonicalization and requesting the
original-routine state is rejected with `QeUnsupported`; the direct P/S path is
unchanged. This prevents silently treating uncorrected ORCA f as canonical.

## Evidence

- `../../MDM_1.1_work/PHASE8C/fixtures/o2_uhf_def2tzvp/`
- `../../MDM_1.1_work/PHASE8C/phase8c_open_shell_metrics.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_multiwfn_comparison.json`
- `tests/fixtures/phase8c/o2_uhf_def2tzvp/`
- `tests/python/test_open_shell_f_support.py`

## Not validated

Other UHF molecules/bases/multiplicities, Cartesian f, g/h, post-HF, PBC,
ECP/EDF, other ORCA versions, and analyses other than Mayer.
