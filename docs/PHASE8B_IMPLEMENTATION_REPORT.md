> **Historical Phase 8B report.** Phase 8C extends the validated scope to
> O₂/def2-TZVP UHF/ROHF and corrects the measured ABI inventory. The ABI
> counts in this report are historical; see `PHASE8C_ARCHITECTURE_AUDIT.md`
> and `checkpoints/PHASE8C_CHECKPOINT.md` for the current state.

# Phase 8B — native spherical f support

**Status:** COMPLETE for canonical spherical f on the validated RHF fixture.
**Python:** `0.3.0.dev0`; **MDM:** `1.2.0`; **native ABI:** `0.2.0` with one
additive flag symbol.

## 1. Starting state and checkpoint

Phase 7C was checkpointed before editing:

`MDM_1.1_work/PHASE8B/CHECKPOINT_PHASE7C/`

Reference state:

| Item | Before 8B |
|---|---|
| Dev library | `8885ae9e…` |
| Frozen 0.2.0 | `9560c0fc…` |
| Tests | 192 passed; CTest 6/6 |
| ABI | 31 legacy + 14 additive = 45 |
| f guard | `l > 2` |
| Vendor | diff empty |
| Scientific refs | `6fb8b315…` |

## 2. Audit result

| Component | Before | Change | Result |
|---|---|---|---|
| `qe_gensbas_build` | rejected `l > 2` | allow `l=3` with canonical flag; reject `l > 3`; reject Cartesian f | PASS |
| `qe_genpprim_generate` | rejected `l > 2` | allow `l=3` through validated basis builder; reject `l > 3` | PASS |
| Cartesian f primitive table | table support present | no new algorithm; validated only for spherical f | PASS for spherical |
| `genSbas`/`genSbas_curr` | vendor supports d/f tables | called with f; `matCar2curr` f table | PASS |
| `genP` | method-generic | f C/P from canonical MDM | PASS |
| `genPprim` | `CO`/primitive table | f primitive density, separate from current P | PASS |
| `matCar2curr`/`gensphcartab` | f 7/10 tables present | no vendor change | PASS |
| Mayer | method-generic | f P/S accepted | PASS |
| g/h | not supported | explicit `l > 3` rejection | BLOCKED |
| Cartesian f native | unvalidated | explicit rejection in basis builder | BLOCKED |

## 3. Native canonical flag

Because Fortran does not receive the MDM source/angular metadata, a new
additive C ABI flag was introduced:

```text
qe_v1_set_angular_canonical(int canonical)
```

The Python Engine sets it from the loaded model:

- `1` when the model is MDM 1.2 with canonical `basis.angular`;
- `0` otherwise.

`qe_gensbas_build` accepts spherical f only when:
- the MDM canonical flag is set;
- the shell is spherical;
- `l <= 3`.

The non-canonical 1.1 f path remains fail-closed for original-routine state
building. The existing direct P/S path is not changed.

## 4. Files changed

Fortran wrappers/state (not vendor):

- `src/state/qe_molecular_state.f90`
- `src/state/qe_state_builder.f90`
- `src/state/qe_gensbas.f90`
- `src/state/qe_genpprim.f90`
- `src/bridge/qe_c_api.f90`
- `include/qe_multiwfn_v1.h`

Python:

- `python/qe_multiwfn/native.py`
- `python/qe_multiwfn/engine.py`

Tests:

- `tests/python/test_native_f_support.py` (new)
- `tests/python/test_orca_angular_integration.py` (Phase 7C backend
  expectation updated to Phase 8B support)

Docs:

- `docs/PHASE8B_*`
- current status/limitations/architecture updated.

No `orca.py` change in Phase 8B. No vendor, frozen, or reference change.

## 5. Validation

- Canonical ORCA 6.1.1 H₂S/def2-TZVP f full flow:
  - `S` max vs canonical supplied S: `3.613623997e-9`;
  - `P` max: `1.734723476e-18`;
  - Mayer max vs direct: `7.543932812e-9`;
  - Mayer max vs Multiwfn standalone: `8.449582811e-9`;
  - `Tr(PS)=18.0000000063`;
  - `PSP−2P=1.825046891e-9`;
  - `Pprim` shape `(85,85)`; `Tr(Pprim*Sprim)=18.0000000063`.
- H₂O/6-31G* d canonical path remains bitwise identical.
- All previous tests remain green: **198 passed**, CTest **6/6**.

## 6. Scientific boundary

This phase validates spherical f for the H₂S/def2-TZVP RHF fixture. It does
not validate Cartesian f, g/h, or UHF/ROHF f (no f open-shell fixture was
available). The backend accepts f because the canonical MDM path is
scientifically validated; it does not accept arbitrary uncorrected ORCA f.

## 7. Final ABI and checks

- Legacy symbols: **31** (unchanged).
- Additive symbols: **15** (Phase 8B adds `qe_v1_set_angular_canonical`).
- Total: **46**; missing legacy = 0.
- Native library version remains `0.2.0`.
- Full Python: **198 passed, 1 warning**.
- CTest: **6/6**.
- H₂O/6-31G* d remains bitwise unchanged.
