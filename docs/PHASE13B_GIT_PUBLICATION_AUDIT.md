# Phase 13B — Git publication audit

**Status:** PASS.
**Scope:** Git initialization, first commit, publication to
`mmfIA/qe-multiwfn`, and first hosted GitHub Actions execution.

## A. Identification

| Item | Value |
|---|---|
| Repository root | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Distribution version | `0.3.0` |
| Molecular Data Model | `1.1.0` |
| Native ABI | `0.2.0` (preserved) |
| Remote | `git@github.com:mmfIA/qe-multiwfn.git` |
| Public URL | https://github.com/mmfIA/qe-multiwfn |
| Branch | `main` |
| Initial commit | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Commit date | `2026-11-14T22:21:45-04:00` |
| Push/CI time | `2026-11-15T02:22:07Z` |

The frozen 0.2.0 tree under `../qe_multiwfn_src` was read only for integrity
comparison and was not modified.

## B. Inventory

### Versioned content (first commit)

271 files, 406,768 inserted lines, 23,973,615 bytes in the working tree
(6.44 MiB of loose Git objects).

| Directory | Files |
|---|---|
| `vendor/` | 74 |
| `docs/` | 64 |
| `tests/` | 45 |
| `python/` | 22 |
| `src/` | 16 |
| `checkpoints/` | 16 |
| `reports/` | 8 |
| `scripts/` | 6 |
| `cmake/` | 5 |
| `examples/` | 3 |
| `include/` | 2 |

Top-level files: `CMakeLists.txt`, `README.md`, `pyproject.toml`,
`setup.py`, `MANIFEST.in`, `.gitignore`, `RELEASE_MANIFEST.txt`,
`RELEASE_MANIFEST_0.2.0.txt`,
`DOCUMENTATION_RECONCILIATION_REPORT.md`.

Tracked native/runtime assets:

- `python/qe_multiwfn/libqe_multiwfn.so` (packaged wheel payload);
- `python/libqe_multiwfn.so` plus development symlinks
  `libqe_multiwfn.so.0` and `libqe_multiwfn.so.0.2.0`;
- `vendor/Multiwfn_2026.11.3_src_Linux/dislin_d-11.0.a` (forced past the
  generic `*.a` ignore so the vendored upstream tree stays verbatim).

### Deliberately excluded from publication

| Item | Decision |
|---|---|
| `dist-phase11/`, `dist-phase12/` | Historical wheels/sdists kept on disk; not published. Added to `.git/info/exclude` so the working tree stays clean. |
| `build/`, `build_audit/` | Local build trees; ignored. |
| `.pytest_cache/`, `__pycache__/`, `*.pyc`, `*.pyo` | Caches; ignored. |
| `python/qe_multiwfn.egg-info/` | Generated metadata; ignored. |
| Generic `dist/`, `*.egg-info/`, venvs, scratch files | Ignored. |

Exclusion of the historical distributions follows the Phase 13B rule not to
publish unnecessary wheels/sdists. Source, build configuration, tests, and the
packaged native library are sufficient to reproduce the build.

## C. Security

- Token, private-key, password, API-key and `.env` scans over the staged and
  committed content: no matches.
- No credentials, SSH keys, database credentials, or environment files were
  published.
- `.gitignore` reviewed: no global `*.so` exclusion; `/build/` and
  `/build_audit/` are anchored so `reports/build/` remains tracked.
- Four checkpoint files and one reconciliation report still contain the
  absolute development path `/home/fsia/...`; two ORCA fixture outputs embed
  the original ORCA working directory. These are provenance records, not
  secrets, and were retained.
- **Licensing status:** the project has no root `LICENSE` file and the vendored
  Multiwfn tree ships no license/notice text in this snapshot. No license was
  invented. This is an open governance item for Phase 13C and does not block
  the technical publication performed here.

## D. Integrity

