# ASE adapter

**Module:** `qe_multiwfn.adapters.ase`
**Functions:** `from_ase_atoms(atoms, ...)`, `from_ase(...)`
**Status:** structural/geometry integration PASS; PBC fail-closed.

## 1. Purpose

ASE is treated as a structural source. It provides atoms, positions and
periodic metadata; it does not provide basis functions, MO coefficients,
overlap or density by itself. The adapter therefore returns a geometry-capable
`MolecularSystemV1` with an incomplete electronic state, not a Mayer-ready
model.

## 2. API

```python
from ase.build import molecule
from qe_multiwfn.adapters.ase import from_ase

atoms = molecule("H2O")
mdm = from_ase(atoms)
assert mdm.readiness.geometry_ready
assert not mdm.readiness.analysis_ready["mayer"]
```

`from_ase` is an alias of `from_ase_atoms`; both use the same structural path.

## 3. Extracted data

- atomic numbers/symbols;
- Cartesian positions, converted from Angstrom to Bohr;
- charge parameter;
- multiplicity parameter or electron-count default;
- source name/version and coordinate conversion provenance;
- structural PBC metadata is inspected, never silently discarded.

The model has an empty AO map and no orbitals/S/P, so it is not ready for
Mayer. `normalization_report` returns `INCOMPLETE`.

## 4. PBC

If any ASE `pbc` direction is true, the adapter raises `AseAdapterError`.
The QE-Multiwfn Mayer backend has no validated PBC path, so periodic ASE
structures must be converted/reduced to a non-periodic model explicitly by the
caller. Cell information is not silently ignored.

## 5. Composition with PySCF

ASE can supply geometry to a PySCF molecule; PySCF then supplies the
electronic state:

```python
from ase.build import molecule
from pyscf import gto, scf
from qe_multiwfn.adapters.pyscf import from_pyscf

atoms = molecule("H2O")
symbols = atoms.get_chemical_symbols()
coords = atoms.get_positions()
atom = "; ".join(
    f"{s} {x:.12f} {y:.12f} {z:.12f}"
    for s, (x, y, z) in zip(symbols, coords)
)
mol = gto.M(atom=atom, basis="sto-3g", unit="Angstrom", verbose=0)
mf = scf.RHF(mol).run()
mdm = from_pyscf(mol, mf)
```

ASE remains independent of PySCF; this composition is optional. The geometry
must be kept consistent between both objects; the adapter does not silently
copy one source into another.

## 6. Validation and limitations

- Isolated geometry: PASS.
- PBC: FAIL-CLOSED.
- No basis/orbitals/electronic density from ASE alone.
- No Mayer readiness claim.
- No hidden unit conversion; Angstrom is converted explicitly to Bohr.
- No database or PySCF dependency in the ASE adapter.
