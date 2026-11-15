"""
qe_multiwfn.adapters.orca — ORCA 6.x JSON → Molecular Data Model 1.0.

This adapter reads the ``sp.json`` produced by ``orca_2json`` (with a
``sp.json.conf`` that requests S, MOs and 1e integrals), plus optional
``sp.out``/``sp.molden.input``/``sp.property.txt`` for provenance.

What it does:
  - reads atoms, coordinates (unit-aware), charge/multiplicity/HFTyp;
  - builds shells, primitive table and the AO→(center, shell, component) map;
  - reads S and the MO coefficients/energies/occupations;
  - derives the RHF density P = 2 * C_occ C_occ^T (adapter-derived, not a
    library `genP` call);
  - records provenance (file hashes, ORCA version, conversion factor).

It does NOT:
  - modify or replace any scientific routine;
  - support UHF/ROHF/post-HF (rejected explicitly);
  - support d/f component codes yet (rejected explicitly; pending audit);
  - use cclib or any external chemistry package.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..molecular import ANGSTROM_TO_BOHR, WFNTYPE_RHF
from ..normalization import attach_normalization
from ..angular import (
    AngularError,
    canonicalize_model_angular,
    known_source_convention,
)
from ..model_v1 import (
    AOFunction,
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
    PrimitiveTable,
    Provenance,
    Shell,
    Wavefunction,
)


class OrcaAdapterError(ValueError):
    """Raised when an ORCA artifact cannot be converted faithfully."""


# Cartesian/spherical component counts per angular momentum.
_NCOMP_CARTESIAN = {0: 1, 1: 3, 2: 6, 3: 10, 4: 15, 5: 21}
_NCOMP_SPHERICAL = {0: 1, 1: 3, 2: 5, 3: 7, 4: 9, 5: 11}

_SHELL_TO_L = {"s": 0, "p": 1, "d": 2, "f": 3, "g": 4, "h": 5}

# Multiwfn component codes (see docs/MOLECULAR_DATA_MODEL_1.0.md).
# ORCA emits spherical d/f by default (5D/7F); the ORCA component order
# matches the Multiwfn spherical internal order:
#   d: dz2, dxz, dyz, dx2y2, dxy      -> -5..-1
#   f: f0, f+1, f-1, f+2, f-2, f+3, f-3 -> -12..-6
# Cartesian d/f codes follow Multiwfn's component order.
_P_COMPONENT = {"x": 2, "y": 3, "z": 4}
_SPHERICAL_BASE = {2: -5, 3: -12, 4: -21, 5: -32}
_D_CARTESIAN = {"xx": 5, "yy": 6, "zz": 7, "xy": 8, "xz": 9, "yz": 10}
_F_CARTESIAN = {
    "xxx": 11, "yyy": 12, "zzz": 13, "xxy": 14, "xxz": 15,
    "yyz": 16, "xyy": 17, "xzz": 18, "yzz": 19, "xyz": 20,
}
_SHELL_CHARS = ("s", "p", "d", "f", "g", "h")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _parse_label(label: str) -> Tuple[int, str, Optional[str], int]:
    """Parse an ORCA AO label like ``0O   1pz``, ``0O   1dz2`` or ``0S   1f+1``.

    Returns (atom_index_0based, shell_char, component_suffix, principal_n).
    """
    m = re.match(r"^\s*(\d+)([A-Za-z]{1,2})\s+(\d+)([spdfgh])([A-Za-z0-9+\-]*)\s*$",
                 label, re.IGNORECASE)
    if not m:
        raise OrcaAdapterError(f"unrecognised ORCA orbital label: {label!r}")
    atom_idx = int(m.group(1))
    shell = m.group(4).lower()
    component = m.group(5).lower() or None
    n = int(m.group(3))
    if shell not in _SHELL_TO_L:
        raise OrcaAdapterError(f"unsupported shell {shell!r} in {label!r}")
    return atom_idx, shell, component, n


def _component_code(l: int, component: Optional[str], position: int,
                    spherical: bool, label: str) -> int:
    if l == 0:
        return 1                      # Multiwfn S
    if l == 1:
        if component not in _P_COMPONENT:
            raise OrcaAdapterError(f"p orbital without x/y/z orientation: {label!r}")
        return _P_COMPONENT[component]
    if not spherical:
        if l == 2:
            table = _D_CARTESIAN
        elif l == 3:
            table = _F_CARTESIAN
        else:
            raise OrcaAdapterError(
                f"Cartesian component codes for l={l} are not supported"
            )
        key = (component or "").lower()
        if key not in table:
            raise OrcaAdapterError(
                f"unrecognised Cartesian {_SHELL_CHARS[l]} component {component!r} "
                f"in {label!r}"
            )
        return table[key]
    base = _SPHERICAL_BASE.get(l)
    if base is None:
        raise OrcaAdapterError(f"spherical component codes for l={l} are not supported")
    return base + position


def _component_name(l: int, component: Optional[str]) -> str:
    if l == 0:
        return "s"
    if l == 1:
        return f"p{component}"
    shell = _SHELL_CHARS[l] if l < len(_SHELL_CHARS) else f"l{l}"
    return f"{shell}{component or ''}"


def _unit_to_string(raw: Optional[str]) -> str:
    if raw is None:
        return "angstrom"
    u = str(raw).strip().lower()
    if u in ("angs", "angstrom", "angstroms", "a"):
        return "angstrom"
    if u in ("bohr", "au", "a.u.", "atomic"):
        return "bohr"
    raise OrcaAdapterError(f"unsupported ORCA coordinate unit: {raw!r}")


def _orca_version(sp_out: Optional[Path]) -> str:
    if sp_out is None or not sp_out.exists():
        return "unknown"
    text = sp_out.read_text(errors="replace")
    m = re.search(r"Program Version\s+(\S+)", text, re.IGNORECASE)
    return m.group(1) if m else "unknown"


def _canonicalize_orca_model_angular(
    model: MolecularSystemV1,
    *,
    version: str,
    enabled: bool,
) -> MolecularSystemV1:
    """Optionally canonicalize an ORCA model to MDM 1.2.

    The legacy path is the default for compatibility.  When enabled, the
    source convention is attached explicitly for every spherical l >= 2 shell.
    The ORCA f phase is registered only for the validated ORCA 6.1.1
    convention; unknown/other versions fail closed.  g/h is not generalized.
    """
    if not enabled:
        return model
    spherical = [sh for sh in model.basis.shells if sh.l >= 2]
    if not spherical:
        # s/p functions are representation-equivalent; no angular metadata is
        # required and the legacy 1.1 model is preserved.
        return model
    if any(sh.l > 3 for sh in spherical):
        raise OrcaAdapterError(
            "ORCA angular canonicalization supports only s/p/d/f; g/h is not generalized"
        )
    if version != "6.1.1":
        raise OrcaAdapterError(
            "ORCA angular canonicalization is validated only for ORCA 6.1.1; "
            f"got source version {version!r}"
        )
    f_shells = [sh for sh in spherical if sh.l == 3]
    if any(not sh.spherical for sh in f_shells):
        raise OrcaAdapterError(
            "ORCA f angular canonicalization requires spherical f shells; "
            "Cartesian f is not supported by the validated convention"
        )
    source = {
        l: known_source_convention(l, "orca", version)
        for l in sorted({int(sh.l) for sh in spherical})
    }
    try:
        canonical = canonicalize_model_angular(model, source=source)
    except AngularError as exc:
        raise OrcaAdapterError(
            f"ORCA angular canonicalization failed: {exc}"
        ) from exc
    canonical.provenance.normalization_steps = list(
        canonical.provenance.normalization_steps
    ) + [
        "ORCA source angular convention registered",
        "canonicalize_model_angular: MDM 1.2",
    ]
    return canonical


def _build_basis(
    atoms_json: List[dict],
    labels: List[str],
    representation: str = "auto",
) -> Tuple[BasisSet, np.ndarray]:
    """Build shells, primitive table and AO map from ORCA JSON data.

    ``representation`` may be ``"auto"`` (infer from the AO labels),
    ``"spherical"`` or ``"cartesian"``. ORCA's default is spherical d/f.
    """
    if representation not in ("auto", "cartesian", "spherical"):
        raise OrcaAdapterError(
            "representation must be 'auto', 'cartesian' or 'spherical'"
        )
    saw_spherical = False
    saw_cartesian_df = False

    parsed = [_parse_label(lab) for lab in labels]
    ncenter = len(atoms_json)
    if any(p[0] < 0 or p[0] >= ncenter for p in parsed):
        raise OrcaAdapterError("AO label atom index out of range")

    # Group labels by atom, preserving file order.
    labels_by_atom: Dict[int, List[Tuple[int, str, Optional[str], int]]] = {
        i: [] for i in range(ncenter)
    }
    for pos, item in enumerate(parsed):
        labels_by_atom[item[0]].append((pos, *item[1:]))

    shells: List[Shell] = []
    aos: List[AOFunction] = []
    pc: List[int] = []
    pt: List[int] = []
    ps: List[int] = []
    pe: List[int] = []
    psl: List[int] = []
    pex: List[float] = []
    pco: List[float] = []
    global_ao = 0
    nprim = 0
    shell_index = 0

    for atom_i, atom in enumerate(atoms_json):
        shells_json = atom.get("Basis")
        if not shells_json:
            raise OrcaAdapterError(f"atom {atom_i} has no basis shells in sp.json")
        atom_labels = labels_by_atom[atom_i]
        cursor = 0
        for sh_j, sh in enumerate(shells_json):
            shell_char = str(sh["Shell"]).lower()
            if shell_char not in _SHELL_TO_L:
                raise OrcaAdapterError(f"unsupported shell type {shell_char!r}")
            l = _SHELL_TO_L[shell_char]
            exponents = np.asarray(sh["Exponents"], dtype=np.float64)
            coefficients = np.asarray(sh["Coefficients"], dtype=np.float64)
            if exponents.shape != coefficients.shape or exponents.size == 0:
                raise OrcaAdapterError("invalid shell exponents/coefficients")
            if np.any(exponents <= 0):
                raise OrcaAdapterError("shell exponents must be positive")

            # Count the AO labels belonging to this shell. They share the
            # same shell letter and the same principal n.
            if cursor >= len(atom_labels):
                raise OrcaAdapterError(
                    f"atom {atom_i}: missing AO labels for shell {sh_j}"
                )
            first_n = atom_labels[cursor][3]
            detected = 0
            while (cursor + detected < len(atom_labels)
                   and _SHELL_TO_L[atom_labels[cursor + detected][1]] == l
                   and atom_labels[cursor + detected][3] == first_n):
                detected += 1
            if detected == 0:
                raise OrcaAdapterError(
                    f"atom {atom_i}: no AO labels for shell {sh_j}"
                )

            if l >= 2:
                if detected == _NCOMP_SPHERICAL[l]:
                    spherical = True
                elif detected == _NCOMP_CARTESIAN[l]:
                    spherical = False
                else:
                    raise OrcaAdapterError(
                        f"atom {atom_i}: shell {sh_j} has {detected} AO labels; "
                        f"expected {_NCOMP_SPHERICAL[l]} (spherical) or "
                        f"{_NCOMP_CARTESIAN[l]} (Cartesian)"
                    )
                if representation == "spherical" and not spherical:
                    raise OrcaAdapterError("caller requested spherical, got Cartesian d/f")
                if representation == "cartesian" and spherical:
                    raise OrcaAdapterError("caller requested Cartesian, got spherical d/f")
                saw_spherical = saw_spherical or spherical
                if not spherical:
                    saw_cartesian_df = True
            else:
                expected = _NCOMP_SPHERICAL[l]  # == Cartesian count for s/p
                if detected != expected:
                    raise OrcaAdapterError(
                        f"atom {atom_i}: shell {sh_j} has {detected} AO labels; "
                        f"expected {expected}"
                    )
                spherical = False

            ncomp = detected
            shell_index += 1
            first_prim = nprim + 1
            for c in range(ncomp):
                pos, lab_shell, component, lab_n = atom_labels[cursor + c]
                if _SHELL_TO_L[lab_shell] != l or lab_n != first_n:
                    raise OrcaAdapterError(
                        f"AO label {labels[pos]!r} does not match shell {shell_char}"
                    )
                code = _component_code(l, component, c, spherical, labels[pos])
                for k in range(exponents.size):
                    nprim += 1
                    pc.append(atom_i + 1)
                    pt.append(code)
                    pex.append(float(exponents[k]))
                    pco.append(float(coefficients[k]))
                    psl.append(shell_index)
                global_ao += 1
                aos.append(AOFunction(
                    index=global_ao,
                    center=atom_i + 1,
                    shell_index=shell_index,
                    l=l,
                    component=_component_name(l, component),
                    multiwfn_type=code,
                    angular_type=l,
                    cartesian=not spherical,
                    source_label=labels[pos],
                    source_index=pos,
                ))
            cursor += ncomp
            shells.append(Shell(
                index=shell_index,
                center=atom_i + 1,
                l=l,
                shell_type=shell_char,
                primitive_start=first_prim,
                primitive_end=nprim,
                exponents=exponents,
                coefficients=coefficients,
                cartesian=not spherical,
                spherical=spherical,
                source_label=f"atom{atom_i}:shell{sh_j}",
            ))
        if cursor != len(atom_labels):
            raise OrcaAdapterError(
                f"atom {atom_i}: {len(atom_labels) - cursor} unused AO label(s)"
            )

    if global_ao != len(labels):
        raise OrcaAdapterError("AO count does not match the MO label list")

    primitives = PrimitiveTable(
        center=np.asarray(pc, dtype=np.int32),
        type=np.asarray(pt, dtype=np.int32),
        exponent=np.asarray(pex, dtype=np.float64),
        coefficient=np.asarray(pco, dtype=np.float64),
        shell_index=np.asarray(psl, dtype=np.int32),
    )
    if saw_spherical and saw_cartesian_df:
        global_repr = "mixed"
    elif saw_spherical:
        global_repr = "spherical"
    else:
        global_repr = "cartesian"
    basis = BasisSet(
        nbasis=len(aos),
        nprims=nprim,
        representation=global_repr,
        ao_order="source",
        shells=shells,
        primitives=primitives,
        aos=aos,
    )
    if not basis.contiguity_ok():
        raise OrcaAdapterError("ORCA AO order is not contiguous per atom")
    return basis, np.asarray([a.center for a in aos], dtype=np.int32)


def _read_orca_molecule(sp_json: Path) -> dict:
    with open(sp_json) as f:
        data = json.load(f)
    if "Molecule" not in data:
        raise OrcaAdapterError("sp.json has no 'Molecule' object")
    return data["Molecule"]


def from_orca_directory(
    mol_dir,
    *,
    representation: str = "auto",
    sp_json_name: str = "sp.json",
    canonicalize_angular: bool = False,
) -> MolecularSystemV1:
    """Build a MolecularSystemV1 from an ORCA single-point directory.

    ``canonicalize_angular=True`` returns an MDM 1.2 model on the validated
    ORCA 6.1.1 s/p/d/f convention.  The default preserves the legacy 1.1
    behavior for backward compatibility.
    """
    mol_dir = Path(mol_dir)
    sp_json = mol_dir / sp_json_name
    if not sp_json.exists():
        raise OrcaAdapterError(f"missing {sp_json}")

    mol = _read_orca_molecule(sp_json)
    required = ("Atoms", "S-Matrix", "MolecularOrbitals", "Charge",
                "Multiplicity", "HFTyp")
    missing = [k for k in required if k not in mol]
    if missing:
        raise OrcaAdapterError(f"sp.json missing required fields: {missing}")

    hftyp = str(mol["HFTyp"]).upper()
    if hftyp != "RHF":
        raise OrcaAdapterError(
            f"only closed-shell RHF is supported in this phase; got HFTyp={hftyp!r}"
        )
    charge = int(mol["Charge"])
    multiplicity = int(mol["Multiplicity"])
    if multiplicity != 1:
        raise OrcaAdapterError("RHF adapter requires multiplicity=1")

    atoms_json = mol["Atoms"]
    z = np.array([int(a["ElementNumber"]) for a in atoms_json], dtype=np.int32)
    coords_raw = np.array([a["Coords"] for a in atoms_json], dtype=np.float64)
    unit_source = _unit_to_string(mol.get("CoordinateUnits"))
    geometry = Geometry.from_source(coords_raw, unit_source)

    nelectron = int(z.sum()) - charge
    electronic = ElectronicState(
        wfntype=WFNTYPE_RHF,
        charge=charge,
        multiplicity=multiplicity,
        nelectron=nelectron,
    )

    labels = mol["MolecularOrbitals"]["OrbitalLabels"]
    basis, ao_centers = _build_basis(atoms_json, labels, representation)

    S = np.asarray(mol["S-Matrix"], dtype=np.float64)
    nbasis = basis.nbasis
    if S.shape != (nbasis, nbasis):
        raise OrcaAdapterError(
            f"S shape {S.shape} does not match nbasis={nbasis} from the AO labels"
        )
    if not np.all(np.isfinite(S)):
        raise OrcaAdapterError("S contains NaN/Inf")
    if np.max(np.abs(S - S.T)) > 1e-10:
        raise OrcaAdapterError("S is not symmetric")
    if float(np.linalg.eigvalsh(S).min()) <= 0.0:
        raise OrcaAdapterError("S is not positive definite")

    mos = mol["MolecularOrbitals"]["MOs"]
    if len(mos) != nbasis:
        raise OrcaAdapterError(
            f"number of MOs ({len(mos)}) differs from nbasis ({nbasis})"
        )
    C = np.array([mo["MOCoefficients"] for mo in mos], dtype=np.float64).T
    if C.shape != (nbasis, len(mos)):
        raise OrcaAdapterError("MO coefficient matrix has an unexpected shape")
    energies = np.array([mo["OrbitalEnergy"] for mo in mos], dtype=np.float64)
    occupations = np.array([mo["Occupancy"] for mo in mos], dtype=np.float64)
    sym_labels = [str(mo.get("OrbitalSymLabel", "")) for mo in mos]

    if not np.all(np.isfinite(C)) or not np.all(np.isfinite(energies)):
        raise OrcaAdapterError("MO coefficients/energies contain NaN/Inf")
    if np.any(occupations < 0):
        raise OrcaAdapterError("negative orbital occupation")

    # RHF closed-shell only: occupied orbitals must be exactly doubly occupied.
    occupied = occupations > 1e-8
    if not np.allclose(occupations[occupied], 2.0, atol=1e-8, rtol=0.0):
        raise OrcaAdapterError(
            "fractional/open-shell occupations are not supported by this RHF adapter"
        )
    if abs(float(occupations.sum()) - nelectron) > 1e-6 * max(1, nelectron):
        raise OrcaAdapterError(
            f"sum(occupations)={occupations.sum()} does not match Ne={nelectron}"
        )

    # Independent RHF density (adapter-derived; no library genP call).
    Cocc = C[:, occupied]
    P = 2.0 * (Cocc @ Cocc.T)

    # Wavefunction audit (strict profile; same as the P0 validation audit).
    ctsc = float(np.max(np.abs(C.T @ S @ C - np.eye(C.shape[1]))))
    if ctsc > 1e-10:
        raise OrcaAdapterError(f"C^T S C orthonormality error {ctsc:.3e} > 1e-10")
    trps = float(np.trace(P @ S))
    if abs(trps - nelectron) > 1e-8:
        raise OrcaAdapterError(f"Tr(P*S)={trps:.12g} != Ne={nelectron}")
    psp_err = float(np.max(np.abs(P @ S @ P - 2.0 * P)))
    scale = max(1.0, float(np.max(np.abs(2.0 * P))))
    if psp_err > 1e-6 * scale:
        raise OrcaAdapterError(f"RHF idempotency error {psp_err:.3e}")

    orbitals = OrbitalSet(
        coefficients=C,
        coefficient_representation="contracted_basis",
        coefficient_layout="ao_orbital",
        energies=energies,
        occupations=occupations,
        spin=["both"] * len(mos),
        symmetry_labels=sym_labels,
        orbital_indices=np.arange(1, len(mos) + 1, dtype=np.int32),
        nocc=int(occupied.sum()),
    )

    # Provenance.
    files = [FileRecord(
        role="orca_json", relative_path=sp_json.name,
        sha256=_sha256_file(sp_json), size=sp_json.stat().st_size,
    )]
    for name, role in (("sp.out", "orca_output"),
                       ("sp.molden.input", "molden"),
                       ("sp.property.txt", "orca_property")):
        p = mol_dir / name
        if p.exists():
            files.append(FileRecord(
                role=role, relative_path=p.name,
                sha256=_sha256_file(p), size=p.stat().st_size,
            ))
    version = _orca_version(mol_dir / "sp.out")
    provenance = Provenance(
        source_program="ORCA",
        source_version=version,
        source_format="orca_json",
        input_files=files,
        coordinate_unit_source=unit_source,
        conversion_factor=(ANGSTROM_TO_BOHR if unit_source == "angstrom" else 1.0),
        adapter_name="qe_multiwfn.adapters.orca",
        adapter_version="1.0.0",
        normalization_steps=[
            "read sp.json",
            f"coordinates {unit_source} -> bohr",
            "build shells/primitives/AO map (s/p)",
            "read S and MOs",
            "derive P = 2 * C_occ C_occ^T (RHF, adapter)",
        ],
        warnings=[],
        hashes={
            "S": _sha256_array(S),
            "C": _sha256_array(C),
            "P_total": _sha256_array(P),
            "coordinates": _sha256_array(geometry.coordinates),
        },
    )

    model = MolecularSystemV1(
        provenance=provenance,
        atoms=Atoms(z=z),
        geometry=geometry,
        electronic=electronic,
        basis=basis,
        wavefunction=Wavefunction(orbitals=orbitals),
        matrices=MatrixBundle(
            S=MatrixRecord(
                data=S, representation="ao_current_basis",
                origin="caller_supplied", derivation="ORCA S-Matrix",
            ),
            P_total=MatrixRecord(
                data=P, representation="ao_current_basis",
                origin="derived_from_orbitals",
                derivation="P = 2 * C_occ C_occ^T (RHF adapter)",
            ),
        ),
        periodicity=Periodicity(),
    )
    attach_normalization(model)
    model = _canonicalize_orca_model_angular(
        model, version=version, enabled=canonicalize_angular
    )
    model.validate(strict=True)
    return model


def from_orca_json(sp_json_path, **kwargs) -> MolecularSystemV1:
    """Convenience wrapper accepting the path to ``sp.json``."""
    sp_json_path = Path(sp_json_path)
    return from_orca_directory(sp_json_path.parent,
                               sp_json_name=sp_json_path.name, **kwargs)


__all__ = [
    "OrcaAdapterError",
    "from_orca_directory",
    "from_orca_json",
]


def from_orca_uhf_directory(
    mol_dir,
    *,
    representation: str = "auto",
    sp_json_name: str = "sp.json",
    canonicalize_angular: bool = False,
) -> MolecularSystemV1:
    """Build a UHF MolecularSystemV1 from an ORCA single-point directory.

    ORCA's JSON stores ``2*nbasis`` spin-orbitals (alpha block followed by
    beta block) with occupancies. This function splits the blocks, derives
    P_alpha/P_beta and validates the UHF trace and idempotency conditions.
    Only closed-shell-like ROHF/post-HF are excluded; UHF is opt-in.
    """
    mol_dir = Path(mol_dir)
    sp_json = mol_dir / sp_json_name
    if not sp_json.exists():
        raise OrcaAdapterError(f"missing {sp_json}")
    mol = _read_orca_molecule(sp_json)

    required = ("Atoms", "S-Matrix", "MolecularOrbitals", "Charge",
                "Multiplicity", "HFTyp")
    missing = [k for k in required if k not in mol]
    if missing:
        raise OrcaAdapterError(f"sp.json missing required fields: {missing}")
    hftyp = str(mol["HFTyp"]).upper()
    if hftyp != "UHF":
        raise OrcaAdapterError(f"from_orca_uhf_directory requires HFTyp=UHF; got {hftyp!r}")
    charge = int(mol["Charge"])
    multiplicity = int(mol["Multiplicity"])
    if multiplicity < 2:
        raise OrcaAdapterError("UHF requires multiplicity >= 2")

    atoms_json = mol["Atoms"]
    z = np.array([int(a["ElementNumber"]) for a in atoms_json], dtype=np.int32)
    coords_raw = np.array([a["Coords"] for a in atoms_json], dtype=np.float64)
    unit_source = _unit_to_string(mol.get("CoordinateUnits"))
    geometry = Geometry.from_source(coords_raw, unit_source)
    nelectron = int(z.sum()) - charge

    S = np.asarray(mol["S-Matrix"], dtype=np.float64)
    nbasis = S.shape[0]
    if S.shape != (nbasis, nbasis):
        raise OrcaAdapterError("S matrix is not square")
    if not np.all(np.isfinite(S)) or np.max(np.abs(S - S.T)) > 1e-10:
        raise OrcaAdapterError("S is not finite/symmetric")
    if float(np.linalg.eigvalsh(S).min()) <= 0.0:
        raise OrcaAdapterError("S is not positive definite")

    labels = mol["MolecularOrbitals"]["OrbitalLabels"]
    mos = mol["MolecularOrbitals"]["MOs"]
    if len(labels) != 2 * nbasis or len(mos) != 2 * nbasis:
        raise OrcaAdapterError(
            f"UHF expects 2*nbasis MOs/labels ({2*nbasis}); "
            f"got labels={len(labels)}, MOs={len(mos)}, nbasis={nbasis}"
        )
    if labels[:nbasis] != labels[nbasis:]:
        raise OrcaAdapterError(
            "UHF alpha/beta AO label blocks are not identical; unsupported layout"
        )
    basis, _ = _build_basis(atoms_json, labels[:nbasis], representation)

    C_all = np.array([mo["MOCoefficients"] for mo in mos], dtype=np.float64).T
    if C_all.shape != (nbasis, 2 * nbasis):
        raise OrcaAdapterError("UHF MO coefficient matrix has an unexpected shape")
    energies = np.array([mo["OrbitalEnergy"] for mo in mos], dtype=np.float64)
    occupations = np.array([mo["Occupancy"] for mo in mos], dtype=np.float64)
    sym_labels = [str(mo.get("OrbitalSymLabel", "")) for mo in mos]
    if not np.all(np.isfinite(C_all)) or not np.all(np.isfinite(energies)):
        raise OrcaAdapterError("UHF MO coefficients/energies contain NaN/Inf")
    if np.any(occupations < 0):
        raise OrcaAdapterError("negative orbital occupation")

    C_alpha = C_all[:, :nbasis]
    C_beta = C_all[:, nbasis:]
    occ_alpha = occupations[:nbasis]
    occ_beta = occupations[nbasis:]
    for label, occ in (("alpha", occ_alpha), ("beta", occ_beta)):
        if not np.all((occ < 1e-8) | np.isclose(occ, 1.0, atol=1e-8)):
            raise OrcaAdapterError(f"UHF {label} occupations must be 0 or 1")
    na = int(round(float(occ_alpha.sum())))
    nb = int(round(float(occ_beta.sum())))
    if abs(float(occ_alpha.sum()) - na) > 1e-6 or abs(float(occ_beta.sum()) - nb) > 1e-6:
        raise OrcaAdapterError("UHF occupations are not integral")
    if na + nb != nelectron:
        raise OrcaAdapterError(
            f"N_alpha+N_beta={na+nb} does not match Ne={nelectron}"
        )
    if na - nb != multiplicity - 1:
        raise OrcaAdapterError(
            f"N_alpha-N_beta={na-nb} inconsistent with multiplicity={multiplicity}"
        )

    P_alpha = (C_alpha * occ_alpha) @ C_alpha.T
    P_beta = (C_beta * occ_beta) @ C_beta.T
    P_total = P_alpha + P_beta

    for label, Cb, N in (("alpha", C_alpha, na), ("beta", C_beta, nb)):
        ctsc = float(np.max(np.abs(Cb.T @ S @ Cb - np.eye(nbasis))))
        if ctsc > 1e-10:
            raise OrcaAdapterError(f"C_{label}^T S C_{label} error {ctsc:.3e} > 1e-10")
    for label, P in (("alpha", P_alpha), ("beta", P_beta)):
        tr = float(np.trace(P @ S))
        expect = float(na if label == "alpha" else nb)
        if abs(tr - expect) > 1e-8:
            raise OrcaAdapterError(f"Tr(P_{label}*S)={tr:.12g} != N_{label}={expect}")
        scale = max(1.0, float(np.max(np.abs(P))))
        err = float(np.max(np.abs(P @ S @ P - P)))
        if err > 1e-6 * scale:
            raise OrcaAdapterError(f"UHF {label} density is not idempotent: {err:.3e}")

    orbitals = OrbitalSet(
        coefficients=C_all,
        coefficient_representation="contracted_basis",
        coefficient_layout="ao_orbital",
        energies=energies,
        occupations=occupations,
        spin=["alpha"] * nbasis + ["beta"] * nbasis,
        symmetry_labels=sym_labels,
        orbital_indices=np.arange(1, 2 * nbasis + 1, dtype=np.int32),
        nocc=int(np.sum(occupations > 1e-8)),
    )

    files = [FileRecord(
        role="orca_json", relative_path=sp_json.name,
        sha256=_sha256_file(sp_json), size=sp_json.stat().st_size,
    )]
    for name, role in (("sp.out", "orca_output"),
                       ("sp.molden.input", "molden"),
                       ("sp.property.txt", "orca_property")):
        p = mol_dir / name
        if p.exists():
            files.append(FileRecord(
                role=role, relative_path=p.name,
                sha256=_sha256_file(p), size=p.stat().st_size,
            ))
    version = _orca_version(mol_dir / "sp.out")
    provenance = Provenance(
        source_program="ORCA",
        source_version=version,
        source_format="orca_json",
        input_files=files,
        coordinate_unit_source=unit_source,
        conversion_factor=(ANGSTROM_TO_BOHR if unit_source == "angstrom" else 1.0),
        adapter_name="qe_multiwfn.adapters.orca",
        adapter_version="1.0.0",
        normalization_steps=[
            "read sp.json (UHF)",
            f"coordinates {unit_source} -> bohr",
            "build shells/primitives/AO map",
            "split alpha/beta MO blocks",
            "derive P_alpha, P_beta and P_total (UHF adapter)",
        ],
        warnings=["UHF spin-resolved wavefunction"],
        hashes={
            "S": _sha256_array(S),
            "C_alpha": _sha256_array(C_alpha),
            "C_beta": _sha256_array(C_beta),
            "P_alpha": _sha256_array(P_alpha),
            "P_beta": _sha256_array(P_beta),
            "P_total": _sha256_array(P_total),
            "coordinates": _sha256_array(geometry.coordinates),
        },
    )

    model = MolecularSystemV1(
        provenance=provenance,
        atoms=Atoms(z=z),
        geometry=geometry,
        electronic=ElectronicState(
            wfntype=1, charge=charge, multiplicity=multiplicity,
            nelectron=nelectron, naelectron=na, nbelectron=nb,
        ),
        basis=basis,
        wavefunction=Wavefunction(orbitals=orbitals),
        matrices=MatrixBundle(
            S=MatrixRecord(data=S, representation="ao_current_basis",
                           origin="caller_supplied", derivation="ORCA S-Matrix"),
            P_total=MatrixRecord(data=P_total, representation="ao_current_basis",
                                 origin="derived_from_orbitals",
                                 derivation="P_total = P_alpha + P_beta"),
            P_alpha=MatrixRecord(data=P_alpha, representation="ao_current_basis",
                                 origin="derived_from_orbitals",
                                 derivation="P_alpha = C_alpha*occ_alpha @ C_alpha^T"),
            P_beta=MatrixRecord(data=P_beta, representation="ao_current_basis",
                                origin="derived_from_orbitals",
                                derivation="P_beta = C_beta*occ_beta @ C_beta^T"),
        ),
        periodicity=Periodicity(),
    )
    attach_normalization(model)
    model = _canonicalize_orca_model_angular(
        model, version=version, enabled=canonicalize_angular
    )
    model.validate(strict=True)
    return model


def from_orca_uhf_json(sp_json_path, **kwargs) -> MolecularSystemV1:
    sp_json_path = Path(sp_json_path)
    return from_orca_uhf_directory(sp_json_path.parent,
                                  sp_json_name=sp_json_path.name, **kwargs)


__all__ += ["from_orca_uhf_directory", "from_orca_uhf_json"]


def from_orca_rohf_directory(
    mol_dir,
    *,
    representation: str = "auto",
    sp_json_name: str = "sp.json",
    canonicalize_angular: bool = False,
) -> MolecularSystemV1:
    """Build a ROHF MolecularSystemV1 from an ORCA single-point directory.

    ORCA's ROHF JSON stores one set of spatial MOs with occupancies 2/1/0.
    The standard ROHF spin densities are:
        P_alpha = sum_{occ>0} C_i C_i^T
        P_beta  = sum_{occ=2} C_i C_i^T
        P_total = P_alpha + P_beta
    This is the convention used by the Multiwfn open-shell path and is
    validated against a fresh Multiwfn standalone run and ORCA's property.
    """
    mol_dir = Path(mol_dir)
    sp_json = mol_dir / sp_json_name
    if not sp_json.exists():
        raise OrcaAdapterError(f"missing {sp_json}")
    mol = _read_orca_molecule(sp_json)

    required = ("Atoms", "S-Matrix", "MolecularOrbitals", "Charge",
                "Multiplicity", "HFTyp")
    missing = [k for k in required if k not in mol]
    if missing:
        raise OrcaAdapterError(f"sp.json missing required fields: {missing}")
    hftyp = str(mol["HFTyp"]).upper()
    if hftyp != "ROHF":
        raise OrcaAdapterError(f"from_orca_rohf_directory requires HFTyp=ROHF; got {hftyp!r}")
    charge = int(mol["Charge"])
    multiplicity = int(mol["Multiplicity"])
    if multiplicity < 2:
        raise OrcaAdapterError("ROHF requires multiplicity >= 2")

    atoms_json = mol["Atoms"]
    z = np.array([int(a["ElementNumber"]) for a in atoms_json], dtype=np.int32)
    coords_raw = np.array([a["Coords"] for a in atoms_json], dtype=np.float64)
    unit_source = _unit_to_string(mol.get("CoordinateUnits"))
    geometry = Geometry.from_source(coords_raw, unit_source)
    nelectron = int(z.sum()) - charge

    S = np.asarray(mol["S-Matrix"], dtype=np.float64)
    nbasis = S.shape[0]
    if S.shape != (nbasis, nbasis):
        raise OrcaAdapterError("S matrix is not square")
    if not np.all(np.isfinite(S)) or np.max(np.abs(S - S.T)) > 1e-10:
        raise OrcaAdapterError("S is not finite/symmetric")
    if float(np.linalg.eigvalsh(S).min()) <= 0.0:
        raise OrcaAdapterError("S is not positive definite")

    labels = mol["MolecularOrbitals"]["OrbitalLabels"]
    mos = mol["MolecularOrbitals"]["MOs"]
    if len(labels) != nbasis or len(mos) != nbasis:
        raise OrcaAdapterError(
            f"ROHF expects nbasis MOs/labels ({nbasis}); got labels={len(labels)}, "
            f"MOs={len(mos)}"
        )
    basis, _ = _build_basis(atoms_json, labels, representation)

    C = np.array([mo["MOCoefficients"] for mo in mos], dtype=np.float64).T
    if C.shape != (nbasis, nbasis):
        raise OrcaAdapterError("ROHF MO coefficient matrix has an unexpected shape")
    energies = np.array([mo["OrbitalEnergy"] for mo in mos], dtype=np.float64)
    occupations = np.array([mo["Occupancy"] for mo in mos], dtype=np.float64)
    sym_labels = [str(mo.get("OrbitalSymLabel", "")) for mo in mos]
    if not np.all(np.isfinite(C)) or not np.all(np.isfinite(energies)):
        raise OrcaAdapterError("ROHF MO coefficients/energies contain NaN/Inf")
    if np.any(occupations < 0):
        raise OrcaAdapterError("negative orbital occupation")
    if not np.all((np.abs(occupations) < 1e-8) | np.isclose(occupations, 1.0, atol=1e-8)
                  | np.isclose(occupations, 2.0, atol=1e-8)):
        raise OrcaAdapterError("ROHF occupations must be 0, 1 or 2")

    alpha_occ = occupations > 0.5
    beta_occ = occupations > 1.5
    na = int(np.sum(alpha_occ))
    nb = int(np.sum(beta_occ))
    if na + nb != nelectron:
        raise OrcaAdapterError(
            f"N_alpha+N_beta={na+nb} does not match Ne={nelectron}"
        )
    if na - nb != multiplicity - 1:
        raise OrcaAdapterError(
            f"N_alpha-N_beta={na-nb} inconsistent with multiplicity={multiplicity}"
        )

    C_alpha = C[:, alpha_occ]
    C_beta = C[:, beta_occ]
    P_alpha = C_alpha @ C_alpha.T
    P_beta = C_beta @ C_beta.T
    P_total = P_alpha + P_beta

    ctsc = float(np.max(np.abs(C.T @ S @ C - np.eye(nbasis))))
    if ctsc > 1e-10:
        raise OrcaAdapterError(f"C^T S C error {ctsc:.3e} > 1e-10")
    for label, P, N in (("alpha", P_alpha, na), ("beta", P_beta, nb)):
        tr = float(np.trace(P @ S))
        if abs(tr - float(N)) > 1e-8:
            raise OrcaAdapterError(f"Tr(P_{label}*S)={tr:.12g} != N_{label}={N}")
        scale = max(1.0, float(np.max(np.abs(P))))
        err = float(np.max(np.abs(P @ S @ P - P)))
        if err > 1e-6 * scale:
            raise OrcaAdapterError(f"ROHF {label} density is not idempotent: {err:.3e}")

    orbitals = OrbitalSet(
        coefficients=C,
        coefficient_representation="contracted_basis",
        coefficient_layout="ao_orbital",
        energies=energies,
        occupations=occupations,
        # ROHF spatial orbitals are shared by both spins; occupations carry
        # the open-shell information.
        spin=["both"] * nbasis,
        symmetry_labels=sym_labels,
        orbital_indices=np.arange(1, nbasis + 1, dtype=np.int32),
        nocc=int(np.sum(alpha_occ)),
    )

    files = [FileRecord(
        role="orca_json", relative_path=sp_json.name,
        sha256=_sha256_file(sp_json), size=sp_json.stat().st_size,
    )]
    for name, role in (("sp.out", "orca_output"),
                       ("sp.molden.input", "molden"),
                       ("sp.property.txt", "orca_property")):
        p = mol_dir / name
        if p.exists():
            files.append(FileRecord(
                role=role, relative_path=p.name,
                sha256=_sha256_file(p), size=p.stat().st_size,
            ))
    version = _orca_version(mol_dir / "sp.out")
    provenance = Provenance(
        source_program="ORCA",
        source_version=version,
        source_format="orca_json",
        input_files=files,
        coordinate_unit_source=unit_source,
        conversion_factor=(ANGSTROM_TO_BOHR if unit_source == "angstrom" else 1.0),
        adapter_name="qe_multiwfn.adapters.orca",
        adapter_version="1.0.0",
        normalization_steps=[
            "read sp.json (ROHF)",
            f"coordinates {unit_source} -> bohr",
            "build shells/primitives/AO map",
            "split occupied/doubly-occupied spatial MOs",
            "derive P_alpha, P_beta and P_total (ROHF adapter)",
        ],
        warnings=["ROHF spin-resolved wavefunction"],
        hashes={
            "S": _sha256_array(S),
            "C": _sha256_array(C),
            "P_alpha": _sha256_array(P_alpha),
            "P_beta": _sha256_array(P_beta),
            "P_total": _sha256_array(P_total),
            "coordinates": _sha256_array(geometry.coordinates),
        },
    )

    model = MolecularSystemV1(
        provenance=provenance,
        atoms=Atoms(z=z),
        geometry=geometry,
        electronic=ElectronicState(
            wfntype=2, charge=charge, multiplicity=multiplicity,
            nelectron=nelectron, naelectron=na, nbelectron=nb,
        ),
        basis=basis,
        wavefunction=Wavefunction(orbitals=orbitals),
        matrices=MatrixBundle(
            S=MatrixRecord(data=S, representation="ao_current_basis",
                           origin="caller_supplied", derivation="ORCA S-Matrix"),
            P_total=MatrixRecord(data=P_total, representation="ao_current_basis",
                                 origin="derived_from_orbitals",
                                 derivation="P_total = P_alpha + P_beta (ROHF)"),
            P_alpha=MatrixRecord(data=P_alpha, representation="ao_current_basis",
                                 origin="derived_from_orbitals",
                                 derivation="P_alpha = C_occ C_occ^T (ROHF)"),
            P_beta=MatrixRecord(data=P_beta, representation="ao_current_basis",
                                origin="derived_from_orbitals",
                                derivation="P_beta = C_doubly C_doubly^T (ROHF)"),
        ),
        periodicity=Periodicity(),
    )
    attach_normalization(model)
    model = _canonicalize_orca_model_angular(
        model, version=version, enabled=canonicalize_angular
    )
    model.validate(strict=True)
    return model


def from_orca_rohf_json(sp_json_path, **kwargs) -> MolecularSystemV1:
    sp_json_path = Path(sp_json_path)
    return from_orca_rohf_directory(sp_json_path.parent,
                                   sp_json_name=sp_json_path.name, **kwargs)


__all__ += ["from_orca_rohf_directory", "from_orca_rohf_json"]


def _read_xyz(path: Path):
    """Read a simple XYZ file (Angstrom)."""
    lines = Path(path).read_text().splitlines()
    if len(lines) < 2:
        raise OrcaAdapterError(f"invalid XYZ file: {path}")
    try:
        n = int(lines[0].strip())
    except ValueError as exc:
        raise OrcaAdapterError(f"invalid XYZ atom count in {path}") from exc
    symbols = []
    coords = []
    for line in lines[2:2 + n]:
        parts = line.split()
        if len(parts) < 4:
            raise OrcaAdapterError(f"invalid XYZ line in {path}: {line!r}")
        symbols.append(parts[0])
        try:
            coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
        except ValueError as exc:
            raise OrcaAdapterError(f"invalid XYZ coordinate in {path}") from exc
    if len(symbols) != n:
        raise OrcaAdapterError(f"truncated XYZ file: {path}")
    return symbols, np.asarray(coords, dtype=np.float64)


def from_orca_optimization(
    mol_dir,
    *,
    representation: str = "auto",
    sp_json_name: str = "sp.json",
    opt_xyz_name: str = "opt.xyz",
    geometry_tol_angstrom: float = 1e-4,
    canonicalize_angular: bool = False,
) -> MolecularSystemV1:
    """Build a model using the optimized geometry and the SP wavefunction.

    The single-point wavefunction in ``sp.json`` must correspond to the
    optimized geometry in ``opt.xyz``. The coordinates are compared and the
    build fails closed if they differ by more than ``geometry_tol_angstrom``.
    """
    mol_dir = Path(mol_dir)
    model = from_orca_directory(
        mol_dir, representation=representation, sp_json_name=sp_json_name,
        canonicalize_angular=canonicalize_angular,
    )
    opt_path = mol_dir / opt_xyz_name
    if not opt_path.exists():
        raise OrcaAdapterError(f"missing optimization geometry: {opt_path}")
    symbols, coords_ang = _read_xyz(opt_path)
    if len(symbols) != model.ncenter:
        raise OrcaAdapterError(
            f"opt.xyz has {len(symbols)} atoms, sp.json has {model.ncenter}"
        )
    if symbols != model.atoms.symbols:
        raise OrcaAdapterError("opt.xyz symbols do not match sp.json atoms")
    coords_bohr = coords_ang * ANGSTROM_TO_BOHR
    max_delta = float(np.max(np.abs(coords_bohr - model.geometry.coordinates)))
    if max_delta > geometry_tol_angstrom * ANGSTROM_TO_BOHR:
        raise OrcaAdapterError(
            f"opt.xyz geometry differs from sp.json by {max_delta:.3e} Bohr "
            f"(tolerance {geometry_tol_angstrom * ANGSTROM_TO_BOHR:.3e})"
        )
    model.geometry = Geometry.from_source(coords_ang, "angstrom")
    model.provenance.input_files.append(FileRecord(
        role="optimized_geometry", relative_path=opt_path.name,
        sha256=_sha256_file(opt_path), size=opt_path.stat().st_size,
    ))
    model.provenance.normalization_steps = list(
        model.provenance.normalization_steps
    ) + [f"geometry from {opt_path.name} (validated vs sp.json)"]
    model.provenance.hashes["coordinates_opt"] = _sha256_array(
        model.geometry.coordinates
    )
    model.validate(strict=True)
    return model


__all__ += ["from_orca_optimization"]
