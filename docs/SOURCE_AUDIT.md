# QE-Multiwfn 0.1.0 — Source Audit (Phase 1)

> **Documento histórico (0.1.0).** A auditoria de fontes foi posteriormente
> estendida; o estado atual e o fecho de dependências da Fase 6 estão em
> `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_STATUS.md` e
> `../../MDM_1.1_work/AUDIT_PHASE6_FINAL.md`.

**Date:** 2026-11-10  
**Source:** `Multiwfn_2026.11.3_src_Linux.zip` (extracted under `vendor/Multiwfn_2026.11.3_src_Linux/`)  
**Toolchain used for verification:** GNU Fortran 16.2.0 (conda-forge), CMake 4.4.5, Ninja, OpenBLAS 0.3.34

---

## 1. Inventory of the upstream source tree

| Path | Type | Purpose |
|------|------|---------|
| `Multiwfn.f90` | program | Interactive driver — **excluded** from QE-Multiwfn |
| `define.f90` | module | `deftype`, `defvar`, `topo`, `surfvertex`, `basinintmod`, `NAOmod`, `consolecolor` |
| `util.f90` | module | `util` — `matmul_blas`, `invmat`, `sort`, helpers |
| `function.f90` | module | `functions` — spatial function evaluation (depends on libreta, Bspline, 2F2) |
| `integral.f90` | module-less | Overlap & related integrals (`genSbas`, `genSbas_curr`, `ask_Sbas_PBC`) |
| `sub.f90` | module-less | Lifecycle helpers: `dealloall`, `dealloall_org`, `genP`, `genPprim`, `genfragatm`, `init_func`, `wfnsanity`, `bascen2basstart_end` |
| `fileIO.f90` | module-less | All native file readers (`readinfile`, `readfch`, `readwfn`, `readwfx`, `readmolden`, `readmwfn`) |
| `bondorder.f90` | module-less | `bondorder_main` (interactive), `calcMayerbndord`, `Mayerbndord`, `Mullikenbndord`, etc. |
| `population.f90` | module-less | Population analyses (`MPA`, `genHirshfeld`, `Hirshfeld_I`, etc.) |
| `GUI.f90` | module | `GUI` (depends on `plot`, `mouse_rotate_mod`) |
| `plot.f90` | module | `plot` (depends on `dislin`, `util`, `defvar`) |
| `dislin_d.f90` | module | `dislin` interface module (the .a lib not needed for symbols we use) |
| `noGUI/dislin_d_empty.f90` | module-less | 5249 dummy routines + `doesnotexist` reporter |
| `noGUI/mouse_rotate_empty.f90` | module | `mouse_rotate_mod` empty stub |
| `Bspline.f90` | module | `bspline_sub_module` |
| `sym.F` | module-less | SYVA symmetry analysis (fixed-form `.F`) |
| `DFTxclib.F` | module-less | DFT exchange-correlation functionals |
| `Lebedev-Laikov.F` | module-less | Angular grid |
| `Lebedev-Laikov.f90` | (none) | — |
| `ext/2F2.f90` | module | `mod_2F2` — fractional derivative / integral interface |
| `ext/2F2.c` + `2F2.h` | C | `hyp2F2` — requires flint/arb |
| `ext/no2F2.f90` | module | `mod_2F2` — fallback that calls C `hyp2F2` |
| `ext/no2F2.c` | C | `hyp2F2` stub that exits |
| `ext/frj.f90` | module-less | MBIS routine (`MBIS_frj`) |
| `ext/xlib.f90` | module-less | X11 hooks (only used by GUI build) |
| `libreta_hybrid/libreta.f90` | module | `libreta` — high-performance ERI backend |
| `libreta_hybrid/boysfunc.f90` | module | `boysfunc` (uses `boysfunc_data1.h`, `boysfunc_data2.h`) |
| `libreta_hybrid/ryspoly.f90` | module | `ryspoly` |
| `libreta_hybrid/hrr_012345.f90` | module | `hrr` (~1 MB) |
| `libreta_hybrid/blockhrr_012345.f90` | module | `blockhrr` (~3.5 MB) |
| `libreta_hybrid/eanvrr_012345.f90` | module | `eanvrr` (~920 KB) |
| `libreta_hybrid/ean.f90` | module | `ean` |
| `libreta_hybrid/naiveeri.f90` | module-less | `naive_eri` etc. |
| Other analysis files (`population.f90`, `topology.f90`, `basin.f90`, `fuzzy.f90`, `deloc_aromat.f90`, `orbcomp.f90`, `orbloc.f90`, `O1.f90`, `surfana.f90`, `procgriddata.f90`, `AdNDP.f90`, `CDA.f90`, `visweak.f90`, `EDA.f90`, `CDFT.f90`, `ETS_NOCV.f90`, `atmraddens.f90`, `NAONBO.f90`, `grid.f90`, `PBC.f90`, `hyper_polar.f90`, `cp2kmate.f90`, `minpack.f90`, `excittrans.f90`, `spectrum.f90`, `DOS.f90`, `0123dim.f90`, `LSB.f90`, `otherfunc.f90`, `otherfunc2.f90`, `otherfunc3.f90`, `edflib.f90`, `fparser.f90`) | module-less | Other analyses — included for symbol resolution of `bondorder_main`'s siblings |

