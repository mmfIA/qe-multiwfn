#!/usr/bin/env bash
# test.sh — run all C and Python tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -d "$ROOT/tools/qe-env/bin" ]; then
    export PATH="$ROOT/tools/qe-env/bin:$PATH"
fi

BUILD_DIR="${1:-build}"

if [ ! -f "$BUILD_DIR/libqe_multiwfn.so" ]; then
    echo "[test] library not found; running build.sh first..."
    "$(dirname "$0")/build.sh" "$BUILD_DIR" 4
fi

export LD_LIBRARY_PATH="$ROOT/$BUILD_DIR:${LD_LIBRARY_PATH:-}"
export QE_MULTIWFN_LIBRARY="$ROOT/$BUILD_DIR/libqe_multiwfn.so"
export PYTHONPATH="$ROOT/python:${PYTHONPATH:-}"

echo "=========================================="
echo "  C tests (ctest)"
echo "=========================================="
( cd "$BUILD_DIR" && ctest --output-on-failure )

echo ""
echo "=========================================="
echo "  Python tests (pytest)"
echo "=========================================="
python3 -m pytest "$ROOT/tests/python/" -v

echo ""
echo "[test] all tests passed."
