"""
qe_multiwfn.adapters.ase — ASE Atoms → geometry-only MolecularSystemV1.

ASE is a geometry/structure library; it does not provide wavefunction
coefficients or basis integrals by itself. This adapter therefore produces a
canonical geometry-only model and marks it as not ready for Mayer. It is
useful for structure ingestion, databases and pre-processing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from ..molecular import ANGSTROM_TO_BOHR
from ..model_v1 import (
    Atoms,
    BasisSet,
    ElectronicState,
    Geometry,
    MatrixBundle,
    MolecularSystemV1,
    Periodicity,
    Provenance,
    FileRecord,
)


class AseAdapterError(ValueError):
    pass


def from_ase_atoms(atoms, *, charge: int = 0, multiplicity: Optional[int] = None,
                   source_name: str = "") -> MolecularSystemV1:
    """Build a geometry-only canonical model from an ``ase.Atoms`` object."""
    try:
        from ase import Atoms as AseAtoms  # noqa: F401
        import ase
    except Exception as exc:  # pragma: no cover
        raise AseAdapterError("ASE is not available; install with: pip install 'qe-multiwfn[ase]'") from exc
    if not hasattr(atoms, "get_atomic_numbers"):
        raise AseAdapterError("expected an ase.Atoms-like object")
    z = np.asarray(atoms.get_atomic_numbers(), dtype=np.int32)
    if z.ndim != 1 or z.size == 0:
        raise AseAdapterError("ASE atoms array is empty")
    coords_ang = np.asarray(atoms.get_positions(), dtype=np.float64)
    if coords_ang.shape != (z.size, 3):
        raise AseAdapterError("ASE positions have an unexpected shape")
    pbc = getattr(atoms, "pbc", None)
    if pbc is not None and np.any(np.asarray(pbc, dtype=bool)):
        raise AseAdapterError("periodic ASE systems are not supported by the current backend")
    nelectron = int(z.sum()) - int(charge)
    if nelectron <= 0:
        raise AseAdapterError("non-positive electron count")
    if multiplicity is None:
        multiplicity = 1 if nelectron % 2 == 0 else 2
    wfntype = 0 if multiplicity == 1 else 1
    if wfntype == 0 and nelectron % 2:
        raise AseAdapterError("closed-shell RHF requires an even electron count")
    na = (nelectron + multiplicity - 1) // 2
    nb = nelectron - na
    atoms_model = Atoms(z=z)
    geometry = Geometry.from_source(coords_ang, "angstrom")
    electronic = ElectronicState(
        wfntype=wfntype, charge=int(charge), multiplicity=int(multiplicity),
        nelectron=nelectron,
        naelectron=na if wfntype != 0 else None,
        nbelectron=nb if wfntype != 0 else None,
    )
    # Geometry-only placeholder basis: no AOs, no matrices.
    basis = BasisSet(nbasis=1, nprims=1, representation="unspecified",
                     normalization_convention="unknown", aos=[])
    prov = Provenance(
        source_program="ASE",
        source_version=getattr(ase, "__version__", "unknown"),
        source_format="ase_atoms",
        coordinate_unit_source="angstrom",
        conversion_factor=ANGSTROM_TO_BOHR,
        adapter_name="qe_multiwfn.adapters.ase",
        adapter_version="1.1.0",
        normalization_steps=["ASE Atoms -> canonical geometry (Angstrom -> Bohr)"],
        hashes={"coordinates": __import__("hashlib").sha256(
            np.ascontiguousarray(geometry.coordinates).tobytes()).hexdigest()},
    )
    if source_name:
        prov.warnings.append(f"source_name={source_name}")
    model = MolecularSystemV1(
        provenance=prov, atoms=atoms_model, geometry=geometry,
        electronic=electronic, basis=basis, matrices=MatrixBundle(),
        periodicity=Periodicity(),
    )
    model.validate(strict=False)
    return model


from_ase = from_ase_atoms

__all__ = ["AseAdapterError", "from_ase_atoms", "from_ase"]
