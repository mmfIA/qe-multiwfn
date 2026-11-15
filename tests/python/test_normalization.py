"""MDM 1.1 — explicit normalization metadata and representation checks."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn import model_v1 as m1
from qe_multiwfn.normalization import (
    analyze_ao_normalization,
    attach_normalization,
    cartesian_primitive_norm,
    component_powers,
    contracted_self_overlap,
    double_factorial,
    normalization_report,
)
from qe_multiwfn.adapters.orca import (
    from_orca_directory,
    from_orca_uhf_directory,
    from_orca_rohf_directory,
)

_HERE = Path(__file__).resolve()
_VALIDATION = _HERE.parents[3] / "QE-Multiwfn-validation"
_ORCA = _VALIDATION / "orca"
_FIX = _VALIDATION / "fixtures" / "cartesian" / "h2o_631gstar_cart"

requires_orca = pytest.mark.skipif(
    not _ORCA.exists(), reason="fixtures unavailable"
)
requires_df = pytest.mark.skipif(
    not (_ORCA / "df").exists(), reason="d/f fixtures unavailable"
)
requires_cartesian = pytest.mark.skipif(
    not _FIX.exists(), reason="Cartesian fixture unavailable"
)


def test_schema_1_1_and_unit_normalization():
    assert m1.SCHEMA_VERSION == "1.1.0"
    assert double_factorial(0) == 1
    assert double_factorial(1) == 1
    assert double_factorial(3) == 3
    assert double_factorial(5) == 15
    assert component_powers("s", 0) == (0, 0, 0)
    assert component_powers("px", 1) == (1, 0, 0)
    assert component_powers("dxx", 2) == (2, 0, 0)
    assert component_powers("dxy", 2) == (1, 1, 0)
    assert component_powers("fxyz", 3) == (1, 1, 1)
    s_norm = cartesian_primitive_norm(1.0, (0, 0, 0))
    p_norm = cartesian_primitive_norm(1.0, (1, 0, 0))
    dxx = cartesian_primitive_norm(1.0, (2, 0, 0))
    dxy = cartesian_primitive_norm(1.0, (1, 1, 0))
    assert abs(s_norm - (2.0 / np.pi) ** 0.75) < 1e-14
    assert abs(p_norm - 2.0 * s_norm) < 1e-12
    assert abs(dxx / dxy - 1.0 / np.sqrt(3.0)) < 1e-12


@requires_orca
def test_contraction_self_overlap_known_shell():
    model = from_orca_directory(_ORCA / "h2")
    shell = model.basis.shells[0]
    ao = model.basis.aos[0]
    powers = component_powers(ao.component, 0)
    diag = contracted_self_overlap(
        shell.exponents, shell.coefficients, powers, normalized_primitives=True
    )
    assert abs(diag - 1.0) < 1e-10
    assert abs(model.matrices.S.data[0, 0] - 1.0) < 1e-10


@requires_orca
@pytest.mark.parametrize("mol", ["h2", "h2o", "benzene"])
def test_orca_rhf_normalization_report(mol):
    model = from_orca_directory(_ORCA / mol)
    rep = normalization_report(model)
    assert rep["status"] == "PASS"
    assert model.basis.normalization_convention in (
        "cartesian_explicit", "mixed", "source_normalized"
    )
    for ao in model.basis.aos:
        assert ao.source_self_overlap is not None
        assert abs(ao.source_self_overlap - 1.0) < 1e-8


@requires_df
@pytest.mark.parametrize("mol", ["h2o_631gstar", "h2s_def2tzvp"])
def test_orca_spherical_df_normalization(mol):
    model = from_orca_directory(_ORCA / "df" / mol)
    rep = normalization_report(model)
    assert rep["status"] == "PASS"
    assert model.basis.normalization_convention == "mixed"
    for ao in model.basis.aos:
        if ao.angular_type >= 2:
            assert ao.normalization_convention == "source_normalized"
            assert abs(ao.source_self_overlap - 1.0) < 1e-8


@requires_orca
def test_orca_uhf_rohf_normalization():
    for fn, d in ((from_orca_uhf_directory, "uhf"), (from_orca_rohf_directory, "rohf")):
        model = fn(_ORCA / d / f"o2_{d}_sto3g")
        rep = normalization_report(model)
        assert rep["status"] == "PASS"
        assert model.basis.normalization_convention == "cartesian_explicit"


@requires_cartesian
def test_cartesian_fixture_normalization_source_scaled():
    model = from_orca_directory(_FIX)
    rep = normalization_report(model)
    assert rep["status"] == "PASS"
    assert model.basis.normalization_convention == "mixed"
    d_aos = [ao for ao in model.basis.aos if ao.angular_type == 2]
    assert d_aos
    for ao in d_aos:
        assert ao.normalization_convention == "cartesian_source_scaled"
        assert ao.contraction_normalization is not None
        assert abs(ao.contraction_normalization - 1.0 / np.sqrt(ao.source_self_overlap)) < 1e-10
    prim = model.basis.primitives
    assert prim.normalization is not None
    for ao in d_aos:
        mask = (prim.shell_index == ao.shell_index) & (prim.type == ao.multiwfn_type)
        assert mask.any()
        assert np.all(prim.normalization[mask] > 0)


def test_legacy_model_normalization_incomplete():
    ms = qe.MolecularSystem(
        ncenter=2, nbasis=2, nprims=2, wfntype=0,
        atomic_numbers=np.array([1, 1], dtype=np.int32),
        coordinates=np.array([[0, 0, 0], [0, 0, 1.4]], dtype=np.float64),
        basis_center=np.array([1, 2], dtype=np.int32),
        basis_type=np.array([0, 0], dtype=np.int32),
        density_total=np.full((2, 2), 2.0 / 3.0),
        overlap=np.array([[1.0, 0.5], [0.5, 1.0]]),
        charge=0, multiplicity=1, nelectron=2,
    )
    model = m1.MolecularSystemV1.from_legacy(ms)
    assert model.basis.normalization_convention == "unknown"
    assert normalization_report(model)["status"] == "INCOMPLETE"


@requires_orca
def test_sp_representation_equivalence():
    """s/p Cartesian and spherical functions are the same physical basis."""
    model = from_orca_directory(_ORCA / "h2")
    with qe.Engine() as eng:
        eng.load_molecule_v1(model)
        eng.prepare()
        cart = eng.calculate_mayer().total

    shells = [replace(s, cartesian=False, spherical=True) for s in model.basis.shells]
    aos = [replace(a, cartesian=False) for a in model.basis.aos]
    basis = replace(model.basis, representation="spherical", shells=shells, aos=aos,
                    normalization_convention="unknown")
    sph_model = replace(model, basis=basis)
    attach_normalization(sph_model)
    assert normalization_report(sph_model)["status"] == "PASS"
    sph_model.validate(strict=True)
    with qe.Engine() as eng:
        eng.load_molecule_v1(sph_model)
        eng.prepare()
        sph = eng.calculate_mayer().total
    np.testing.assert_allclose(sph, cart, atol=0.0, rtol=0.0)


@requires_df
@requires_cartesian
def test_5d_6d_are_distinct_basis_sets():
    """5D and 6D d are different basis sets; no false equivalence is claimed."""
    sph = from_orca_directory(_ORCA / "df" / "h2o_631gstar")
    cart = from_orca_directory(_FIX)
    assert sph.nbasis == 18
    assert cart.nbasis == 19
    assert sph.basis.representation == "spherical"
    assert cart.basis.representation == "cartesian"
    assert normalization_report(sph)["status"] == "PASS"
    assert normalization_report(cart)["status"] == "PASS"
