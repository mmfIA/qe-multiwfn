"""Phase 9B — public MDM builder tests."""
from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn import model_v1 as m1
from qe_multiwfn.builder import (
    BasisInput, MolecularDataBuilder, ShellInput, build_molecular_system,
    from_numpy,
)
from qe_multiwfn.adapters.orca import (
    from_orca_directory, from_orca_rohf_directory, from_orca_uhf_directory,
)

_HERE = Path(__file__).resolve()
_VAL = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VAL / "orca"
requires_orca = pytest.mark.skipif(
    not _ORCA.exists(), reason="scientific fixtures unavailable"
)


def _minimal_rhf():
    S = np.array([[1.0, 0.5], [0.5, 1.0]])
    P = np.full((2, 2), 2.0 / 3.0)
    aos = [
        m1.AOFunction(index=1, center=1, l=0, component="s", multiwfn_type=1,
                      angular_type=0, cartesian=True),
        m1.AOFunction(index=2, center=2, l=0, component="s", multiwfn_type=1,
                      angular_type=0, cartesian=True),
    ]
    return S, P, aos


def _basis_input_from_model(model, *, keep_angular=True):
    shells = []
    for sh in model.basis.shells:
        names = [a.component for a in model.basis.aos if a.shell_index == sh.index]
        shells.append(ShellInput(
            center=sh.center, l=sh.l, exponents=sh.exponents,
            coefficients=sh.coefficients,
            representation="spherical" if sh.spherical else "cartesian",
            component_order=names, source_label=sh.source_label,
            angular=sh.angular if keep_angular else None,
        ))
    return BasisInput(
        shells=shells,
        representation=model.basis.representation,
        normalization_convention=model.basis.normalization_convention,
        ao_order=model.basis.ao_order,
        angular=model.basis.angular if keep_angular else None,
    )


def test_builder_direct_numpy_rhf_and_array_ownership():
    S, P, aos = _minimal_rhf()
    basis = BasisInput(aos=aos, nbasis=2, nprims=2,
                       representation="cartesian",
                       normalization_convention="source_normalized")
    b = MolecularDataBuilder()
    b.set_geometry(atomic_numbers=[1, 1],
                   coordinates=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.4]],
                   unit="bohr")
    b.set_electronic_state(wfntype="RHF", charge=0, multiplicity=1)
    b.set_basis(basis)
    b.set_overlap(S)
    b.set_density(total=P)
    mdm = b.build()
    assert mdm.nbasis == 2 and mdm.ncenter == 2
    assert mdm.electronic.nelectron == 2
    assert mdm.matrices.S.data is not S
    S[0, 1] = 0.0
    np.testing.assert_allclose(mdm.matrices.S.data[0, 1], 0.5)
    with qe.Engine() as eng:
        res = eng.calculate_mayer(mdm)
    assert res.total.shape == (2, 2)
    assert res.total_semantics == "closed_shell_mayer"
    assert res.mayer_total is res.total


def test_builder_requires_explicit_unit_and_open_shell_method():
    b = MolecularDataBuilder()
    with pytest.raises(ValueError, match="unit"):
        b.set_geometry(atomic_numbers=[1], coordinates=[[0, 0, 0]])
    with pytest.raises(ValueError, match="wfntype"):
        b.set_electronic_state(charge=0, multiplicity=2)


def test_builder_rejects_bad_arrays():
    b = MolecularDataBuilder()
    b.set_geometry(atomic_numbers=[2], coordinates=[[0, 0, 0]], unit="bohr")
    b.set_electronic_state(wfntype=0, charge=0, multiplicity=1)
    b.set_basis(BasisInput(aos=[m1.AOFunction(index=1, center=1, angular_type=0,
                                               multiwfn_type=1)], nbasis=1, nprims=1))
    b.set_overlap(np.eye(2))
    b.set_density(total=np.eye(2))
    with pytest.raises(ValueError, match="shape"):
        b.build()
    with pytest.raises(ValueError, match="finite|NaN|Inf"):
        b.set_geometry(atomic_numbers=[1], coordinates=[[0, np.nan, 0]], unit="bohr")


