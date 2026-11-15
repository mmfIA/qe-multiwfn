"""Permanent native-boundary negative tests (E1 and E2).

These tests bypass ``MolecularSystem`` validation and call the low-level
``NativeAPI`` directly, so the Fortran-side checks are exercised. They
complement the C ABI negative tests in ``tests/native/test_abi_negative.c``.
"""
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.native import NativeAPI, QE_STATE_SYSTEM_LOADED


def _loaded_api():
    """Return an initialized engine with a valid 2x2 metadata/basis model."""
    api = NativeAPI()
    api.initialize()
    api.begin_system(2, 2, 2, qe.molecular.WFNTYPE_RHF)
    api.set_atomic_data(
        np.array([1, 1], dtype=np.int32),
        np.asfortranarray(
            np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64).T
        ),
    )
    api.set_electronic_metadata(0, 1, 2)
    api.set_basis_data(
        np.array([1, 2], dtype=np.int32),
        np.array([0, 0], dtype=np.int32),
        nprims=2,
    )
    return api


def _finish(api):
    try:
        api.release_system()
    finally:
        api.finalize()


def test_e1_tr_ps_mismatch_is_rejected_by_fortran():
    api = _loaded_api()
    try:
        # P = I, S = 2I, Ne = 2 gives Tr(P*S) = 4. The Fortran check
        # must reject this even though the density is symmetric.
        api.set_density(np.eye(2))
        api.set_overlap(2.0 * np.eye(2))
        with pytest.raises(qe.QeInvalidArgument, match=r"Tr\(P\*S\)"):
            api.prepare_system()
        assert api.get_engine_state() == QE_STATE_SYSTEM_LOADED
        with pytest.raises(qe.QeInvalidState):
            api.get_mayer_dimensions()
    finally:
        _finish(api)


def test_e2_nan_density_is_rejected():
    api = _loaded_api()
    try:
        P = np.full((2, 2), 2.0 / 3.0)
        P[0, 0] = np.nan
        with pytest.raises(qe.QeInvalidArgument, match="NaN/Inf"):
            api.set_density(P)
        assert api.get_engine_state() == QE_STATE_SYSTEM_LOADED
    finally:
        _finish(api)


def test_e2_positive_inf_overlap_is_rejected():
    api = _loaded_api()
    try:
        S = np.array([[1.0, 0.5], [0.5, 1.0]])
        S[0, 0] = np.inf
        with pytest.raises(qe.QeInvalidArgument, match="NaN/Inf"):
            api.set_overlap(S)
        assert api.get_engine_state() == QE_STATE_SYSTEM_LOADED
    finally:
        _finish(api)


def test_e2_negative_inf_overlap_is_rejected():
    api = _loaded_api()
    try:
        S = np.array([[1.0, 0.5], [0.5, 1.0]])
        S[1, 1] = -np.inf
        with pytest.raises(qe.QeInvalidArgument, match="NaN/Inf"):
            api.set_overlap(S)
        assert api.get_engine_state() == QE_STATE_SYSTEM_LOADED
    finally:
        _finish(api)


def test_e2_nan_overlap_is_rejected():
    api = _loaded_api()
    try:
        S = np.array([[1.0, 0.5], [0.5, 1.0]])
        S[0, 1] = np.nan
        S[1, 0] = np.nan
        with pytest.raises(qe.QeInvalidArgument, match="NaN/Inf"):
            api.set_overlap(S)
        assert api.get_engine_state() == QE_STATE_SYSTEM_LOADED
    finally:
        _finish(api)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
