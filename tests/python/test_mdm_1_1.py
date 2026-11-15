"""MDM 1.1 consolidation and backward-compatibility checks."""
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn import model_v1 as m1
from qe_multiwfn.normalization import normalization_report
from qe_multiwfn.adapters.orca import (
    from_orca_directory, from_orca_uhf_directory, from_orca_rohf_directory,
)

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
requires_orca = pytest.mark.skipif(
    not _ORCA.exists(), reason="fixtures unavailable"
)


def _legacy_h2():
    return qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=2, wfntype=0,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([[0, 0, 0], [0, 0, 1.4]], dtype=np.float64),
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.full((2, 2), 2.0 / 3.0),
        overlap=np.array([[1.0, 0.5], [0.5, 1.0]]),
        charge=0, multiplicity=1, nelectron=2,
    )


@requires_orca
def test_schema_1_1_fields_and_summary():
    model = from_orca_directory(_ORCA / "h2o")
    assert model.schema_version == "1.1.0"
    assert model.basis.normalization_convention in ("mixed", "cartesian_explicit")
    assert any(ao.source_self_overlap is not None for ao in model.basis.aos)
    s = model.summary()
    assert s["schema_version"] == "1.1.0"
    assert "normalization_convention" in s
    assert normalization_report(model)["status"] == "PASS"


def test_legacy_roundtrip_still_bitwise():
    ms = _legacy_h2()
    model = m1.MolecularSystemV1.from_legacy(ms)
    assert model.schema_version == "1.1.0"
    assert model.basis.normalization_convention == "unknown"
    back = model.to_legacy()
    assert np.array_equal(back.atomic_numbers, ms.atomic_numbers)
    assert np.array_equal(back.coordinates, ms.coordinates)
    assert np.array_equal(back.basis_center, ms.basis_center)
    assert np.array_equal(back.basis_type, ms.basis_type)
    assert np.array_equal(back.density_total, ms.density_total)
    assert np.array_equal(back.overlap, ms.overlap)


@requires_orca
def test_mdm_components_present_for_rhf_uhf_rohf():
    for model in (
        from_orca_directory(_ORCA / "h2o"),
        from_orca_uhf_directory(_ORCA / "uhf" / "o2_uhf_sto3g"),
        from_orca_rohf_directory(_ORCA / "rohf" / "o2_rohf_sto3g"),
    ):
        assert model.atoms.ncenter == model.geometry.coordinates.shape[0]
        assert model.electronic.charge is not None
        assert model.electronic.multiplicity is not None
        assert model.wavefunction is not None
        assert model.matrices.S is not None
        assert model.matrices.P_total is not None
        assert model.basis.primitives is not None
        assert model.basis.shells
        assert model.basis.aos
        assert model.provenance.source_program == "ORCA"
        model.validate(strict=True)
        assert normalization_report(model)["status"] == "PASS"
        if model.electronic.wfntype in (1, 2):
            assert model.matrices.P_alpha is not None
            assert model.matrices.P_beta is not None
            assert np.allclose(
                model.matrices.P_total.data,
                model.matrices.P_alpha.data + model.matrices.P_beta.data,
                atol=1e-12,
            )
