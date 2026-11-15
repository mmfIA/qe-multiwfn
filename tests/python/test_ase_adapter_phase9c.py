"""Phase 9C — ASE structural integration and PBC fail-closed tests."""
import numpy as np
import pytest

pytest.importorskip("ase")
from ase import Atoms

import qe_multiwfn as qe
from qe_multiwfn.adapters.ase import AseAdapterError, from_ase, from_ase_atoms


def test_ase_structural_alias_and_geometry_only():
    atoms = Atoms("H2O", positions=[[0, 0, 0], [0, 0, 1], [0, 1, 0]],
                  cell=[10, 10, 10], pbc=False)
    a = from_ase(atoms)
    b = from_ase_atoms(atoms)
    assert a.atoms.z.tolist() == b.atoms.z.tolist()
    np.testing.assert_allclose(a.geometry.coordinates, b.geometry.coordinates)
    assert a.readiness.geometry_ready is True
    assert a.readiness.analysis_ready["mayer"] is False
    with pytest.raises(qe.QeError):
        with qe.Engine() as eng:
            eng.calculate_mayer(a)


def test_ase_periodic_fails_closed():
    atoms = Atoms("H", positions=[[0, 0, 0]], cell=[5, 5, 5],
                  pbc=[True, False, False])
    with pytest.raises(AseAdapterError, match="periodic"):
        from_ase_atoms(atoms)
