# Phase 9A — MDM as universal input contract

**Audit date:** 2026-11-14
**Tree:** `<repository>`
**Verdict:** **PARTIAL**
**Scope:** audit only. No executable code, ABI, fixture, vendor or frozen file
was changed.

## 1. Method

The audit inspected the Python MDM (`molecular.py`, `model_v1.py`,
`angular.py`, `normalization.py`), the Engine (`engine.py`, `native.py`,
`results.py`), all adapters (`orca`, ASE, cclib), the C headers and the
Fortran state/Mayer wrappers. Existing tests and non-destructive probes were
used; no test was modified.

The name **MolecularData** in the Phase 9A brief maps to the current
`MolecularSystemV1` tree. The older `MolecularSystem` remains a separate
RHF-only 0.1.1 compatibility container.

## 2. Hierarchy and responsibilities

```text
MolecularSystemV1
├── schema_version      1.1 default; 1.2 opt-in
├── provenance          Provenance (metadata only; not used by Engine)
├── atoms               Atoms
├── geometry            Geometry (internal unit always Bohr)
├── electronic          ElectronicState (wfntype/charge/multiplicity/Ne)
├── basis               BasisSet
│   ├── shells          list[Shell]
│   ├── primitives      PrimitiveTable? (required for full state)
│   └── aos             list[AOFunction] (required by Engine)
├── wavefunction        Wavefunction? (required for full state)
├── matrices            MatrixBundle (S/P direct path or generated path)
├── core_correction     CoreCorrection? (modeled; execution unsupported)
├── periodicity         Periodicity (isolated default; Engine rejects PBC)
└── readiness           ReadinessFlags (computed; not a substitute for validate)
```

## 3. Structure-by-structure audit

### 3.1 `FileRecord` and `Provenance`

| Question | Finding |
|---|---|
| Responsibility | Traceability of source files, conversions, hashes and angular transforms. |
| Required | `FileRecord`: `role`, `relative_path`. `Provenance`: `source_program`, `source_format`, `coordinate_unit_source` must be valid. |
| Optional | File hash/size/time; source version; adapter name/version; warnings; hashes; `angular_transforms`. |
| Validation | `source_program` and `source_format` non-empty; unit is `bohr`/`angstrom`; SHA length when present. |
| Scientific data | None. This is metadata. |
| Discarded | File bytes, absolute paths, program-specific parser objects are not retained. |
| ORCA / file / external dependency | No hard dependency. `source_program` defaults to `"python"`; `input_files` may be empty. |
| Direct memory | Yes; defaults make it constructible in memory. |
| Sufficient for Engine | No, but not required by Engine. `Engine` never reads provenance. |
| Redundancy / ambiguity | `source_version` is documented as required by the 1.0 spec but is not validated; defaults to empty. `FileRecord` can be empty. Good for traceability, not a scientific blocker. |

**Conclusion:** provenance is correctly optional in practice and is not an
ORCA requirement. A source can supply only `source_program="python"` and
`source_format="arrays"`.

### 3.2 `Atoms` and `Geometry`

| Question | Finding |
|---|---|
| Responsibility | Chemical identity, nuclear/effective charges, labels, coordinates and optional cell. |
| Required | `Atoms.z` (1-D, 1..118); `Geometry.coordinates` `(ncenter,3)`. |
| Optional | `symbols` (auto-filled), `nuclear_charge` (default Z), effective charges, labels/residue/ghost; cell vectors and periodic directions. |
| Validation | Z range; symbol/Z consistency; finite coordinates; fixed `unit_internal="bohr"`; source unit valid; cell shapes. |
| Scientific data | Z, effective charge, coordinates, cell. |
| Discarded | PDB residue names/labels are preserved but not used; no conversion history beyond provenance. |
| ORCA / file / external | No; `Geometry.from_source` is a generic unit converter. |
| Direct memory | Yes; NumPy arrays. |
| Sufficient for Engine | Z and coordinates are sufficient for the Engine; labels/residue/cell are ignored or rejected (PBC). |
| Redundancy / ambiguity | `unit_source` is metadata; `coordinates` are always Bohr. `nuclear_charge` can disagree with Z without an explicit validation warning. `ghost` is not used by the current Mayer path. |

