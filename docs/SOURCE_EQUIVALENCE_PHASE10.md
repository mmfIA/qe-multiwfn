# Source equivalence — Phase 10

**Status:** PASS on the validated cases. All comparisons align units, AO order,
angular convention and normalization first.

## 1. Cross-source matrix

| System | Method | Reference | Other source | Max S/Δ | Max Mayer/Δ |
|---|---|---|---|---|---|
| H₂/STO-3G | RHF | ORCA | PySCF | `2.31e-9` | `1.33e-15` |
| H₂O/STO-3G | RHF | ORCA | PySCF | `3.14e-9` | `3.22e-8` |
| O₂/STO-3G | UHF | ORCA | PySCF | `3.33e-9` | `2.53e-12` (α/β `≤2.0e-15`) |
| O₂/STO-3G | ROHF | ORCA | PySCF | `3.33e-9` | `2.22e-15` (α/β `≤2.4e-15`) |
| H₂O/6-31G* | RHF spherical d | ORCA | PySCF | — | `3.78e-6` |
| H₂O/6-31G* | RHF Cartesian d | ORCA/PySCF fixture | PySCF | — | `9.43e-7` |
| H₂S/def2-TZVP | RHF spherical f | ORCA | PySCF direct | `3.64e-9` | `5.97e-7` |
| H₂S/def2-TZVP | RHF spherical f | ORCA | PySCF full | — | `1.02e-6` |
| H₂/O₂/H₂O synthetic | RHF | identical arrays | Database A vs B | exact | exact |

Tolerances:

- `S` comparison: `1e-7` for matched source-normalized bases.
- `Mayer`: `1e-6` for matched methods; `1e-5` for the 6-31G* d and f
  SCF/integration comparison; not a relaxation of strict source validation.
- Database synthetic records use exact equality because inputs are identical.

The PySCF p order (`px,py,pz`) is mapped to MDM (`pz,px,py`); spherical d/f
are mapped to canonical MDM order. S and C receive the same permutation.
PySCF raw s/p/d contraction coefficients are converted to unit primitive-
contraction normalization before full-state execution; no C re-signing or
phase is invented.

## 2. Full-state P0 results

After the Phase 10 normalization fix:

| Case | Generated CᵀSC | Generated Tr(PS) |
|---|---:|---:|
| PySCF H₂S/def2-TZVP f | `8.54e-14` | `18.000000000000018` |
| PySCF H₂O/STO-3G | `~2.00e-8` | `10.000000155` |
| PySCF H₂O/6-31G* spherical d | `~2.11e-7` | `10.000000425` |
| PySCF O₂/STO-3G UHF | `~2.62e-8` | `16.000000328` |
| PySCF O₂/STO-3G ROHF | `~2.60e-8` | `16.000000328` |

The generated-state bound remains `1e-6`; source-supplied matrices retain
`1e-10`/`1e-8`. See `PHASE10_NORMALIZATION_AUDIT.md`.

## 3. Source independence

- PySCF and ORCA produce equivalent MDMs for matched states.
- NumPy/builder and database records produce equivalent MDMs and Engine
  results for identical scientific arrays.
- ASE contributes geometry only and is never compared as an electronic
  source.
- Provenance/source labels differ; scientific results do not.

## 4. Evidence

- `tests/python/test_pyscf_adapter.py`
- `tests/python/test_database_adapter.py`
- `tests/python/test_ase_adapter.py`
- `tests/python/test_ase_adapter_phase9c.py`
- `tests/python/test_builder.py`
- `MDM_1.1_work/PHASE9C/phase9c_p0_metrics.txt`
- `MDM_1.1_work/PHASE10/phase10_p0_metrics.txt` (Phase 10 full-f update)
- Existing Phase 6/7/8 canonical validation.

## 5. H₂S/def2-TZVP difference audit

The Phase 10 difference (PySCF direct `5.97e-7`; full `1.02e-6` vs ORCA) was
investigated separately from the internal generated-state validation bound.

Measured after AO/angular alignment:

- S max difference: `3.64e-9`, with identical diagonal within `4.4e-16`;
- P_total max difference: `2.86e-6`;
- MO C differs by large signed/rotated values because the two SCF programs
  choose different orbital bases/signs, while the occupied density is nearly
  the same;
- Mayer difference is distributed as roughly `3e-7` off-diagonal and
  `6e-7` on the diagonal; it is not concentrated in an f component.

This is a cross-backend SCF numerical/density difference, not a normalization
or angular-convention failure. The canonical references and tolerances are
unchanged. The direct/full values remain documented as known source differences.

