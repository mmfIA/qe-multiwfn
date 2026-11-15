"""PySCF in-memory adapter for the canonical MDM builder.

The adapter extracts geometry, basis, orbitals and optionally the overlap
matrix from a converged PySCF ``Molecule``/SCF object. It never writes files
and never calls the QE-Multiwfn native library.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from ..angular import (
    AngularBasisMetadata, AngularConvention, CANONICAL_CONVENTION_ID,
    canonical_convention,
)
from ..builder import BasisInput, MolecularDataBuilder, ShellInput
from ..normalization import component_powers, contracted_self_overlap
from ..model_v1 import (
    SCHEMA_VERSION_1_1, SCHEMA_VERSION_1_2, Provenance, symbol_from_z,
)


class PyscfAdapterError(ValueError):
    pass


def _canonical_component_name(component: str) -> str:
    value = component.strip().lower()
    mapping = {
        "dz^2": "dz2",
        "dx2-y2": "dx2-y2",
        "f+0": "f0",
    }
    return mapping.get(value, value)


def _pyscf_components(l: int, cartesian: bool) -> Tuple[str, ...]:
    if l == 0:
        return ("s",)
    if l == 1:
        return ("px", "py", "pz")
    if l == 2:
        if cartesian:
            return ("xx", "xy", "xz", "yy", "yz", "zz")
        return ("dxy", "dyz", "dz^2", "dxz", "dx2-y2")
    if l == 3 and not cartesian:
        return ("f-3", "f-2", "f-1", "f+0", "f+1", "f+2", "f+3")
    raise PyscfAdapterError(
        f"PySCF angular l={l} with cartesian={cartesian} is outside the "
        "validated basis scope"
    )


def _mdm_components(l: int, cartesian: bool) -> Tuple[str, ...]:
    if l < 2:
        return ("s",) if l == 0 else ("pz", "px", "py")
    if l == 2:
        if cartesian:
            return ("xx", "xy", "xz", "yy", "yz", "zz")
        return ("dz2", "dxz", "dyz", "dx2-y2", "dxy")
    if l == 3:
        return ("f0", "f+1", "f-1", "f+2", "f-2", "f+3", "f-3")
    raise PyscfAdapterError(f"unsupported angular l={l}")


def _method_kind(mf: Any) -> int:
    try:
        from pyscf import dft, scf
    except Exception as exc:  # pragma: no cover
        raise PyscfAdapterError("PySCF is not available; install with: pip install 'qe-multiwfn[pyscf]'") from exc
    if isinstance(mf, dft.rks.KohnShamDFT):
        raise PyscfAdapterError("PySCF DFT/Kohn-Sham objects are not supported")
    if isinstance(mf, scf.rohf.ROHF):
        return 2
    if isinstance(mf, scf.uhf.UHF):
        return 1
    if isinstance(mf, scf.hf.RHF):
        return 0
    raise PyscfAdapterError(
        "from_pyscf supports PySCF RHF, UHF and ROHF objects only"
    )


def _unit_contraction_coefficients(l: int, exponents, coefficients,
                                    component: str):
    if l > 2:
        return coefficients
    powers = component_powers(component, l)
    diag = contracted_self_overlap(exponents, coefficients, powers)
    if diag <= 0.0 or not np.isfinite(diag):
        raise PyscfAdapterError("invalid PySCF contraction normalization")
    return coefficients / np.sqrt(diag)


def _basis_spec(mol: Any, *, schema_version: str) -> Tuple[BasisInput, np.ndarray, str]:
    cartesian = bool(getattr(mol, "cart", False))
    shells = []
    perm = []
    saw_f = False
    saw_spherical_df = False
    py_base = 0
    natm = int(mol.natm)
    for atom_i in range(natm):
        symbol = mol.atom_symbol(atom_i)
        rows = mol._basis.get(symbol)
        if not rows:
            raise PyscfAdapterError(f"PySCF basis missing for atom {atom_i} ({symbol})")
        for row in rows:
            l = int(row[0])
            if l > 3:
                raise PyscfAdapterError(
                    f"angular momentum l={l} is not supported by the backend"
                )
            if l == 3 and cartesian:
                raise PyscfAdapterError("Cartesian f is not supported")
            nctr = len(row[1]) - 1
            if nctr < 1:
                raise PyscfAdapterError("invalid PySCF contraction row")
            py_components = tuple(
                _canonical_component_name(c)
                for c in _pyscf_components(l, cartesian)
            )
            mdm_components = _mdm_components(l, cartesian)
            for contraction in range(nctr):
                exps = np.asarray([float(item[0]) for item in row[1:]], dtype=np.float64)
                coeffs = np.asarray(
                    [float(item[contraction + 1]) for item in row[1:]],
                    dtype=np.float64,
                )
                if l == 0:
                    coeffs = _unit_contraction_coefficients(l, exps, coeffs, "s")
                elif l == 1:
                    coeffs = _unit_contraction_coefficients(l, exps, coeffs, "pz")
                elif l == 2:
                    coeffs = _unit_contraction_coefficients(l, exps, coeffs, "xy")
                shells.append(ShellInput(
                    center=atom_i + 1, l=l, exponents=exps,
                    coefficients=coeffs,
                    representation="cartesian" if l < 2 or cartesian else "spherical",
                    component_order=mdm_components,
                ))
                for component in mdm_components:
                    py_index = py_components.index(component)
                    perm.append(py_base + py_index)
                py_base += len(py_components)
                saw_f = saw_f or l == 3
                saw_spherical_df = saw_spherical_df or (l >= 2 and not cartesian)
    if len(perm) != int(mol.nao_nr()):
        raise PyscfAdapterError(
            f"constructed AO order length {len(perm)} != PySCF nao {mol.nao_nr()}"
        )
    if schema_version == SCHEMA_VERSION_1_2 and not saw_f:
        schema_version = SCHEMA_VERSION_1_1
    angular = None
    if schema_version == SCHEMA_VERSION_1_2:
        shells = [replace(shell, angular=canonical_convention(shell.l))
                  for shell in shells]
        angular = AngularBasisMetadata(
            representation="spherical_real",
            phase_convention="canonical-real-spherical",
            normalization="unit_spherical",
            convention_id=CANONICAL_CONVENTION_ID,
            state="canonical",
        )
    normalization = "source_normalized" if not cartesian else "unknown"
    return BasisInput(
        shells=shells,
        representation=("spherical" if saw_spherical_df else "cartesian"),
        normalization_convention=normalization, ao_order="canonical",
        angular=angular,
    ), np.asarray(perm, dtype=np.int64), schema_version


def _arrays(mf: Any, wfntype: int):
    C = getattr(mf, "mo_coeff", None)
    occ = getattr(mf, "mo_occ", None)
    ene = getattr(mf, "mo_energy", None)
    if C is None or occ is None:
        raise PyscfAdapterError("SCF object has no mo_coeff/mo_occ")
    if wfntype == 1:
        C_arr = np.asarray(C)
        occ_arr = np.asarray(occ)
        if C_arr.ndim == 3 and C_arr.shape[0] == 2:
            Ca, Cb = C_arr[0], C_arr[1]
            oa, ob = occ_arr[0], occ_arr[1]
        elif isinstance(C, (tuple, list)) and len(C) == 2:
            Ca = np.asarray(C[0], dtype=np.float64)
            Cb = np.asarray(C[1], dtype=np.float64)
            oa = np.asarray(occ[0], dtype=np.float64)
            ob = np.asarray(occ[1], dtype=np.float64)
        else:
            raise PyscfAdapterError("UHF requires alpha and beta mo_coeff blocks")
        Ca = np.asarray(Ca, dtype=np.float64)
        Cb = np.asarray(Cb, dtype=np.float64)
        oa = np.asarray(oa, dtype=np.float64)
        ob = np.asarray(ob, dtype=np.float64)
        ea = np.asarray(ene[0], dtype=np.float64) if ene is not None else np.zeros(oa.size)
        eb = np.asarray(ene[1], dtype=np.float64) if ene is not None and len(ene) > 1 else np.zeros(ob.size)
        C = np.concatenate([Ca, Cb], axis=1)
        occ = np.concatenate([oa, ob])
        ene = np.concatenate([ea, eb])
        spins = ["alpha"] * Ca.shape[1] + ["beta"] * Cb.shape[1]
    else:
        C = np.asarray(C, dtype=np.float64)
        occ = np.asarray(occ, dtype=np.float64)
        ene = np.asarray(ene, dtype=np.float64) if ene is not None else np.zeros(occ.size)
        spins = ["both"] * occ.size
    if C.ndim != 2 or occ.ndim != 1 or ene.ndim != 1:
        raise PyscfAdapterError("invalid PySCF orbital array dimensions")
    if occ.size != C.shape[1] or ene.size != occ.size:
        raise PyscfAdapterError("PySCF orbital arrays are inconsistent")
    return C, occ, ene, spins


def from_pyscf(mol: Any, mf: Any, *, include_overlap: bool = True,
               schema_version: Optional[str] = None,
               adapter_version: str = "1.0.0"):
    """Build a MolecularSystemV1 directly from PySCF objects.

    Parameters
    ----------
    mol : pyscf.gto.Mole
        Molecule with a basis and geometry in memory.
    mf : pyscf.scf.hf.RHF/UHF/ROHF
        Converged SCF object.
    include_overlap : bool
        If True (default), attach the PySCF overlap matrix and derived
        density; this uses the direct S/P Engine path. If False, omit S/P and
        use the full basis/orbital path (source-normalized spherical bases).
    schema_version : str or None
        ``None`` selects 1.1, or 1.2 automatically when spherical f is present.
    """
    try:
        import pyscf
    except Exception as exc:  # pragma: no cover
        raise PyscfAdapterError("PySCF is not available; install with: pip install 'qe-multiwfn[pyscf]'") from exc
    if not hasattr(mol, "nao_nr") or not hasattr(mol, "atom_coords"):
        raise PyscfAdapterError("mol must be a PySCF Mole object")
    if not bool(getattr(mf, "converged", False)):
        raise PyscfAdapterError("PySCF SCF object is not converged")
    wfntype = _method_kind(mf)
    if schema_version is None:
        schema_version = SCHEMA_VERSION_1_2 if not bool(getattr(mol, "cart", False)) else SCHEMA_VERSION_1_1
    if schema_version not in (SCHEMA_VERSION_1_1, SCHEMA_VERSION_1_2):
        raise PyscfAdapterError(f"unsupported schema_version {schema_version!r}")
    if getattr(mol, "_ecp", None):
        raise PyscfAdapterError("PySCF ECP bases are not supported by the current backend")
    charge = int(mol.charge)
    multiplicity = int(mol.spin) + 1
    nelectron = int(mol.nelectron)
    z = np.asarray(mol.atom_charges(), dtype=np.int32)
    coords = np.asarray(mol.atom_coords(unit="Bohr"), dtype=np.float64)
    if coords.shape != (z.size, 3):
        raise PyscfAdapterError("PySCF atom coordinates have an unexpected shape")
    basis_spec, perm, schema_version = _basis_spec(mol, schema_version=schema_version)
    if not include_overlap and any(shell.l == 2 and shell.representation == "cartesian" for shell in basis_spec.shells):
        raise PyscfAdapterError(
            "PySCF Cartesian-d full state requires include_overlap=True; "
            "per-component normalization is not inferred without S"
        )
    C, occ, ene, spins = _arrays(mf, wfntype)
    if C.shape[0] != len(perm):
        raise PyscfAdapterError(
            f"PySCF coefficient rows {C.shape[0]} != constructed AO count {len(perm)}"
        )
    C = C[perm, :].copy()
    S = None
    if include_overlap:
        S = np.asarray(mol.intor("int1e_ovlp"), dtype=np.float64)
        if S.shape != (len(perm), len(perm)):
            raise PyscfAdapterError("PySCF overlap shape does not match nao")
        S = S[np.ix_(perm, perm)].copy()
        if not np.isfinite(S).all() or np.max(np.abs(S - S.T)) > 1e-10:
            raise PyscfAdapterError("PySCF overlap is non-finite or non-symmetric")
    prov = Provenance(
        source_program="PySCF",
        source_version=str(getattr(pyscf, "__version__", "unknown")),
        source_format="pyscf_objects",
        coordinate_unit_source="bohr",
        conversion_factor=1.0,
        adapter_name="qe_multiwfn.adapters.pyscf",
        adapter_version=adapter_version,
        normalization_steps=["PySCF Mole/SCF -> canonical MDM"],
        hashes={
            "C": hashlib.sha256(np.ascontiguousarray(C).tobytes()).hexdigest(),
            "coordinates": hashlib.sha256(np.ascontiguousarray(coords).tobytes()).hexdigest(),
            **({} if S is None else {
                "S": hashlib.sha256(np.ascontiguousarray(S).tobytes()).hexdigest()
            }),
        },
    )
    builder = MolecularDataBuilder(schema_version=schema_version, provenance=prov)
    builder.set_geometry(atomic_numbers=z, coordinates=coords, unit="bohr")
    builder.set_electronic_state(
        wfntype=wfntype, charge=charge, multiplicity=multiplicity,
        nelectron=nelectron,
    )
    builder.set_basis(basis_spec)
    if S is not None:
        builder.set_overlap(S)
    builder.set_orbitals(C, occ, energies=ene, spins=spins,
                         layout="ao_orbital")
    return builder.build(validate=True)


__all__ = ["PyscfAdapterError", "from_pyscf"]
