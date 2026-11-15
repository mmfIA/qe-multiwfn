"""Consistency checks for the versioned 115-test skip inventory."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_INV = json.loads((_HERE / "skip_inventory.json").read_text())


def test_inventory_totals():
    totals = _INV["totals"]
    assert totals["functions"] == 115
    assert totals["independent"] == 14
    assert totals["fixture_dependent"] == 101
    assert totals["independent_without_optional_packages"] == 11
    assert len(_INV["modules"]) == 20


def test_inventory_names_exist_in_modules():
    for filename, entry in _INV["modules"].items():
        path = _HERE / filename
        assert path.exists(), f"inventory references missing module: {filename}"
        names = set(re.findall(r"^def (test_[A-Za-z0-9_]+)\(",
                               path.read_text(), re.M))
        assert set(entry["independent"]).issubset(names)
        assert set(entry["fixture_dependent"]).issubset(names)
        assert len(entry["independent"]) + len(entry["fixture_dependent"]) == entry["total"]
        for key in ("dependency", "fixture", "condition", "reason", "type", "phase"):
            assert entry.get(key), f"{filename}: missing inventory field {key}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
