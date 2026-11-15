# Phase 13A checkpoint — Git preparation and CI hardening

**Status:** **PASS** for the preparation scope.
**Git commit:** none.
**Remote:** none.
**Push:** none.
**Native rebuild:** none.

## 1. Starting state

| Item | Value |
|---|---|
| Root | `<repository>` |
| Python | 3.12.16 |
| Package | 0.3.0 |
| Native library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | 44 = 17 legacy + 27 additive |
| Phase 12 wheel | `397f9c221959b804939bd84748e716e1ac6ef1bd20d2d3e5bc1c49321ea97666` |
| Phase 12 sdist | `85096ed16da76b41f0158d7f35f4df2788d31b0029bd7231a664970b739162ff` |
| Git repository | absent |
| Hosted CI | not part of 13A; still unavailable |

## 2. Files created/modified

Created:
- `.gitignore`
- `docs/PHASE13A_PREPARATION_AUDIT.md`
- `checkpoints/PHASE13A_CHECKPOINT.md`

Modified:
- `.github/workflows/ci.yml`

No Fortran, ABI header, scientific Python module, native library, package
`.so`, scientific reference, tolerance, frozen artifact or distribution
artifact was modified.

## 3. CI corrections

- Explicit `setuptools>=68`, `wheel`, `build`, `pytest`, NumPy in the build
  job.
- Explicit `gcc` alongside gfortran/cmake/OpenBLAS.
- Optional job now installs native runtime system packages.
- Optional job no longer uses `--no-deps` for optional packages; transitives
  resolve normally.
- cclib import is checked.
- No `continue-on-error`.
- Target remains Linux x86_64 / CPython 3.12; no Windows/macOS/ARM/manylinux
  claim.

YAML syntax check: PASS.

## 4. `.gitignore` validation

Validated in a temporary `/tmp` Git repository (not the project tree):

- essential files tracked: package native `.so`, vendor, docs, checkpoints,
  reports, dist-phase11/12, workflow;
- ignored: `__pycache__`, `build`, `build_audit`, `build_ci`,
  `.pytest_cache`, `*.egg-info`, temporary files;
- no global `*.so` ignore;
- `/build/` anchored so `reports/build/` remains tracked.

No source repository was initialized, committed, reset, cleaned or pushed.

## 5. Versionable inventory

First commit is intended to include:
- `src/`, `include/`, `python/`, `vendor/`, `tests/`;
- `CMakeLists.txt`, `cmake/`, `scripts/`, `examples/`;
- `docs/`, `checkpoints/`, `reports/`, release manifests;
- `pyproject.toml`, `setup.py`, `MANIFEST.in`, `.gitignore`;
- `.github/workflows/ci.yml`;
- `dist-phase11/` and `dist-phase12/`;
- README/license notices.

Ignored: build trees, caches, egg-info, generic `dist/`, venvs, local scratch.
No file was removed.

## 6. Integrity

| Check | Result |
|---|---|
| Native hash | `e9ac3a73…` unchanged |
| Package `.so` hash | `e9ac3a73…` unchanged |
| Frozen hash | `9560c0fc…` unchanged |
| Frozen packages | `sha256sum -c` OK |
| Vendor diff | 0 |
| Phase 12 wheel/sdist | unchanged |
| Phase 11 wheel/sdist | unchanged |
| Forbidden destructive Git ops | none |
| Native build/test run | none |

## 7. Limitations

- Hosted CI is not executed; tree is not a Git/GitHub repository.
- No first commit created, by instruction.
- No remote configured or pushed.
- `.gitignore` validation used a temporary repository only.

## 8. Gate

Phase 13A is complete and ready for a Git repository initialization/commit
phase. Phase 13B is not started.
