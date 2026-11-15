# Phase 9A — public API and result semantics

**Verdict:** **PARTIAL**
**Scope:** audit only; no API names, formulas or results were changed.

## 1. Public surface

### Top-level `qe_multiwfn`

| Export | Kind | Purpose |
|---|---|---|
| `Engine` | class | load MDM/legacy system, prepare, generate S/P, run Mayer |
| `MolecularSystem` | legacy class | 0.1.1 RHF-only direct S/P container |
| `MolecularSystemV1` | class | canonical MDM root |
| `model_v1` | module | all MDM dataclasses/enums/helpers |
| `MayerResult` | class | Mayer result container |
| `QeError` + typed subclasses | exceptions | C status mapping |
| `NATIVE_LIBRARY_PATH`, `NATIVE_LIBRARY_VERSION` | constants | native diagnostics |
| `attach_normalization`, `normalization_report` | functions | normalization metadata |
| angular classes/functions | API | convention, phase and canonicalization |
| `angular` | module | angular functions/types |

`model_v1` exposes `Atoms`, `Geometry`, `ElectronicState`, `Shell`,
`PrimitiveTable`, `AOFunction`, `BasisSet`, `OrbitalSet`, `Wavefunction`,
`MatrixRecord`, `MatrixBundle`, `CoreCorrection`, `Periodicity`,
`ReadinessFlags`, `derive_rhf_density`, `wavefunction_report` and
`legacy_representable` through its `__all__`. Only `MolecularSystemV1` is
re-exported at top level.

### Separate subpackages

| Module | Exports | Note |
|---|---|---|
| `qe_multiwfn.analysis` | `calculate_mayer` | accepts legacy `MolecularSystem` only |
| `qe_multiwfn.adapters.orca` | ORCA/RHF/UHF/ROHF/optimization converters | file-based |
| `qe_multiwfn.adapters.ase` | `from_ase_atoms` | geometry-only |
| `qe_multiwfn.adapters.cclib` | `from_cclib`, `from_cclib_data` | cclib data/file |
| `qe_multiwfn.native` | `NativeAPI` | low-level; not user-facing |
| `qe_multiwfn.normalization` | normalization helpers | metadata only |

## 2. Engine API

| Method | Contract |
|---|---|
| `Engine.initialize/finalize` | native lifecycle |
| `load_molecule(MolecularSystem)` | legacy RHF direct S/P path |
| `load_molecule_v1(MolecularSystemV1, allow_open_shell=False, prepare_from_orbitals=False)` | canonical MDM path |
| `prepare()` | commit direct MDM state or build S/P from basis/orbitals |
| `generate_density()` | original `genP` after prepared state |
| `generated_density(result_id=0)` | read generated P total/alpha/beta |
| `generate_overlap()` | original `genSbas_curr` |
| `generated_overlap()` | read generated S |
| `generate_cartesian_overlap()` | original `genSbas` diagnostic; f not validated |
| `generated_cartesian_overlap()` | read Cartesian overlap |
| `generate_primitive_density()` | original `genPprim` |
| `generated_primitive_density(result_id=0)` | read primitive P |
| `generated_primitive_overlap()` | primitive S validation |
| `calculate_mayer()` | original `calcMayerbndord` |
| `release_molecule()` | release native state |

The API is coherent for a Python scientific library: the user does not need
to know Fortran globals, the `.so` layout or the Multiwfn menu. The main
usability gaps are the missing high-level MDM builder and the split between
legacy and v1 loading.

## 3. Public API findings

| ID | Finding | Severity / impact |
|---|---|---|
| API-1 | `analysis.calculate_mayer` accepts only legacy `MolecularSystem`. | Users with `MolecularSystemV1` must use Engine manually. |
| API-2 | No public one-shot `calculate_mayer(MolecularSystemV1)` or builder. | Direct memory use is possible but verbose. |
| API-3 | `MayerResult.total` is misleading for UHF/ROHF (see §4). | High risk of wrong scientific interpretation. |
| API-4 | `MayerResult` has no `total_semantics`/wfntype-name metadata. | Users cannot tell what `total` means without reading source/docs. |
| API-5 | `Engine.calculate_mayer` auto-prepares only from `SYSTEM_LOADED`; other state transitions rely on native errors. | Minor usability/consistency issue. |
| API-6 | `generate_*` methods do not check Python-side state before calling native. | Errors are later/native; not a scientific bug. |
| API-7 | `MolecularSystemV1` submodels are not top-level exports. | Discoverability; `qe.model_v1.Atoms` works. |
| API-8 | `Engine.__init__` sets `_prepare_from_orbitals` twice. | Cosmetic. |
| API-9 | `RHF` legacy accepts only wfntype 0; v1 is opt-in. | Intentional compatibility, but two loading APIs. |

## 4. `MayerResult` semantic audit

### 4.1 What the native routine computes

