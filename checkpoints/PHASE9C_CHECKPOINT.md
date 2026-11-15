# Phase 9C checkpoint — external scientific sources

**Status:** COMPLETE.
**Global verdict:** **PASS** for the Phase 9C acceptance scope, with documented
limits (PySCF spherical-f full state, Cartesian-d full normalization, no real
database connector, no PBC/DFT/post-HF/ECP).
**Phase 10:** not started.

## 1. Initial state

| Item | Value |
|---|---|
| Tree | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Python | `0.3.0.dev0` |
| MDM | `1.1.0` default; `1.2.0` opt-in |
| Native ABI | `0.2.0` |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Prior suite | 215 Python / CTest 6/6 |
| Environment | PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1 |

## 2. P0 — full-state validation

Full-state S is built by `genSbas_curr`; P by `genP`. Coefficients are the
source/builder coefficients, not normalized by the validation layer.

Measured generated `CᵀSC` errors:

| Case | Max |
|---|---:|
| ORCA H₂O/STO-3G | `7.78e-9` |
| ORCA H₂O/6-31G* spherical d | `1.08e-8` |
| ORCA H₂O/6-31G* Cartesian d | `2.11e-7` |
| ORCA H₂S/def2-TZVP f | `2.06e-8` |
| ORCA O₂/STO-3G UHF | `1.02e-8` / `1.09e-8` |
| ORCA O₂/STO-3G ROHF | `1.05e-8` |
| PySCF H₂O/STO-3G | `2.00e-8` |
| PySCF H₂O/6-31G* spherical d | `2.11e-7` |
| PySCF O₂/STO-3G UHF | `2.62e-8` / `2.58e-8` |
| PySCF O₂/STO-3G ROHF | `2.60e-8` |

Generated traces differ from Ne by at most `4.25e-7`. The Engine now validates
generated S/P dimensions, finiteness, symmetry, trace, generated `CᵀSC` and
method-specific idempotency. Generated-state bounds are:

- `GENERATED_STATE_ELECTRON_TOL = 1e-6`
- `GENERATED_STATE_ORTHONORM_TOL = 1e-6`

Source-supplied matrices retain the strict profile (`1e-10` orthonormality,
`1e-8` electron count). The generated bounds are scientifically tied to the
native integration precision, not a relaxation of source validation.

## 3. PySCF

API:

```python
from qe_multiwfn.adapters.pyscf import from_pyscf

mdm = from_pyscf(mol, mf)
```

Implemented in `python/qe_multiwfn/adapters/pyscf.py` using the existing
`MolecularDataBuilder`.

Supported:
- PySCF 2.15.0 RHF, UHF, ROHF;
- STO-3G RHF/UHF/ROHF;
- H₂O/6-31G* spherical d;
- H₂O/6-31G* Cartesian d on the direct path;
- H₂S/def2-TZVP spherical f on the direct path (canonical MDM 1.2);
- `include_overlap=False` full state for RHF/UHF/ROHF s/p/d;
- explicit AO permutation from PySCF to MDM order;
- `from_pyscf` rejects DFT, non-converged SCF, ECP, g/h, Cartesian f and
  unsupported post-HF.

Blocked:
- PySCF spherical-f full state (`include_overlap=False`) because native
  full-state f normalization/trace is not validated;
- PySCF Cartesian-d full state without S (normalization not inferred);
- DFT/post-HF/ECP.

## 4. ASE

`from_ase_atoms` and `from_ase` remain structural adapters.

- Extracts Z, positions, charge/multiplicity, source metadata.
- Angstrom → Bohr explicit.
- PBC is now fail-closed: any periodic direction raises `AseAdapterError`.
- No electronic state or basis is fabricated; `analysis_ready["mayer"]` is
  false.
- Composition with PySCF is documented: ASE geometry → PySCF Molecule/SCF →
  `from_pyscf`.

## 5. Database protocol

`python/qe_multiwfn/adapters/database.py` provides:

- `DatabaseRecord` with geometry, units, basis, method, orbitals, matrices,
  IDs, source and metadata;
- `from_database_record` mapping through `build_molecular_system`;
- provenance retaining record ID/source without connection details;
- no network, credentials, database engine or schema dependency.

Synthetic tests create two independent records with different IDs/sources and
identical arrays; both produce identical MDM and Mayer results.

## 6. cclib/ORCA audit

- Existing ORCA adapter remains unchanged and compatible.
- Existing cclib adapter remains fail-closed for the real ORCA 6.1.1 parser
  (`orcaparser.py:2799` in cclib 1.8.1).
- Synthetic cclib-like data with an explicit canonical basis still passes
  RHF/UHF/ROHF.
- No missing data is invented.

## 7. Tests

| Suite | Result |
|---|---|
| Python | **230 passed, 1 warning** |
| CTest | **6/6 passed** |
| Previous suite | 215 passed |
| Phase 9C additions | 15 (11 PySCF, 2 ASE, 2 database) |

The single warning is the pre-existing ASE/NumPy deprecation warning.

New tests:
- `tests/python/test_pyscf_adapter.py`
- `tests/python/test_ase_adapter_phase9c.py`
- `tests/python/test_database_adapter.py`

## 8. Files

