# Public API — QE-Multiwfn 0.3.0-dev

**Status:** Phase 9B. `MayerResult` has additive semantic properties; existing
fields and numerical results are unchanged. The builder is public.

## 1. Top-level exports

```python
import qe_multiwfn as qe
```

| Export | Purpose |
|---|---|
| `qe.Engine` | native lifecycle, MDM loading, S/P generation, Mayer |
| `qe.MolecularSystem` | legacy 0.1.1 RHF direct S/P container |
| `qe.MolecularSystemV1` | canonical MDM root |
| `qe.MolecularDataBuilder` | in-memory MDM builder |
| `qe.BasisInput`, `qe.ShellInput` | basis construction records |
| `qe.build_molecular_system`, `qe.from_numpy` | one-call array constructor |
| `qe.model_v1` | all MDM dataclasses and enums |
| `qe.MayerResult` | Mayer result matrices and semantics |
| `qe.attach_normalization`, `qe.normalization_report` | normalization helpers |
| angular classes/functions | angular convention, phase and canonicalization |
| `QeError` and subclasses | typed native errors |
| `qe.NATIVE_LIBRARY_PATH`, `qe.NATIVE_LIBRARY_VERSION` | native diagnostics |

`from qe_multiwfn.analysis import calculate_mayer` accepts both legacy
`MolecularSystem` and `MolecularSystemV1`; `qe.analysis` is also available as
a top-level submodule.

### Adapter entry points

| Module | Function |
|---|---|
| `qe_multiwfn.adapters.orca` | `from_orca_directory`, UHF/ROHF JSON variants |
| `qe_multiwfn.adapters.pyscf` | `from_pyscf(mol, mf)` |
| `qe_multiwfn.adapters.ase` | `from_ase(atoms)`, `from_ase_atoms(atoms)` |
| `qe_multiwfn.adapters.database` | `DatabaseRecord`, `from_database_record`, `DatabaseProvider`, `InMemoryDatabaseProvider`, `from_database_provider` |
| `qe_multiwfn.adapters.cclib` | `from_cclib`, `from_cclib_data` |

All adapters return a `MolecularSystemV1`; the Engine never receives an ORCA,
PySCF, ASE, cclib or database object.

```python
from qe_multiwfn.adapters.pyscf import from_pyscf

mdm = from_pyscf(mol, mf)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

ASE is structural only. A database adapter maps its record to
`DatabaseRecord`; no database connection is part of the core.

## 2. Builder

See `MDM_BUILDER.md` for full details. The core flow is:

```python
builder = qe.MolecularDataBuilder()
builder.set_geometry(atomic_numbers=z, coordinates=coords,
                     unit="angstrom")
builder.set_electronic_state(wfntype="UHF", charge=0, multiplicity=3)
builder.set_basis(qe.BasisInput(shells=[...],
                                normalization_convention="source_normalized"))
builder.set_orbitals(C, occupations, energies=energies, spins=spins,
                     layout="ao_orbital")
