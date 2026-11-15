# Distribution policy — QE-Multiwfn 0.3.0

## 1. Official supported target

**Linux x86_64 / CPython 3.12.**

The wheel produced is:

```text
qe_multiwfn-0.3.0-cp312-cp312-linux_x86_64.whl
```

This is the only platform/Python combination with executed install and
scientific smoke evidence.

## 2. Not claimed

- Windows;
- macOS;
- ARM;
- other Linux architectures;
- other CPython ABI versions;
- manylinux;
- arbitrary glibc distributions.

No wheel is published for those targets. A successful source import is not a
platform compatibility claim.

## 3. Native dependencies

The package includes `libqe_multiwfn.so` with RUNPATH `$ORIGIN`. It dynamically
requires the runtime:

- `libopenblas.so.0`;
- `libgfortran.so.5`;
- `libgcc_s.so.1`;
- `libm.so.6`;
- `libmvec.so.1`;
- `libc.so.6`.

These are external system runtime dependencies; OpenBLAS/gfortran are not
bundled in the wheel. `ldd -r` is clean in the reference environment.

## 4. Wheel policy

- `linux_x86_64` tag, not manylinux.
- No claim of manylinux compliance.
- No system library is bundled without a separate licensing/distribution
  evaluation.
- No absolute development paths in wheel contents.

## 5. Sdist policy

The sdist carries Python source, documentation and the validated native
library. Installing it does not rebuild the native library. It is therefore
platform-specific in practice despite the generic sdist filename.

The sdist is not claimed bit-for-bit reproducible. A future manylinux/source
build policy requires a separate toolchain and license review.

## 6. Versioning

The reference package remains 0.3.0. Packaging-only fixes may become 0.3.1 only
after rebuilding and re-running the full validation; the 0.3.0 artifacts must
not be silently overwritten.
