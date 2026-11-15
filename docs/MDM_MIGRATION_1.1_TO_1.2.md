# MDM migration 1.1 → 1.2

## 1. Compatibility policy

- `SCHEMA_VERSION` remains `1.1.0` as the default.
- Existing 1.1 models remain valid and are not rewritten automatically.
- `SUPPORTED_SCHEMA_VERSIONS = ("1.1.0", "1.2.0")`.
- A model becomes 1.2.0 only through an explicit
  `canonicalize_model_angular(...)` call.
- Unknown schema versions are rejected.

## 2. What changes for a 1.1 model

Nothing is required. A 1.1 model has no angular metadata; its angular state is
`unknown`, which is explicit and fail-closed.

If a caller wants a canonical 1.2 model:

1. provide an explicit source convention for every spherical `l >= 2` shell;
2. call `canonicalize_model_angular`;
3. keep the returned model; the input model is not mutated.

## 3. What changes for a 1.2 model

- `basis.angular` is present and in `canonical` state.
- every shell has canonical angular metadata;
- orbitals and AO-current-basis matrices have canonical angular metadata;
- `Provenance.angular_transforms` records the transform(s);
- `to_legacy()` is rejected because 0.1.1 cannot represent the angular
  metadata;
- `with_ao_order()` is rejected because it would invalidate the canonical
  AO/component mapping.

## 4. Old data and unknowns

- 1.1 models are never assigned a convention by default.
- Missing source metadata for d/f shells causes `canonicalize` to fail.
- An unknown source state, wrong order, bad signs or wrong normalization
  fails closed.
- A source `f` convention does not imply a g/h convention.
- Primitive-basis matrices are not transformed by the spherical phase API.

## 5. Verification

The migration keeps:

- 155 pre-existing Python tests passing (plus new Phase 7B tests);
- CTest 6/6 without rebuilding the library;
- the native library hash unchanged;
- ABI verified as 17 legacy + 27 additive symbols (44 total; Phase 8C), with
  the legacy surface unchanged (15 additive symbols since the frozen baseline);
- `vendor/`, frozen 0.2.0 and reference results unchanged.

See `MDM_1.1_work/PHASE7B/MIGRATION_REPORT.md` and
`MDM_1.1_work/PHASE7B/TEST_REPORT.md`.
