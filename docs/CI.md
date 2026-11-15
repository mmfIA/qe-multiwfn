# CI — Phase 13C.4

**Workflow:** `.github/workflows/ci.yml`
**Status:** configured. The last hosted runs for the published tree were
13C.2 runs `43711107774` (code) and `43711807880` (docs), both success.
The 13C.4/13C.5 changes have **not** been committed/pushed yet, so their hosted CI
has not run. Local simulations below are not a substitute.

## Jobs

1. Python 3.12 on Ubuntu x86_64.
2. Build the wheel and sdist with `python -m build`.
3. Build the native CTest suite and run **CTest 7/7**.
4. Run the Python suite with `pytest -q -rs` (skip reasons visible).
5. Install the wheel in an isolated venv and run the installed smoke test.
6. Install optional PySCF/ASE/cclib extras and run the optional-dependency
   Python suite with `pytest -q -rs` (not only an import check).

## Matrix

| Axis | Values |
|---|---|
| Python | 3.12 |
| Profile | minimal; full optional |
| OS | ubuntu-latest |
| PySCF | 2.15.0 when full extras selected |
| ASE | 3.29.0 when full extras selected |
| cclib | 1.8.1 when full extras selected |

Versions not in the matrix are not claimed. Additional versions require their
own observed test runs; the workflow does not infer compatibility from import
success.

## P0 and external fixtures

The versioned P0 harness is `tests/python/test_p0_validation.py`, with the
SHA-256 manifest `tests/python/p0_fixtures.json`. It requires the external
`QE-Multiwfn-validation` tree via `QE_P0_FIXTURES`; without it the system
tests skip explicitly. The historical 223-test P0 suite remains external and
is not a hidden PASS. The full protocol can be run with
`scripts/run_p0_validation.sh`.

## Local simulations (13C.4/13C.5, not hosted)

| Scenario | Result |
|---|---|
| With external fixtures | 256 passed |
| Build-test profile, no fixtures | 109 passed, 50 skipped |
| Optional-dependency profile, no fixtures | 114 passed, 46 skipped |
| P0 historical suite | 223/223 |

Hosted CI must be run after publication authorization.
