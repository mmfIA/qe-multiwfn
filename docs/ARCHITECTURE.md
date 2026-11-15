# Architecture

> **Current scope:** this document describes the original 0.1.x bridge and
> the current 0.3.0 extensions (MDM 1.1/1.2 and Phases 6–8C). The native ABI is
> 0.2.0; the development library exposes 17 legacy + 27 additive symbols
> (44 total; see `PHASE8C_ARCHITECTURE_AUDIT.md`).
> For current test counts and blockers see `IMPLEMENTATION_STATUS.md`,
> `LIMITATIONS.md` and `../../MDM_1.1_work/AUDIT_PHASE6_FINAL.md`.

## Overview

QE-Multiwfn is a **shared library** (`libqe_multiwfn.so`) built from
upstream Multiwfn sources plus a thin Fortran/C ABI layer. Python
calls into the library via `ctypes`, passing NumPy arrays directly
through RAM (no intermediate files).

```
┌─────────────────────────────────────────────────────────────────┐
│                          PYTHON                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ MolecularSystem│  │     Engine     │  │  MayerResult   │    │
│  │  (molecular.py)│  │  (engine.py)   │  │  (results.py)  │    │
│  └────────┬───────┘  └────────┬───────┘  └────────▲───────┘    │
│           │ NumPy arrays       │                    │            │
│           │ (F-contiguous)     │                    │ NumPy       │
│           ▼                    ▼                    │             │
│  ┌──────────────────────────────────────┐           │             │
│  │  native.py (ctypes CDLL wrapper)     │           │             │
│  │  - argtypes / restype                │           │             │
│  │  - status -> exception               │           │             │
│  └────────────────┬─────────────────────┘           │             │
└───────────────────┼─────────────────────────────────┼─────────────┘
                    │ C ABI (no name mangling)         │
                    ▼                                  │
┌───────────────────────────────────────────────────┐ │
│              libqe_multiwfn.so                    │ │
│  ┌─────────────────────────────────────────────┐  │ │
│  │  qe_c_api.f90 (bind(C) entry points)         │  │ │
│  │  qe_initialize / qe_finalize / ...           │  │ │
│  └────────────────┬────────────────────────────┘  │ │
│                   │                                │ │
│  ┌────────────────▼────────────────────────────┐  │ │
│  │  qe_engine_lifecycle.f90                   │  │ │
│  │  qe_engine_state.f90 (state machine)       │  │ │
│  │  qe_error_handler.f90 (status + messages)  │  │ │
│  └────────────────┬───────────────────────────┘  │ │
│                   │                                │ │
│  ┌────────────────▼────────────────────────────┐  │ │
│  │  qe_state_builder.f90                       │  │ │
│  │  qe_molecular_state.f90                     │  │ │
│  │  (push Python data into Multiwfn globals)   │  │ │
│  └────────────────┬───────────────────────────┘  │ │
│                   │                                │ │
│  ┌────────────────▼────────────────────────────┐  │ │
│  │  qe_mayer.f90 (adapter)                     │  │ │
│  │  qe_analysis_state.f90 (result buffers)    │  │ │
│  └────────────────┬───────────────────────────┘  │ │
│                   │                                │ │
│  ┌────────────────▼────────────────────────────┐  │ │
│  │  qe_genp / qe_genpprim / qe_gensbas         │  │ │
│  │  qe_electronic_state (Phase 6 adapters)     │  │ │
│  └────────────────┬───────────────────────────┘  │ │
│                   │                                │ │
│  ┌────────────────▼────────────────────────────┐  │ │
│  │  Multiwfn scientific core                   │  │ │
│  │  - bondorder.f90::calcMayerbndord           │  │ │
│  │  - sub.f90::genP / genPprim                 │  │ │
│  │  - integral.f90::genSbas / genSbas_curr     │  │ │
│  │  - util.f90::matmul_blas (-> dgemm)         │  │ │
│  │  - defvar globals (Ptot, Sbas, basstart,...) │  │ │
│  └─────────────────────────────────────────────┘  │ │
└────────────────────────────────────────────────────┼─┘
                                                     │
                              result buffer (double*)│
                                                     │
                              returned via C ABI ────┘
```

## Memory ownership

| Data | Owner | Lifetime |
|------|-------|----------|
| NumPy input arrays (atomic_numbers, coordinates, density, overlap) | Python | Until `engine.load_molecule()` returns; Fortran copies into its own allocatables |
| Fortran-side `the_mol` (canonical model) | Fortran (qe_state_builder) | Until `qe_release_system()` is called |
| Multiwfn globals (`Ptot`, `Sbas`, `basstart`, etc.) | Fortran (defvar) | Until `qe_release_system()` is called |
| Result buffers (`mayer_total`, ...) | Fortran (qe_analysis_state) | Until next `qe_calculate_mayer()` or `qe_release_system()` |
| Output buffer (NumPy) returned to Python | Python | Until caller deletes it |

**Critical rule**: the C ABI never retains Python pointers after a call
returns. Every `qe_set_*` function copies the input buffer into Fortran
memory.

## State machine

```
                  qe_initialize()
   UNINITIALIZED ─────────────────► INITIALIZED
                                          │
                       qe_begin_system() │
                                          ▼
                                    SYSTEM_LOADED
                                          │
                       qe_prepare_system()│
                                          ▼
                                   SYSTEM_PREPARED
                                          │
                       qe_calculate_mayer()│
                                          ▼
                                  RESULT_AVAILABLE
                                          │
                       qe_release_system()│
                                          ▼
                                    INITIALIZED
                                          │
                       qe_finalize()     │
                                          ▼
                                    UNINITIALIZED
```

