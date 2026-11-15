# Installation validation — Phase 12

## 1. Reference install

```bash
python3 -m venv /tmp/qe_multiwfn_phase11
/tmp/qe_multiwfn_phase11/bin/python -m pip install numpy==2.5.4
/tmp/qe_multiwfn_phase11/bin/python -m pip install \
  dist-phase12/qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl
cd /tmp
/tmp/qe_multiwfn_phase11/bin/python tests/installed_smoke.py
```

The smoke test verifies:
- package version `0.3.0`;
- native ABI `0.2.0`;
- package-local native library;
- NumPy MDM construction;
- Engine/Mayer;
- readiness.

## 2. Minimal imports

The isolated venv has no PySCF/ASE/cclib. `import qe_multiwfn` succeeds and
optional modules are not imported. Accessing an adapter without its package
produces a specific `*AdapterError` with the extra install command.

## 3. Sdist

The sdist was force-installed into the same venv with `--no-deps`; the
installed package imported and executed the smoke test successfully.

## 4. Native loading

Installed path:

```text
<venv>/lib/python3.12/site-packages/qe_multiwfn/libqe_multiwfn.so
```

Hash matches `e9ac3a73…`; `ldd -r` reports no unresolved symbols; RUNPATH is
`$ORIGIN`.

## 5. Platform

Only Linux x86_64 / CPython 3.12 was installed and executed. No other platform
installation is claimed.
