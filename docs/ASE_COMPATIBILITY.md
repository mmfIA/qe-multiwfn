# ASE compatibility — Phase 10

**Tested version:** ASE 3.29.0
**Status:** structural adapter PASS; PBC fail-closed.

## 1. Supported API

```python
from ase.build import molecule
from qe_multiwfn.adapters.ase import from_ase, from_ase_atoms

atoms = molecule("H2O")
mdm = from_ase(atoms)
```

Both names call the same structural conversion.

## 2. Extracted fields

- `get_atomic_numbers()`;
- `get_positions()` in Angstrom;
- charge/multiplicity parameters;
- `pbc` flags;
- source name/version metadata.

Internal coordinates are Bohr. No basis, orbitals, density or overlap is
fabricated.

## 3. PBC

Any true `pbc` direction raises `AseAdapterError`. The native Mayer backend
has no validated PBC path. Cell vectors and periodic flags are not silently
discarded.

## 4. Composition

ASE may supply geometry to a PySCF `Molecule`; PySCF supplies the electronic
state:

```python
from ase.build import molecule
from pyscf import gto, scf
from qe_multiwfn.adapters.pyscf import from_pyscf

atoms = molecule("H2O")
atom = "; ".join(
    f"{s} {x:.12f} {y:.12f} {z:.12f}"
    for s, (x, y, z) in zip(atoms.get_chemical_symbols(),
                           atoms.get_positions())
)
mol = gto.M(atom=atom, basis="sto-3g", unit="Angstrom", verbose=0)
mf = scf.RHF(mol).run()
mdm = from_pyscf(mol, mf)
```

ASE does not depend on PySCF and remains optional.

## 5. Version policy

| ASE version | Status |
|---|---|
| 3.29.0 | tested PASS |
| other versions | not tested; no claim |

Only the public `Atoms` methods above are used. Importing ASE is not required
for `import qe_multiwfn` or for the NumPy/builder/Engine path.

## 6. Limitations

- structural only;
- no electronic information;
- no PBC execution;
- no Mayer readiness by itself;
- positions are explicitly converted from Angstrom to Bohr.
