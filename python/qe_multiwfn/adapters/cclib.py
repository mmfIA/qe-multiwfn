"""
qe_multiwfn.adapters.cclib — cclib data → canonical MolecularSystemV1.

cclib is an independent parser. This adapter extracts geometry, electronic
metadata, MO coefficients/occupations/energies and overlap matrices. It does
not trust cclib's AO ordering blindly: the caller may supply a canonical
BasisSet (for example from the ORCA JSON adapter) and the model's strict
C^TSC validation is applied. Without a basis, the result is a partial model
marked INCOMPLETE and cannot run Mayer.

ORCA 6.1.1 output currently triggers a cclib parser error; the adapter
fails closed with a clear exception instead of guessing.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import numpy as np

from ..molecular import ANGSTROM_TO_BOHR
from ..model_v1 import (
    Atoms,
    BasisSet,
    ElectronicState,
    FileRecord,
    Geometry,
    MatrixBundle,
    MatrixRecord,
    MolecularSystemV1,
    OrbitalSet,
    Periodicity,
    Provenance,
    Wavefunction,
)
from ..normalization import attach_normalization, normalization_report


class CclibAdapterError(ValueError):
    pass


def from_cclib(filepath, **kwargs) -> MolecularSystemV1:
    """Read a file with cclib and convert it (fail-closed on parser errors)."""
    try:
        import cclib
    except Exception as exc:  # pragma: no cover
        raise CclibAdapterError("cclib is not available; install with: pip install 'qe-multiwfn[cclib]'") from exc
    path = Path(filepath)
    if not path.exists():
        raise CclibAdapterError(f"file not found: {path}")
    try:
        data = cclib.io.ccread(str(path))
    except Exception as exc:
        raise CclibAdapterError(
            f"cclib could not parse {path}: {type(exc).__name__}: {exc}"
        ) from exc
    if data is None:
        raise CclibAdapterError(f"cclib returned no data for {path}")
    return from_cclib_data(data, source_file=path, **kwargs)


def _infer_wfntype(data) -> int:
    md = getattr(data, "metadata", {}) or {}
    hf = str(md.get("hf", "")).upper()
    if hf in ("RHF", "RESTRICTED HARTREE-FOCK"):
        return 0
    if hf in ("ROHF", "RESTRICTED OPEN-SHELL HARTREE-FOCK"):
        return 2
    if hf in ("UHF", "UNRESTRICTED HARTREE-FOCK"):
        return 1
    coeffs = getattr(data, "mocoeffs", None)
    if coeffs is not None and len(coeffs) == 2:
        return 1
    return 0


def _density_rhf(C, occ):
    occupied = occ > 1e-8
    if not np.allclose(occ[occupied], 2.0, atol=1e-8):
        raise CclibAdapterError("RHF occupations are not doubly occupied")
    return 2.0 * (C[:, occupied] @ C[:, occupied].T)


def from_cclib_data(data, *, source_file: Optional[Path] = None,
                    basis: Optional[BasisSet] = None,
                    strict: bool = True) -> MolecularSystemV1:
    """Convert a cclib-like object (or cclib ``ccData``) to the model."""
    z = np.asarray(getattr(data, "atomnos", []), dtype=np.int32)
    if z.size == 0:
        raise CclibAdapterError("cclib data has no atomnos")
    coords_ang = np.asarray(getattr(data, "atomcoords", None), dtype=np.float64)
    if coords_ang.ndim == 3:  # multiple frames; use the last
        coords_ang = coords_ang[-1]
    if coords_ang.shape != (z.size, 3):
        raise CclibAdapterError("cclib atomcoords shape is invalid")
    charge = int(getattr(data, "charge", 0))
    multiplicity = int(getattr(data, "mult", 1))
    nelectron = int(z.sum()) - charge
    wfntype = _infer_wfntype(data)
    if wfntype == 0 and nelectron % 2:
        raise CclibAdapterError("RHF requires an even electron count")
    if wfntype == 0 and multiplicity != 1:
        raise CclibAdapterError("RHF requires multiplicity=1")

    S = getattr(data, "aooverlaps", None)
    coeffs = getattr(data, "mocoeffs", None)
    occs = getattr(data, "moocc", None)
    enes = getattr(data, "moenergies", None)
    if S is None or coeffs is None or occs is None:
        raise CclibAdapterError(
            "cclib data lacks aooverlaps/mocoeffs/moocc; cannot build S/P"
        )
    S = np.asarray(S, dtype=np.float64)
    nbasis = S.shape[0]
    if S.shape != (nbasis, nbasis):
        raise CclibAdapterError("cclib overlap matrix is not square")
    if basis is not None and basis.nbasis != nbasis:
        raise CclibAdapterError(
            f"provided basis nbasis={basis.nbasis} != cclib nbasis={nbasis}"
        )

    P_total = None; P_alpha = None; P_beta = None
    orbital_sets = []
    if wfntype == 0:
        C = np.asarray(coeffs[0], dtype=np.float64)
        occ = np.asarray(occs[0], dtype=np.float64)
        P_total = _density_rhf(C, occ)
        orbital_sets.append(OrbitalSet(
            coefficients=C, coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital",
            energies=np.asarray(enes[0], dtype=np.float64) if enes is not None else np.zeros(C.shape[1]),
            occupations=occ, spin=["both"] * C.shape[1],
        ))
        na = nb = nelectron // 2
    elif wfntype == 1:
        if len(coeffs) < 2:
            raise CclibAdapterError("UHF requires alpha and beta MO sets")
        Ca = np.asarray(coeffs[0], dtype=np.float64)
        Cb = np.asarray(coeffs[1], dtype=np.float64)
        oa = np.asarray(occs[0], dtype=np.float64)
        ob = np.asarray(occs[1], dtype=np.float64)
        P_alpha = (Ca * oa) @ Ca.T
        P_beta = (Cb * ob) @ Cb.T
        P_total = P_alpha + P_beta
        na = int(round(float(oa.sum())))
        nb = int(round(float(ob.sum())))
        # store alpha then beta with spin labels
        ene_a = np.asarray(enes[0], dtype=np.float64) if enes is not None else np.zeros(Ca.shape[1])
        ene_b = np.asarray(enes[1], dtype=np.float64) if enes is not None and len(enes) > 1 else np.zeros(Cb.shape[1])
        orbital_sets.append(OrbitalSet(
            coefficients=np.concatenate([Ca, Cb], axis=1),
            coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital",
            energies=np.concatenate([ene_a, ene_b]),
            occupations=np.concatenate([oa, ob]),
            spin=["alpha"] * Ca.shape[1] + ["beta"] * Cb.shape[1],
        ))
    elif wfntype == 2:
        C = np.asarray(coeffs[0], dtype=np.float64)
        occ = np.asarray(occs[0], dtype=np.float64)
        alpha = occ > 0.5
        beta = occ > 1.5
        P_alpha = C[:, alpha] @ C[:, alpha].T
        P_beta = C[:, beta] @ C[:, beta].T
        P_total = P_alpha + P_beta
        na = int(np.sum(alpha)); nb = int(np.sum(beta))
        orbital_sets.append(OrbitalSet(
            coefficients=C, coefficient_representation="contracted_basis",
            coefficient_layout="ao_orbital",
            energies=np.asarray(enes[0], dtype=np.float64) if enes is not None else np.zeros(C.shape[1]),
            occupations=occ, spin=["both"] * C.shape[1],
        ))
    else:
        raise CclibAdapterError(f"unsupported wfntype {wfntype}")

    if abs(na + nb - nelectron) > 1e-6 * max(1, nelectron):
        raise CclibAdapterError("cclib occupations do not sum to nelectron")

    if basis is None:
        basis = BasisSet(nbasis=nbasis, nprims=nbasis, representation="unspecified",
                         normalization_convention="unknown", aos=[])

    atoms = Atoms(z=z)
    geometry = Geometry.from_source(coords_ang, "angstrom")
    electronic = ElectronicState(
        wfntype=wfntype, charge=charge, multiplicity=multiplicity,
        nelectron=nelectron,
        naelectron=na if wfntype != 0 else None,
        nbelectron=nb if wfntype != 0 else None,
    )
    matrices = MatrixBundle(
        S=MatrixRecord(S, representation="ao_current_basis", origin="caller_supplied",
                       derivation="cclib aooverlaps"),
        P_total=MatrixRecord(P_total, representation="ao_current_basis",
                             origin="derived_from_orbitals",
                             derivation="P built from cclib MOs/occupations"),
        P_alpha=MatrixRecord(P_alpha, representation="ao_current_basis",
                             origin="derived_from_orbitals") if P_alpha is not None else None,
        P_beta=MatrixRecord(P_beta, representation="ao_current_basis",
                            origin="derived_from_orbitals") if P_beta is not None else None,
    )
    md = getattr(data, "metadata", {}) or {}
    files = []
    if source_file is not None:
        files.append(FileRecord(role="cclib_input", relative_path=source_file.name,
                                sha256=__import__("hashlib").sha256(
                                    source_file.read_bytes()).hexdigest(),
                                size=source_file.stat().st_size))
    prov = Provenance(
        source_program=str(md.get("package", "cclib")),
        source_version=str(md.get("package_version", getattr(data, "metadata", {}).get("package_version", ""))),
        source_format="cclib",
        input_files=files,
        coordinate_unit_source="angstrom",
        conversion_factor=ANGSTROM_TO_BOHR,
        adapter_name="qe_multiwfn.adapters.cclib",
        adapter_version="1.1.0",
        normalization_steps=["cclib -> canonical model (Angstrom -> Bohr)"],
        hashes={
            "S": __import__("hashlib").sha256(
                np.ascontiguousarray(S).tobytes()).hexdigest(),
            "P_total": __import__("hashlib").sha256(
                np.ascontiguousarray(P_total).tobytes()).hexdigest(),
            "coordinates": __import__("hashlib").sha256(
                np.ascontiguousarray(geometry.coordinates).tobytes()).hexdigest(),
        },
    )
    model = MolecularSystemV1(
        provenance=prov, atoms=atoms, geometry=geometry, electronic=electronic,
        basis=basis, wavefunction=Wavefunction(orbitals=orbital_sets[0]),
        matrices=matrices, periodicity=Periodicity(),
    )
    # Attach normalization only if a complete AO mapping was supplied.
    if model.basis.aos:
        attach_normalization(model)
    model.validate(strict=strict and bool(model.basis.aos))
    return model


__all__ = ["CclibAdapterError", "from_cclib", "from_cclib_data"]
