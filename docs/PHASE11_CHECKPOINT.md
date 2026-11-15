# Phase 11 checkpoint — distribution, compatibility and operational maturity

**Status:** COMPLETE.
**Global verdict:** **PASS** for the implemented/tested Phase 11 scope, with
documented platform, version, Cartesian-d and external-provider limits.

## 1. Starting state

| Item | Value |
|---|---|
| Tree | `<repository>` |
| Python | `0.3.0` (packaged) |
| MDM | `1.1.0` default; `1.2.0` opt-in |
| Native ABI | `0.2.0` |
| Dev library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Prior tests | 231 Python / CTest 6/6 |
| Environment | PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1, NumPy 2.5.4, Python 3.12.16 |

## 2. Packaging

Configuration:

- `pyproject.toml` with setuptools backend;
- minimal `setup.py` `BinaryDistribution` marker for a platform-specific wheel;
- `MANIFEST.in` for sdist documentation and package `.so`;
- package name `qe-multiwfn`, import `qe_multiwfn`, version `0.3.0`;
- package-data `qe_multiwfn/libqe_multiwfn.so`;
- NumPy required; PySCF/ASE/cclib optional extras pinned to tested versions.

Artifacts:

```text
dist-phase11/qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl
dist-phase11/qe_multiwfn-0.3.0.tar.gz
```

`python/qe_multiwfn/libqe_multiwfn.so` is byte-identical to the validated dev
library. The wheel carries the library inside the package; the native loader
uses the package directory, not a hard-coded development path.

Excluded from wheel: tests, vendor, frozen source, build directories, caches.
Sdist includes Python code, documentation and the native library.

## 3. Isolated installation

Created `/tmp/qe_multiwfn_phase11` with only NumPy (no PySCF/ASE/cclib).
Installed the wheel, then verified:

```text
version 0.3.0
lib <venv>/site-packages/qe_multiwfn/libqe_multiwfn.so
native ABI 0.2.0
optional modules loaded []
Mayer 2x2 result [[1,1],[1,1]]
readiness {'mayer': True}
```

The sdist was subsequently force-installed into the same venv and imported
successfully. No repository `PYTHONPATH` or absolute development library path
was used.

Optional-dependency probes without PySCF/ASE/cclib produced specific errors:

```text
PyscfAdapterError: PySCF is not available; install with ...
AseAdapterError: ASE is not available; install with ...
CclibAdapterError: cclib is not available; install with ...
```

## 4. Native library / ABI

- Installed library hash must match `e9ac3a73…`.
- Native ABI remains `0.2.0`, 17 legacy + 27 additive = 44 symbols.
- RUNPATH `$ORIGIN`; system dependencies: OpenBLAS, libgfortran, libgcc,
  libm, libc.
- No native source, shared library, header declaration or frozen artifact was
  changed.
- No native rebuild was performed.

## 5. CI and compatibility

Created `.github/workflows/ci.yml` with:

- Python 3.12 Ubuntu job;
- wheel/sdist build;
- native CMake build and CTest;
- Python suite;
- isolated wheel install and installed-package smoke test;
- full optional-extras import job.

The workflow is configured but was not executed on a hosted GitHub runner in
this environment. Local isolated install is the executed evidence.

Compatibility matrix is documented in `docs/COMPATIBILITY_MATRIX.md`: only
Python 3.12, NumPy 2.5.4, PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1 and Linux
x86_64 are tested. No other version is claimed.

## 6. Cartesian-d

The full-state PySCF Cartesian-d path remains **BLOCKED**:

- direct S/P path is valid;
- direct generated S/P matches source;
- native `build_electronic_state` full path fails its trace check;
- no normalization factor is invented and no tolerance is relaxed;
- `from_pyscf(..., include_overlap=False)` raises `PyscfAdapterError`.

See `docs/CARTESIAN_D_NORMALIZATION.md`.

## 7. H₂S/def2-TZVP equivalence

The direct/full PySCF vs ORCA difference was investigated independently of
the internal generated-state bound:

- S max `3.64e-9`; diagonal agrees within `4.4e-16`;
- P_total max `2.86e-6`;
- C differs by SCF orbital signs/rotations, as expected;
- Mayer difference `5.97e-7` direct, `1.02e-6` full;
- difference is distributed across the matrix, not concentrated in f;
- no reference or tolerance change is required.

It is a cross-backend SCF numerical/density difference, not an angular or
normalization failure. See `docs/SOURCE_EQUIVALENCE_PHASE10.md` and
`docs/SOURCE_EQUIVALENCE_PHASE11.md`.

## 8. Public API / p ordering

