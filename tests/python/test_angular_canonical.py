"""Phase 7B — canonical angular MDM contract and phase transforms.

These tests do not call the native backend and do not unblock f/g/h.
"""
from __future__ import annotations

from dataclasses import replace
import numpy as np
import pytest

import qe_multiwfn as qe
from qe_multiwfn.model_v1 import (
    Atoms, BasisSet, ElectronicState, Geometry, MatrixBundle, MatrixRecord,
    MolecularSystemV1, OrbitalSet, Periodicity, Provenance, Shell,
    AOFunction, Wavefunction, SCHEMA_VERSION_1_1, SCHEMA_VERSION_1_2,
)
from qe_multiwfn.angular import (
    AngularConvention, AngularConventionError, AngularUnsupportedError,
    AngularAlreadyCanonicalError, AngularStateError,
    canonical_convention, known_source_convention, phase_matrix,
    canonicalize_model_angular, validate_1_2_angular,
    apply_phase_to_coefficients, apply_phase_to_matrix,
)

_F_COMPONENTS = ("f0", "f+1", "f-1", "f+2", "f-2", "f+3", "f-3")
_F_TYPES = (-12, -11, -10, -9, -8, -7, -6)
_D_COMPONENTS = ("dz2", "dxz", "dyz", "dx2-y2", "dxy")
_D_TYPES = (-5, -4, -3, -2, -1)
_P_COMPONENTS = ("pz", "px", "py")
_P_TYPES = (4, 2, 3)


def _components(l):
    if l == 0:
        return (("s", 1),)
    if l == 1:
        return tuple(zip(_P_COMPONENTS, _P_TYPES))
    if l == 2:
        return tuple(zip(_D_COMPONENTS, _D_TYPES))
    if l == 3:
        return tuple(zip(_F_COMPONENTS, _F_TYPES))
    raise ValueError(l)


def _orthonormal(n, rng):
    q, r = np.linalg.qr(rng.normal(size=(n, n)))
    return q * np.sign(np.diag(r))


def make_model(*, l_values=(0, 1, 2, 3), wfntype=0, seed=7, cartesian_d=False):
    rng = np.random.default_rng(seed)
    shells = []
    aos = []
    pstart = 1
    shell_index = 0
    for l in l_values:
        is_cart = (l == 2 and cartesian_d) or (l < 2)
        if l == 2 and cartesian_d:
            comps = (("xx", 5), ("yy", 6), ("zz", 7), ("xy", 8), ("xz", 9), ("yz", 10))
        else:
            comps = _components(l)
        shell_index += 1
        shells.append(Shell(
            index=shell_index, center=1, l=l,
            shell_type=("s", "p", "d", "f")[l],
            primitive_start=pstart, primitive_end=pstart + len(comps) - 1,
            exponents=np.array([1.0]), coefficients=np.array([1.0]),
            cartesian=is_cart, spherical=not is_cart,
            source_label=f"synthetic-l{l}",
        ))
        for j, (name, typ) in enumerate(comps):
            aos.append(AOFunction(
                index=len(aos) + 1, center=1, shell_index=shell_index,
                l=l, component=name, multiwfn_type=typ,
                angular_type=l, cartesian=is_cart, source_label=name,
                source_index=len(aos),
            ))
        pstart += len(comps)
    n = len(aos)
    basis = BasisSet(
        nbasis=n, nprims=n, representation="spherical" if any(l >= 2 for l in l_values) else "cartesian",
        normalization_convention="source_normalized", shells=shells, aos=aos,
    )
    S = rng.normal(size=(n, n))
    S = S @ S.T + n * np.eye(n)
    S = (S + S.T) / 2.0
    w, V = np.linalg.eigh(S)
    S_inv_sqrt = (V * (1.0 / np.sqrt(w))) @ V.T
    one = _orthonormal(n, rng)
    ne = 2
    nocc = ne // 2
    if wfntype == 0:
        C = S_inv_sqrt @ one
        occ = np.zeros(n); occ[:nocc] = 2.0
        Cocc = C[:, :nocc]
        P = 2.0 * (Cocc @ Cocc.T)
        orb = OrbitalSet(
            coefficients=C, coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital", energies=np.zeros(n),
            occupations=occ, spin=["both"] * n,
        )
        matrices = MatrixBundle(
            S=MatrixRecord(S, representation="ao_current_basis"),
            P_total=MatrixRecord(P, representation="ao_current_basis",
                                 origin="derived_from_orbitals"),
        )
    elif wfntype == 1:
        one_b = _orthonormal(n, rng)
        Ca = S_inv_sqrt @ one
        Cb = S_inv_sqrt @ one_b
        oa = np.zeros(n); oa[0] = 1.0
        ob = np.zeros(n); ob[0] = 1.0
        Pa = Ca[:, :1] @ Ca[:, :1].T
        Pb = Cb[:, :1] @ Cb[:, :1].T
        C = np.concatenate([Ca, Cb], axis=1)
        orb = OrbitalSet(
            coefficients=C, coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital", energies=np.zeros(2 * n),
            occupations=np.concatenate([oa, ob]),
            spin=["alpha"] * n + ["beta"] * n,
        )
        matrices = MatrixBundle(
            S=MatrixRecord(S, representation="ao_current_basis"),
            P_total=MatrixRecord(Pa + Pb, representation="ao_current_basis",
                                 origin="derived_from_orbitals"),
            P_alpha=MatrixRecord(Pa, representation="ao_current_basis",
                                 origin="derived_from_orbitals"),
            P_beta=MatrixRecord(Pb, representation="ao_current_basis",
                                origin="derived_from_orbitals"),
        )
    elif wfntype == 2:
        C = S_inv_sqrt @ one
        occ = np.zeros(n); occ[0] = 1.0
        Cocc = C[:, :1]
        Pa = Cocc @ Cocc.T
        Pb = Cocc @ Cocc.T
        orb = OrbitalSet(
            coefficients=C, coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital", energies=np.zeros(n),
            occupations=np.where(np.arange(n) == 0, 2.0, 0.0),
            spin=["both"] * n,
        )
        matrices = MatrixBundle(
            S=MatrixRecord(S, representation="ao_current_basis"),
            P_total=MatrixRecord(Pa + Pb, representation="ao_current_basis",
                                 origin="derived_from_orbitals"),
            P_alpha=MatrixRecord(Pa, representation="ao_current_basis",
                                 origin="derived_from_orbitals"),
            P_beta=MatrixRecord(Pb, representation="ao_current_basis",
                                origin="derived_from_orbitals"),
        )
    else:
        raise ValueError(wfntype)
    electronic = ElectronicState(
        wfntype=wfntype, charge=0, multiplicity=1, nelectron=ne,
        naelectron=1 if wfntype in (1, 2) else None,
        nbelectron=1 if wfntype in (1, 2) else None,
    )
    model = MolecularSystemV1(
        provenance=Provenance(source_program="synthetic", source_format="arrays"),
        atoms=Atoms(z=np.array([2], dtype=np.int32)),
        geometry=Geometry(coordinates=np.zeros((1, 3), dtype=np.float64)),
        electronic=electronic, basis=basis,
        wavefunction=Wavefunction(orbitals=orb), matrices=matrices,
        periodicity=Periodicity(),
    )
    return model