**Conclusion:** geometry input is origin-neutral. Internal unit handling is
clear: callers must pass Bohr or use `Geometry.from_source`/`from_arrays`.

### 3.3 `ElectronicState`

| Question | Finding |
|---|---|
| Responsibility | `wfntype`, charge, multiplicity, Ne and spin electron counts. |
| Required | `wfntype`, `charge`, `multiplicity`, `nelectron`. |
| Optional | `naelectron`, `nbelectron`, `imodwfn`, energy, virial, ECP core count. |
| Validation | wfntype 0..4; multiplicity ≥1; Ne >0; RHF requires mult=1 and even Ne; alpha/beta non-negative. ROHF/UHF parity and `na+nb` consistency are only checked by `validate_against`/strict paths, not in the constructor. |
| Scientific data | wfntype, charge, multiplicity, Ne, alpha/beta counts. |
| Discarded | Energy/virial are metadata, not used by Mayer. |
| ORCA / file / external | No. |
| Direct memory | Yes. |
| Sufficient for Engine | Yes for RHF/UHF/ROHF; post-HF values 3/4 are represented but rejected by the current Engine. |
| Redundancy / ambiguity | `nelectron` is redundant with sum(Z)-charge; it is validated in `MolecularSystemV1.validate`, but not in a standalone `ElectronicState`. `naelectron`/`nbelectron` may be absent and are inferred from multiplicity in some paths. |

### 3.4 `Shell`

| Question | Finding |
|---|---|
| Responsibility | One contracted shell: center, l, primitive range, contraction and representation. |
| Required | `index`, `center`, `l`, `shell_type`, `primitive_start/end`, `exponents`, `coefficients`. |
| Optional | `normalization`, `contraction_normalization`, `source_label`, `multipole`, `angular`. |
| Validation | 1-based indexes/center; l≥0; valid primitive range; positive exponents; matching coefficient shape; exactly one of Cartesian/spherical; angular l/representation consistency. |
| Scientific data | Exponents, contraction coefficients, center, l, representation. |
| Discarded | Source shell label is preserved but not used by Engine; primitive-block normalization may be absent. |
| ORCA / file / external | No; `source_label` is informational. |
| Direct memory | Yes; NumPy arrays. |
| Sufficient for full Engine path | Not alone: needs primitive table, AO map, normalization and orbitals. Not needed for the direct P/S path. |
| Redundancy / ambiguity | Shell exponents/coefficients duplicate `PrimitiveTable` data (when both exist). `shell_type` is not validated against `l`; `primitive_start/end` are not cross-checked against the primitive table beyond range; `source_label` is free text. |

### 3.5 `PrimitiveTable`

| Question | Finding |
|---|---|
| Responsibility | Global primitive records: center, component type, exponent, contraction coefficient, optional normalization and shell link. |
| Required | `center`, `type`, `exponent`, `coefficient`. |
| Optional | `normalization`, `shell_index`. |
| Validation | Equal lengths; positive centers/exponents; positive 1-based shell indexes when present; shape. |
| Scientific data | Primitive exponents, coefficients, component types. |
| Discarded | Source primitive labels are not stored. |
| ORCA / file / external | No. |
| Direct memory | Yes. |
| Sufficient for full Engine | Not alone; needs shells/AO map and normalization. |
| Redundancy / ambiguity | `type` accepts any int32; no range/component validation in Python. `shell_index` is optional, but the full-state Fortran path benefits from it. `Normalization` defaults to `None`, while `qe_gensbas_build` requires per-AO normalization metadata. |

### 3.6 `AOFunction`

