# Documentation reconciliation report — QE-Multiwfn 0.3.0-dev

**Date:** 2026-11-14  
**Tree:** `/home/fsia/Quimica/qe_multiwfn_030_dev`  
**Scope:** documentation and public comments only.  
**No scientific functionality, executable code, ABI signature, test, reference result, vendor file or frozen artifact was changed.**

## 1. Summary

The documentation was reconciled with the actual 0.3.0-dev state: MDM 1.1, Phase 6, RHF/UHF/ROHF, original genP/genPprim/genSbas/genSbas_curr, 31 legacy + 14 additive ABI symbols, and the known f/g/h and cclib blockers. Historical documents received explicit scope banners so their older counts are not read as current.

## 2. Files modified

| File | SHA-256 before | SHA-256 after |
|---|---|---|
| `README.md` | `eac3a52e2942c28d3af3560c04cf1182a5d9597f7391818760b1b2ce50ed9da8` | `da1b1e2ab72de3846f5f286722e59d023019dec9d9ae2b61b42f268739824f62` |
| `CMakeLists.txt` | `1f727ff0102d074b98975bc6d0f02d7f1bd3af6d3ccadb72cf75060834885b7a` | `b92d435038eaddaffead9bd12eef46662ede252139e8cc76d6c09314a6b7de8f` |
| `include/qe_multiwfn_v1.h` | `3719c153115e0ab1133b8a975abb8cc18e51669adc73f5b21fb66516bdcb73c7` | `b92664989c7ace095cf33d13d1669fa76c6b294875ce963cd819046ac5c2f036` |
| `docs/ARCHITECTURE.md` | `2538c82a14da615c31e45d50215b91eed12cc08ed331ba245da8d90ea370bccd` | `4991b6cbbcb2409235b48b5f40878991163072d46d6d74e85115d9d46ae2fb90` |
| `docs/IMPLEMENTATION_STATUS.md` | `7f33150a6275324214c7f1bd8b4fed924054c30c9878d003bcafa8abf741f0ba` | `f988f0cdec088829228dc42c3c829daa224edfe4cd15f51dce124ec4f9c2e1ea` |
| `docs/LIMITATIONS.md` | `da3ee6b44ceb021174e7de273b7ec9f716756413064c75e8a5e92811e87074f8` | `6750146420092494c636df05c42170cf483ab2600ccf6c59abb9de75247198ed` |
| `docs/M1_IMPLEMENTATION_REPORT.md` | `a70aadfbecd26e99a1540847c6370ace8a7cc846c08e6090a426a1c7af42907c` | `68b14d4a98e896644ad1302a00301944d5f7d6b9d9f47bda5416f63899d644be` |
| `docs/MOLECULAR_DATA_MODEL_1.0.md` | `951ba5a9da5999368eb82abe320340109a4f7399fd8022dd5906c7f0c2a2b2ff` | `e87c3e89f484c2b174fee4dc0884bc9ace1ccf80be159424cdb3f499c2dd833d` |
| `docs/MOLECULAR_DATA_MODEL_1.1.md` | `7f53c1a9cb3a0163a909ad23f3576bae95e3f6eae94c5a0d0cd7dc9867e928b2` | `7d6fbb15e6e118cdb5a42e7ae1a6cd75cda86a05cef882fb4a06a084e81fcddb` |
| `docs/RELEASE_NOTES_0.1.1.md` | `22021d37ba7660169620fe7e6165e067bf5671b7fa1e1c8d891631890cb61ab5` | `3448e1752c74a6758499cc25f1cada1c87f19b083d9796cd1b97d7de96c31d5d` |
| `docs/BUILD_VERIFICATION_0.1.1.md` | `bb2e5214f4adcd00ded9939758466a7375696c2bfce5cb323880a33a090e8d00` | `5fcf4162d899f039d9fa5c85616cd7993c73c5416a791f8668524ecdaa276585` |
| `docs/FINAL_REPORT_0.1.0.md` | `846d94632541c17ec82476b2413c4d0aecec0af3572f3a8bf84bc817651c56e4` | `44a826f83c68e587efad4f581be211f05bdb26405366bc83fcef3053a7c1634b` |
| `docs/SOURCE_AUDIT.md` | `a218cddb0a5b4e543159ab7f3c6bbc8ead4b23a211f8f997dbe665678f3f5a74` | `88e26598cedd9cd53fc7a064aa4ecfccd2212e9527ce56e46470aba1078367d4` |
| `docs/EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md` | `bca455b3b184c967e8256293522a621ff4e581ed308926a3440395d5f52a6229` | `8d3711df120d3c0d0d57500f9f71203b0db3fb703fff2579d4ef27ebbad94314` |
| `checkpoints/PHASE5_GENP_AUDIT.md` | `f7589d61432533eb87d62bc6e6004d168a832d2b81928ff9b8d89e863df6e384` | `5c25d64e638d1b03218470c9619b8edd0abceed970b50dd4685583bb58e07a3e` |

