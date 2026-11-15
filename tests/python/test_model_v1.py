"""Molecular Data Model 1.0 — Phase 2 tests (MDM-001..015, subset)."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn import model_v1 as m1
from qe_multiwfn.molecular import ANGSTROM_TO_BOHR


def _h2() -> qe.MolecularSystem:
    return qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=2, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([[0.0, 0.0, 0.0],
                              [0.0, 0.0, 1.4]], dtype=np.float64),
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.full((2, 2), 2.0 / 3.0),
        overlap=np.array([[1.0, 0.5], [0.5, 1.0]]),
        charge=0, multiplicity=1, nelectron=2,
    )


def _three_atom() -> qe.MolecularSystem:
    S = np.array([
        [1.0, 0.4, 0.3],
        [0.4, 1.0, 0.5],
        [0.3, 0.5, 1.0],
    ])
    L = np.linalg.cholesky(S)
    C = np.linalg.solve(L.T, np.eye(3)[:, :2])
    P = 2.0 * C @ C.T
    return qe.MolecularSystem(
        ncenter=3, nbasis=3, nprims=3, wfntype=qe.molecular.WFNTYPE_RHF,
        atomic_numbers=np.array([1, 1, 2], dtype=np.int32),
        coordinates=np.array([[0.0, 0.0, 0.0],
                              [0.0, 0.0, 1.0],
                              [0.0, 0.0, 2.0]]),
        basis_center=np.array([1, 2, 3], dtype=np.int32),
        basis_type=np.array([0, 0, 0], dtype=np.int32),
        density_total=P,
        overlap=S,
        charge=0, multiplicity=1, nelectron=4,
    )


def test_schema_version_and_legacy_flag():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    assert model.schema_version == "1.1.0"
    assert model.legacy is True
    assert model.ncenter == 2 and model.nbasis == 2 and model.nprims == 2
    assert model.summary()["has_S"] and model.summary()["has_P_total"]


def test_from_legacy_preserves_arrays_bitwise():
    ms = _three_atom()
    model = m1.MolecularSystemV1.from_legacy(ms)
    assert np.array_equal(model.atoms.z, ms.atomic_numbers)
    assert np.array_equal(model.geometry.coordinates, ms.coordinates)
    assert np.array_equal(model.basis.center_array(), ms.basis_center)
    assert np.array_equal(model.basis.angular_type_array(), ms.basis_type)
    assert np.array_equal(model.matrices.S.data, ms.overlap)
    assert np.array_equal(model.matrices.P_total.data, ms.density_total)


def test_roundtrip_legacy_v1_legacy_bitwise():
    ms = _three_atom()
    back = m1.MolecularSystemV1.from_legacy(ms).to_legacy()
    assert np.array_equal(back.atomic_numbers, ms.atomic_numbers)
    assert np.array_equal(back.coordinates, ms.coordinates)
    assert np.array_equal(back.basis_center, ms.basis_center)
    assert np.array_equal(back.basis_type, ms.basis_type)
    assert np.array_equal(back.density_total, ms.density_total)
    assert np.array_equal(back.overlap, ms.overlap)
    assert back.nprims == ms.nprims
    assert back.charge == ms.charge
    assert back.multiplicity == ms.multiplicity
    assert back.nelectron == ms.nelectron


def test_from_legacy_readiness():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    r = model.readiness
    assert r.geometry_ready and r.basis_ready and r.overlap_ready
    assert r.density_ready
    assert r.analysis_ready["mayer"] is True


def test_to_legacy_rejects_non_rhf():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    uhf = replace(
        model,
        electronic=m1.ElectronicState(
            wfntype=1, charge=0, multiplicity=2, nelectron=2,
            naelectron=2, nbelectron=0,
        ),
    )
    assert uhf.is_legacy_representable() is False
    assert any("RHF" in b for b in uhf.legacy_blockers())
    with pytest.raises(ValueError, match="not representable"):
        uhf.to_legacy()


def test_to_legacy_rejects_missing_density():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    no_p = replace(model, matrices=m1.MatrixBundle(S=model.matrices.S))
    assert no_p.is_legacy_representable() is False
    with pytest.raises(ValueError, match="P_total"):
        no_p.to_legacy()


def test_to_legacy_rejects_pbc():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    pbc = replace(
        model,
        periodicity=m1.Periodicity(
            ifPBC=3,
            directions=np.array([True, True, True]),
            cell_vectors=np.eye(3) * 10.0,
        ),
    )
    assert pbc.is_legacy_representable() is False
    assert any("periodic" in b for b in pbc.legacy_blockers())


def test_strict_validation_rejects_bad_trace():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    bad_p = m1.MatrixRecord(
        data=model.matrices.P_total.data * 1.1,
        representation="ao_current_basis",
        origin="caller_supplied",
    )
    bad = replace(
        model,
        matrices=m1.MatrixBundle(S=model.matrices.S, P_total=bad_p),
    )
    with pytest.raises(ValueError, match=r"Tr\(P\*S\)"):
        bad.validate(strict=True)


def test_geometry_from_angstrom_is_explicit():
    coords_ang = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    geom = m1.Geometry.from_source(coords_ang, "angstrom")
    assert geom.unit_source == "angstrom"
    assert geom.unit_internal == "bohr"
    np.testing.assert_allclose(geom.coordinates, coords_ang * ANGSTROM_TO_BOHR)


def test_ao_permutation_applied_to_matrices_and_metadata():
    ms = _h2()
    model = m1.MolecularSystemV1.from_legacy(ms)
    perm = [1, 0]
    p = model.with_ao_order(perm)
    np.testing.assert_array_equal(p.matrices.S.data, model.matrices.S.data[np.ix_(perm, perm)])
    np.testing.assert_array_equal(
        p.matrices.P_total.data, model.matrices.P_total.data[np.ix_(perm, perm)]
    )
    np.testing.assert_array_equal(p.basis.center_array(), np.array([2, 1]))
    # Original model is not mutated.
    np.testing.assert_array_equal(model.basis.center_array(), np.array([1, 2]))
    assert p.basis.ao_order == "permuted"


def test_ao_permutation_preserves_mayer_result():
    ms = _h2()
    model = m1.MolecularSystemV1.from_legacy(ms)
    permuted = model.with_ao_order([1, 0]).to_legacy()

    with qe.Engine() as eng:
        eng.load_molecule(ms)
        eng.prepare()
        base = eng.calculate_mayer().total
        eng.load_molecule(permuted)
        eng.prepare()
        perm = eng.calculate_mayer().total

    np.testing.assert_allclose(perm, base, atol=0.0, rtol=0.0)


def test_orbital_orthonormality_checked_when_coefficients_present():
    ms = _three_atom()
    model = m1.MolecularSystemV1.from_legacy(ms)
    S = ms.overlap
    L = np.linalg.cholesky(S)
    C = np.linalg.solve(L.T, np.eye(3)[:, :2])
    orb = m1.OrbitalSet(
        coefficients=C,
        coefficient_representation="contracted_basis",
        coefficient_layout="ao_orbital",
        energies=np.array([-1.0, -0.5]),
        occupations=np.array([2.0, 2.0]),
        spin=["both", "both"],
    )
    wf = m1.Wavefunction(orbitals=orb)
    good = replace(model, wavefunction=wf)
    good.validate(strict=True)  # must not raise

    bad_orb = replace(orb, coefficients=C * np.array([[1.1], [1.0], [1.0]]))
    bad = replace(model, wavefunction=m1.Wavefunction(orbitals=bad_orb))
    with pytest.raises(ValueError, match="orthonormality"):
        bad.validate(strict=True)


def test_schema_version_rejected():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    with pytest.raises(ValueError, match="schema_version"):
        replace(model, schema_version="2.0.0")


def test_legacy_helper():
    assert m1.legacy_representable(_h2()) is True


def test_engine_v1_abi_runs_mayer():
    ms = _h2()
    model = m1.MolecularSystemV1.from_legacy(ms)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        v1_result = eng.calculate_mayer().total
        eng.load_molecule(ms)
        eng.prepare()
        legacy_result = eng.calculate_mayer().total
    np.testing.assert_allclose(v1_result, legacy_result, atol=0.0, rtol=0.0)


def test_engine_v1_readiness_bits():
    ms = _h2()
    model = m1.MolecularSystemV1.from_legacy(ms)
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        flags = eng._api.get_readiness_v1()
        for bit in (
            qe.native.QE_V1_READY_GEOMETRY,
            qe.native.QE_V1_READY_BASIS,
            qe.native.QE_V1_READY_DENSITY,
            qe.native.QE_V1_READY_OVERLAP,
            qe.native.QE_V1_READY_AO_MAP,
            qe.native.QE_V1_READY_MAYER,
        ):
            assert flags & bit


def _three_atom_with_orbitals():
    ms = _three_atom()
    S = ms.overlap
    L = np.linalg.cholesky(S)
    C = np.linalg.solve(L.T, np.eye(3)[:, :2])
    model = m1.MolecularSystemV1.from_legacy(ms)
    orb = m1.OrbitalSet(
        coefficients=C,
        coefficient_representation="contracted_basis",
        coefficient_layout="ao_orbital",
        energies=np.array([-1.0, -0.5]),
        occupations=np.array([2.0, 2.0]),
        spin=["both", "both"],
    )
    return replace(model, wavefunction=m1.Wavefunction(orbitals=orb))


def test_derive_density_from_orbitals_matches_supplied():
    model = _three_atom_with_orbitals()
    no_p = replace(model, matrices=m1.MatrixBundle(S=model.matrices.S))
    derived = m1.derive_rhf_density(no_p)
    assert derived.matrices.P_total is not None
    assert derived.matrices.P_total.origin == "derived_from_orbitals"
    assert np.array_equal(
        derived.matrices.P_total.data, model.matrices.P_total.data
    )


def test_wavefunction_report_pass():
    model = _three_atom_with_orbitals()
    rep = m1.wavefunction_report(model)
    assert rep["status"] == "PASS"
    for key in ("orthonormality_CtSC", "electron_count_TrPS",
                "idempotency_PSP", "symmetry_P", "symmetry_S",
                "positivity_S"):
        assert rep[key]["passed"] is True


def test_wavefunction_report_incomplete_without_coefficients():
    model = m1.MolecularSystemV1.from_legacy(_three_atom())
    rep = m1.wavefunction_report(model)
    assert rep["orthonormality_CtSC"]["passed"] is None
    assert rep["status"] == "INCOMPLETE"


def test_wavefunction_report_fails_on_bad_density():
    model = _three_atom_with_orbitals()
    bad_p = m1.MatrixRecord(
        data=model.matrices.P_total.data * 1.05,
        representation="ao_current_basis",
        origin="caller_supplied",
    )
    bad = replace(model, matrices=m1.MatrixBundle(
        S=model.matrices.S, P_total=bad_p))
    rep = m1.wavefunction_report(bad)
    assert rep["status"] == "FAIL"


def test_model_represents_uhf_but_engine_rejects_it():
    """Phase 8 preparation: the model can carry UHF data; the core cannot
    execute it yet and must reject it explicitly (no silent downgrade)."""
    model = m1.MolecularSystemV1.from_legacy(_h2())
    P = model.matrices.P_total.data
    S = model.matrices.S.data
    uhf = replace(
        model,
        electronic=m1.ElectronicState(
            wfntype=1, charge=0, multiplicity=2, nelectron=2,
            naelectron=2, nbelectron=0,
        ),
        matrices=m1.MatrixBundle(
            S=model.matrices.S,
            P_total=model.matrices.P_total,
            P_alpha=m1.MatrixRecord(data=P, representation="ao_current_basis",
                                    origin="caller_supplied"),
            P_beta=m1.MatrixRecord(data=np.zeros_like(P),
                                   representation="ao_current_basis",
                                   origin="caller_supplied"),
        ),
    )
    uhf.validate(strict=False)
    assert uhf.is_legacy_representable() is False
    with pytest.raises(qe.QeUnsupported):
        with qe.Engine() as eng:
            eng.load_molecule_v1(uhf)


def test_to_legacy_rejects_ecp_metadata():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    ecp = replace(model, core_correction=m1.CoreCorrection(
        status="ecp_with_edf", core_electron_count=0, source="test"))
    assert ecp.is_legacy_representable() is False
    assert any("ECP" in b for b in ecp.legacy_blockers())
    with pytest.raises(ValueError, match="ECP"):
        ecp.to_legacy()


def test_shell_and_primitive_validation_negative():
    with pytest.raises(ValueError, match="positive"):
        m1.Shell(index=1, center=1, l=0, shell_type="s",
                 primitive_start=1, primitive_end=1,
                 exponents=np.array([-1.0]), coefficients=np.array([1.0]))
    with pytest.raises(ValueError, match="exponents/coefficients"):
        m1.Shell(index=1, center=1, l=0, shell_type="s",
                 primitive_start=1, primitive_end=1,
                 exponents=np.array([1.0, 2.0]), coefficients=np.array([1.0]))
    with pytest.raises(ValueError, match="primitive range"):
        m1.Shell(index=1, center=1, l=0, shell_type="s",
                 primitive_start=2, primitive_end=1,
                 exponents=np.array([1.0]), coefficients=np.array([1.0]))
    with pytest.raises(ValueError, match="positive"):
        m1.PrimitiveTable(center=np.array([1]), type=np.array([1]),
                          exponent=np.array([0.0]), coefficient=np.array([1.0]))


def test_periodicity_default_is_isolated():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    assert model.periodicity.ifPBC == 0
    assert not model.periodicity.directions.any()


def test_engine_rejects_pbc():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    pbc = replace(model, periodicity=m1.Periodicity(
        ifPBC=3, directions=np.array([True, True, True]),
        cell_vectors=np.eye(3) * 10.0))
    with pytest.raises(qe.QeUnsupported, match="periodic"):
        with qe.Engine() as eng:
            eng.load_molecule_v1(pbc)


def test_engine_rejects_incomplete_ecp_edf():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    ecp = replace(model, core_correction=m1.CoreCorrection(
        status="incomplete", source="test"))
    with pytest.raises(qe.QeIncompleteState, match="ECP/EDF"):
        with qe.Engine() as eng:
            eng.load_molecule_v1(ecp)


def test_engine_rejects_post_hf():
    model = m1.MolecularSystemV1.from_legacy(_h2())
    post = replace(model, electronic=m1.ElectronicState(
        wfntype=4, charge=0, multiplicity=2, nelectron=2,
        naelectron=2, nbelectron=0))
    with pytest.raises(qe.QeUnsupported):
        with qe.Engine() as eng:
            eng.load_molecule_v1(post, allow_open_shell=True)