| Question | Finding |
|---|---|
| Responsibility | One contracted basis function in the authoritative AO ordering. |
| Required | `index`, `center`; `MolecularSystemV1.validate` additionally requires `angular_type` for every AO. |
| Optional | `shell_index`, `l`, `component`, `multiwfn_type`, `angular_type`, `legacy_basis_type`, `cartesian`, `source_label/index`, normalization fields. |
| Validation | 1-based index/center; optional shell index; nonnegative l/source index; angular/legacy aliases; normalization convention enum and finite/positive contraction. It does **not** require `shell_index` or `multiwfn_type`, despite the 1.0 spec. |
| Scientific data | center, l, component/code, shell link, representation. |
| Discarded | Source labels/indexes preserved as metadata. |
| ORCA / file / external | No; `component` is a standard name/code, not ORCA-only. |
| Direct memory | Yes. |
| Sufficient for Engine | Engine requires the AO list; it substitutes `0` for missing `multiwfn_type` and `i` for missing `source_index`. Full-state Fortran validation checks shell/l/center consistency. |
| Redundancy / ambiguity | `l`, `angular_type`, `legacy_basis_type` and `multiwfn_type` are related but not one canonical field. `shell_index` is optional in code but documented as required. `multiwfn_type=0` substitution can hide missing component metadata. |

### 3.7 `BasisSet`

| Question | Finding |
|---|---|
| Responsibility | Container for basis dimensions, representation, ordering, shells, primitives, AO map and angular contract. |
| Required | `nbasis`, `nprims`; `aos` is required by Engine, not by `BasisSet`. |
| Optional | `nindbasis`, Cartesian/spherical counts, `representation`, `normalization_convention`, `ao_order`, `shells`, `primitives`, `angular`. |
| Validation | nbasis≥1; nprims≥nbasis; known representation/convention; AO indices 1..nbasis; primitive count; shell primitive end; angular type. It does not enforce `aos` presence or that shells/AOs/primitives are mutually consistent. |
| Scientific data | AO ordering, shell/l/component map, primitives. |
| Discarded | Source-specific basis labels not used by the backend; normalization metadata is separate. |
| ORCA / file / external | No. |
| Direct memory | Yes, but the user must construct all substructures manually. |
| Sufficient for Engine | Direct P/S path: `nbasis`, `aos`, S/P; full state: shells/primitives/AO map/normalization/orbitals. |
| Redundancy / ambiguity | `nbasis_cartesian`/`nbasis_spherical` are optional and not cross-checked; `representation` can be `unspecified` while `aos` are spherical; `ao_order` is a string, not an enforced permutation. |

### 3.8 `OrbitalSet` and `Wavefunction`

| Question | Finding |
|---|---|
| Responsibility | Molecular coefficients, energies, occupations, spin labels and layout. |
| Required | coefficients, representation, layout, energies, occupations, spin. |
| Optional | symmetry labels, orbital indices, HOMO/LUMO, nocc, angular. |
| Validation | finite arrays; representation/layout enums; energies/occupations 1-D matching; nonnegative occupations; spin length; coefficient shape per declared layout; optional angular type. |
| Scientific data | C, energies, occupations, spin. |
| Discarded | Symmetry labels are preserved as metadata. |
| ORCA / file / external | No. |
| Direct memory | Yes. |
| Sufficient for full Engine | Yes if the coefficient shape matches nbasis and the model has basis/normalization; Python does not enforce `C.shape[0]==nbasis` in all cases. |
| Redundancy / ambiguity | `nocc` is optional/derived; occupations can be fractional but no sum/Ne check at construction; spin labels are strings, not a fixed enum type. |

### 3.9 `MatrixRecord` and `MatrixBundle`

| Question | Finding |
|---|---|
| Responsibility | S, P_total, P_alpha, P_beta, primitive P and extra AO matrices with representation/origin/hashes. |
| Required | data, representation for any present record. |
| Optional | layout, symmetric, origin, derivation, tolerance, SHA, angular. |
| Validation | square/finite data; representation enum; origin enum; SHA auto-filled; angular type. `layout` is not validated; `symmetric=False` causes `MolecularSystemV1.validate` to skip symmetry. |
| Scientific data | S/P and representation. |
| Discarded | No S/P data is discarded; hash/derivation retained. |
| ORCA / file / external | No. |
| Direct memory | Yes. |
| Sufficient for Engine | Yes; Engine sends P/S for the direct path, or builds them for the full path. |
| Redundancy / ambiguity | `P_total` is redundant with P_alpha+P_beta for open-shell and is checked only in strict validation. `P_total_prim` is not checked by `MolecularSystemV1.validate`. `symmetric=False` is a fail-open option unless callers enforce it. |

