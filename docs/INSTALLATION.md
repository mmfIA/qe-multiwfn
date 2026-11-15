# Installation — QE-Multiwfn 0.3.0

## 1. Basic install from the built wheel

```bash
python3 -m venv /tmp/qe-multiwfn-venv
/tmp/qe-multiwfn-venv/bin/python -m pip install numpy
/tmp/qe-multiwfn-venv/bin/python -m pip install \
  dist-phase12/qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl
```

The wheel is Linux x86_64 / CPython 3.12 and requires system OpenBLAS,
libgfortran and libgcc. The native library is inside the package.

## 2. Verify installation outside the repository

```bash
cd /tmp
/tmp/qe-multiwfn-venv/bin/python - <<'PY'
import qe_multiwfn as qe
print(qe.__version__)
print(qe.NATIVE_LIBRARY_PATH)
print(qe.NATIVE_LIBRARY_VERSION)
PY
```

A minimal NumPy MDM/Mayer smoke test is in
`tests/installed_smoke.py` and in the Phase 11 checkpoint commands.

## 3. Optional scientific extras

```bash
pip install "qe_multiwfn[pyscf]==0.3.0"
pip install "qe_multiwfn[ase]==0.3.0"
pip install "qe_multiwfn[cclib]==0.3.0"
pip install "qe_multiwfn[full]==0.3.0"
```

Extras are optional. The core import, builder, MDM, Engine, native Library and
Mayer path do not require PySCF, ASE, cclib or a database provider.

If an optional package is missing, the adapter raises a specific message:

```text
PySCF is not available; install with: pip install 'qe-multiwfn[pyscf]'
```

## 4. From sdist

```bash
/tmp/qe-multiwfn-venv/bin/python -m pip install \
  dist-phase12/qe_multiwfn-0.3.0.tar.gz
```

The sdist carries the same native library and Python code; installation was
tested without rebuilding the native library.

## 5. Platform boundary

Only Linux x86_64 / CPython 3.12 with the tested OpenBLAS/gfortran runtime is
claimed. No Windows, macOS, ARM or other Python ABI wheel is produced or
claimed.

## 6. Development-tree usage

The source tree can still be used with `PYTHONPATH=python`; that is a
development workflow, not the distribution verification workflow.
