#!/usr/bin/env bash
# configure.sh — set up the CMake build directory.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Auto-detect toolchain (prefer conda env if installed)
if [ -d "$ROOT/tools/qe-env/bin" ]; then
    export PATH="$ROOT/tools/qe-env/bin:$PATH"
fi

BUILD_TYPE="${1:-Release}"
BUILD_DIR="${2:-build}"

# Generator auto-detection: Ninja is preferred, but a host without Ninja
# must still be able to configure with the standard Unix Makefiles generator.
if [ -n "${QE_CMAKE_GENERATOR:-}" ]; then
    GENERATOR="$QE_CMAKE_GENERATOR"
elif command -v ninja >/dev/null 2>&1; then
    GENERATOR="Ninja"
else
    GENERATOR="Unix Makefiles"
fi

echo "[configure] root:        $ROOT"
echo "[configure] build_type:  $BUILD_TYPE"
echo "[configure] build_dir:   $BUILD_DIR"
echo "[configure] generator:   $GENERATOR"
echo "[configure] PATH first:  $(echo $PATH | tr ':' '\n' | head -1)"

cmake -S . -B "$BUILD_DIR" -G "$GENERATOR" \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DCMAKE_Fortran_COMPILER=gfortran \
    -DCMAKE_C_COMPILER=gcc \
    -DQE_STRICT_LEGACY=ON

echo "[configure] done."
