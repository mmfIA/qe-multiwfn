# Database connector architecture — Phase 10

**Module:** `qe_multiwfn.adapters.database`
**Status:** generic protocol + in-memory reference connector PASS; no real
database dependency.

## 1. Boundary

```text
external provider
      -> provider-specific mapping
      -> DatabaseRecord
      -> from_database_provider / from_database_record
      -> MolecularDataBuilder
      -> MolecularSystemV1
      -> Engine
```

The core knows only `DatabaseRecord`, `DatabaseProvider` and the MDM builder.
It does not know a database name, query language, connection, schema, network
or credentials.

## 2. Protocol

`DatabaseProvider` requires one method:

```python
def get_record(self, record_id: str) -> DatabaseRecord: ...
```

`InMemoryDatabaseProvider` is the reference implementation used for tests and
offline demonstrations. A real connector is a separate module implementing the
same method.

`from_database_provider(provider, record_id, *, basis=None, validate=True)`
retrieves one record and calls `from_database_record`.

## 3. Record maturity

`DatabaseRecord` can represent:

1. **structural**: geometry only; `basis`/orbitals/matrices absent;
2. **basis**: geometry + `BasisInput`/`BasisSet`;
3. **electronic**: basis + orbitals and/or S/P;
4. **analysis-ready**: MDM readiness applies only after conversion and
   validation.

The protocol never labels a structural record as Mayer-ready. Missing data is
reported by the builder/Engine; no data is invented.

## 4. Fields

`record_id`, `source`, `atomic_numbers`, `coordinates`, `coordinate_unit`,
`basis`, `charge`, `multiplicity`, `wfntype`, `nelectron`, coefficients,
occupations, energies, spins, overlap, densities, schema version, provenance,
metadata.

Required/conditional behavior is inherited from `MolecularDataBuilder` and
`MolecularSystemV1.validate`.

## 5. Connectors

- `InMemoryDatabaseProvider` is implemented and tested.
- A future connector should:
  - fetch a record by ID;
  - map source fields to `DatabaseRecord`;
  - attach provenance/record ID;
  - optionally pass a prebuilt basis;
  - never call Fortran, the Engine native API or a subprocess.
- Connectors are optional modules; `import qe_multiwfn` must not require any
  database package.

## 6. Tests

`tests/python/test_database_adapter.py` covers:

- two synthetic sources with identical scientific arrays → identical MDM and
  Engine result;
- provider lookup by ID;
- missing record;
- duplicate ID;
- missing/unknown source, unit, basis validation.

No network, credentials or real database is used.

## 7. Limitations

- no real provider connector;
- no schema discovery or query layer;
- no caching;
- PBC/post-HF/ECP records remain outside the validated execution scope.
