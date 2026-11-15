"""Installed-package smoke test; run outside the source tree."""
import numpy as np
import qe_multiwfn as qe
from qe_multiwfn import BasisInput, build_molecular_system
from qe_multiwfn.model_v1 import AOFunction


def main():
    assert qe.__version__ == "0.3.0"
    assert qe.NATIVE_LIBRARY_VERSION == "0.2.0"
    S = np.array([[1.0, 0.5], [0.5, 1.0]])
    P = np.full((2, 2), 2.0 / 3.0)
    aos = [
        AOFunction(index=1, center=1, l=0, component="s",
                   angular_type=0, multiwfn_type=1),
        AOFunction(index=2, center=2, l=0, component="s",
                   angular_type=0, multiwfn_type=1),
    ]
    mdm = build_molecular_system(
        atomic_numbers=[1, 1],
        coordinates=[[0, 0, 0], [0, 0, 1.4]],
        coordinate_unit="bohr", wfntype="RHF", multiplicity=1,
        basis=BasisInput(aos=aos, nbasis=2, nprims=2,
                         normalization_convention="source_normalized"),
        overlap=S, density_total=P,
    )
    with qe.Engine() as engine:
        result = engine.calculate_mayer(mdm)
    assert result.total.shape == (2, 2)
    assert mdm.readiness.analysis_ready["mayer"] is True
    print("PASS", qe.__version__, qe.NATIVE_LIBRARY_PATH)


if __name__ == "__main__":
    main()