### 3.10 `CoreCorrection` and `Periodicity`

| Question | Finding |
|---|---|
| Responsibility | ECP/EDF and PBC metadata. |
| Required | none beyond status. |
| Optional | ECP elements, effective Z, core electrons, EDF primitives/coefficients; PBC cell/neighbor/overlap. |
| Validation | status enum; numeric shapes; ifPBC 0..3; vectors shapes. Cross-consistency is limited. |
| Scientific data | Effective Z/core/EDF and cell. |
| Discarded | No scientific payload intentionally dropped, but execution is not implemented. |
| ORCA / file / external | No. |
| Direct memory | Yes. |
| Sufficient for Engine | No for PBC (`ifPBC>0` rejected) or ECP/EDF (incomplete/rejected); these are not part of the validated Mayer scope. |
| Redundancy / ambiguity | `CoreCorrection` and `Atoms.effective_nuclear_charge` both carry ECP data; no single source of truth. |

### 3.11 `MolecularSystemV1`

| Question | Finding |
|---|---|
| Responsibility | Root universal container and validation/readiness coordinator. |
| Required | `provenance`, `atoms`, `geometry`, `electronic`, `basis`; `schema_version` in {1.1,1.2}. |
| Optional | wavefunction, matrices, core/periodicity (defaults), legacy flag. |
| Validation | `validate(strict=False)` checks provenance, atom/geometry count, electron count, basis/AO centers, PBC cell, matrix shapes/symmetry, readiness and 1.2 angular. `strict=True` additionally checks S/P representation, Tr(PS), RHF idempotency, C^TSC, spin traces/idempotency and P_total=Pa+Pb. |
| Scientific data | All root scientific data above. |
| Discarded | Provenance and source labels are retained, not used by backend. |
| ORCA / file / external | None in the model. |
| Direct memory | Yes; all fields are Python/NumPy dataclasses. |
| Sufficient for Engine | Yes for direct P/S; full state needs complete basis/orbitals/normalization. Engine calls `validate(strict=False)`, not strict. |
| Redundancy / ambiguity | `legacy` flag; electron counts duplicated; `nbasis`/`nprims` duplicated in derived properties; `analysis_ready["mayer"]` excludes ROHF (bug); `with_ao_order` only for 1.1; `schema 1.2` requires angular metadata. |

## 4. Required versus metadata

### Scientific fields required for the current Mayer path

- atoms: Z
- geometry: Bohr coordinates (non-PBC)
- electronic: wfntype/charge/multiplicity/Ne; Na/Nb for open-shell
- basis: nbasis, AO map (`aos`), and for the full path shells/primitives/AO map/normalization
- wavefunction: coefficients/occupations/spin for the full path
- matrices: S and P (direct path), or S/P generated from basis/orbitals
- angular: canonical metadata for 1.2 spherical f
- units: internal Bohr, declared source unit

### Metadata that must remain optional

- `Provenance` (source program/version/format, file records, hashes)
- source labels, residue names, symmetry labels, HOMO/LUMO
- total energy, virial ratio, ECP core count
- adapter name/version
- `FileRecord` entries

The current default `Provenance(source_program="python", source_format="arrays")`
allows a non-ORCA producer to use the model without fabricating ORCA metadata.
`Engine` does not read provenance at all.

## 5. Validation gaps and ambiguities

