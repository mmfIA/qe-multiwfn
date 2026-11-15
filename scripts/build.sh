#!/usr/bin/env bash
# build.sh — compile libqe_multiwfn.so and tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -d "$ROOT/tools/qe-env/bin" ]; then
    export PATH="$ROOT/tools/qe-env/bin:$PATH"
fi

BUILD_DIR="${1:-build}"
PARALLEL="${2:-4}"

if [ ! -d "$BUILD_DIR" ]; then
    echo "[build] build dir '$BUILD_DIR' does not exist; running configure.sh first..."
    "$(dirname "$0")/configure.sh" Release "$BUILD_DIR"
fi

echo "[build] starting parallel build (j=$PARALLEL)..."
cmake --build "$BUILD_DIR" --parallel "$PARALLEL"

echo "[build] done. Library at: $BUILD_DIR/libqe_multiwfn.so"
ls -la "$BUILD_DIR"/libqe_multiwfn.so* | head