def _source_map():
    return {
        2: known_source_convention(2, "orca", "6.1.1"),
        3: known_source_convention(3, "orca", "6.1.1"),
    }


def test_phase_matrix_f_is_diagonal():
    D = phase_matrix(3, known_source_convention(3, "orca", "6.1.1").phase_signs)
    assert np.array_equal(D, np.diag([1, 1, 1, 1, 1, -1, -1]))
    assert np.array_equal(D @ D, np.eye(7))


def test_canonical_convention_order_and_f():
    for l in (0, 1, 2, 3):
        c = canonical_convention(l)
        assert c.state == "canonical"
        assert c.magnetic_order == qe.angular.CANONICAL_MAGNETIC_ORDER[l]
        assert all(s == 1 for s in c.phase_signs)


def test_canonicalize_rhf_f_preserves_invariants():
    model = make_model()
    S0 = model.matrices.S.data.copy()
    P0 = model.matrices.P_total.data.copy()
    C0 = model.wavefunction.orbitals.coefficients.copy()
    out = canonicalize_model_angular(model, source=_source_map())
    assert out.schema_version == SCHEMA_VERSION_1_2
    assert out.basis.angular.state == "canonical"
    assert all(sh.angular.state == "canonical" for sh in out.basis.shells)
    S = out.matrices.S.data; P = out.matrices.P_total.data
    C = out.wavefunction.orbitals.coefficients
    np.testing.assert_allclose(C.T @ S @ C, np.eye(C.shape[1]), atol=1e-11)
    np.testing.assert_allclose(np.trace(P @ S), np.trace(P0 @ S0), atol=1e-11)
    np.testing.assert_allclose(P @ S @ P, 2.0 * P, atol=1e-10)
    # The f rows of C change sign for F+3/F-3, not for F0..F±2.
    f_idx = np.array([a.index - 1 for a in out.basis.aos if a.l == 3])
    expected = np.diag([1, 1, 1, 1, 1, -1, -1])
    np.testing.assert_allclose(C[f_idx, :], (expected @ C0[f_idx, :]), atol=1e-11)
    assert out.provenance.angular_transforms[-1].phase_signs == (1, 1, 1, 1, 1, -1, -1)


def test_canonicalize_operator_and_extra():
    model = make_model()
    n = model.nbasis
    rng = np.random.default_rng(3)
    O = rng.normal(size=(n, n)); O = (O + O.T) / 2
    model.matrices.extra["O"] = MatrixRecord(O, representation="ao_current_basis")
    out = canonicalize_model_angular(model, source=_source_map())
    O2 = out.matrices.extra["O"].data
    f = np.array([a.index - 1 for a in out.basis.aos if a.l == 3])
    D = np.eye(n); D[f, f] = np.array([1, 1, 1, 1, 1, -1, -1])
    np.testing.assert_allclose(O2, D @ O @ D, atol=1e-12)


