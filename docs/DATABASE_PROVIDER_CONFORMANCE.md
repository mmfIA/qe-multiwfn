# DatabaseProvider conformance — Phase 12

## 1. Contract

```python
class DatabaseProvider(Protocol):
    def get_record(self, record_id: str) -> DatabaseRecord: ...
```

The provider returns a source-neutral `DatabaseRecord`; conversion is
performed by `from_database_provider`/`from_database_record` and the same
`MolecularDataBuilder`.

## 2. External implementation test

`tests/python/test_database_adapter.py` defines an `ExternalProvider` class
directly in the test, outside the QE-Multiwfn database module. It implements
only:

```python
def get_record(self, record_id):
    ...
```

The test confirms that this external provider can feed the protocol without
knowing Fortran, ctypes, ABI, Engine internals or native symbols.

## 3. Reference connector

`InMemoryDatabaseProvider` remains the reference:

- lookup by ID;
- duplicate ID rejection;
- missing ID raises `KeyError`;
- no network, credentials or external dependency.

## 4. Real connectors

No real external database connector is implemented or claimed. A future
connector must remain optional, must not perform network access at import and
must use the same contract.

## 5. Core isolation

The core import does not import a provider or database package. Provider errors
are local to the adapter/conversion layer.