The new report itself is `DOCUMENTATION_RECONCILIATION_REPORT.md` and is not included in the table above.

### What changed

- `README.md`: rewritten current status, two execution paths, ABI counts, implemented routines, adapters, scientific results, build/test commands, limitations and documentation map.
- `docs/IMPLEMENTATION_STATUS.md`: current 0.3.0-dev status and test/ABI counts; historical snapshots separated.
- `docs/LIMITATIONS.md`: current scope; f/g/h, F±3, cclib, PBC, post-HF, ECP/EDF, thread safety, package and `nmo=nbasis` limitations.
- `docs/ARCHITECTURE.md`: current MDM/Phase 6 layers, new modules/adapters, ABI and cache boundaries.
- `include/qe_multiwfn_v1.h`: comments only; ROHF is no longer described as rejected, orbitals are documented as used by Phase 6 genP/genPprim, current ABI counts and direct/full-state paths clarified. No declaration, macro or constant changed.
- `CMakeLists.txt`: comments only. The native `VERSION 0.2.0` and all functional CMake content remain unchanged.
- `docs/M1_IMPLEMENTATION_REPORT.md`, `docs/MOLECULAR_DATA_MODEL_1.0.md`, `docs/RELEASE_NOTES_0.1.1.md`, `docs/BUILD_VERIFICATION_0.1.1.md`, `docs/FINAL_REPORT_0.1.0.md`, `docs/SOURCE_AUDIT.md`, `docs/EXTENSION_PLAN_UHF_ROHF_AND_ANALYSES.md`: historical/scope banners; no technical results rewritten.
- `docs/MOLECULAR_DATA_MODEL_1.1.md`: ABI count corrected to 31 legacy + 14 additive; Phase 6 s/p/d test note added.
- `checkpoints/PHASE5_GENP_AUDIT.md`: historical banner; Phase 6 integration now supersedes the old “no integration yet” wording.

## 3. Integrity before/after

| Item | Result |
|---|---|
| Dev library SHA-256 | `8885ae9e94671956bde79e217dddcda1d8c554465a8daab2316f53cb7662da38` (unchanged) |
| Frozen 0.2.0 SHA-256 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` (unchanged) |
| Frozen packages | `sha256sum -c SHA256SUMS.txt` OK for fullsource and library |
| Vendor | `diff -qr` against frozen vendor empty |
| ABI symbols | 31 legacy / 45 total / 14 additive; missing legacy = 0 |
| `ldd -r` | no undefined symbols |
| RUNPATH | `$ORIGIN` |
| Canonical validation | `comparisons/validation_results.json = 6fb8b315…`; H₂/H₂O/C₆H₆ Mayer bit-identical |
| Derived manifest | `6aff745e…` (unchanged) |

A full-tree manifest comparison (excluding `build/`, `build_audit/`, `.pytest_cache` and `__pycache__`) shows the 15 documentation/comment files above changed, plus this new report file. No `.f90`, `.py`, `.c`, `.so`, test, reference-result, `vendor/` or frozen file changed. The CMake and header diffs contain comment lines only; no declaration, macro, constant or functional CMake statement changed.

## 4. Validation

Commands executed after the edits:

```bash
PYTHONPATH="$PWD/python" python3 -m pytest tests/python -q
(cd build && ctest --output-on-failure)
sha256sum python/libqe_multiwfn.so
nm -D --defined-only python/libqe_multiwfn.so
ldd -r python/libqe_multiwfn.so
```

- Python: **155 passed, 1 warning** (log `/tmp/qe_doc_recon_pytest.log`).
- CTest: **6/6 passed** (log `/tmp/qe_doc_recon_ctest.log`).
- Library hash unchanged: `8885ae9e94671956bde79e217dddcda1d8c554465a8daab2316f53cb7662da38`.
- ABI: 31 legacy + 14 additive = 45; no legacy removed.
- Scientific references unchanged (canonical artifact hashes and bit-identical Mayer baselines).
- The library was **not** rebuilt or replaced during this documentation task. The existing clean-build artifact (`build_audit`) already has the same hash.

## 5. Deferred items (code, deliberately untouched)

- `python/qe_multiwfn/engine.py` has a duplicated `_prepare_from_orbitals = False` assignment; it is executable Python and was not changed under this documentation-only task.
- Historical source comments such as `qe_molecular_state.f90` (“not used by Mayer 0.1.x”) were not edited because Fortran source is out of scope for this task.
- `CMakeLists.txt` keeps `project VERSION 0.2.0` intentionally: it is the native ABI/SONAME version, while the Python package is `0.3.0.dev0`.
- f/g/h original-routine support, cclib ORCA 6.1.1 parsing, PBC, post-HF and ECP/EDF remain blocked/unimplemented; no functionality was claimed as complete.

## 6. Closure declaration

Documentation reconciliation is complete. No functional change was made. No F±3, cclib, PBC, post-HF, ECP/EDF or packaging work was started. The next phase should be planned separately.
