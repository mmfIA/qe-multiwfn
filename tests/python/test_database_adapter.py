"""Phase 9C — generic database-record protocol tests."""
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn import BasisInput
from qe_multiwfn.adapters.database import (
    DatabaseRecord, InMemoryDatabaseProvider, from_database_provider,
    from_database_record,
)
from qe_multiwfn.model_v1 import AOFunction


def _basis():
    return BasisInput(
        aos=[
            AOFunction(index=1, center=1, l=0, component="s",
                       angular_type=0, multiwfn_type=1),
            AOFunction(index=2, center=2, l=0, component="s",
                       angular_type=0, multiwfn_type=1),
        ],
        nbasis=2, nprims=2, normalization_convention="source_normalized",
    )


def _record(source, record_id):
    return DatabaseRecord(
        record_id=record_id,
        source=source,
        atomic_numbers=[1, 1],
        coordinates=[[0, 0, 0], [0, 0, 1.4]],
        coordinate_unit="bohr",
        basis=_basis(),
        charge=0, multiplicity=1, wfntype=0,
        overlap=np.array([[1.0, 0.5], [0.5, 1.0]]),
        density_total=np.full((2, 2), 2.0 / 3.0),
        metadata={"method": "synthetic"},
    )


def test_synthetic_database_records_converge():
    r1 = from_database_record(_record("database-A", "A-001"))
    r2 = from_database_record(_record("database-B", "B-009"))
    assert r1.nbasis == r2.nbasis == 2
    np.testing.assert_array_equal(r1.matrices.S.data, r2.matrices.S.data)
    np.testing.assert_array_equal(r1.matrices.P_total.data,
                                  r2.matrices.P_total.data)
    with qe.Engine() as e1:
        a = e1.calculate_mayer(r1).total
    with qe.Engine() as e2:
        b = e2.calculate_mayer(r2).total
    np.testing.assert_array_equal(a, b)
    assert "A-001" in str(r1.provenance.warnings)
    assert "B-009" in str(r2.provenance.warnings)


def test_database_record_validation_errors():
    r = _record("db", "id")
    with pytest.raises(ValueError, match="record_id"):
        from_database_record(DatabaseRecord(
            record_id="", source="db", atomic_numbers=[1],
            coordinates=[[0, 0, 0]], coordinate_unit="bohr", basis=_basis()))
    with pytest.raises(ValueError, match="source"):
        from_database_record(DatabaseRecord(
            record_id="x", source="", atomic_numbers=[1],
            coordinates=[[0, 0, 0]], coordinate_unit="bohr", basis=_basis()))
    with pytest.raises(ValueError, match="coordinate_unit"):
        from_database_record(DatabaseRecord(
            record_id="x", source="db", atomic_numbers=[1],
            coordinates=[[0, 0, 0]], coordinate_unit="meter", basis=_basis()))
    with pytest.raises(ValueError, match="basis"):
        from_database_record(DatabaseRecord(
            record_id="x", source="db", atomic_numbers=[1],
            coordinates=[[0, 0, 0]], coordinate_unit="bohr"))
    assert isinstance(r, DatabaseRecord)


def test_in_memory_database_provider():
    records = [_record("database-A", "A-001"), _record("database-B", "B-009")]
    provider = InMemoryDatabaseProvider(records)
    a = from_database_provider(provider, "A-001")
    b = from_database_provider(provider, "B-009")
    assert a.nbasis == b.nbasis == 2
    with pytest.raises(KeyError, match="not found"):
        from_database_provider(provider, "missing")
    with pytest.raises(ValueError, match="duplicate"):
        InMemoryDatabaseProvider([records[0], records[0]])


def test_external_provider_conformance():
    class ExternalProvider:
        def __init__(self, record):
            self.record = record

        def get_record(self, record_id):
            if record_id != self.record.record_id:
                raise KeyError(record_id)
            return self.record

    provider = ExternalProvider(_record("external-source", "EXT-1"))
    mdm = from_database_provider(provider, "EXT-1")
    assert mdm.nbasis == 2
    with pytest.raises(KeyError):
        from_database_provider(provider, "missing")
