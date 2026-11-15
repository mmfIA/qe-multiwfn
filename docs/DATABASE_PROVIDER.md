# DatabaseProvider — Phase 11

**Module:** `qe_multiwfn.adapters.database`
**Status:** generic protocol and in-memory reference connector PASS.

## 1. Contract

```python
class DatabaseProvider(Protocol):
    def get_record(self, record_id: str) -> DatabaseRecord: ...
```

The provider is the only database-aware layer. It maps its native record to
`DatabaseRecord`; `from_database_provider` and `from_database_record` use the
same `MolecularDataBuilder`.

## 2. Reference connector

`InMemoryDatabaseProvider`:

- stores records by ID;
- rejects duplicate IDs;
- returns `KeyError` for an unknown ID;
- has no network, credentials or external dependency.

Example:

```python
from qe_multiwfn.adapters.database import (
    InMemoryDatabaseProvider, from_database_provider,
)

provider = InMemoryDatabaseProvider([record_a, record_b])
mdm = from_database_provider(provider, "A-001")
```

## 3. Record maturity

`DatabaseRecord` distinguishes, by the fields supplied:

1. structural geometry;
2. geometry + basis;
3. geometry + basis + orbitals/matrices;
4. analysis-ready only after MDM/Engine validation.

Structural records are never marked Mayer-ready.

## 4. Real connectors

A real connector must be a separate optional module. It must not require
network access on import, must not add credentials to the core, and must not
call Fortran, ctypes, ABI or Engine internals. Its `get_record` returns the
same `DatabaseRecord` contract.

No real external connector is implemented or claimed in this phase.

## 5. Tests

`tests/python/test_database_adapter.py` covers synthetic sources, provider
lookup, missing/duplicate records and contract validation.
