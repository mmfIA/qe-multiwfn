# QE-Multiwfn 0.1.1 — correction release

> **Historical document (0.1.1/0.2.0).** It records the frozen release notes
> at that time. Current 0.3.0-dev status and counts are in
> `docs/IMPLEMENTATION_STATUS.md` and `docs/LIMITATIONS.md`.

## Structural corrections

1. Basis ownership arrays now have length `nbasis`, not `nprims`.
2. `nprims` is independent and can exceed `nbasis`; this removes the incorrect equality restriction.
3. `basstart` / `basend` are derived from basis-function centers and interleaved center blocks are rejected.
4. The API accepts only closed-shell RHF in this release; multiplicity, positive even electron count, Tr(P*S)=N_e, and the RHF idempotency relation P*S*P=2P are validated.
5. Metadata derivation no longer sums atomic numbers before atomic data exists.
6. Data setters are blocked outside `SYSTEM_LOADED`, preventing mutation of Python-side state while Multiwfn globals still contain an older prepared snapshot.
7. System release clears cached Mayer results. The C ABI dimensions getter writes zero to its output on failure.
8. CMake now requires and links LAPACK as well as BLAS.
10. The build compiles only the upstream source dependency closure for the exposed Mayer path and uses a linker export map so only `qe_*` ABI symbols are public.
11. Build RPATH no longer contains the previous environment's implicit linker path list.

## Verification performed in the ChatGPT sandbox

- GNU Fortran 14.2.0 / GCC, CMake 3.31.6, Ninja.
- Release configuration completed.
- Shared library built successfully.
- `ctest`: 4/4 passed.
- `pytest`: 29/29 passed.
- `ldd -r`: no unresolved symbols reported.
- Dynamic symbol inspection: 17 exported `qe_*` functions; Multiwfn internals are hidden.
- Vendor-source integrity: 74 files in the supplied original ZIP and 74 files in `vendor/`; 0 missing, 0 extra, 0 hash differences (SHA-256).

## Scientific validation still pending

The contracted-dimension regression uses `nbasis=2`, `nprims=6`, but it is not
a full H₂/STO-3G SCF calculation. The sandbox has no PySCF or Psi4 installation
and no independent ORCA calculation artifact. Therefore this release must not
be described as independently validated against a real contracted-basis
wavefunction or a separate interactive Multiwfn run.

## Addendum — P0 reproduction on the target host (2026-11-14)

The limitation above applied to the isolated sandbox release. In the P0
operational audit on the user's host, the same 0.1.1 source was rebuilt
(gfortran 15.2.0 / CMake 4.2.3 / OpenBLAS), producing
`libqe_multiwfn.so` SHA-256 `b981c10b30dc6dc9e9b702c60f163a271279e70082c16f53305ec531f9eb9d56`.
With this build and an external ORCA 6.1.1 → adapter → Multiwfn 2026.11.3
flow, H₂, H₂O and C₆H₆ all reproduced the previously validated Mayer matrices
bit-for-bit (three independent result sets compared element by element).

This addendum does not change the 0.1.1 API or scientific scope: the library
receives P and S, and does not generate them or read quantum-chemistry files.
The evidence and caveats are recorded in
`QE-Multiwfn-validation/reports/P0_OPERATIONAL_VERIFICATION.md`.

## Addendum — Molecular Data Model 1.0 (development layer, 2026-11-14)

An additive v1 layer was implemented without changing the 0.1.1 API:

- Python `MolecularSystemV1` with `from_legacy`/`to_legacy` (bit-for-bit),
  strict validation and AO permutation;
- additive `qe_v1_*` C ABI for atoms, shells, primitives, AO map, density,
  overlap, optional orbitals and readiness;
- ORCA 6.1.1 JSON adapter for RHF s/p systems, with full provenance;
- the v1 path reproduces the H₂/H₂O/C₆H₆ Mayer matrices bit-for-bit and
  remains within the unchanged QE × Multiwfn criterion.

The legacy 17-symbol ABI, the original `calcMayerbndord` path and all
scientific tolerances are unchanged. UHF/ROHF, d/f shells, PBC and ECP/EDF
remain explicitly unsupported.


## QE-Multiwfn 0.2.0 (2026-11-14)

- Backward-compatible 0.1.1 ABI (17 symbols, version node
  `QE_MULTIWFN_0.1.1`).
- Additive v1 ABI (12 `qe_v1_*` symbols, version node `QE_MULTIWFN_0.2.0`).
- Molecular Data Model 1.0, ORCA adapter, spherical/Cartesian d/f,
  opt-in UHF/ROHF, strict validation and provenance.
- P0 RHF results remain bit-for-bit identical.