**Total source files (Fortran + C):** 73 textual, ~250 857 lines, ~21 MB (before preprocessor expansion of `libreta_hybrid/*.h` headers).

---

## 2. Compilation feasibility with GNU Fortran

Verified empirically that **all** Multiwfn source files compile with `gfortran -fPIC -cpp -O1` after providing `dislin.mod` from `dislin_d.f90` (the interface module — the actual GUI library `dislin_d-11.0.a` is **not** linked because we use the noGUI empty stubs for symbol bodies).

### Required preprocessor flag

| Original option (Intel) | GNU equivalent | Notes |
|---|---|---|
| `-fpp` | `-cpp` | `define.f90`, `function.f90`, `dislin_d.f90`, `DFTxclib.F`, `sym.F` contain `#ifdef _WIN32` and similar |
| `-mkl` | `-lblas` (OpenBLAS) | Only `dgemm` is exercised by `calcMayerbndord`; OpenBLAS is sufficient |
| `-qopenmp` | `-fopenmp` | **Not enabled in v0.1.0** — first version is single-threaded |
| `-static-intel` | (none) | Incompatible with shared library; not used |
| `-stand f08` | `-std=f2008` | **Not enabled** — original code uses legacy features (`real*8`, `do/end` without integer expr, label-style `goto`) that fail strict F2008; we use `-std=legacy` instead |
| `-fpscomp logicals` | (none) | Intel-only; not needed |
| `-diag-disable ...` | (none) | Intel-only diagnostics |

### Compiler warnings observed (non-fatal)

- `Legacy Extension: Missing comma in FORMAT string` (`util.f90:2831`)
- `Deleted feature: End expression in DO loop must be integer` (`function.f90:4393`, `libreta_hybrid/libreta.f90:280`)
- `Legacy Extension: Label not in same block as GOTO` (`plot.f90:1368`)

All are accepted under `-std=legacy`.

### `2F2` fractional-derivative backend

`function.f90` uses `mod_2F2`, which expects a C function `hyp2F2` (provided by `ext/2F2.c` using flint/arb). Since flint is **not** installable in this sandbox, we provide a Fortran-side stub `hyp2F2` that writes a warning to stderr and returns a sentinel. The Mayer code path never reaches `hyp2F2` (it is only called from `fracderiv` / `orbfracderiv_eval`), so Mayer results are unaffected. **This is documented in `docs/LIMITATIONS.md`.**

---

## 3. Dependency graph relevant to `calcMayerbndord`

```
calcMayerbndord (bondorder.f90)
├── use defvar       (define.f90)
│   └── use deftype  (define.f90)
├── use util         (util.f90)
│   └── use defvar
└── calls:
    └── matmul_blas  (util.f90)
        └── dgemm    (BLAS — OpenBLAS in our build)
```

The **runtime** dependencies of `calcMayerbndord` itself are only `defvar` and `util` plus BLAS.

However, because the **whole `bondorder.f90` translation unit** is compiled as one object, the linker also pulls in `bondorder_main` (interactive menu), `Mayerbndord`, `Mullikenbndord`, `decompMullikenBO`, `OrbPertMayer`, `decompWibergNAO`, `IBSI`. Those routines call:

- `ask_sbas_pbc` (from `integral.f90`)
- `fuzzyana` (from `fuzzy.f90`)
- `multicenter`, `multicenternao` (from `deloc_aromat.f90`, `NAONBO.f90`)
- `cpxMayer`, `NAOinfo`, `genNAO` (from `NAONBO.f90`)
- `dealloall`, `dealloall_org`, `cmp_sumbondord` (from `sub.f90`)
- various `util` and `defvar` symbols

That cascade pulls in essentially every analysis module. **For v0.1.0 we therefore compile the entire scientific core (everything except `Multiwfn.f90` and the GUI-only `xlib.f90`) and link it into `libqe_multiwfn.so`.** This is the path-of-least-resistance approach explicitly allowed by the master spec (Strategy A in §6.3 of `Pasted Content`).

A future optimization (post-0.1.0) can extract `calcMayerbndord` into a small standalone file to slim the binary; that requires a per-line patch and is out of scope for now.

---

## 4. Global state used by `calcMayerbndord`

| Variable | Type | Source | Role |
|---|---|---|---|
| `ncenter` | `integer` (module `defvar`, `define.f90:264`) | scalar | Number of atoms |
| `nbasis` | `integer` (module `defvar`, `define.f90:300`) | scalar | Number of basis functions |
| `wfntype` | `integer` (module `defvar`, `define.f90:267`) | scalar | 0=RHF, 1=UHF, 2=ROHF, 3=R-post-HF, 4=U-post-HF |
| `basstart(:)` | `integer, allocatable` (`define.f90:307`) | array(`ncenter`) | First basis index per atom (0 ⇒ no basis on this atom) |
| `basend(:)` | `integer, allocatable` (`define.f90:307`) | array(`ncenter`) | Last basis index per atom |
| `Ptot(:,:)` | `real*8, allocatable` (`define.f90:324`) | matrix(`nbasis,nbasis`) | Total density matrix |
| `Palpha(:,:)` | `real*8, allocatable` | matrix(`nbasis,nbasis`) | α-spin density (only when `wfntype∈{1,2,4}`) |
| `Pbeta(:,:)` | `real*8, allocatable` | matrix(`nbasis,nbasis`) | β-spin density (only when `wfntype∈{1,2,4}`) |
| `Sbas(:,:)` | `real*8, allocatable` (`define.f90:310`) | matrix(`nbasis,nbasis`) | Overlap matrix |

**No other globals are read by `calcMayerbndord`.**

---

## 5. Required pre-conditions for calling `calcMayerbndord`

The QE-Multiwfn state builder must ensure, before invoking the routine:

1. `ncenter > 0`
2. `nbasis > 0`
3. `wfntype` is one of `{0,1,2,3,4}`
4. `a(:)` is allocated with size `ncenter` (referenced via `use defvar`)
5. `basstart` and `basend` are allocated with size `ncenter`, with `basstart(i) ∈ {0} ∪ [1,nbasis]`, `basend(i) ≥ basstart(i)` when `basstart(i) ≠ 0`, and `basend(i) = 0` when `basstart(i) = 0`
6. `Ptot` allocated and properly sized (`nbasis × nbasis`), with finite values
7. If `wfntype ∈ {1,2,4}`: `Palpha` and `Pbeta` allocated and sized
8. `Sbas` allocated and sized
9. `wfntype == 0` for v0.1.0 first integration (other `wfntype` values accepted by `calcMayerbndord` itself, but **state preparation paths** for UHF/ROHF/post-HF are not yet validated)

For v0.1.0, we **explicitly reject** `ifPBC ≠ 0` until Mayer-on-PBC is validated (see `docs/LIMITATIONS.md`).

---

## 6. Build-system strategy

### What we will NOT modify in upstream

- All `.f90` and `.F` source files are preserved byte-for-byte under `vendor/Multiwfn_2026.11.3_src_Linux/`.
- The original `Makefile` is left untouched.
- `patches/` is empty for v0.1.0.

### What we DO add