Each transition is validated. Calling `qe_calculate_mayer()` in
`SYSTEM_LOADED` (without prepare) returns `QE_ERROR_INVALID_STATE`.

## Current extension — MDM 1.1 and Phase 6

The additive v1 layer carries the full canonical model (atoms, geometry,
shells, primitives, AO map, normalization metadata, orbitals and optional S/P)
through the 44-symbol C ABI (17 legacy + 27 additive). Two paths are exposed:

1. **Direct P/S path:** the model supplies `matrices.S` and
   `matrices.P_total`; `qe_v1_model_commit()` prepares the Multiwfn globals.
   This is the frozen 0.2.0-compatible path.
2. **Original-routine state path:** `qe_v1_build_electronic_state()` builds
   the basis/orbital globals and calls the original `genSbas_curr` and `genP`
   (`prepare_from_orbitals=True` in Python). `genPprim` and the diagnostic
   Cartesian overlap are separate additive calls.

The original routines are compiled from `vendor/` without modification; the
dependency closure is `define`, `util`, `Bspline`, `2F2`, LIBRETA,
`function`, `sub`, `integral`, `PBC` and `bondorder`. `ifiletype=9` and
`ifPBC=0` are fixed by the wrapper and have no public setters. Derived
Cartesian-overlap and primitive-density caches are validity-checked and
invalidated on a new system/basis rebuild.

Spherical f is accepted in the original-routine state path when the model is
canonical MDM 1.2. g/h is rejected fail-closed; Cartesian f is not validated. cclib's real ORCA 6.1.1
text parser is blocked; synthetic conversion with an explicit basis is
supported. PBC, post-HF and ECP/EDF are not implemented. See
`LIMITATIONS.md` for the current scope.

## Memory layout

All matrices are **column-major (Fortran order)** at the C ABI boundary.

In Python:
```python
arr = np.asfortranarray(arr, dtype=np.float64)
assert arr.flags.f_contiguous
```

Coordinates convention:
- API Python-side: `(ncenter, 3)`
- Buffer at C ABI: `(3, ncenter)` — `coordinates.T` is sent

Mayer result matrix:
- Shape `(ncenter, ncenter)`, column-major
- Symmetric (so the row/column distinction is moot for this case)

## Files and responsibilities

| File | Role |
|------|------|
| `include/qe_multiwfn.h` | Public C ABI contract |
| `src/bridge/qe_c_api.f90` | Implements `bind(C)` functions; delegates to other modules |
| `src/bridge/qe_status.f90` | Status code constants |
| `src/bridge/qe_error_handler.f90` | Last-error storage; `qe_get_last_error` impl |
| `src/bridge/qe_memory.f90` | `c_f_pointer` helpers, validation |
| `src/bridge/qe_hyp2f2_stub.f90` | Stub for `hyp2F2` C symbol (no flint) |
| `src/engine/qe_engine_state.f90` | State machine |
| `src/engine/qe_engine_lifecycle.f90` | `qe_initialize`/`qe_finalize`/`qe_get_engine_state` |
| `src/state/qe_molecular_state.f90` | Canonical `qe_mol_t` type (MDM 1.1 fields) |
| `src/state/qe_state_builder.f90` | Validates model + pushes into Multiwfn globals |
| `src/state/qe_genp.f90` | Non-interactive adapter for original `genP` |
| `src/state/qe_genpprim.f90` | Non-interactive adapter for original `genPprim` |
| `src/state/qe_gensbas.f90` | Non-interactive adapter for `genSbas`/`genSbas_curr` |
| `src/state/qe_electronic_state.f90` | Full MDM → S/P → state orchestration |
| `src/analysis/qe_analysis_state.f90` | Result buffer storage |
| `src/analysis/qe_mayer.f90` | Mayer adapter — calls original `calcMayerbndord` |
| `include/qe_multiwfn_v1.h` | Additive MDM/v1 ABI contract |
| `python/qe_multiwfn/native.py` | ctypes wrapper; status→exception |
| `python/qe_multiwfn/engine.py` | `Engine` class (context manager) |
| `python/qe_multiwfn/molecular.py` | Legacy `MolecularSystem` dataclass |
| `python/qe_multiwfn/model_v1.py` | MDM 1.0/1.1 model and validation |
| `python/qe_multiwfn/normalization.py` | Primitive/contraction normalization metadata |
| `python/qe_multiwfn/adapters/orca.py` | ORCA 6.x JSON adapter |
| `python/qe_multiwfn/adapters/ase.py` | ASE geometry-only adapter |
| `python/qe_multiwfn/adapters/cclib.py` | cclib data adapter (ORCA parser fail-closed) |
| `python/qe_multiwfn/results.py` | `MayerResult` dataclass |
| `python/qe_multiwfn/exceptions.py` | Exception class hierarchy |
| `python/qe_multiwfn/analysis/bond_order.py` | Convenience `calculate_mayer()` |

## Source adapters and the universal builder (Phase 10)

All scientific sources converge on the same path:

```text
PySCF / ASE / ORCA / cclib / database records / NumPy
                         |
                 adapter or builder
                         |
              MolecularDataBuilder
                         |
              MolecularSystemV1 (MDM)
                         |
              strict/generated validation
                         |
                    Engine
                         |
              ctypes / C ABI / Fortran
```

`Engine` imports no adapter. PySCF and ASE are optional dependencies and are
imported only inside their adapter modules. The database connector protocol is
source-neutral and has no network/credential dependency. The native library,
ABI and frozen artifacts remain unchanged. Generated full-state matrices are
validated separately from source-supplied matrices; see
`PHASE10_NORMALIZATION_AUDIT.md`.
