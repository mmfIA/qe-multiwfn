# PySCF adapter

**Module:** `qe_multiwfn.adapters.pyscf`
**Function:** `from_pyscf(mol, mf, *, include_overlap=True, schema_version=None)`
**Tested version:** PySCF 2.15.0
**Status:** RHF/UHF/ROHF in-memory conversion PASS; DFT/post-HF rejected.

## 1. API

```python
from pyscf import gto, scf
from qe_multiwfn.adapters.pyscf import from_pyscf
import qe_multiwfn as qe

mol = gto.M(atom="O 0 0 0; O 0 0 1.2", basis="sto-3g",
            charge=0, spin=2, verbose=0)
mf = scf.ROHF(mol).run()
mdm = from_pyscf(mol, mf)

with qe.Engine() as engine:
    result = engine.calculate_mayer(mdm)
```

No file is written or read. `from_pyscf` builds `BasisInput`/`ShellInput`
records and calls the same `MolecularDataBuilder` used by other sources.

## 2. Supported objects and methods

| PySCF object | Status | Notes |
|---|---|---|
| `scf.hf.RHF` | PASS | one spatial MO set, doubly occupied |
| `scf.uhf.UHF` | PASS | alpha/beta arrays preserved |
| `scf.rohf.ROHF` | PASS | one spatial set with 2/1/0 occupations |
| DFT (`pyscf.dft.*KS`) | BLOCKED | rejected before conversion |
| Post-HF / non-SCF object | BLOCKED | rejected |
| Non-converged SCF | BLOCKED | explicit error |

The adapter does not infer the method from matrix shape; it checks the PySCF
class and the `mo_coeff`/`mo_occ` structure.

## 3. Data extracted

- `mol.atom_charges()` and `mol.atom_coords(unit="Bohr")`;
- `mol.charge`, `mol.spin` → multiplicity, `mol.nelectron`;
- `mol._basis` shell/contraction rows, translated to `ShellInput`;
- `mol.cart` → Cartesian/spherical representation;
- `mf.mo_coeff`, `mf.mo_occ`, `mf.mo_energy`;
- `mol.intor("int1e_ovlp")` when `include_overlap=True`;
- `pyscf.__version__` and source metadata in provenance.

The builder derives `P_total`, `P_alpha` and `P_beta` from the method-specific
coefficients and occupations; no density formula is duplicated in the
adapter.

## 4. AO ordering and angular conventions

PySCF's AO order is converted to a deterministic MDM order before the
builder:

| l | PySCF source order | MDM order |
|---|---|---|
| s | `s` | `s` |
| p | `px,py,pz` | `pz,px,py` |
| d spherical | `dxy,dyz,dz^2,dxz,dx2-y2` | `dz2,dxz,dyz,dx2-y2,dxy` |
| f spherical | `f-3,f-2,f-1,f+0,f+1,f+2,f+3` | `f0,f+1,f-1,f+2,f-2,f+3,f-3` |
| d Cartesian | `xx,xy,xz,yy,yz,zz` | same source order |

`S` and `C` are permuted by the same AO permutation. The spherical d/f
mapping was checked against the ORCA canonical H₂S/def2-TZVP overlap: the f
block agrees to about `4e-16` after mapping, so no extra phase is introduced.
Spherical f is expressed as canonical MDM 1.2; d-only and s/p models remain
1.1.

`mol.cart=True` (Cartesian d) is accepted for the direct S/P path. Cartesian
f and g/h are rejected. The current backend does not validate full-state
Cartesian d normalization; use `include_overlap=True` for that case.

## 5. Full state versus direct path

- `include_overlap=True` (default): S is attached and P is derived by the
  builder. The Engine uses the direct S/P path.
- `include_overlap=False`: S/P are omitted; the Engine uses
  `prepare_from_orbitals=True` and the original `genSbas_curr`/`genP` path.
  This is supported for source-normalized spherical s/p/d/f, including
  H₂S/def2-TZVP spherical f (canonical MDM 1.2), and UHF/ROHF.
  PySCF contraction coefficients are normalized to unit primitive-contraction
  overlap before the full-state build; the source molecular orbitals are kept
  in the same physical basis.
- Cartesian-d full state without S remains blocked: per-component Cartesian
  normalization is not represented safely by the current shell contract.

## 6. Validation and errors

- Rejects non-converged SCF, DFT, post-HF, ECP, g/h, Cartesian f.
- Validates `S` symmetry/finiteness and coefficient dimensions.
- Feeds the builder's strict source-matrix validation for the direct path.
- Does not invent missing basis or orbital data.
- `PyscfAdapterError` is raised for unsupported or inconsistent input.

## 7. Tested methods and bases

| Case | Method | Basis | Result |
|---|---|---|---|
| H₂ | RHF | STO-3G | PASS |
| H₂O | RHF | STO-3G | PASS |
| O₂ | UHF | STO-3G | PASS |
| O₂ | ROHF | STO-3G | PASS |
| H₂O | RHF | 6-31G* spherical d | PASS |
| H₂O | RHF | 6-31G* Cartesian d | PASS (direct path) |
| H₂S | RHF | def2-TZVP spherical f | PASS (direct and full; 1.2) |

See `SOURCE_EQUIVALENCE.md` for numerical comparisons.

## 8. Limitations

- Spherical f full-state (`include_overlap=False`) is blocked; direct path is
  validated.
- Cartesian d full-state normalization is not inferred without S.
- g/h, Cartesian f, PBC, post-HF and ECP are blocked.
- PySCF versions other than 2.15.0 have not been validated.
- The adapter assumes the standard PySCF AO order described above; a custom
  PySCF basis with a different layout must be mapped explicitly.
- DFT is deliberately rejected even though its objects inherit from SCF
  classes; its density/method semantics are not the validated RHF/UHF/ROHF
  contract.
