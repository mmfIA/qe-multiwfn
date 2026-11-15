# QE-Multiwfn 0.3.0

> **Distribution source tree.** Python `0.3.0`, Molecular Data Model `1.1.0`,
> and native ABI `0.2.0` (intentionally preserved).
> The frozen 0.2.0 release remains in `../qe_multiwfn_src` and in the audit
> freezer; it is not modified by this tree.

**QuantumEngine-Multiwfn (QE-Multiwfn)** is a Python-callable Fortran library
that exposes the scientific core of [Multiwfn](http://sobereva.com/multiwfn)
as an in-memory computational backend, without menus, GUI, or intermediate
disk files.

## Current status

| Item | Value |
|---|---|
| Python package | `0.3.0` |
| Molecular Data Model | schema `1.1.0` |
| Native ABI | `0.2.0` (preserved for compatibility) |
| Frozen release | QE-Multiwfn 0.2.0, SHA-256 `9560c0fc…` |
| Dev library | `python/libqe_multiwfn.so`, SHA-256 `e9ac3a73…` |
| Exported ABI symbols | **17 legacy + 27 additive = 44**; 15 symbols added since the frozen baseline; no legacy symbol removed |

The 0.3.0 wheel and sdist are produced in `dist-phase12/`.

## Implemented

- Mayer bond order through the original `calcMayerbndord` routine.
- RHF, plus opt-in UHF and ROHF (`allow_open_shell=True`).
- Canonical Molecular Data Model 1.1: atoms, geometry, shells, primitives,
  AO map, normalization metadata, orbitals, S/P, readiness and provenance.
- Original Multiwfn state preparation on the validated s/p/d scope:
  - `genP` (`Ptot`, `Palpha`, `Pbeta`);
  - `genPprim` (primitive-basis density, kept separate from the AO density);
  - `genSbas` / `genSbas_curr` (Cartesian and spherical d);
  - native spherical f support on canonical MDM 1.2 data (RHF H₂S;
    UHF/ROHF O₂ in Phase 8C).
  - complete flow `MDM → basis → orbitals → genSbas_curr → genP → Mayer`.
- Public in-memory MDM builder (`MolecularDataBuilder`/`build_molecular_system`)
  for NumPy and Python objects, with no file/adapter requirement.
- ORCA 6.x JSON adapter for RHF/UHF/ROHF and optimization geometry.
- PySCF 2.15 RHF/UHF/ROHF in-memory adapter (s/p/d/f spherical; direct f).
- ASE geometry-only adapter; periodic ASE input fails closed.
- Generic in-memory database-record protocol.
- cclib conversion from cclib-like data when an explicit canonical basis is
  supplied; the real ORCA text parser is currently blocked.
- Fail-closed state/cache handling and non-interactive Fortran paths
  (`ifiletype=9`, `ifPBC=0`; no public setters for those globals).

## Two execution paths

1. **Caller-supplied matrices (direct path, compatible with 0.2.0).**
   The model/adapter supplies `matrices.S` and `matrices.P_total`; the library
   prepares the Multiwfn globals and calls the original Mayer routine.
2. **Original-routine state construction (0.3.0).**
   The model supplies basis and orbitals; the library builds S/P with the
   original `genSbas_curr`/`genP`. Use `prepare_from_orbitals=True`.
  Spherical f requires the canonical MDM 1.2 path; see Phase 8B/8C.

```python
import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import from_orca_directory

model = from_orca_directory("QE-Multiwfn-validation/orca/h2o")

with qe.Engine() as engine:
    # No matrices.S / matrices.P_total are required on this path.
    engine.load_molecule_v1(model, prepare_from_orbitals=True)
    engine.prepare()
    result = engine.calculate_mayer()

print(result.total)
```

The legacy 0.1.1 API (`MolecularSystem` + `load_molecule`) remains available
for callers that already have density and overlap matrices. The direct v1 path
(`load_molecule_v1(model)` without `prepare_from_orbitals`) remains unchanged.

### In-memory builder

```python
import qe_multiwfn as qe

mdm = qe.build_molecular_system(
    atomic_numbers=[2], coordinates=[[0, 0, 0]],
    coordinate_unit="bohr", wfntype="RHF", multiplicity=1,
    basis=qe.BasisInput(
        shells=[qe.ShellInput(center=1, l=0,
                              exponents=[1.0], coefficients=[1.0])],
        normalization_convention="source_normalized",
    ),
    coefficients=[[1.0]], occupations=[2.0],
)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

The builder accepts NumPy arrays/objects directly and never reads an input
file. A minimal AO map can be supplied for the direct S/P path; full state
needs shells, primitives and normalization metadata. See `docs/MDM_BUILDER.md`.

PySCF objects can be converted directly:

```python
from qe_multiwfn.adapters.pyscf import from_pyscf

mdm = from_pyscf(mol, mf)
with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

ASE provides structural geometry only; database records use the generic
`adapters.database` protocol. See `docs/PYSCF_ADAPTER.md`,
`docs/ASE_ADAPTER.md` and `docs/DATABASE_INPUT_PROTOCOL.md`.

## Scientific validation

- RHF H₂/H₂O/C₆H₆: S/P/Mayer bit-identical to the P0 baseline; QE × Multiwfn
  `max|Δ|` = 1.33e-15 / 3.61e-9 / 4.98e-9.
- UHF/ROHF O₂/STO-3G: validated against ORCA and Multiwfn.
- UHF/ROHF O₂/def2-TZVP spherical f (Phase 8C): full native flow PASS;
  S max `5.94e-9`, Mayer vs ORCA `≤1.17e-8`, α/β vs Multiwfn `≤4.93e-9`.
- H₂O/6-31G* spherical d and PySCF Cartesian d: validated; the original
  `genSbas_curr`/`genP` flow matches within source-matrix precision.
- Phase 6 full flow without `matrices.S`/`P_total`: **PASS** for seven cases,
  Mayer `max|Δ|` ≤ 4.1e-8.
- Current suite: **233 Python tests passed**, **CTest 6/6**.

See `docs/MDM_BUILDER.md`, `docs/MDM_VALIDATION.md`,
`docs/PUBLIC_API.md`, `docs/PYSCF_ADAPTER.md`, `docs/ASE_ADAPTER.md`,
`docs/DATABASE_INPUT_PROTOCOL.md`, `docs/SOURCE_EQUIVALENCE.md`,
`docs/PHASE8C_SCIENTIFIC_VALIDATION.md`,
`../MDM_1.1_work/PHASE6_REPORT.md`, `../MDM_1.1_work/PHASE6_RESIDUALS.md` and
`../MDM_1.1_work/AUDIT_PHASE6_FINAL.md`.

## Build and test

```bash
cmake -S . -B build_audit -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_Fortran_COMPILER=gfortran -DCMAKE_C_COMPILER=gcc \
  -DQE_STRICT_LEGACY=ON -DQE_BUILD_TESTS=ON
cmake --build build_audit --parallel 4
(cd build_audit && ctest --output-on-failure)
PYTHONPATH="$PWD/python" python3 -m pytest tests/python -q
```

To run against the clean build instead of the bundled library:

```bash
export QE_MULTIWFN_LIBRARY="$PWD/build_audit/libqe_multiwfn.so"
export LD_LIBRARY_PATH="$PWD/build_audit:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$PWD/python:${PYTHONPATH:-}"
```

Requirements: gfortran, GCC, CMake, OpenBLAS, Python 3.12, numpy and pytest.
PySCF, ASE and cclib are optional and only needed for their adapters.

## Architecture

```text
ORCA / PySCF / ASE / cclib / database records / canonical matrices
                         │
                         ▼
      Molecular Data Model 1.1 (Python)
      atoms, geometry, basis, AO map, normalization,
      orbitals, matrices, provenance
                         │
                         ▼
      Engine / NativeAPI (ctypes, NumPy Fortran order)
                         │
                         ▼
      C ABI: 17 legacy + 27 additive symbols (44 total)
                         │
                         ▼
      Fortran canonical state (`the_mol`) → Multiwfn globals (`defvar`)
                         │
        ┌────────────────┼─────────────────────┐
        ▼                ▼                     ▼
  calcMayerbndord   genP / genPprim       genSbas / genSbas_curr
        │                │                     │
        └────────────────┴─────────────────────┘
                         ▼
              Fortran buffers → NumPy results
```

Memory is copied at the C ABI boundary: Python owns its input arrays, Fortran
owns the Multiwfn globals. There is one active system per process; the global
Multiwfn state is not thread-safe.

## Repository layout

```text
qe_multiwfn_030_dev/
├── CMakeLists.txt
├── include/                  # public C headers (legacy + additive v1)
├── src/
│   ├── bridge/               # C ABI, status, errors, memory, 2F2 stub
│   ├── engine/               # lifecycle and state machine
│   ├── state/                # MDM storage, state builder, genP/genPprim/genSbas
│   └── analysis/             # result buffers and original Mayer adapter
├── python/qe_multiwfn/       # Engine, MDM, adapters, normalization
├── tests/                    # C ABI + Python tests
├── vendor/                   # pristine Multiwfn 2026.11.3 source
├── docs/                     # current and historical documentation
└── checkpoints/              # MDM 1.1 and Phase 6 checkpoints
```

## Known limitations

- **f** is supported natively for canonical MDM 1.2 spherical f; the
  original-routine path is validated on H₂S/def2-TZVP (RHF) and
  O₂/def2-TZVP (UHF/ROHF). **g/h** remains fail-closed (`l > 3`). Cartesian
  f is not validated and is rejected by the native basis builder.
- **cclib / ORCA 6.1.1:** cclib 1.8.1 fails in
  `orcaparser.py:2799 _append_scfvalues_scftargets`; the adapter fails closed.
- **ASE:** geometry only; it does not run Mayer without basis/orbitals.
- **PBC, post-HF, ECP/EDF:** not implemented; PBC and post-HF are rejected.
- **Thread safety / multiple engines:** not supported; one active system.
- **RHF `nmo == nbasis`:** still requires validation for bases with linear
  dependence (`nindbasis < nbasis`).
- **`hyp2F2`:** documented stub; unused by the validated s/p/d path.
- **Native readers (FCH/WFN/WFX/Molden/MWFN):** not exposed as core readers;
  adapters are separate.
- **0.3.0 package:** wheel/sdist built; platform wheel is Linux x86_64/Python 3.12.

See `docs/LIMITATIONS.md` for the detailed scope.

## Documentation map

**Current (0.3.0):**
`README.md`, `docs/IMPLEMENTATION_STATUS.md`, `docs/LIMITATIONS.md`,
`docs/ARCHITECTURE.md`, `docs/MOLECULAR_DATA_MODEL_1.1.md`,
`checkpoints/PHASE6_ELECTRONIC_STATE.md`,
`../MDM_1.1_work/PHASE6_REPORT.md`,
`../MDM_1.1_work/AUDIT_PHASE6_FINAL.md`,
`../MDM_1.1_work/TRANSFER_TO_OPENCODE_GO.md`.

**Historical (scope-specific):**
`docs/MOLECULAR_DATA_MODEL_1.0.md` (1.0 specification),
`docs/M1_IMPLEMENTATION_REPORT.md` (0.2.0/M1),
`docs/RELEASE_NOTES_0.1.1.md` and `docs/BUILD_VERIFICATION_0.1.1.md` (0.1.1),
`docs/FINAL_REPORT_0.1.0.md` and `docs/SOURCE_AUDIT.md` (0.1.0),
`docs/EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md` (original plan; UHF/ROHF
implemented since then, PBC/post-HF/ECP/EDF still pending).

## License

Multiwfn is © Tian Lu (Beijing Kein Research Center for Natural Sciences)
and is distributed under its own license (see `vendor/` and Multiwfn's
official terms). The upstream license applies to all Multiwfn-derived code.
The wrapper code in `src/`, `python/`, `tests/`, `cmake/`, `include/`, and
`scripts/` is provided under the same Multiwfn license terms for consistency,
with attribution to the original author preserved.

## Important input conventions

- `basis_center` and `basis_type` have length `nbasis`; `nprims` is an
  independent primitive count and may be larger.
- AO blocks for each atom must be contiguous.
- Coordinates are explicitly Angstrom or Bohr; the canonical model stores Bohr.
- Setters are accepted only while a system is loaded.
- The original-routine path copies input buffers into Fortran memory; no
  Python pointer is retained after a call.
- Missing basis, orbitals, normalization metadata or inconsistent dimensions
  fail closed; no stale derived result is accepted.
