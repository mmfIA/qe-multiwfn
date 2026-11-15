#!/usr/bin/env bash
# verify_installation.sh — confirm the toolchain and Python environment.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ok=0
fail=0

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        printf "  [OK]    %-30s -> %s\n" "$name" "$(eval "$cmd" | head -1)"
        ok=$((ok + 1))
    else
        printf "  [FAIL]  %-30s (command: %s)\n" "$name" "$cmd"
        fail=$((fail + 1))
    fi
}

echo "=========================================="
echo "  Toolchain verification"
echo "=========================================="

# Prefer project-local conda env if installed
if [ -d "$ROOT/tools/qe-env/bin" ]; then
    export PATH="$ROOT/tools/qe-env/bin:$PATH"
fi

check "gfortran" "gfortran --version"
check "gcc"      "gcc --version"
check "cmake"    "cmake --version"
# Ninja is optional: configure.sh falls back to Unix Makefiles.
if command -v ninja >/dev/null 2>&1; then
    check "ninja (preferred)" "ninja --version"
else
    check "make (Ninja fallback)" "make --version"
fi
check "python3"  "python3 --version"
check "pytest"   "python3 -m pytest --version"

echo ""
echo "=========================================="
echo "  Libraries"
echo "=========================================="
if [ -f "$ROOT/tools/qe-env/lib/libblas.so" ]; then
    echo "  [OK]    libblas.so                    -> $ROOT/tools/qe-env/lib/libblas.so"
    ok=$((ok + 1))
elif ldconfig -p 2>/dev/null | grep -q libblas; then
    echo "  [OK]    libblas.so                    -> system"
    ok=$((ok + 1))
else
    echo "  [FAIL]  libblas.so not found"
    fail=$((fail + 1))
fi

echo ""
echo "=========================================="
echo "  Result"
echo "=========================================="
echo "  Passed: $ok"
echo "  Failed: $fail"
[ $fail -eq 0 ]
