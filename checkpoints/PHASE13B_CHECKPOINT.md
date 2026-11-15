# Phase 13B checkpoint — Git initialization and GitHub publication

**Status:** **PASS**.
**Initial commit:** `0c4b65f37a4696940d9030e07e6c8ce64191c3c2`.
**Remote:** `git@github.com:mmfIA/qe-multiwfn.git`.
**Hosted CI:** run `43667450749`, conclusion **success**.

## 1. Starting state

| Item | Value |
|---|---|
| Root | `/home/fsia/Quimica/qe_multiwfn_030_dev` |
| Package | `0.3.0` |
| MDM | `1.1.0` |
| Native ABI | `0.2.0` |
| Dev library SHA-256 | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` |
| Frozen 0.2.0 SHA-256 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| Phase 12 wheel SHA-256 | `397f9c221959b804939bd84748e716e1ac6ef1bd20d2d3e5bc1c49321ea97666` |
| Phase 12 sdist SHA-256 | `85096ed16da76b41f0158d7f35f4df2788d31b0029bd7231a664970b739162ff` |
| ABI | 44 = 17 legacy + 27 additive |
| Prior Git repository | absent (initialized in this phase) |
| Hosted CI before 13B | never executed |

## 2. Actions performed

1. Verified project identity, GitHub CLI account `mmfIA`, SSH authentication,
   and target repository visibility (PUBLIC).
2. Confirmed no existing `.git`; initialized Git and renamed the branch to
   `main`.
3. Reviewed `.gitignore`, `.github/workflows/ci.yml`, Phase 13A documents, and
   validated the workflow YAML.
4. Inventoried the tree; explicitly staged source, vendor, tests, docs,
   checkpoints, reports, build configuration, CI, and native libraries.
5. Force-added `vendor/.../dislin_d-11.0.a` so the vendored upstream tree
   remains complete despite the generic `*.a` ignore.
6. Excluded `dist-phase11/` and `dist-phase12/` from the first commit via
   `.git/info/exclude`; the files remain on disk unchanged.
7. Re-verified library, frozen, wheel, sdist hashes and the ABI counts;
   confirmed `vendor/` is identical to the frozen tree.
8. Created the initial commit, added the `origin` remote, verified the remote
   was empty, and pushed `main` without force.
9. Monitored the hosted workflow to real completion, not just trigger.
10. Created `docs/PHASE13B_GIT_PUBLICATION_AUDIT.md` and this checkpoint.

No scientific source, ABI header, adapter, normalization, MDM, engine,
builder, tolerance, fixture, reference result, frozen artifact, or historical
distribution was modified. No native rebuild was performed.

## 3. First commit

| Item | Value |
|---|---|
| Commit | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Message | `Initial release: QE-Multiwfn 0.3.0` |
| Branch | `main` |
| Files | 271 |
| Insertions | 406,768 |
| Working-tree bytes | 23,973,615 |
| Loose Git objects | 6.44 MiB |

Tracked highlights: `src/` (16), `include/` (2), `python/` (22, including
both `libqe_multiwfn.so` copies and the `.so.0` symlinks), `vendor/` (74,
including `dislin_d-11.0.a`), `tests/` (45), `cmake/` (5), `scripts/` (6),
`examples/` (3), `docs/` (64), `checkpoints/` (16), `reports/` (8),
`.github/workflows/ci.yml`, and build packaging files.

Not published: `dist-phase11/`, `dist-phase12/`, `build/`, `build_audit/`,
caches, `egg-info`, generic `dist/`, venvs, scratch.

## 4. Remote and push

```
origin  git@github.com:mmfIA/qe-multiwfn.git (fetch)
origin  git@github.com:mmfIA/qe-multiwfn.git (push)
```

- `git ls-remote origin` before push: empty (new repository).
- Push result: `* [new branch] main -> main`; tracking set to `origin/main`.
- Remote `refs/heads/main` equals the local commit hash.
- No `--force`, no remote overwrite, no unrelated repository used.

## 5. Hosted CI

| Item | Value |
|---|---|
| Workflow | `qe-multiwfn-ci` |
| Run ID | `43667450749` |
| URL | https://github.com/mmfIA/qe-multiwfn/actions/runs/43667450749 |
| Commit | `0c4b65f37a4696940d9030e07e6c8ce64191c3c2` |
| Event | push to `main` |
| Conclusion | success (5m04s) |
| Runner | GitHub-hosted `ubuntu-26.04`, CPython 3.12.16 |

| Job | ID | Result |
|---|---|---|
| `build-test (3.12)` | `132669876343` | success (4m28s) |
| `optional-full` | `132670989881` | success (32s) |

Validated on the hosted runner:

- wheel and sdist built (`qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl`,
  `qe_multiwfn-0.3.0.tar.gz`);
- CMake native build completed;
- CTest 6/6 passed;
- Python suite: 82 passed, 20 skipped;
- isolated wheel install and installed smoke test: `PASS 0.3.0`;
- optional stack import check with PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1:
  printed `0.3.0`.

Only non-failing warnings: Node.js 20 action deprecation and the
`ubuntu-latest` image migration notice.

## 6. Integrity

| Check | Result |
|---|---|
| Dev library hash | `e9ac3a73…` unchanged |
| Frozen library hash | `9560c0fc…` unchanged |
| Phase 12 wheel/sdist | unchanged |
| Vendor diff vs frozen tree | empty |
| ABI | 44 = 17 legacy + 27 additive |
| Scientific modifications | none |
| Native rebuild | none |
| Sensitive files published | none detected |

## 7. Open items for Phase 13C

1. Add a root `LICENSE` and upstream Multiwfn/Dislin notices before a formal
   redistributable release (not invented in this phase).
2. Decide whether to publish historical `dist-phase11/`/`dist-phase12/`
   artifacts or attach them to a GitHub Release.
3. Decide whether to publish the external `QE-Multiwfn-validation` scientific
   fixtures so the 20 skipped Python tests can run in hosted CI.
4. Optionally expand the CI matrix (Python versions and/or platforms) with
   explicit support claims.
5. Optionally create a tagged release and release assets for `0.3.0`.
6. Replace deprecated `actions/checkout@v4` / `actions/setup-python@v5`
   usages when updated majors are available.
7. Optionally remove absolute `/home/fsia/...` provenance paths from public
   documentation if redaction is desired.

## 8. Gate

Phase 13B acceptance criteria 1–14 are satisfied: correct tree, clean Git
initialization, `.gitignore` respected, essential files versioned, no secrets,
native library preserved, scientific integrity confirmed, exclusive correct
remote, initial commit created and pushed to `main`, hosted workflow executed
and succeeded, results recorded, and audit/checkpoint documents created.

The repository is ready for Phase 13C (release governance and broader hosted
validation).
