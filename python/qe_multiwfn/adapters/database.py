"""Generic database-record protocol for the canonical MDM builder.

This module intentionally knows nothing about a database engine, schema,
connection or network. A database adapter maps its own record to
``DatabaseRecord`` and calls ``from_database_record``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Sequence

import numpy as np

from ..builder import build_molecular_system
from ..model_v1 import Provenance


@dataclass
class DatabaseRecord:
    record_id: str
    source: str
    atomic_numbers: Sequence[int]
    coordinates: Sequence[float]
    coordinate_unit: str
    basis: Any = None
    charge: int = 0
    multiplicity: int = 1
    wfntype: Optional[Any] = None
    nelectron: Optional[int] = None
    coefficients: Any = None
    occupations: Any = None
    energies: Any = None
    spins: Any = None
    overlap: Any = None
    density_total: Any = None
    density_alpha: Any = None
    density_beta: Any = None
    schema_version: str = "1.1.0"
    provenance: Optional[Provenance] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def from_database_record(record: DatabaseRecord, *, basis=None,
                         validate: bool = True):
    """Convert a source-neutral database record into a validated MDM."""
    if not isinstance(record, DatabaseRecord):
        raise TypeError("record must be a DatabaseRecord")
    if not str(record.record_id).strip():
        raise ValueError("DatabaseRecord.record_id is required")
    if not str(record.source).strip():
        raise ValueError("DatabaseRecord.source is required")
    if record.coordinate_unit not in ("angstrom", "bohr"):
        raise ValueError("DatabaseRecord.coordinate_unit must be angstrom or bohr")
    basis = record.basis if basis is None else basis
    if basis is None:
        raise ValueError("DatabaseRecord.basis is required")
    provenance = record.provenance
    if provenance is None:
        provenance = Provenance(
            source_program=str(record.source),
            source_version="",
            source_format="database_record",
            adapter_name="qe_multiwfn.adapters.database",
            adapter_version="1.0.0",
            coordinate_unit_source=record.coordinate_unit,
            conversion_factor=(1.0 if record.coordinate_unit == "bohr" else 1.0 / 0.529177210903),
        )
    metadata = {
        "record_id": str(record.record_id),
        "source": str(record.source),
        **dict(record.metadata or {}),
    }
    provenance.warnings.append("database record: " + str(metadata))
    return build_molecular_system(
        atomic_numbers=record.atomic_numbers,
        coordinates=record.coordinates,
        coordinate_unit=record.coordinate_unit,
        charge=record.charge,
        multiplicity=record.multiplicity,
        nelectron=record.nelectron,
        wfntype=record.wfntype,
        basis=basis,
        overlap=record.overlap,
        density_total=record.density_total,
        density_alpha=record.density_alpha,
        density_beta=record.density_beta,
        coefficients=record.coefficients,
        occupations=record.occupations,
        energies=record.energies,
        spins=record.spins,
        schema_version=record.schema_version,
        provenance=provenance,
        validate=validate,
    )


class DatabaseProvider(Protocol):
    """Minimal provider interface required by the core protocol."""

    def get_record(self, record_id: str) -> DatabaseRecord:
        ...


class InMemoryDatabaseProvider:
    """Reference connector for tests and in-memory scientific records."""

    def __init__(self, records):
        self._records = {}
        for record in records:
            if not isinstance(record, DatabaseRecord):
                raise TypeError("provider records must be DatabaseRecord objects")
            if record.record_id in self._records:
                raise ValueError(f"duplicate record_id {record.record_id!r}")
            self._records[record.record_id] = record

    def get_record(self, record_id: str) -> DatabaseRecord:
        try:
            return self._records[record_id]
        except KeyError as exc:
            raise KeyError(f"database record not found: {record_id!r}") from exc


def from_database_provider(provider: DatabaseProvider, record_id: str,
                           *, basis=None, validate: bool = True):
    """Load one provider record and convert it through the generic protocol."""
    if not hasattr(provider, "get_record"):
        raise TypeError("provider must implement get_record(record_id)")
    record = provider.get_record(record_id)
    return from_database_record(record, basis=basis, validate=validate)


__all__ = [
    "DatabaseRecord", "DatabaseProvider", "InMemoryDatabaseProvider",
    "from_database_record", "from_database_provider",
]
