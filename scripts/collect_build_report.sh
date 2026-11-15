#!/usr/bin/env bash
# collect_build_report.sh — generate reports/build/ artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPORT_DIR="$ROOT/reports/build"
mkdir -p "$REPORT_DIR"

if [ -d "$ROOT/tools/qe-env/bin" ]; then
    export PATH="$ROOT/tools/qe-env/bin:$PATH"
fi

BUILD_DIR="${1:-build}"

# 1. Compiler info
{
    echo "===== CMake ====="
    cmake --version | head -1
    echo ""
    echo "===== Fortran compiler ====="
    gfortran --version | head -3
    echo ""
    echo "===== C compiler ====="
    gcc --version | head -1
    echo ""
    echo "===== BLAS ====="
    ls -la "$ROOT/tools/qe-env/lib"/libblas* 2>/dev/null || echo "(system BLAS)"
} > "$REPORT_DIR/compiler_info.txt"

# 2. Configure log
if [ -f "$BUILD_DIR/CMakeCache.txt" ]; then
    cp "$BUILD_DIR/CMakeCache.txt" "$REPORT_DIR/cmake_configure.log"
fi

# 3. Build log (re-run cmake --build to capture)
# (just copy the file if present)
if [ -f /tmp/build.log ]; then
    cp /tmp/build.log "$REPORT_DIR/build.log"
fi

# 4. Linked libraries
{
    echo "===== ldd libqe_multiwfn.so ====="
    ldd "$BUILD_DIR/libqe_multiwfn.so" 2>&1 | head -30
} > "$REPORT_DIR/linked_libraries.txt"

# 5. Exported symbols (qe_ prefixed)
nm -D "$BUILD_DIR/libqe_multiwfn.so" | grep -E " T qe_" | sort > "$REPORT_DIR/exported_symbols.txt"

# 6. Test summary
{
    echo "===== C test summary ====="
    ( cd "$BUILD_DIR" && ctest 2>&1 )
    echo ""
    echo "===== Python test summary ====="
    export LD_LIBRARY_PATH="$ROOT/$BUILD_DIR:${LD_LIBRARY_PATH:-}"
    export QE_MULTIWFN_LIBRARY="$ROOT/$BUILD_DIR/libqe_multiwfn.so"
    export PYTHONPATH="$ROOT/python:${PYTHONPATH:-}"
    python3 -m pytest "$ROOT/tests/python/" 2>&1 | tail -20
} > "$REPORT_DIR/test_summary.md" 2>&1

echo "[collect] reports written to $REPORT_DIR/"
ls -la "$REPORT_DIR/"
