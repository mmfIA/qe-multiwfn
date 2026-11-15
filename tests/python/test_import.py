"""Test that the qe_multiwfn package imports and the library loads."""
import pytest


def test_import():
    import qe_multiwfn
    assert hasattr(qe_multiwfn, "Engine")
    assert hasattr(qe_multiwfn, "MolecularSystem")
    assert hasattr(qe_multiwfn, "MayerResult")


def test_native_library_loaded():
    import qe_multiwfn
    assert qe_multiwfn.NATIVE_LIBRARY_PATH is not None
    assert qe_multiwfn.NATIVE_LIBRARY_VERSION == "0.2.0"


if __name__ == "__main__":
    test_import()
    test_native_library_loaded()
    print("PASS: test_import")
