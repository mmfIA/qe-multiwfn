# Phase 13A — Git preparation and CI hardening audit

**Status:** PASS for the preparation scope.
**Scope:** local Git preparation only. No commit, remote, push, native rebuild,
scientific test run or artifact rebuild was performed.

## 1. Initial audit

| Item | Value |
|---|---|
| Repository root | `<repository>` |
| Python | 3.12.16 |
| Native library | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| `python/qe_multiwfn/libqe_multiwfn.so` | same hash |
| Frozen 0.2.0 library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Canonical results | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| Validation manifest | `6aff745e05feee71f9c2c9a6e47a854093353d50ad0dbcb059feaa1869fb97e6` |
| Build config | `pyproject.toml`, `setup.py`, `MANIFEST.in`, CMake |
| Git status | **not a Git repository**; no commit/remote |

Artifacts:

| Artifact | SHA-256 |
|---|---|
| Phase 11 wheel | `b7a106cbeae95cf5e2613f95370553cffe786864ae2c52c0f18a297af9446279` |
| Phase 11 sdist | `094a3ab74c8876026fe2644009601ae85c821ffd0b41570824275b784d002a68` |
| Phase 12 wheel | `397f9c221959b804939bd84748e716e1ac6ef1bd20d2d3e5bc1c49321ea97666` |
| Phase 12 sdist | `85096ed16da76b41f0158d7f35f4df2788d31b0029bd7231a664970b739162ff` |

## 2. Build and packaging audit

`pyproject.toml` uses setuptools, package-dir `python`, package data
`libqe_multiwfn.so`, and optional extras:

- PySCF `>=2.14,<2.16`;
- ASE `>=3.28,<3.30`;
- cclib `1.8.1`;
- full.

`setup.py` marks the distribution as binary/platform-specific. `MANIFEST.in`
includes README, docs and the packaged `.so` in the sdist. The package version
is 0.3.0.

No build configuration changes were needed in Phase 13A.

## 3. CI audit and changes

The Phase 12 workflow was audited and corrected:

| Finding | Correction |
|---|---|
| Build dependencies did not explicitly pin `setuptools>=68`/`wheel`/`build` | Added explicit install |
| `gcc` was not explicit in job 1 system packages | Added `gcc` |
| Optional job lacked native runtime system packages | Added `libopenblas-dev` and `libgfortran5` |
| Optional job used `--no-deps` while installing optional packages | Removed `--no-deps`; transitives resolve normally |
| cclib import was not checked | Added `CclibAdapterError`/`from_cclib_data` import |
| Full-extra install could miss NumPy/transitives | NumPy and wheel are installed with resolved dependencies |

The two jobs remain:

1. `build-test` — wheel/sdist, native CMake build, CTest, Python suite,
   isolated wheel install, installed smoke test.
2. `optional-full` — wheel build, system runtime packages, PySCF 2.15.0,
   ASE 3.29.0, cclib 1.8.1, import checks.

No `continue-on-error`; no unsupported platform/Python matrix claim; target
remains Linux x86_64 / Python 3.12.

Hosted execution is not part of Phase 13A and remains unavailable because the
source tree is not a Git/GitHub repository.

## 4. `.gitignore`

Created with explicit tracking decisions:

**Ignored**
- `__pycache__/`, `*.py[cod]`, pytest/mypy/ruff caches;
- `.coverage`, htmlcov;
- `*.egg-info/`, eggs, generic `/build/`, generic `/dist/`;
- root `/build_audit/`, `/build_ci/`;
- CMakeFiles, CMake cache/install files, objects, modules, static/shared
  library build products, editors/OS files, venvs/local toolchains, scratch
  files.

**Tracked intentionally**
- `python/qe_multiwfn/libqe_multiwfn.so` (no global `*.so` ignore);
- `python/libqe_multiwfn.so`;
- `vendor/`;
- `docs/`;
- `checkpoints/`;
- `reports/` (including `reports/build/`);
- `dist-phase11/` and `dist-phase12/`;
- `.github/workflows/ci.yml`.

The anchored `/build/` avoids ignoring `reports/build/`.

## 5. Git validation without initializing the source repository

A temporary repository under `/tmp/qe_gitcheck` was used only to evaluate the
patterns. It was not created under the project tree.

Results:

- tracked: source `.so`, `vendor/`, docs, checkpoints, reports,
  `dist-phase11`, `dist-phase12`, `.github/workflows/ci.yml`;
- ignored: `__pycache__`, `build`, `build_audit`, `build_ci`,
  `.pytest_cache`, `*.egg-info`, `*.tmp`.

No Git commit, remote, push, reset or checkout was performed.

## 6. Files for the first commit

| Category | Content |
|---|---|
| Source | `src/`, `include/`, `python/qe_multiwfn/` Python modules, `python/libqe_multiwfn.so`, package `.so` |
| Scientific core/vendor | `vendor/`, CMake config, `cmake/` |
| Tests | `tests/`, native tests, Python tests |
| Documentation | `README.md`, `docs/` |
| Checkpoints | `checkpoints/` |
| Build/config | `CMakeLists.txt`, `pyproject.toml`, `setup.py`, `MANIFEST.in`, `scripts/`, `.gitignore` |
| CI | `.github/workflows/ci.yml` |
| Distribution | `dist-phase11/`, `dist-phase12/` |
| Examples/reports | `examples/`, `reports/`, release manifests |
| Local/generated (ignored) | build trees, caches, egg-info, generic dist, venv, scratch |

## 7. Validation

- YAML parsed successfully with PyYAML.
- `.gitignore` patterns evaluated in a temporary Git repository.
- Native library hash unchanged.
- Both packaged `.so` copies unchanged.
- `dist-phase11` and `dist-phase12` hashes unchanged.
- Vendor diff: 0.
- Frozen packages: `sha256sum -c` OK.
- No native rebuild.
- No scientific tests executed in this preparation phase.
- No source, ABI, Fortran, scientific tolerance or reference result changed.

## 8. Limitations

- Hosted CI remains unexecuted.
- The tree is not yet a Git repository; no commit/remote exists.
- Only the local workflow/configuration was validated.
