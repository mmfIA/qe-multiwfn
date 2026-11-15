"""ASE geometry adapter and ORCA geometry equivalence."""
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn.adapters.ase import from_ase_atoms
from qe_multiwfn.adapters.orca import from_orca_directory
from qe_multiwfn.normalization import normalization_report

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
if not _ORCA.exists():
    pytest.skip("fixtures unavailable", allow_module_level=True)

try:
    from ase.io import read as ase_read
except Exception:
    ase_read = None


@pytest.mark.skipif(ase_read is None, reason="ASE not installed")
@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_ase_geometry_matches_orca(mol):
    atoms = ase_read(str(_ORCA / mol / "opt.xyz"))
    model = from_ase_atoms(atoms)
    ref = from_orca_directory(_ORCA / mol)
    assert model.atoms.z.tolist() == ref.atoms.z.tolist()
    assert np.max(np.abs(model.geometry.coordinates - ref.geometry.coordinates)) < 1e-6
    assert model.readiness.geometry_ready is True
    assert model.readiness.basis_ready is False
    assert model.readiness.analysis_ready["mayer"] is False
    assert normalization_report(model)["status"] == "INCOMPLETE"


def test_ase_geometry_only_cannot_run_mayer():
    from qe_multiwfn.adapters.ase import from_ase_atoms
    from ase.build import molecule
    model = from_ase_atoms(molecule("H2O"))
    with pytest.raises(qe.QeError):
        with qe.Engine() as eng:
            eng.load_molecule_v1(model)