@requires_orca
def test_builder_full_state_from_shell_inputs_without_files():
    src = from_orca_directory(_ORCA / "h2o")
    orb = src.wavefunction.orbitals
    basis = _basis_input_from_model(src, keep_angular=False)
    basis = BasisInput(shells=basis.shells, representation=basis.representation,
                       normalization_convention="source_normalized")
    mdm = build_molecular_system(
        atomic_numbers=src.atoms.z, coordinates=src.geometry.coordinates,
        coordinate_unit="bohr", wfntype=0, multiplicity=1,
        basis=basis, coefficients=orb.coefficients,
        occupations=orb.occupations, energies=orb.energies, spins=orb.spin,
        coefficient_layout=orb.coefficient_layout,
    )
    assert mdm.matrices.S is None and mdm.matrices.P_total is None
    assert mdm.basis.shells and mdm.basis.primitives and mdm.basis.aos
    with qe.Engine() as eng:
        result = eng.calculate_mayer(mdm)
    with qe.Engine() as eng:
        ref = eng.calculate_mayer(src)
    np.testing.assert_allclose(result.total, ref.total, atol=1e-7, rtol=0.0)


@pytest.mark.parametrize("fn,name", [
    (from_orca_uhf_directory, "uhf"),
    (from_orca_rohf_directory, "rohf"),
])
@requires_orca
def test_builder_open_shell_arrays_and_mayer_semantics(fn, name):
    src = fn(_ORCA / name / f"o2_{name}_sto3g")
    orb = src.wavefunction.orbitals
    b = MolecularDataBuilder()
    b.set_geometry(atomic_numbers=src.atoms.z, coordinates=src.geometry.coordinates,
                   unit="bohr")
    b.set_electronic_state(wfntype=src.electronic.wfntype,
                           charge=src.electronic.charge,
                           multiplicity=src.electronic.multiplicity,
                           nelectron=src.electronic.nelectron)
    b.set_basis(src.basis)
    b.set_overlap(src.matrices.S.data)
    b.set_orbitals(orb.coefficients, orb.occupations, energies=orb.energies,
                   spins=orb.spin, layout=orb.coefficient_layout)
    mdm = b.build()
    with qe.Engine() as eng:
        res = eng.calculate_mayer(mdm)
    assert res.has_spin_components
    assert res.total_semantics == "generalized_wiberg_mixed"
    assert res.mixed is res.total
    np.testing.assert_allclose(res.mayer_total, res.alpha + res.beta)
    assert not np.allclose(res.total, res.mayer_total)
    with qe.Engine() as eng:
        ref = eng.calculate_mayer(src)
    np.testing.assert_allclose(res.total, ref.total, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(res.alpha, ref.alpha, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(res.beta, ref.beta, atol=1e-7, rtol=0.0)


@requires_orca
def test_builder_canonical_f_preserves_1_2_metadata():
    src = from_orca_directory(_ORCA / "df" / "h2s_def2tzvp",
                              canonicalize_angular=True)
    orb = src.wavefunction.orbitals
    mdm = build_molecular_system(
        atomic_numbers=src.atoms.z, coordinates=src.geometry.coordinates,
        coordinate_unit="bohr", wfntype=0, multiplicity=1,
        basis=_basis_input_from_model(src),
        overlap=src.matrices.S.data, coefficients=orb.coefficients,
        occupations=orb.occupations, energies=orb.energies, spins=orb.spin,
        coefficient_layout=orb.coefficient_layout, schema_version="1.2.0",
    )
    assert mdm.schema_version == "1.2.0"
    assert mdm.basis.angular.state == "canonical"
    assert all(sh.angular and sh.angular.state == "canonical"
               for sh in mdm.basis.shells)
    with qe.Engine() as eng:
        res = eng.calculate_mayer(mdm)
    assert res.total.shape == (3, 3)


@requires_orca
def test_builder_rejects_unknown_full_state_normalization():
    src = from_orca_directory(_ORCA / "h2o")
    orb = src.wavefunction.orbitals
    basis = _basis_input_from_model(src, keep_angular=False)
    basis = BasisInput(shells=basis.shells, representation=basis.representation,
                       normalization_convention="unknown")
    with pytest.raises(qe.QeIncompleteState, match="normalization"):
        build_molecular_system(
            atomic_numbers=src.atoms.z, coordinates=src.geometry.coordinates,
            coordinate_unit="bohr", wfntype=0, multiplicity=1, basis=basis,
            coefficients=orb.coefficients, occupations=orb.occupations,
            energies=orb.energies, spins=orb.spin,
            coefficient_layout=orb.coefficient_layout,
        )


@requires_orca
def test_builder_readiness_rohf_and_analysis_wrapper():
    src = from_orca_rohf_directory(_ORCA / "rohf" / "o2_rohf_sto3g")
    assert src.readiness.analysis_ready["mayer"] is True
    from qe_multiwfn.analysis import calculate_mayer
    res = calculate_mayer(src)
    assert res.has_spin_components
    assert res.metadata["wavefunction_type"] == 2


def test_engine_direct_path_uses_strict_validation():
    S, P, aos = _minimal_rhf()
    bad = P.copy()
    bad[0, 0] += 1.0
    mdm = build_molecular_system(
        atomic_numbers=[1, 1], coordinates=[[0, 0, 0], [0, 0, 1.4]],
        coordinate_unit="bohr", wfntype=0, multiplicity=1,
        basis=BasisInput(aos=aos, nbasis=2, nprims=2,
                         normalization_convention="source_normalized"),
        overlap=S, density_total=bad, validate=False,
    )
    with pytest.raises(ValueError):
        with qe.Engine() as eng:
            eng.load_molecule_v1(mdm)


def test_builder_accepts_noncontiguous_and_float32_arrays():
    S_base = np.zeros((2, 4), dtype=np.float64)
    S_base[:, ::2] = np.array([[1.0, 0.5], [0.5, 1.0]])
    S = S_base[:, ::2]
    P_base = np.zeros((2, 4), dtype=np.float64)
    P_base[:, ::2] = np.full((2, 2), 2.0 / 3.0, dtype=np.float64)
    P = P_base[:, ::2]
    assert not S.flags.c_contiguous and not P.flags.c_contiguous
    _, _, aos = _minimal_rhf()
    mdm = build_molecular_system(
        atomic_numbers=np.array([1, 1], dtype=np.int64),
        coordinates=np.array([[0, 0, 0], [0, 0, 1.4]], dtype=np.float32),
        coordinate_unit="bohr", wfntype=0, multiplicity=1,
        basis=BasisInput(aos=aos, nbasis=2, nprims=2,
                         normalization_convention="source_normalized"),
        overlap=S, density_total=P,
    )
    assert mdm.matrices.S.data.dtype == np.float64
    assert mdm.matrices.P_total.data.dtype == np.float64
    np.testing.assert_allclose(mdm.matrices.S.data,
                               [[1.0, 0.5], [0.5, 1.0]])


@pytest.mark.parametrize("fn,name", [
    (from_orca_uhf_directory, "uhf"),
    (from_orca_rohf_directory, "rohf"),
])
@requires_orca
def test_builder_full_state_open_shell_without_matrices(fn, name):
    src = fn(_ORCA / name / f"o2_{name}_sto3g")
    orb = src.wavefunction.orbitals
    basis = _basis_input_from_model(src, keep_angular=False)
    basis = BasisInput(shells=basis.shells, representation=basis.representation,
                       normalization_convention="source_normalized")
    mdm = build_molecular_system(
        atomic_numbers=src.atoms.z, coordinates=src.geometry.coordinates,
        coordinate_unit="bohr", wfntype=src.electronic.wfntype,
        multiplicity=src.electronic.multiplicity, basis=basis,
        coefficients=orb.coefficients, occupations=orb.occupations,
        energies=orb.energies, spins=orb.spin,
        coefficient_layout=orb.coefficient_layout,
    )
    assert mdm.matrices.S is None and mdm.matrices.P_total is None
    with qe.Engine() as eng:
        result = eng.calculate_mayer(mdm)
    with qe.Engine() as eng:
        ref = eng.calculate_mayer(src)
    np.testing.assert_allclose(result.total, ref.total, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(result.alpha, ref.alpha, atol=1e-7, rtol=0.0)
    np.testing.assert_allclose(result.beta, ref.beta, atol=1e-7, rtol=0.0)
