# Phase 12 checkpoint — operational validation and distribution policy

**Status:** COMPLETE locally.
**Global verdict:** **PARTIAL** — all locally executable work passed, but the
required hosted CI execution is **BLOCKED** because this tree is not a Git/
GitHub repository with an available runner.

## 1. Starting state

| Item | Value |
|---|---|
| Tree | `<repository>` |
| Package | 0.3.0 |
| Native ABI | 0.2.0 |
| Native library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Prior suite | 232 Python / CTest 6/6 |
| Environment | Linux x86_64, Python 3.12.16, NumPy 2.5.4, PySCF 2.15.0, ASE 3.29.0 |

## 2. CI

- Workflow audited: `.github/workflows/ci.yml`.
- YAML syntax valid.
- **Hosted execution: BLOCKED**; no Git repository/remote exists.
- No URL/run ID/commit fabricated.
- Local equivalents executed: CTest 6/6, Python suite, wheel/sdist install,
  smoke test, optional imports, ldd/ABI.

See `PHASE12_CI_RESULTS.md`.

## 3. Additional compatibility matrix

Executed in an isolated venv:

| Component | Version | Result |
|---|---|---|
| NumPy | 2.4.6 | PASS |
| PySCF | 2.14.0 | PASS (18 PySCF/ASE tests) |
| ASE | 3.28.0 | PASS (structural) |
| cclib | 1.8.1 | partial as documented |

Reference 2.15.0/3.29.0 remains tested. Other versions are not claimed.

## 4. Distribution policy

Official target: **Linux x86_64 / CPython 3.12**.

- wheel tag: `cp312-cp312-linux_x86_64`;
- not manylinux;
- no Windows/macOS/ARM/other ABI claim;
- external system dependencies: OpenBLAS, libgfortran, libgcc, libm, libc;
- RUNPATH `$ORIGIN`;
- sdist contains Python code, docs and native library; installation does not
  rebuild native code;
- sdist not claimed bit-for-bit reproducible.

See `DISTRIBUTION_POLICY.md`, `DEPENDENCIES.md`, `INSTALLATION_VALIDATION.md`.

## 5. DatabaseProvider

- Contract audited;
- external provider implemented in the test module and passes;
- in-memory reference provider retained;
- no real external connector, network, credentials or mandatory dependency.

See `DATABASE_PROVIDER_CONFORMANCE.md`.

## 6. Scientific boundaries preserved

- PySCF Cartesian-d full remains BLOCKED;
- DFT/post-HF/ECP/PBC blocked;
- g/h and Cartesian f blocked;
- cclib ORCA 6.1.1 fail-closed;
- H₂S difference remains documented cross-backend SCF difference;
- p order is `pz, px, py` and is explicitly tested.

## 7. Tests

| Suite | Result |
|---|---|
| Python | **233 passed, 1 warning** |
| CTest | **6/6 passed** |
| Prior | 232 |
| New Phase 12 | external provider conformance test |
| Extra matrix | 18 relevant PySCF/ASE tests PASS |
| Wheel/sdist install | PASS |
| Installed smoke | PASS |
| Hosted CI | **BLOCKED** |

## 8. Integrity

| Item | Value |
|---|---|
| Native library | `e9ac3a73…` |
| Frozen | `9560c0fc…` |
| ABI | 44 = 17 legacy + 27 additive |
| Vendor | diff empty |
| Frozen packages | `sha256sum -c` OK |
| Canonical refs | `6fb8b315…` |
| Manifest | `6aff745e…` |
| Native rebuild | none |
| Fortran/ABI | unchanged |

## 9. Documentation

Created/updated:
- `PHASE12_CI_RESULTS.md`
- `DISTRIBUTION_POLICY.md`
- `COMPATIBILITY_MATRIX.md`
- `DEPENDENCIES.md`
- `INSTALLATION_VALIDATION.md`
- `DATABASE_PROVIDER_CONFORMANCE.md`
- `RELEASE_PROCESS.md`
- `PHASE12_CHECKPOINT.md`
- README/status/limitations/architecture/packaging/installation

## 10. Acceptance

| Area | Result |
|---|---|
| Hosted CI | **BLOCKED** |
| Local build/CTest | PASS |
| Local Python suite | PASS |
| Wheel/sdist install | PASS |
| Minimal install | PASS |
| Optional dependencies | PASS |
| Distribution policy | PASS |
| Additional versions | PASS for tested versions |
| DatabaseProvider conformance | PASS |
| Integrity | PASS |
| Scientific regression | PASS |

## 11. Remaining work

- Execute hosted CI once a Git/GitHub remote is available and record the URL.
- Decide whether to pursue manylinux/multi-platform support.
- Test additional Python/NumPy versions only with real evidence.
- Evaluate a real optional DatabaseProvider connector.
- Native Cartesian-d full-state work requires a separate authorized phase.

## 12. Gate

Phase 12 is complete locally but **not globally PASS** because hosted CI is
BLOCKED. Phase 13 is not started.