| Check | Result |
|---|---|
| Dev library `python/qe_multiwfn/libqe_multiwfn.so` | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Dev library `python/libqe_multiwfn.so` | same hash |
| Frozen 0.2.0 library | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` (confirmed in `../qe_multiwfn_src`) |
| Phase 12 wheel | `397f9c221959b804939bd84748e716e1ac6ef1bd20d2d3e5bc1c49321ea97666` (unchanged, local) |
| Phase 12 sdist | `85096ed16da76b41f0158d7f35f4df2788d31b0029bd7231a664970b739162ff` (unchanged, local) |
| ABI symbols | 44 = 17 legacy (`QE_MULTIWFN_0.1.1`) + 27 additive (`QE_MULTIWFN_0.2.0`) |
| Vendor diff vs frozen tree | empty (identical) |
| Native rebuild | none |
| Scientific source/ABI changes | none |

No Fortran, C, header, scientific Python module, adapter, normalization,
MDM, engine, builder, tolerance, fixture, reference result, frozen tree, or
distribution artifact was altered during Phase 13B.

## E. Git

| Item | Value |
|---|---|
| Commit | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Message | `Initial release: QE-Multiwfn 0.3.0` |
| Branch | `main` |
| Remote | `origin` → `git@github.com:mmfIA/qe-multiwfn.git` |
| Push | `* [new branch] main -> main`; no force, no divergence |
| Remote `refs/heads/main` | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Working tree after commit | clean |

No existing `.git` directory was overwritten and no remote other than
`mmfIA/qe-multiwfn` was configured.

## F. GitHub Actions

| Item | Value |
|---|---|
| Workflow | `qe-multiwfn-ci` |
| Run ID | `43667450749` |
| Run URL | https://github.com/mmfIA/qe-multiwfn/actions/runs/43667450749 |
| Commit tested | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Trigger | `push` to `main` |
| Conclusion | **success** |
| Duration | 5m04s |
| Runner | GitHub-hosted `ubuntu-26.04`, CPython 3.12.16 |

Jobs:

| Job | ID | Result | Duration |
|---|---|---|---|
| `build-test (3.12)` | `132669876343` | success | 4m28s |
| `optional-full` | `132670989881` | success | 32s |

`build-test` steps, all successful: checkout; setup-python 3.12; system
dependencies (gfortran, gcc, cmake, OpenBLAS); Python build dependencies;
wheel + sdist build; CMake configure/build with tests; CTest; Python
development suite; isolated wheel install; installed-package smoke test.

Measured results:

- CTest: 6/6 passed (`lifecycle_c`, `memory_transfer_c`,
  `error_handling_c`, `mayer_c`, `v1_abi_c`, `uhf_abi_c`).
- Python development suite: **82 passed, 20 skipped**.
- Installed wheel: `PASS 0.3.0` against the wheel-packaged
  `libqe_multiwfn.so`.
- `optional-full`: wheel build and install with PySCF 2.15.0, ASE 3.29.0 and
  cclib 1.8.1; import check printed `0.3.0`.

Annotations were non-failing warnings only: Node.js 20 action deprecation and
the `ubuntu-latest` image migration notice.

## G. Limitations

1. Historical `dist-phase11/` and `dist-phase12/` wheels/sdists were preserved
   locally but not published; no GitHub Release assets were created.
2. The external validation tree `QE-Multiwfn-validation` is not part of this
   repository. Consequently 20 Python tests that depend on those scientific
   fixtures skip on hosted CI (the suite remains green and self-contained).
3. No root `LICENSE` and no bundled upstream Multiwfn license/notice text;
   licensing must be resolved before a formal redistributable release.
4. Hosted CI covers only Linux x86_64 / CPython 3.12; no Windows, macOS, ARM,
   or additional Python versions are claimed.
5. The workspace image is currently `ubuntu-26.04` under the `ubuntu-latest`
   label; a documented future label migration may change the base image.
6. Local provenance documents retain absolute `/home/fsia/...` paths.
7. The documentation commit that adds this audit triggers an additional CI run;
   the results above correspond to the initial release commit.