- Correct MDM p order: `pz, px, py`.
- PySCF source p order: `px, py, pz`; adapter maps to `pz, px, py`.
- Added an explicit test asserting distinct p components and Multiwfn codes
  `4,2,3`.
- Corrected/consistent documentation.
- No scientific transformation change was needed because the transformation
  was already correct.

## 9. DatabaseProvider

- `DatabaseProvider` protocol and `InMemoryDatabaseProvider` retained.
- `from_database_provider` added/validated.
- No real database/network connector is claimed.
- Core import does not require a provider or database package.

## 10. Tests

| Suite | Result |
|---|---|
| Python | **232 passed, 1 warning** |
| CTest | **6/6 passed** |
| Prior | 231 |
| New Phase 11 | 1 explicit p-component test |
| Installed wheel | PASS |
| Installed sdist | PASS |
| Optional-dependency failure messages | PASS |
| Warning | pre-existing ASE/NumPy deprecation |

Logs: `MDM_1.1_work/PHASE11/phase11_pytest.log`,
`phase11_ctest.log`.

## 11. Files

Created:
- `pyproject.toml`, `setup.py`, `MANIFEST.in`
- `.github/workflows/ci.yml`
- `tests/installed_smoke.py`
- `docs/PACKAGING.md`, `INSTALLATION.md`, `COMPATIBILITY_MATRIX.md`, `CI.md`,
  `CARTESIAN_D_NORMALIZATION.md`, `DATABASE_PROVIDER.md`,
  `SOURCE_EQUIVALENCE_PHASE11.md`, `PHASE11_CHECKPOINT.md`
- `dist-phase11/` wheel and sdist

Modified:
- `python/qe_multiwfn/__init__.py` version `0.3.0`
- `python/qe_multiwfn/adapters/pyscf.py` (full-f normalization, explicit
  Cartesian-d block)
- `python/qe_multiwfn/adapters/database.py` (provider API)
- `python/qe_multiwfn/adapters/ase.py` (optional-dependency message)
- `python/qe_multiwfn/adapters/cclib.py` (optional-dependency message)
- `tests/python/test_pyscf_adapter.py`, `test_database_adapter.py`
- `README.md`, `docs/ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`,
  `LIMITATIONS.md`, `MDM_VALIDATION.md`, `SOURCE_EQUIVALENCE.md`,
  `SOURCE_EQUIVALENCE_PHASE10.md`, `PUBLIC_API.md`
- copied `python/libqe_multiwfn.so` into `python/qe_multiwfn/` as package data

No Fortran, native source, ABI, vendor or frozen artifact changed.

## 12. Integrity

| Item | Value |
|---|---|
| Native library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | 44 = 17 legacy + 27 additive |
| Vendor diff | 0 |
| Frozen packages | `sha256sum -c` OK |
| Canonical refs | `6fb8b315…` |
| Manifest | `6aff745e…` |
| Native rebuild | none |

Artifact hashes are recorded separately in
`MDM_1.1_work/PHASE11/phase11_artifact_hashes.txt`; full source/docs hashes in
`phase11_final_hashes.txt`.

## 13. Acceptance matrix

| Area | Result |
|---|---|
| Wheel | **PASS** |
| Sdist | **PASS** |
| Metadata/version | **PASS** |
| Isolated install | **PASS** |
| Minimal core/Engine/Mayer | **PASS** |
| Optional dependencies | **PASS** (specific errors) |
| CI configuration | **PASS (not hosted-run)** |
| Python/PySCF/ASE matrix | **PASS for tested versions only** |
| Cartesian-d full | **BLOCKED** justified |
| H₂S difference | **PASS investigated/documented** |
| p ordering | **PASS** |
| DatabaseProvider | **PASS** |
| Prior tests | **PASS** |
| ABI/frozen/vendor | **PASS** |
| Documentation | **PASS** |

## 14. Remaining limits / pending

- Platform wheel only Linux x86_64/CPython 3.12; no Windows/macOS/ARM.
- Hosted CI was not executed here.
- PySCF versions other than 2.15.0 and ASE versions other than 3.29.0 are
  untested.
- PySCF Cartesian-d full state blocked.
- No real database connector.
- PBC/DFT/post-HF/ECP/g/h/Cartesian f remain out of scope.
- cclib real ORCA parser remains blocked.
- Sdist includes documentation but the native library is platform-specific.
- License/upstream terms are documented in README; no new project license was
  asserted.

## 15. Gate

Phase 11 is complete. Phase 12 is not started. Recommended next phase:
multi-platform packaging (or a deliberate Linux-only support policy), hosted
CI execution, Python/NumPy/PySCF version matrix, and an authorized native
Cartesian-d full-state investigation if that feature is required.
