#!/usr/bin/env bash
# Run the versioned P0 protocol against external fixtures.
#
# The fixtures are NOT redistributed. Point QE_P0_FIXTURES at the external
# QE-Multiwfn-validation directory (default: ../QE-Multiwfn-validation).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P0_ROOT="${QE_P0_FIXTURES:-$ROOT_DIR/../QE-Multiwfn-validation}"

if [[ ! -d "$P0_ROOT" ]]; then
  echo "P0 fixtures not found: $P0_ROOT" >&2
  echo "Set QE_P0_FIXTURES to the external QE-Multiwfn-validation directory." >&2
  exit 2
fi

export QE_P0_FIXTURES="$(cd "$P0_ROOT" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT_DIR/python${PYTHONPATH:+:$PYTHONPATH}"

cd "$ROOT_DIR"
exec python3 -m pytest tests/python/test_p0_validation.py -q -rs -p no:cacheprovider "$@"