- `cmake/FortranSources.cmake` — explicit, ordered list of Multiwfn sources (excluding `Multiwfn.f90`, `noGUI/*` empty stubs are used in place of `dislin_d-11.0.a` + `mouse_rotate.f90` + `xlib.f90`).
- `cmake/CompilerOptions.cmake` — gfortran flags (`-cpp -fPIC -std=legacy -O2`).
- `cmake/DetectBLAS.cmake` — find BLAS via `find_package(BLAS)`, fall back to `-lblas`.
- A small Fortran stub `src/bridge/qe_hyp2f2_stub.f90` providing the `hyp2F2` C symbol (since flint/arb is not available).
- New `qe_*` modules under `src/{bridge,engine,state,analysis}/`.

### Excluded sources

| File | Reason |
|------|--------|
| `Multiwfn.f90` | Interactive `program` — replaced by our `qe_c_api.f90` |
| `mouse_rotate.f90` | GUI-only; replaced by `noGUI/mouse_rotate_empty.f90` |
| `xlib.f90` (in `ext/`) | GUI-only X11 hooks; not needed in shared library |
| `ext/2F2.c` | Requires flint/arb; replaced by Fortran stub `qe_hyp2f2_stub.f90` |

### Build products

- `libqe_multiwfn.so` — the shared library
- `qecompile_test` — a small Fortran test driver (built only in Debug) that calls `calcMayerbndord` directly to verify the upstream code is reachable

---

## 7. Empirical verification

We have already, in this Phase 1 audit:

1. ✅ Compiled every Multiwfn `.f90`/`.F` source with `gfortran -cpp -fPIC -O1 -std=legacy` (warnings only, no errors).
2. ✅ Linked a small test driver that calls `calcMayerbndord` against a 2-atom, 2-basis RHF system.
3. ✅ Verified the result matches the manual computation `BO_{AB} = (PS)_{AB}(PS)_{BA}` where `PS = P·S`.

Test input:

```
P = [1.0  0.5]    S = [1.0  0.5]
    [0.5  1.0]        [0.5  1.0]

PS = P·S = [1.25  1.00]
           [1.00  1.25]

BO_{1,2} = PS(1,2) · PS(2,1) = 1.00 · 1.00 = 1.00
```

Test output (program-produced):

```
PS = P*S matrix:
  1.2500  1.0000
  1.0000  1.2500
Mayer BO matrix:
   1.000000    1.000000
   1.000000    1.000000
```

**Conclusion:** the original Multiwfn Mayer routine executes correctly under our gfortran/OpenBLAS toolchain. The infrastructure for Phase 2 (CMake) is therefore ready.

---

## 8. Risks and follow-ups

| Risk | Mitigation |
|------|------------|
| `bondorder_main` and other interactive routines are linked into the `.so`, but never called from our C ABI | Acceptable; they just sit as dead code. Can be stripped in a future revision. |
| `ask_sbas_pbc` writes to `stdout` and reads from `stdin` if ever invoked | Our C ABI must **never** call `bondorder_main`, `Mayerbndord`, `Mullikenbndord`, `IBSI`, etc. — only `calcMayerbndord`. Documented in `qe_mayer.f90` and `docs/LIMITATIONS.md`. |
| `STOP` / `ERROR STOP` exist in some readers | Only reachable from `readinfile` and other interactive paths, never from `calcMayerbndord` directly. Our C ABI bypasses `readinfile`. |
| `2F2` / `hyp2F2` path is dead for Mayer but live in `function.f90`'s `fracderiv` | Provide a Fortran stub that returns a sentinel; document that fractional derivatives are unavailable in v0.1.0. |
| OpenMP not enabled | Documented as a v0.1.0 limitation. |

---

## 9. Phase 1 conclusion

Phase 1 is **complete**. We have:

- Mapped the upstream source tree (73 files, 250 857 LOC).
- Verified GNU Fortran compatibility for every needed source.
- Identified the exact globals and pre-conditions required by `calcMayerbndord`.
- Demonstrated end-to-end that the original routine produces correct numerical results under our toolchain.
- Defined the CMake strategy (Phase 2) without modifying any upstream file.

Phase 2 can now begin: building `libqe_multiwfn.so` via CMake.