Created:
- `python/qe_multiwfn/adapters/pyscf.py`
- `python/qe_multiwfn/adapters/database.py`
- `tests/python/test_pyscf_adapter.py`
- `tests/python/test_database_adapter.py`
- `tests/python/test_ase_adapter_phase9c.py`
- `docs/PYSCF_ADAPTER.md`
- `docs/ASE_ADAPTER.md`
- `docs/DATABASE_INPUT_PROTOCOL.md`
- `docs/SOURCE_EQUIVALENCE.md`
- `checkpoints/PHASE9C_CHECKPOINT.md`

Modified:
- `python/qe_multiwfn/adapters/ase.py` (PBC fail-closed, `from_ase` alias)
- `python/qe_multiwfn/engine.py` (generated `CᵀSC` check)
- `docs/MDM_VALIDATION.md`
- `docs/PUBLIC_API.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/LIMITATIONS.md`
- `README.md`

No Fortran, native library, ABI, vendor or frozen file was changed.

## 9. Integrity

| Item | Value |
|---|---|
| Dev library | `e9ac3a73f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | **44** = 17 legacy + 27 additive; no change |
| Vendor diff | 0 |
| Frozen packages | `sha256sum -c` OK |
| Canonical results | `6fb8b315…` |
| Manifest | `6aff745e…` |
| Native rebuild | not required |

Source hashes:

| File | SHA-256 |
|---|---|
| `adapters/pyscf.py` | `7406c933c4ed53a96bacb062d6dd2873c29748d50781c797ab4a835099a20704` |
| `adapters/database.py` | `4f43525b409814dec2a1c26ca86c607018e690ff6c7c7d2f97f40a0b55d69eae` |
| `adapters/ase.py` | `3ebbee552dece02888607a8bd56b5765c63f2414b28c67bdcd38913507f1fce0` |
| `engine.py` | `c97d59896cf72359cf8d3ab131ac80d5fb0552080387f53a5f75d82e2f92c080` |
| `test_pyscf_adapter.py` | `d45e189f7f4fbf8deb3fffdc72ae5030d6f9d238a40ae62c12482ceddae66753` |
| `test_database_adapter.py` | `5c093d803342b5b8f953ef5d05948c12e22a21cac6d59a3808177e4c24064ff9` |
| `test_ase_adapter_phase9c.py` | `ca57e05f273ef72c7e09e1cd69d770a193171d58b490f725ed773db7ad01fba3` |

Documentation hashes:

| File | SHA-256 |
|---|---|
| `PYSCF_ADAPTER.md` | `a7d44b46d966b43ec98d962b57e1d029068d1368381ed3250b9fab798eff05eb` |
| `ASE_ADAPTER.md` | `b5c50980d47599f7c68a3be2967a1111912344e51a6780dad0824860b1935cdc` |
| `DATABASE_INPUT_PROTOCOL.md` | `ba3ae29bf93691d9cafbf5523cc3638b0c7bcca2138539999305cc27c82ee4ca` |
| `SOURCE_EQUIVALENCE.md` | `0203c16a4f595dc78fae042e3d0e6a9e48241276913f6fbd68dfb7996a0482ff` |
| `PUBLIC_API.md` | `822051461f0ee4f4ca6187370c9c7024e75b7549a4eb685112653c5924cc9a29` |
| `MDM_VALIDATION.md` | `776322b864a8f9dda3c41f5dce9b47650665bba66716a51edcf53ad90f4767de` |
| `IMPLEMENTATION_STATUS.md` | `557f5d4edcb7f7e9fd53e885410f38ca74b198ce14bee24cd3f0391ee75246fc` |
| `LIMITATIONS.md` | `de4fab8e095788ea8be8ef97f951f61e69ebe0809f8a99e0df8cce590882c340` |
| `README.md` | `190b844aa1dc28c6361d49e3ba172f521506e59fb1a5215d5d641e9aee998f09` |

## 10. Acceptance matrix

| Area | Result |
|---|---|
| Full-state validation | **PASS** (differentiated source/generated bounds) |
| PySCF RHF | **PASS** |
| PySCF UHF | **PASS** |
| PySCF ROHF | **PASS** |
| AO ordering | **PASS** |
| Normalization | **PASS** (source-normalized; unsupported conventions fail closed) |
| Angular conventions | **PASS** (s/p/d/f spherical; d Cartesian direct) |
| ASE structural | **PASS** |
| ASE PBC | **FAIL-CLOSED** |
| Database protocol | **PASS** |
| Synthetic records | **PASS** |
| Builder integration | **PASS** |
| Engine integration | **PASS** |
| Source equivalence | **PASS** on validated cases |
| ORCA compatibility | **PASS** |
| Prior tests | **PASS** |
| ABI | **PASS** (unchanged 44) |
| Frozen | **PASS** |
| Vendor | **PASS** |
| Documentation | **PASS** |

## 11. Remaining limits

- PySCF spherical-f full state is blocked; direct PySCF f is validated.
- PySCF Cartesian-d full state without S is not inferred.
- DFT/post-HF/ECP/PBC remain outside the validated backend scope.
- g/h and Cartesian f remain blocked.
- No real database connector or network integration.
- cclib's real ORCA 6.1.1 parser remains blocked.
- PySCF versions other than 2.15.0 and ASE versions other than 3.29.0 are not
  validated.
- Source-equivalence tolerances are methodological SCF/integration bounds,
  not relaxations of the native source-matrix validation.

## 12. Gate

Phase 9C is complete. Phase 10 is not started. Recommended next step: a
focused adapter-hardening/validation phase for additional PySCF versions,
PySCF full-state f normalization, optional Cartesian-d full-state
normalization, and real database connectors behind the existing protocol.
