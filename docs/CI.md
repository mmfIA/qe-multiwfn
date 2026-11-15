# CI — Phase 11

**Workflow:** `.github/workflows/ci.yml`
**Status:** configured; hosted execution is **BLOCKED** because this checkout is not a Git/GitHub repository. Phase 12 local matrix tests were executed separately.

## Jobs

The workflow covers:

1. Python 3.12 on Ubuntu x86_64.
2. Build the wheel and sdist with `python -m build`.
3. Install the wheel in an isolated venv.
4. Import the installed package, check version, native path and ABI.
5. Run a NumPy builder → Engine → Mayer smoke test from outside the tree.
6. Install optional extras in a full-profile job.
7. Build the native CTest suite and run CTest 6/6.
8. Run the Python suite in the development profile.

## Matrix

| Axis | Values |
|---|---|
| Python | 3.12 |
| Profile | minimal; full optional |
| OS | ubuntu-latest |
| PySCF | 2.15.0 when full extras selected |
| ASE | 3.29.0 when full extras selected |

Versions not in the matrix are not claimed. Additional versions require their
own observed test runs; the workflow does not infer compatibility from import
success.

## Limitation

The workflow is reproducible configuration, but it was not executed on a hosted
runner. The Phase 12 local matrix and isolated-venv installation are the
executed evidence. See `PHASE12_CI_RESULTS.md`.
