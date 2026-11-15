# Release process — QE-Multiwfn 0.3.0

## 1. Version

- package version: `0.3.0`;
- native ABI: `0.2.0`;
- package version is independent of ABI.

A packaging-only fix may become `0.3.1` only after a fresh build, isolated
install and full scientific regression. Existing 0.3.0 artifacts are not
overwritten silently.

## 2. Required checks

1. Confirm native library hash and frozen/vendor integrity.
2. Run full Python suite.
3. Run CTest.
4. Build wheel and sdist.
5. Run `twine check`.
6. Install wheel in clean venv.
7. Install sdist in clean venv.
8. Run installed smoke test from outside the repository.
9. Verify optional-dependency errors and one full-extra profile.
10. Record artifact hashes.

## 3. Publication policy

- No automatic PyPI publication.
- No credentials or tokens are stored in the repository.
- No release is published without explicit authorization.
- GitHub Actions packaging is configured, not a publication workflow.
- Rollback means retaining the previous wheel/sdist and their hashes; the
  frozen/native references must never be rolled back by overwriting.

## 4. Reproducibility

The current sdist/wheel are not claimed bit-for-bit reproducible. Any future
reproducible-build claim must be demonstrated by two independent builds and
recorded hashes.

## 5. Phase 12 reproducibility observation

Two builds with `SOURCE_DATE_EPOCH=1700000000` produced the same wheel hash:

```text
397f9c221959b804939bd84748e716e1ac6ef1bd20d2d3e5bc1c49321ea97666
```

The sdist hashes differed between the two builds, so sdist bit-for-bit
reproducibility is **not** claimed. The final wheel and sdist hashes are in
`MDM_1.1_work/PHASE12/phase12_artifact_hashes.txt`.
