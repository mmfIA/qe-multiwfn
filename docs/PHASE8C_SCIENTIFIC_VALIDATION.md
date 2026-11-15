# Phase 8C — scientific validation of open-shell spherical f

**Status:** COMPLETE for the executed O₂/def2-TZVP UHF and ROHF fixtures.
**Scope:** canonical MDM 1.2 spherical f; no Cartesian f, g/h or post-HF claim.
**Backend:** original `genSbas_curr`, `genP`, `genPprim`, `matCar2curr` and
`calcMayerbndord`.

## 1. Question

Phase 8B validated spherical f only for closed-shell H₂S/def2-TZVP. Phase 8C
asks whether the same canonical-f path is correct for open-shell densities,
where alpha and beta coefficients, densities and Mayer matrices are separate.

## 2. Fixtures

Both fixtures are the same molecule and basis so that the UHF and ROHF paths
can be compared without a geometry/basis confound:

| Item | Value |
|---|---|
| Molecule | O₂, `O 0 0 0; O 0 0 1.207 Å` |
| Charge / multiplicity | `0` / `3` |
| Basis | def2-TZVP |
| Basis functions | 62 |
| Primitive Gaussians | 102 |
| f shells | 2 (one per O atom) |
| f AOs | 14, seven (`F0,F+1,F-1,F+2,F-2,F+3,F-3`) per O |
| Electrons | 16; UHF/ROHF α = 9, β = 7 |
| Source | ORCA 6.1.1, `TightSCF`, `KeepInts` |
| MDM source | `1.1.0`; canonicalized to `1.2.0` with ORCA f phase |

The ORCA inputs, outputs, JSON and Molden files are in
`../../MDM_1.1_work/PHASE8C/fixtures/`; compact copies of the JSON/output used
by the test suite are in `tests/fixtures/phase8c/`.

## 3. Method

1. Convert the ORCA 6.1.1 source model to canonical MDM 1.2 with the source
   f phase `(1,1,1,1,1,-1,-1)`.
2. Verify `C_can = D_f C_source` and
   `S_can = D_f S_source D_f` exactly.
3. Run the full native flow from the canonical model:
   `load_molecule_v1(..., allow_open_shell=True, prepare_from_orbitals=True)`
   → `prepare()` → generated `S`, `P_total`, `P_alpha`, `P_beta` → Mayer.
4. Check `Tr(P S)`, `Tr(P_alpha S)`, `Tr(P_beta S)`, channel idempotency,
   `CᵀSC`, and the separate primitive-basis density.
5. Compare alpha, beta and mixed Mayer matrices with:
   - ORCA's direct matrices (the independent source reference);
   - Multiwfn 2026.11.3 standalone on the ORCA Molden file (external
     comparison only; never a runtime backend).

## 4. Results

### 4.1 UHF

| Quantity | Value |
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
| Mayer total (mixed) max vs ORCA | `1.160394980104229e-08` |
| Mayer α max vs ORCA | `1.845970043490297e-09` |
| Mayer β max vs ORCA | `6.4279244149645365e-09` |
| `P_prim` trace | `16.000000002734154` |
| `P_alpha,prim` / `P_beta,prim` trace | `8.999999997859856` / `7.000000004874300` |
| Mayer α max vs Multiwfn | `2.933520426573466e-09` |
| Mayer β max vs Multiwfn | `4.926598240473368e-09` |
| Mayer mixed max vs Multiwfn | `2.451203018338788e-09` |

### 4.2 ROHF

