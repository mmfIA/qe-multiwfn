"""Test engine lifecycle: initialize, state queries, finalize."""
import pytest
import qe_multiwfn as qe


def test_lifecycle():
    eng = qe.Engine()
    assert eng.state == "UNINITIALIZED"
    eng.initialize()
    assert eng.state == "INITIALIZED"
    eng.finalize()
    assert eng.state == "UNINITIALIZED"


def test_double_initialize_fails():
    eng = qe.Engine()
    eng.initialize()
    with pytest.raises(qe.QeInvalidState):
        eng.initialize()
    eng.finalize()


def test_double_finalize_safe():
    # finalize without initialize is silently ignored (no exception)
    eng = qe.Engine()
    eng.finalize()


def test_context_manager():
    with qe.Engine() as eng:
        assert eng.state == "INITIALIZED"
    assert eng.state == "UNINITIALIZED"


def test_context_manager_releases_molecule_on_exception():
    with pytest.raises(RuntimeError):
        with qe.Engine() as eng:
            # Force an exception inside the block
            raise RuntimeError("oops")
    # After the with-block, the engine should be finalized
    assert eng.state == "UNINITIALIZED"


def test_prepare_without_load_fails():
    with qe.Engine() as eng:
        with pytest.raises(qe.QeError):
            eng.prepare()


def test_calculate_mayer_without_load_fails():
    with qe.Engine() as eng:
        with pytest.raises(qe.QeError):
            eng.calculate_mayer()


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
