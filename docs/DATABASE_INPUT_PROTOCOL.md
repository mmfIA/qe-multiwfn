# Database input protocol

**Module:** `qe_multiwfn.adapters.database`
**Objects:** `DatabaseRecord`, `from_database_record(record, *, basis=None)`
**Status:** generic protocol PASS; no real database connector.

## 1. Principle

The MDM never knows a database name, schema, query language, connection
object or response format. A database adapter owns that knowledge and maps
one record to the source-neutral `DatabaseRecord`; conversion then uses the
same builder, normalization and Engine as every other source.

```text
database record
      -> database-specific adapter
      -> DatabaseRecord
      -> from_database_record
      -> MolecularDataBuilder
      -> MolecularSystemV1
      -> Engine
```

## 2. Fields

| Field | Required | Meaning |
|---|---|---|
| `record_id` | yes | source-local identifier, provenance only |
| `source` | yes | source/database label, provenance only |
| `atomic_numbers` | yes | `(ncenter,)` |
| `coordinates` | yes | `(ncenter, 3)` |
| `coordinate_unit` | yes | `"angstrom"` or `"bohr"` |
| `basis` | yes | `BasisInput` or `BasisSet` from the source |
| `charge` | no | default 0 |
| `multiplicity` | no | default 1 |
| `wfntype` | no | explicit RHF/UHF/ROHF when needed |
| `nelectron` | no | defaults to ΣZ−charge |
| `coefficients` | conditional | MO coefficients |
| `occupations` | conditional | orbital occupations |
| `energies` | no | orbital energies metadata |
| `spins` | conditional | UHF/ROHF spin labels when needed |
| `overlap` | no | direct S |
| `density_total` | no | direct total P |
| `density_alpha`, `density_beta` | conditional | direct open-shell P |
| `schema_version` | no | default 1.1.0 |
| `provenance` | no | optional source provenance |
| `metadata` | no | source-specific traceability |

The `basis`, orbitals and matrices are passed unchanged to the builder. No
density formula, normalization algorithm or validation is reimplemented in
this module.

## 3. Conversion

```python
from qe_multiwfn.adapters.database import DatabaseRecord, from_database_record

record = DatabaseRecord(
    record_id="A-001",
    source="synthetic-db",
    atomic_numbers=[1, 1],
    coordinates=[[0, 0, 0], [0, 0, 1.4]],
    coordinate_unit="bohr",
    basis=basis_input,
    wfntype="RHF", multiplicity=1,
    overlap=S, density_total=P,
)
mdm = from_database_record(record)
```

Validation is inherited from the builder and Engine; the protocol does not
add a parallel scientific path.

## 4. Provenance

`record_id`, `source` and `metadata` are added to provenance warnings. If the
caller supplies no provenance, the adapter creates a generic
`source_format="database_record"` entry with the database label and unit
conversion. No connection details or credentials are stored.

## 5. Synthetic test

`tests/python/test_database_adapter.py` creates two independent synthetic
records with different IDs and database labels but identical scientific
arrays. Both produce the same MDM and the same Engine Mayer result. No real
database, network, credentials or file is used.

## 6. Limitations

- No concrete database connector is implemented.
- No schema discovery, query execution, caching or network layer.
- The database adapter must provide a valid basis or complete AO map; the MDM
  cannot infer a basis from geometry alone.
- PBC, post-HF and ECP records remain outside the validated execution scope.
- Source-specific conventions must be mapped before the record is passed in;
  unknown conventions fail closed in the builder.