`src/analysis/qe_mayer.f90` calls the original
`bondorder.f90::calcMayerbndord(bndmattot, bndmata, bndmatb)`. The vendor
source explicitly documents:

- restricted closed-shell: `bndmattot` is the conventional closed-shell
  Mayer matrix;
- unrestricted: `bndmattot` is the **generalized Wiberg bond order** from the
  total/mixed alpha+beta density, while `bndmata` and `bndmatb` are the
  alpha- and beta-spin Mayer matrices.

The routine forms:

```text
PS_tot = P_total S
bndmattot(A,B) = sum_{i in A, j in B} PS_tot(i,j) PS_tot(j,i)
bndmata/b    = alpha/beta analogues with the unrestricted factor
```

`P_total = P_alpha + P_beta` by contract; `PS_tot` therefore contains both
same-spin and cross-spin terms. Consequently:

```text
MayerResult.total != MayerResult.alpha + MayerResult.beta   (UHF/ROHF)
```

The `alpha + beta` matrix is the all-electron total-spin Mayer matrix. Multiwfn
prints it as "Total" and prints `bndmattot` separately as "mixed alpha&beta
density matrix". Phase 8C measured the difference directly (O₂/def2-TZVP:
about `0.42` for UHF and `0.50` for ROHF off-diagonal, so this is not a small
rounding issue).

### 4.2 Field semantics

| Field | RHF (0/3) | UHF (1) | ROHF (2) |
|---|---|---|---|
| `MayerResult.total` | conventional closed-shell Mayer; `bndmattot` | generalized Wiberg / mixed-density matrix; **not** alpha+beta | same as UHF |
| `MayerResult.alpha` | `None` | alpha-spin Mayer matrix | alpha-spin Mayer matrix |
| `MayerResult.beta` | `None` | beta-spin Mayer matrix | beta-spin Mayer matrix |
| `has_spin_components` | `False` | `True` | `True` |
| `metadata["wavefunction_type"]` | `0` | `1` | `2` |
| `metadata["has_spin_components"]` | `False` | `True` | `True` |

For RHF, `total` is the scientific total. For open shell, `total` is the
mixed/GWBO matrix produced by the C ABI's `QE_MAYER_TOTAL` slot; it is not a
renaming of `alpha + beta`.

### 4.3 Documentation risk

- `results.py:18` describes `total` as "total Mayer bond order matrix" without
  the open-shell exception.
- README/quickstarts pass `result.total` without semantics.
- Some historical docs use "QE total (Wiberg/mixed)" but the public class name
  does not expose that.
- A user who computes `result.total` for UHF/ROHF and compares it with
  Multiwfn's "Total" line will see a large difference and may incorrectly
  conclude that the library or validation is wrong.

### 4.4 Recommendation (do not implement in 9A)

Preserve old results and add explicit semantics in Phase 9B:

```text
MayerResult
  total          # backward-compatible; documented per wfntype
  alpha          # unchanged
  beta           # unchanged
  mixed          # additive: current bndmattot (generalized Wiberg)
  mayer_total    # additive: alpha + beta for open-shell; = total for RHF
  metadata:
    total_semantics = "closed_shell_mayer" | "generalized_wiberg_mixed"
    wavefunction_type_name = "RHF" | "UHF" | "ROHF" | ...
```

For open-shell, `mixed` should equal the current `total` (or `total` should be
an alias of `mixed` for compatibility), and `mayer_total = alpha + beta` must
be computed and documented. A future breaking rename belongs to a major
release, not 9A.

## 5. Exception and error API

`QeError(code, message, routine)` and subclasses map C statuses 1..12 via
`STATUS_TO_EXCEPTION`. This is coherent and usable. The `code`, `message` and
`routine` fields are public and stable. No audit finding that changes error
codes was identified.

## 6. API acceptance criteria for Phase 9B

1. A user can construct an MDM from NumPy/Python objects without an adapter or
   file.
2. `Engine.load_molecule_v1` accepts that MDM and runs the documented path.
3. The public API exposes a clear `MayerResult` matrix for:
   - closed-shell total;
   - open-shell alpha, beta, alpha+beta total;
   - open-shell mixed/GWBO.
4. `MayerResult` metadata states the semantic unambiguously.
5. The legacy `MolecularSystem` path remains compatible.
6. Exceptions remain typed and documented.
7. API tests cover all four matrices and both direct and full-state paths.

## 7. Evidence

- `python/qe_multiwfn/results.py:14-69`
- `python/qe_multiwfn/engine.py:435-484`
- `python/qe_multiwfn/analysis/bond_order.py:12-27`
- `src/analysis/qe_mayer.f90:38-78`
- `src/analysis/qe_analysis_state.f90:18-48`
- `vendor/Multiwfn_2026.11.3_src_Linux/bondorder.f90:188-344`
- Phase 8C reports, especially `docs/PHASE8C_SCIENTIFIC_VALIDATION.md` §4.4