| ID | Location | Finding | Impact |
|---|---|---|---|
| MDM-1 | `model_v1.py:867` | `analysis_ready["mayer"]` allows wfntype 0/1 only; ROHF (2) is reported not ready. | Readiness is wrong for a validated ROHF path; Engine does not currently consume it. |
| MDM-2 | `model_v1.py:471` | `AOFunction.shell_index`/`multiwfn_type` are optional, although the 1.0 spec treats shell_index as required. | Direct/Engine input can be ambiguous; Engine substitutes `0` for multiwfn_type. |
| MDM-3 | `model_v1.py:887-1022` | `validate(strict=False)` does not require S positive definite, does not enforce matrix `symmetric=True`, and does not validate orbitals against nbasis/Ne; strict path also skips C^TSC if C row count differs. | A malformed model can reach the native layer; native may fail later. |
| MDM-4 | `model_v1.py:369-409` | `Shell` does not validate shell_type/l consistency, primitive row ownership, or normalizations; `BasisSet` does not require shells/AOs/primitives to agree. | Full-state input needs extra checks in Fortran or a future builder. |
| MDM-5 | `model_v1.py:419-449` | Primitive `type` is not range-validated; `shell_index` is optional. | A malformed primitive type can remain latent until the native state build. |
| MDM-6 | `model_v1.py:626-668` | Orbital occupations are not checked against Ne/wfntype; coefficient row count is not required to equal nbasis. | A caller can construct an internally inconsistent wavefunction. |
| MDM-7 | `normalization.py:201` | `attach_normalization` mutates the model; Engine does not call it. Full state requires normalization metadata to be attached or supplied. | Direct MDM construction needs an explicit normalization step. |
| MDM-8 | `model_v1.py:684-710` | `MatrixRecord.layout` is unvalidated; `symmetric=False` bypasses symmetry validation. | Fail-open metadata option. |
| MDM-9 | `model_v1.py:1151` | `with_ao_order` drops `basis.angular`/matrix angular metadata (called only for 1.1; 1.2 rejects). | Fine for 1.1, but permutation is not a general 1.2 operation. |
| MDM-10 | `angular.py:729` | `validate_1_2_angular` validates state/order/l but not matrix convention-id identity or basis/shell representation consistency. | 1.2 models can be partially canonical without an exact provenance match. |

No gap was fixed in Phase 9A; all are candidates for Phase 9B or later.

## 6. Universal-contract assessment

| Criterion | Status | Evidence |
|---|---|---|
| Scientific data represented | PASS | Atoms, geometry, electronic, basis, orbitals, matrices, angular, units. |
| Source-neutral model | PASS | No ORCA import/fields required in `MolecularSystemV1` or `Engine`; provenance defaults to Python/arrays. |
| Direct in-memory construction | PARTIAL | Dataclasses allow it; a synthetic direct P/S probe ran without files. No high-level builder; full basis/normalization is manual. |
| Metadata separation | PASS | Provenance/file/labels are optional and ignored by Engine. |
| Validation/fail-closed | PARTIAL | Strict validation exists but Engine uses `strict=False`; gaps MDM-1..MDM-10. |
| Compatibility with legacy | PASS | `MolecularSystemV1.from_legacy`/`to_legacy` and legacy `MolecularSystem` retained. |
| PBC/ECP/post-HF | NOT APPLICABLE to validated scope | Modeled or rejected, not executed. |

**Conclusion:** the MDM is already the correct architectural center and is
origin-neutral for the validated RHF/UHF/ROHF and canonical-f scope. It is
not yet a fully ergonomic universal builder: direct construction is possible
but low-level, several invariants are deferred to the native layer, and
`analysis_ready`/Mayer total semantics need correction/documentation. The
Phase 9B specification proposes the missing builder and validation contract.

## 7. Files inspected

- `python/qe_multiwfn/model_v1.py`
- `python/qe_multiwfn/molecular.py`
- `python/qe_multiwfn/angular.py`
- `python/qe_multiwfn/normalization.py`
- `python/qe_multiwfn/engine.py`
- `python/qe_multiwfn/native.py`
- `python/qe_multiwfn/results.py`
- `python/qe_multiwfn/analysis/bond_order.py`
- `python/qe_multiwfn/adapters/{orca,ase,cclib}.py`
- `include/qe_multiwfn.h`, `include/qe_multiwfn_v1.h`
- `src/analysis/qe_mayer.f90`, `src/analysis/qe_analysis_state.f90`
- `vendor/Multiwfn_2026.11.3_src_Linux/bondorder.f90`
- `docs/MOLECULAR_DATA_MODEL_1.0.md`, `1.1.md`, `1.2.md`
- Existing tests `test_model_v1.py`, `test_angular_canonical.py`,
  `test_full_flow_mdm.py`, `test_open_shell_f_support.py`