| Quantity | Value |
|---|---|
| `S` max vs canonical ORCA S | `5.93500075474207e-09` |
| `P_total` max | `1.1102230246251565e-16` |
| `P_alpha` / `P_beta` max | `5.551115123125783e-17` / `5.551115123125783e-17` |
| `Tr(P S)` | `16.000000000000010` |
| `Tr(P_alpha S)` / `Tr(P_beta S)` | `9.000000000000005` / `7.000000000000006` |
| `Cᵀ S C − I` (both channels) | `1.3633538742396922e-13` |
| `P_alpha S P_alpha − P_alpha` | `1.2212453270876722e-15` |
| `P_beta S P_beta − P_beta` | `1.2212453270876722e-15` |
| Mayer total (mixed) max vs ORCA | `1.161722051890024e-08` |
| Mayer α max vs ORCA | `2.378837404837242e-09` |
| Mayer β max vs ORCA | `6.076570802093784e-09` |
| `P_prim` trace | `16.000000002448946` |
| `P_alpha,prim` / `P_beta,prim` trace | `8.999999998062659` / `7.000000004386289` |
| Mayer α max vs Multiwfn | `3.194906061931846e-09` |
| Mayer β max vs Multiwfn | `2.1216830514703133e-09` |
| Mayer mixed max vs Multiwfn | `1.073222399838869e-09` |

### 4.3 f-specific checks

- The canonical ORCA f self-overlap differs from identity by at most
  `6.661338147750939e-16`; the generated native f self-overlap differs by at
  most `2.6645352591003757e-15`, and generated-vs-source f-block max is
  `2.4424906541753444e-15`.
- f–s/p/d cross-blocks are nonzero (max `0.21302211385097844`) and are part of
  the validated `S` comparison; this is not a diagonal-only check.
- The two f shells are on different centers (AOs 25–31 and 56–62), exercising
  multiple f shells rather than a single-center special case.
- Component-wise block checks cover all l=0/1/2/3 pairs, not only a global
  maximum. `S` block max ranges from `2.43e-9` (s–f) to `5.94e-9` (p–p);
  `f–f` is `3.94e-9`; `P` block max is `0.0` for UHF and `≤1.11e-16` for
  ROHF. The complete 7×7 f self-overlap matrix is stored in the evidence JSON.
- `D_f C_source` and `D_f S_source D_f` reproduce the canonical objects
  exactly (`0.0` difference) for both UHF and ROHF.

### 4.4 Open-shell result semantics

`MayerResult.total` for UHF/ROHF is the **mixed-density** Mayer matrix returned
by the original routine, not the arithmetic α+β "all electrons" matrix. The
α and β matrices are separate. Multiwfn prints both a "total (all electrons)"
and a "mixed density" matrix for these cases; the native `total` must be
compared with Multiwfn's mixed-density matrix, while native `alpha`/`beta`
compare with Multiwfn's alpha/beta matrices. This avoids a false 0.42–0.50
apparent discrepancy caused by comparing different quantities.

## 5. Verdict

| Path | Verdict |
|---|---|
| UHF spherical f, O₂/def2-TZVP, canonical MDM 1.2 | **PASS** |
| ROHF spherical f, O₂/def2-TZVP, canonical MDM 1.2 | **PASS** |
| P/S/alpha/beta/primitive density and Mayer | **PASS** |
| f–s/p/d cross-blocks and multiple f centers | **PASS** |
| Cartesian f | **NOT VALIDATED / rejected** |
| g/h | **BLOCKED (`l > 3`)** |
| Other bases/molecules/open-shell multiplicities | **NOT VALIDATED** |

## 6. Not validated

This is not a universal open-shell f claim. It does not establish:

- other f bases or molecules (only H₂S/def2-TZVP RHF and O₂/def2-TZVP
  UHF/ROHF were executed);
- f in other analyses (only Mayer is exposed);
- Cartesian f, g/h, PBC, post-HF, ECP/EDF;
- ORCA versions other than 6.1.1 for this angular convention;
- thread safety or multiple simultaneous systems.

## 7. Evidence

- `docs/PHASE8C_UHF_F_VALIDATION.md`
- `docs/PHASE8C_ROHF_F_VALIDATION.md`
- `docs/PHASE8C_ANALYSIS_SUPPORT_MATRIX.md`
- `../../MDM_1.1_work/PHASE8C/phase8c_open_shell_metrics.json`
- `../../MDM_1.1_work/PHASE8C/phase8c_multiwfn_comparison.json`
- `../../MDM_1.1_work/PHASE8C/fixtures/` (ORCA inputs/outputs/JSON/Molden and
  Multiwfn `bndmat.txt`)
- `tests/python/test_open_shell_f_support.py` (four backend tests)
