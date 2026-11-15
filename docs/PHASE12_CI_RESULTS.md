# Phase 12 — CI results

**Status:** **BLOCKED — hosted CI execution unavailable in this environment.**

## 1. Why

The development tree is not a Git repository and has no configured Git remote
or GitHub repository:

```text
fatal: not a git repository (or any of the parent directories): .git
```

No GitHub Actions run URL, run ID, commit or hosted runner can be truthfully
reported. Local execution is not substituted for hosted execution.

## 2. Workflow audit

`.github/workflows/ci.yml` exists and covers:

1. checkout;
2. Python 3.12 setup;
3. system toolchain (gfortran/cmake/OpenBLAS);
4. wheel/sdist build;
5. native CMake build;
6. CTest;
7. Python suite;
8. isolated wheel install;
9. installed smoke test;
10. optional-full import job.

The workflow was syntax-checked locally with PyYAML. It was not executed on a
hosted runner.

## 3. Local execution evidence

Local equivalents were executed:

- native CTest: 6/6;
- Python suite: 233 passed, 1 warning;
- wheel installed in a clean venv;
- sdist installed in a clean venv;
- installed smoke test from `/tmp`;
- optional-dependency absence errors;
- PySCF 2.14.0 + ASE 3.28.0 + NumPy 2.4.6 matrix:
  `18 passed` relevant adapter tests;
- `ldd -r` and ABI inspection of the installed library.

## 4. Required next action

When a Git/GitHub remote is available:

1. commit this tree;
2. execute the workflow;
3. record URL, run ID, commit and runner;
4. fix any hosted failure;
5. run again;
6. update this document and the checkpoint.

Until then, hosted CI remains BLOCKED and the global Phase 12 status is
PARTIAL as required by the phase criteria.

## 5. Reproducibility observation

With `SOURCE_DATE_EPOCH=1700000000`, two independent builds produced the same
wheel hash (`397f9c…`). The sdist hashes differed, so no bit-for-bit sdist
reproducibility is claimed. This is a packaging observation only; scientific
artifacts were not changed.
