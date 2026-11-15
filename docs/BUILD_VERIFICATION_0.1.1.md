# Build and verification record — 0.1.1

> **Historical document (0.1.1).** Counts, hashes and symbol totals here
> describe that frozen release. Current 0.3.0-dev build/test status is in
> `docs/IMPLEMENTATION_STATUS.md` and `../../MDM_1.1_work/AUDIT_PHASE6_FINAL.md`.

## Environment

- OS/container: Linux x86_64
- GNU Fortran: 14.2.0
- GCC: system compiler from the same toolchain
- CMake: 3.31.6
- Ninja: available
- Python: 3.13.5
- pytest: 9.0.2
- BLAS: `/usr/lib/x86_64-linux-gnu/libblas.so`
- LAPACK: `/usr/lib/x86_64-linux-gnu/liblapack.so`

## Commands executed

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DQE_BUILD_TESTS=ON
cmake --build build --parallel 8
ctest --test-dir build --output-on-failure
QE_MULTIWFN_LIBRARY="$PWD/build/libqe_multiwfn.so" \
  PYTHONPATH="$PWD/python" python3 -m pytest tests/python -q
./scripts/test.sh build
```

## Results

- CMake configure: passed.
- Release shared-library build: passed.
- C tests: 4 passed, 0 failed.
- Python tests: 29 passed, 0 failed.
- `ldd -r build/libqe_multiwfn.so`: all dependencies resolved; no undefined symbol diagnostics.
- `readelf -d`: runtime search path is `$ORIGIN`, not an absolute build-machine path.
- Dynamic ABI: 17 exported `qe_*` symbols; internal Multiwfn symbols are hidden by `cmake/qe_multiwfn.map`.
- Shared object version: `libqe_multiwfn.so.0.1.1`.

## Upstream source integrity

The 74 regular files in `vendor/Multiwfn_2026.11.3_src_Linux/` were compared
against the supplied `Multiwfn_2026.11.3_src_Linux.zip` using SHA-256. Result:

- Original archive files: 74
- Vendored files: 74
- Missing: 0
- Extra: 0
- Different hashes: 0

The build uses the minimal upstream dependency closure for the currently
exposed Mayer path: `define.f90`, `util.f90`, and `bondorder.f90`. The other
upstream source files remain present and byte-identical in `vendor/`.

## Scientific validation caveat

The Mayer routine called is the original Multiwfn `calcMayerbndord`, and its
output is cross-checked against an independent NumPy implementation. The tests
also validate the RHF trace and idempotency conditions. However, the `nprims=6`,
`nbasis=2` regression validates the dimension contract only; it is not an
independent H2/STO-3G SCF calculation. An external SCF reference and a separate
run of the original Multiwfn executable remain pending.
- Example scripts: 3/3 executed successfully (`example_lifecycle.py`, `example_memory_transfer.py`, `example_mayer_rhf.py`).

## P0 re-verification on the target host (2026-11-14)

The sandbox record above was reproduced on the user's Ubuntu host with a
different toolchain, then extended to the integrated flow.

- Host/toolchain: Ubuntu 26.04.1 x86-64; GNU Fortran/GCC 15.2.0; CMake 4.2.3;
  GNU Make 4.4.1 (Ninja absent, Makefiles generator used); Python 3.12.16;
  NumPy 2.5.4; pytest 9.2.0; system OpenBLAS.
- Clean build via `scripts/clean.sh`, `scripts/configure.sh`,
  `scripts/build.sh`: passed.
- `libqe_multiwfn.so` SHA-256
  `b981c10b30dc6dc9e9b702c60f163a271279e70082c16f53305ec531f9eb9d56`;
  RUNPATH `$ORIGIN`; 17 exported `qe_*` symbols.
- `ldd -r`: no undefined symbols.
- CTest 4/4; library pytest 29/29; validation pytest 223/223; examples 3/3.
- Upstream vendor integrity re-checked after the build: 74/74 files
  byte-identical to the official source ZIP.
- Fresh ORCA 6.1.1 and Multiwfn 2026.11.3 executions reproduced the archived
  H₂/H₂O/C₆H₆ results; global validation status PASS.

The build scripts now auto-select Ninja when present and otherwise fall back to
Unix Makefiles, so the documented build works on hosts without Ninja. Evidence:
`QE-Multiwfn-validation/reports/P0_OPERATIONAL_VERIFICATION.md`.

## M1 additive build verification (2026-11-14)

- Clean build via `scripts/clean.sh`, `scripts/configure.sh`,
  `scripts/build.sh` on the same host (GNU Fortran 15.2.0, CMake 4.2.3,
  OpenBLAS).
- `libqe_multiwfn.so` SHA-256
  `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72`
  (also refreshed into `python/libqe_multiwfn.so`).
- CTest: **6/6** (the original 4 plus `v1_abi_c` and `uhf_abi_c`).
- Python library tests: **94/94** (29 legacy, 27 model, 26 ORCA/d-f, 5 UHF, 4 ROHF, 3 Cartesian).
- Dynamic ABI: **29 exported `qe_*` symbols** (17 legacy + 12 additive v1);
  `ldd -r` clean; RUNPATH `$ORIGIN`.
- Upstream vendor: unchanged (74/74).
- Scientific v1 flow: H₂/H₂O/C₆H₆ Mayer matrices bit-identical to the P0
  baseline; QE × Multiwfn max|Δ| 1.33e−15 / 3.61e−9 / 4.98e−9.
- Spherical d/f: H₂O/6-31G* and H₂S/def2-TZVP PASS.
- UHF (opt-in): O₂/STO-3G PASS; α/β × Multiwfn ≤ 2.89e−15.
- ROHF (opt-in): O₂/STO-3G PASS; α/β × Multiwfn ≤ 2.22e−15.
- Cartesian d/f: H₂O/6-31G* (6D) PASS; QE × Multiwfn ≤ 1.21e−9.
