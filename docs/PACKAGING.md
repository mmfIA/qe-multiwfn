# Packaging — QE-Multiwfn 0.3.0

**Status:** wheel and sdist produced and tested on Linux x86_64 / Python 3.12.
**Build backend:** setuptools (`pyproject.toml` + minimal `setup.py` binary
distribution marker).

## 1. Package layout

```text
pyproject.toml
setup.py                 # BinaryDistribution: marks the wheel platform-specific
MANIFEST.in              # sdist documentation and native library
python/qe_multiwfn/      # Python package (import name qe_multiwfn)
python/qe_multiwfn/libqe_multiwfn.so
dist-phase12/            # built wheel and sdist
```

`python/qe_multiwfn/libqe_multiwfn.so` is a byte-for-byte copy of the validated
development library:

```text
e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119
```

The wheel contains that library inside the importable package. The native
loader checks the package directory first; no development path is required.

## 2. Version

| Source | Value |
|---|---|
| `pyproject.toml` | `0.3.0` |
| `qe_multiwfn.__version__` | `0.3.0` |
| wheel/sdist filename | `0.3.0` |
| native ABI | `0.2.0` |

All package version sources agree. The native ABI version is intentionally
independent.

## 3. Build

```bash
cd qe_multiwfn_030_dev
python3 -m pip install build
python3 -m build --no-isolation --wheel --sdist --outdir dist-phase12
```

Artifacts produced in this environment:

```text
qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl
qe_multiwfn-0.3.0.tar.gz
```

The wheel is platform-specific because it carries the native shared library.
No source rebuild of the native library is performed; the validated library is
packaged.

## 4. Included / excluded

Wheel includes:
- all `qe_multiwfn` Python modules;
- `adapters/` and `analysis/`;
- `libqe_multiwfn.so`;
- distribution metadata.

Sdist includes:
- Python package and native library;
- `pyproject.toml`, `setup.py`, `MANIFEST.in`;
- README and `docs/*.md`.

Excluded: `vendor/`, frozen source, build directories, caches, test outputs,
virtual environments, `.pytest_cache`, and development-only artifacts.

## 5. Native library

The packaged library has RUNPATH `$ORIGIN` and depends on the host
`libopenblas.so.0`, `libgfortran.so.5`, `libgcc_s`, `libm`, and `libc`.
The wheel does not bundle BLAS/gfortran; the validated Linux environment must
provide them. `ldd -r` and ABI inspection are part of the release checks.

## 6. License / upstream terms

The project README states that Multiwfn and Multiwfn-derived code retain their
upstream terms. No separate project license is invented by this packaging
phase. Users must consult the upstream Multiwfn terms before redistribution.

## 7. Reproducibility

The sdist is not claimed bit-for-bit reproducible across arbitrary timestamps.
Build provenance, hashes, wheel contents and installed behavior are recorded in
the Phase 11 checkpoint. `SOURCE_DATE_EPOCH` may be used for future reproducible
builds, but no claim is made without a repeat-build comparison.
