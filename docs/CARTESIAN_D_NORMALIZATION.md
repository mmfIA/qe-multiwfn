# Cartesian-d full-state normalization — Phase 11

**Case:** H₂O/6-31G* PySCF, `mol.cart=True`.
**Direct path:** PASS.
**Full path (`include_overlap=False`):** BLOCKED; explicit
`PyscfAdapterError`.

## 1. What was already correct

The PySCF adapter:

- extracts Cartesian d shells in PySCF order
  `xx,xy,xz,yy,yz,zz`;
- applies the same AO permutation to S and C;
- validates the direct path C/S/P;
- produces Mayer results consistent with the ORCA/PySCF Cartesian-d fixture
  (`9.43e-7` maximum difference).

A direct MDM built from PySCF S/P produces generated overlap and density that
match the supplied PySCF matrices to `7.77e-16` and `0.0` respectively.

## 2. What fails

The native `qe_v1_build_electronic_state` full path for PySCF Cartesian d
fails its trace check:

```text
Tr(P*S)=9.9653832279 Ne=10
```

The same package/geometry/basis through the direct path has
`Tr(P*S)=10.000000000000002` and correct S/P.

The failure is therefore in the native full-state construction/association
for Cartesian d, not in the PySCF overlap, AO ordering, or raw s/p/d
contraction normalization that Phase 10 fixed.

## 3. Missing information

The current MDM shell contract represents one contraction per shell and the
native full-state path associates C, shell component ordering and P through
its own globals. For Cartesian d, per-component normalization/coupling cannot
be validated from the available PySCF shell metadata alone without relying on
the S matrix or changing native behavior.

No factor is guessed:

- no component-specific normalization factor is invented;
- no matrix is symmetrized to hide the trace error;
- no source matrix is discarded;
- the validation threshold is not relaxed.

## 4. Decision

Keep `include_overlap=False` blocked for PySCF Cartesian d:

```python
from_pyscf(mol, mf, include_overlap=False)
# PyscfAdapterError: PySCF Cartesian-d full state requires include_overlap=True
```

Use the direct path for Cartesian d:

```python
mdm = from_pyscf(mol, mf)  # include_overlap=True
```

## 5. Future requirements

Liberation requires either:

1. a native full-state Cartesian-d validation/association fix in an authorized
   native phase, or
2. an independently derived per-component normalization/association contract
   with a scientific validation against an independent reference.

It cannot be released by a tolerance change or by inferring a factor from the
same S matrix that the full path is supposed to reconstruct.
