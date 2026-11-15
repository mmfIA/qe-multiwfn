"""Phase 7C — ORCA MDM 1.2 contract tests."""
from pathlib import Path
import numpy as np
import pytest

from qe_multiwfn.adapters.orca import from_orca_directory
from qe_multiwfn.angular import (
    AngularConvention, AngularConventionError, AngularUnsupportedError,
    known_source_convention, phase_matrix,
)

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
_H2S = _ORCA / "df" / "h2s_def2tzvp"
_H2O_D = _ORCA / "df" / "h2o_631gstar"
requires_orca = pytest.mark.skipif(
    not _H2S.exists(), reason="validation fixtures unavailable"
)


def test_known_orca_f_convention_shape():
    c = known_source_convention(3, "orca", "6.1.1")
    assert c.state == "source"
    assert c.phase_signs == (1, 1, 1, 1, 1, -1, -1)
    D = phase_matrix(3, c.phase_signs)
    assert np.array_equal(D, np.diag([1, 1, 1, 1, 1, -1, -1]))
    assert np.array_equal(D @ D, np.eye(7))


def test_unknown_program_fails_closed():
    with pytest.raises(AngularConventionError):
        known_source_convention(3, "not-a-program", "1.0")


def test_phase_matrix_rejects_order_reordering():
    with pytest.raises(AngularUnsupportedError):
        phase_matrix(3, (1, 1, 1, 1, 1, -1, -1),
                     source_order=(0, 1, -1, 2, -2, 3, -3),
                     target_order=(0, -1, 1, 2, -2, 3, -3))


@requires_orca
def test_orca_f_canonical_model_has_shell_metadata():
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    assert can.schema_version == "1.2.0"
    for sh in can.basis.shells:
        assert sh.angular is not None
        assert sh.angular.state == "canonical"
        assert sh.angular.l == sh.l
    assert can.basis.angular is not None
    assert can.basis.angular.state == "canonical"


@requires_orca
def test_orca_f_source_metadata_is_recorded():
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    rec = can.provenance.angular_transforms[-1]
    assert rec.source_convention_id
    assert rec.canonical_convention_id == "qe-mdm-real-spherical-1.0"
    assert rec.l == 3
    assert rec.phase_signs == (1, 1, 1, 1, 1, -1, -1)
    assert can.provenance.source_program == "ORCA"
    assert can.provenance.source_version == "6.1.1"


@requires_orca
def test_orca_d_canonical_model_has_identity_phase():
    can = from_orca_directory(_H2O_D, canonicalize_angular=True)
    dsh = [sh for sh in can.basis.shells if sh.l == 2]
    assert dsh
    for sh in dsh:
        assert sh.angular.phase_signs == (1, 1, 1, 1, 1)
        assert sh.angular.state == "canonical"
    assert can.schema_version == "1.2.0"


@requires_orca
def test_orca_canonical_does_not_mutate_source():
    src = from_orca_directory(_H2S)
    C0 = src.wavefunction.orbitals.coefficients.copy()
    S0 = src.matrices.S.data.copy()
    can = from_orca_directory(_H2S, canonicalize_angular=True)
    assert src.schema_version == "1.1.0"
    np.testing.assert_array_equal(src.wavefunction.orbitals.coefficients, C0)
    np.testing.assert_array_equal(src.matrices.S.data, S0)
    assert can is not src
