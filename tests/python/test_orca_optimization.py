"""ORCA optimization geometry + SP wavefunction integration."""
from pathlib import Path
import numpy as np
import pytest
import qe_multiwfn as qe
from qe_multiwfn.adapters.orca import (
    OrcaAdapterError, from_orca_directory, from_orca_optimization,
)
from qe_multiwfn.normalization import normalization_report

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
if not _ORCA.exists():
    pytest.skip("fixtures unavailable", allow_module_level=True)


@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_opt_geometry_matches_sp_and_mayer(mol):
    sp = from_orca_directory(_ORCA / mol)
    opt = from_orca_optimization(_ORCA / mol)
    assert opt.geometry.unit_source == "angstrom"
    assert np.max(np.abs(opt.geometry.coordinates - sp.geometry.coordinates)) < 1e-6
    assert normalization_report(opt)["status"] == "PASS"
    with qe.Engine() as eng:
        eng.load_molecule_v1(opt)
        eng.prepare()
        B = eng.calculate_mayer().total
    with qe.Engine() as eng:
        eng.load_molecule_v1(sp)
        eng.prepare()
        Bsp = eng.calculate_mayer().total
    np.testing.assert_array_equal(B, Bsp)


def test_opt_geometry_mismatch_fails_closed(tmp_path):
    src = _ORCA / "h2"
    for fn in ("sp.json", "sp.inp", "sp.out", "sp.molden.input", "sp.property.txt",
               "sp.gbw", "sp.json.conf"):
        if (src / fn).exists():
            (tmp_path / fn).write_bytes((src / fn).read_bytes())
    (tmp_path / "opt.xyz").write_text(
        "2\nmismatch\nH 0 0 0\nH 0 0 5.0\n"
    )
    with pytest.raises(OrcaAdapterError, match="differs"):
        from_orca_optimization(tmp_path)