builder.set_overlap(S)
builder.set_density(total=P_total, alpha=P_alpha, beta=P_beta)
mdm = builder.build()
```

The builder never reads files and never imports an adapter. Direct P/S input
can use a minimal `BasisInput(aos=...)`; full-state input needs shells,
primitives, an AO map and normalization metadata.

## 3. Engine

| Method | Meaning |
|---|---|
| `load_molecule(system)` | legacy RHF direct S/P path |
| `load_molecule_v1(system, allow_open_shell=False, prepare_from_orbitals=False)` | canonical MDM path |
| `prepare()` | commit direct state or build S/P from basis/orbitals |
| `generate_density()`, `generated_density()` | original `genP` and result |
| `generate_overlap()`, `generated_overlap()` | original `genSbas_curr` and result |
| `generate_cartesian_overlap()` | diagnostic `genSbas`; f not validated |
| `generate_primitive_density()`, `generated_primitive_density()` | original `genPprim` |
| `generated_primitive_overlap()` | primitive S validation |
| `calculate_mayer(system=None, *, allow_open_shell=None)` | load/prepare if a system is supplied, then Mayer |
| `release_molecule()` | release native state |

`calculate_mayer(mdm)` automatically permits UHF/ROHF and automatically uses
the full basis/orbital path when S/P are absent. The no-argument form is
unchanged.

## 4. MayerResult semantics

The native routine `calcMayerbndord` returns three slots:

| Field | RHF | UHF/ROHF |
|---|---|---|
| `result.total` | closed-shell Mayer total | generalized Wiberg / mixed-density matrix (`bndmattot`) |
| `result.alpha` | `None` | alpha-spin Mayer matrix |
| `result.beta` | `None` | beta-spin Mayer matrix |
| `result.mixed` | `None` | alias of `total` |
| `result.generalized_wiberg` | `None` | alias of `total` |
| `result.mayer_total` | `total` | `alpha + beta` |
| `result.alpha_plus_beta` | `total` | `alpha + beta` |
| `result.total_semantics` | `closed_shell_mayer` | `generalized_wiberg_mixed` |

For UHF/ROHF, `result.total` is **not** a synonym for `alpha + beta`.
Multiwfn prints the all-electron `alpha + beta` matrix as “Total” and the
`bndmattot` matrix separately as “mixed density”. The existing `total` field
is preserved for compatibility; use `mixed`/`generalized_wiberg` and
`mayer_total` to make the distinction explicit.

`metadata` contains:

- `analysis` — `"Mayer"`;
- `wavefunction_type` — native integer;
- `wavefunction_type_name` — `RHF`, `UHF`, `ROHF`, etc.;
- `total_semantics` — explicit semantics;
- `has_spin_components` — whether alpha/beta are populated;
- `ncenter`.

## 5. Direct example

```python
import numpy as np
import qe_multiwfn as qe
from qe_multiwfn.model_v1 import AOFunction

S = np.array([[1.0, 0.5], [0.5, 1.0]])
P = np.full((2, 2), 2.0 / 3.0)
mdm = qe.build_molecular_system(
    atomic_numbers=[1, 1],
    coordinates=[[0, 0, 0], [0, 0, 1.4]],
    coordinate_unit="bohr",
    wfntype="RHF", multiplicity=1,
    basis=qe.BasisInput(
        aos=[
            AOFunction(index=1, center=1, l=0, component="s",
                       angular_type=0, multiwfn_type=1),
            AOFunction(index=2, center=2, l=0, component="s",
                       angular_type=0, multiwfn_type=1),
        ],
        nbasis=2, nprims=2, normalization_convention="source_normalized",
    ),
    overlap=S, density_total=P,
)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
assert result.total.shape == (2, 2)
```

## 6. Full-state example

```python
import numpy as np
import qe_multiwfn as qe

mdm = qe.build_molecular_system(
    atomic_numbers=[2], coordinates=[[0, 0, 0]],
    coordinate_unit="bohr", wfntype="RHF", multiplicity=1,
    basis=qe.BasisInput(
        shells=[qe.ShellInput(center=1, l=0,
                              exponents=[1.0], coefficients=[1.0])],
        normalization_convention="source_normalized",
    ),
    coefficients=np.array([[1.0]]), occupations=np.array([2.0]),
)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

The full path has no input file and no adapter dependency. The He-like model
is an architectural example, not a scientific benchmark.

## 7. Compatibility

- `MolecularSystem`/`load_molecule` remain 0.1.1-compatible.
- `MolecularSystemV1` remains the MDM contract.
- `total`/`alpha`/`beta` retain their numerical values.
- New builder and result properties are additive.
- Default MDM schema remains `1.1.0`; canonical angular input remains explicit
  `1.2.0`.
- No ABI symbol was added or removed in Phase 9B.

## 8. Errors

`QeError` subclasses map native statuses 1..12. Builder/contract errors use
`ValueError` or `QeIncompleteState`; unsupported scientific scope uses
`QeUnsupported`. See `MDM_BUILDER.md` and `MDM_VALIDATION.md`.
