#!/usr/bin/env bash
# clean.sh — remove build artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

rm -rf build build-debug
echo "[clean] removed build directories."