def test_double_transform_rejected():
    out = canonicalize_model_angular(make_model(), source=_source_map())
    with pytest.raises(AngularAlreadyCanonicalError):
        canonicalize_model_angular(out, source=_source_map())


def test_missing_source_for_d_f_rejected():
    with pytest.raises(AngularStateError):
        canonicalize_model_angular(
            make_model(), source={3: known_source_convention(3, "orca", "6.1.1")}
        )


def test_unknown_source_rejected():
    bad = replace(known_source_convention(3, "orca", "6.1.1"), state="unknown")
    with pytest.raises(AngularStateError):
        canonicalize_model_angular(make_model(), source={2: known_source_convention(2, "orca", "6.1.1"), 3: bad})


def test_dimension_and_sign_validation():
    with pytest.raises(AngularConventionError):
        phase_matrix(3, (1, 1, 1))
    with pytest.raises(AngularConventionError):
        apply_phase_to_coefficients(np.zeros((4, 4)), [0, 1, 2], np.ones(2), layout="ao_orbital")
    with pytest.raises(AngularConventionError):
        apply_phase_to_matrix(np.zeros((4, 4)), [0, 1, 2], np.array([1, 2, 1]))


def test_multiple_f_shells():
    model = make_model(l_values=(0, 1, 2, 3, 3))
    out = canonicalize_model_angular(model, source=_source_map())
    fsh = [sh for sh in out.basis.shells if sh.l == 3]
    assert len(fsh) == 2
    assert all(sh.angular.state == "canonical" for sh in fsh)
    S = out.matrices.S.data; C = out.wavefunction.orbitals.coefficients
    np.testing.assert_allclose(C.T @ S @ C, np.eye(C.shape[1]), atol=1e-11)


def test_mixed_shells_and_summary():
    model = make_model()
    out = canonicalize_model_angular(model, source=_source_map())
    s = out.summary()
    assert s["schema_version"] == "1.2.0"
    assert s["angular"]["basis"]["state"] == "canonical"
    assert len(s["angular"]["shells"]) == len(out.basis.shells)


def test_rhf_to_legacy_rejected_after_1_2():
    out = canonicalize_model_angular(make_model(), source=_source_map())
    with pytest.raises(ValueError):
        out.to_legacy()


def test_with_ao_order_rejected_1_2():
    out = canonicalize_model_angular(make_model(), source=_source_map())
    with pytest.raises(ValueError):
        out.with_ao_order(list(range(out.nbasis)))


def test_uhf_and_rohf_invariants():
    for wf in (1, 2):
        model = make_model(wfntype=wf)
        S0 = model.matrices.S.data.copy()
        Pa0 = model.matrices.P_alpha.data.copy(); Pb0 = model.matrices.P_beta.data.copy()
        out = canonicalize_model_angular(model, source=_source_map())
        S = out.matrices.S.data
        np.testing.assert_allclose(np.trace(out.matrices.P_alpha.data @ S),
                                   np.trace(Pa0 @ S0), atol=1e-11)
        np.testing.assert_allclose(np.trace(out.matrices.P_beta.data @ S),
                                   np.trace(Pb0 @ S0), atol=1e-11)
        assert out.electronic.wfntype == wf
        np.testing.assert_allclose(
            out.matrices.P_total.data,
            out.matrices.P_alpha.data + out.matrices.P_beta.data, atol=1e-12
        )


def test_schema_1_1_remains_default_and_valid():
    model = make_model()
    assert model.schema_version == SCHEMA_VERSION_1_1
    model.validate(strict=False)


def test_invalid_schema_rejected():
    model = make_model()
    with pytest.raises(ValueError, match="schema_version"):
        replace(model, schema_version="2.0.0")


def test_missing_shell_metadata_in_1_2_rejected():
    model = make_model()
    # Build a model with 1.2 declared but no angular metadata; the constructor
    # must fail closed.
    with pytest.raises(ValueError, match="canonical basis.angular"):
        replace(model, schema_version="1.2.0")


def test_canonical_cartesian_d_is_identity_phase():
    from qe_multiwfn.angular import canonical_cartesian_convention
    model = make_model(l_values=(0, 1, 2), cartesian_d=True)
    src = replace(canonical_cartesian_convention(2), state="source",
                  convention_id="synthetic-cartesian-d")
    out = canonicalize_model_angular(model, source={2: src})
    assert out.schema_version == "1.2.0"
    dsh = [sh for sh in out.basis.shells if sh.l == 2][0]
    assert dsh.angular.state == "canonical"
    assert dsh.angular.representation == "cartesian"
    np.testing.assert_allclose(out.matrices.S.data, model.matrices.S.data)
    np.testing.assert_allclose(out.matrices.P_total.data, model.matrices.P_total.data)


def test_coefficient_layout_orbital_ao_phase():
    C = np.arange(12, dtype=float).reshape(3, 4)  # (nmo, nao)
    D = np.array([1.0, -1.0])
    out = apply_phase_to_coefficients(C, [1, 3], D, layout="orbital_ao")
    expected = C.copy(); expected[:, [1, 3]] *= D[None, :]
    np.testing.assert_allclose(out, expected)
