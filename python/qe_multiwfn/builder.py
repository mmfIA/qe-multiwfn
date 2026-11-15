"""Public in-memory builder for the Molecular Data Model.

The builder converts NumPy arrays and Python objects into a validated
MolecularSystemV1.  It does not read files, call adapters or execute the
native backend.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .angular import AngularBasisMetadata, AngularConvention, AngularObjectMetadata
from .exceptions import QeIncompleteState
from .model_v1 import (
    AOFunction,
    Atoms,
    BasisSet,
    ElectronicState,
    Geometry,
    MatrixBundle,
    MatrixRecord,
    MolecularSystemV1,
    OrbitalSet,
    Periodicity,
    PrimitiveTable,
    Provenance,
    SCHEMA_VERSION_1_1,
    SCHEMA_VERSION_1_2,
    Shell,
    WAVEFUNCTION_TYPES,
    Wavefunction,
    symbol_from_z,
)
from .normalization import attach_normalization

_SYMBOLS = {symbol_from_z(z): z for z in range(1, 119)}

_COMPONENTS = {
    (0, "cartesian"): ("s",),
    (1, "cartesian"): ("px", "py", "pz"),
    (2, "cartesian"): ("xx", "yy", "zz", "xy", "xz", "yz"),
    (2, "spherical"): ("dz2", "dxz", "dyz", "dx2-y2", "dxy"),
    (3, "cartesian"): ("xxx", "yyy", "zzz", "xxy", "xxz", "yyz", "xyy", "xzz", "yzz", "xyz"),
    (3, "spherical"): ("f0", "f+1", "f-1", "f+2", "f-2", "f+3", "f-3"),
}

_CODES = {
    "s": 1,
    "px": 2, "py": 3, "pz": 4,
    "xx": 5, "yy": 6, "zz": 7, "xy": 8, "xz": 9, "yz": 10,
    "xxx": 11, "yyy": 12, "zzz": 13, "xxy": 14, "xxz": 15,
    "yyz": 16, "xyy": 17, "xzz": 18, "yzz": 19, "xyz": 20,
    "dz2": -5, "dxz": -4, "dyz": -3, "dx2-y2": -2, "dxy": -1,
    "f0": -12, "f+1": -11, "f-1": -10, "f+2": -9, "f-2": -8,
    "f+3": -7, "f-3": -6,
}

_SHELL_CHAR = {0: "s", 1: "p", 2: "d", 3: "f"}


def _canonical_component_name(l: int, name: str) -> str:
    key = str(name).strip().lower().replace(" ", "")
    if l == 0:
        if key in ("s", "1s", "0s"):
            return "s"
    if l == 1:
        if key in ("x", "px"):
            return "px"
        if key in ("y", "py"):
            return "py"
        if key in ("z", "pz"):
            return "pz"
    if key in ("x2-y2", "dx2-y2", "dx2y2"):
        key = "dx2-y2"
    if key not in _CODES:
        raise ValueError(f"unsupported component {name!r} for l={l}")
    if l == 2 and key not in _COMPONENTS[(2, "cartesian")] + _COMPONENTS[(2, "spherical")]:
        raise ValueError(f"component {name!r} is not a d component")
    if l == 3 and key not in _COMPONENTS[(3, "cartesian")] + _COMPONENTS[(3, "spherical")]:
        raise ValueError(f"component {name!r} is not an f component")
    return key


def _default_components(l: int, representation: str) -> Tuple[str, ...]:
    if l < 0 or l > 3:
        raise ValueError("the current backend supports l=0..3 only")
    if l < 2:
        return _COMPONENTS[(l, "cartesian")]
    key = "spherical" if representation == "spherical" else "cartesian"
    return _COMPONENTS[(l, key)]


def _component_codes(l: int, names: Sequence[str], representation: str) -> Tuple[int, ...]:
    expected = _default_components(l, representation)
    if len(names) != len(expected):
        raise ValueError(f"l={l} requires {len(expected)} components, got {len(names)}")
    out = []
    for name in names:
        key = _canonical_component_name(l, name)
        if key not in expected:
            if representation == "spherical" and key in _COMPONENTS[(l, "cartesian")]:
                raise ValueError(f"Cartesian component {name!r} in a spherical shell")
            if representation == "cartesian" and key in _COMPONENTS[(l, "spherical")]:
                raise ValueError(f"spherical component {name!r} in a Cartesian shell")
            raise ValueError(f"component {name!r} is not valid for l={l}/{representation}")
        out.append(_CODES[key])
    return tuple(out)


@dataclass(frozen=True)
class ShellInput:
    center: int
    l: int
    exponents: Sequence[float]
    coefficients: Sequence[float]
    representation: str = "spherical"
    component_order: Optional[Sequence[str]] = None
    multiwfn_types: Optional[Sequence[int]] = None
    normalization: Optional[Sequence[float]] = None
    contraction_normalization: Optional[float] = None
    source_label: Optional[str] = None
    angular: Optional[AngularConvention] = None


@dataclass(frozen=True)
class BasisInput:
    shells: Sequence[ShellInput] = ()
    aos: Optional[Sequence[AOFunction]] = None
    primitives: Optional[PrimitiveTable] = None
    nbasis: Optional[int] = None
    nprims: Optional[int] = None
    representation: str = "unspecified"
    normalization_convention: str = "unknown"
    ao_order: str = "canonical"
    nindbasis: Optional[int] = None
    nbasis_cartesian: Optional[int] = None
    nbasis_spherical: Optional[int] = None
    angular: Optional[AngularBasisMetadata] = None


class MolecularDataBuilder:
    """Build a validated MolecularSystemV1 from in-memory data."""

    def __init__(self, *, schema_version: str = SCHEMA_VERSION_1_1,
                 provenance: Optional[Provenance] = None):
        self.schema_version = schema_version
        self.provenance = provenance
        self._z = None
        self._symbols = None
        self._coordinates = None
        self._coordinate_unit = None
        self._electronic = None
        self._basis = None
        self._overlap = None
        self._density_total = None
        self._density_alpha = None
        self._density_beta = None
        self._extra_matrices: Dict[str, tuple] = {}
        self._coefficients = None
        self._occupations = None
        self._energies = None
        self._spins = None
        self._coefficient_layout = "ao_orbital"
        self._coefficient_representation = "contracted_basis"
        self._angular = None

    def set_geometry(self, *, atomic_numbers=None, symbols=None, coordinates,
                     unit: Optional[str] = None) -> "MolecularDataBuilder":
        if unit is None:
            raise ValueError("coordinate unit must be explicit ('angstrom' or 'bohr')")
        if unit not in ("angstrom", "bohr"):
            raise ValueError("coordinate unit must be 'angstrom' or 'bohr'")
        if atomic_numbers is None and symbols is None:
            raise ValueError("atomic_numbers or symbols is required")
        if atomic_numbers is not None:
            z = np.asarray(atomic_numbers, dtype=np.int32)
            if z.ndim != 1 or z.size == 0:
                raise ValueError("atomic_numbers must be a non-empty 1-D array")
            if symbols is not None:
                syms = [str(s).strip().capitalize() for s in symbols]
                if len(syms) != z.size:
                    raise ValueError("symbols length must match atomic_numbers")
                for zi, si in zip(z, syms):
                    if _SYMBOLS.get(si) != int(zi):
                        raise ValueError(f"symbol {si!r} inconsistent with Z={int(zi)}")
            else:
                syms = [symbol_from_z(int(zi)) for zi in z]
        else:
            syms = [str(s).strip().capitalize() for s in symbols]
            try:
                z = np.asarray([_SYMBOLS[s] for s in syms], dtype=np.int32)
            except KeyError as exc:
                raise ValueError(f"unknown chemical symbol: {exc.args[0]!r}") from exc
        coords = np.asarray(coordinates, dtype=np.float64)
        if coords.shape != (z.size, 3):
            raise ValueError("coordinates must have shape (ncenter, 3)")
        if not np.isfinite(coords).all():
            raise ValueError("coordinates contain NaN/Inf")
        self._z = np.array(z, dtype=np.int32, copy=True)
        self._symbols = list(syms)
        self._coordinates = np.array(coords, dtype=np.float64, copy=True)
        self._coordinate_unit = unit
        return self

    def set_electronic_state(self, *, wfntype=None, charge=0, multiplicity=1,
                              nelectron=None, naelectron=None,
                              nbelectron=None) -> "MolecularDataBuilder":
        if wfntype is None:
            if int(multiplicity) != 1:
                raise ValueError("wfntype is required for open-shell states")
            wfntype = 0
        if isinstance(wfntype, str):
            names = {v.upper(): k for k, v in WAVEFUNCTION_TYPES.items()}
            key = wfntype.strip().upper()
            if key not in names:
                raise ValueError(f"unknown wfntype {wfntype!r}")
            wfntype = names[key]
        wfntype = int(wfntype)
        if wfntype not in WAVEFUNCTION_TYPES:
            raise ValueError(f"unknown wfntype {wfntype}")
        self._electronic = {
            "wfntype": wfntype,
            "charge": int(charge),
            "multiplicity": int(multiplicity),
            "nelectron": None if nelectron is None else int(nelectron),
            "naelectron": None if naelectron is None else int(naelectron),
            "nbelectron": None if nbelectron is None else int(nbelectron),
        }
        return self

    def set_basis(self, basis) -> "MolecularDataBuilder":
        if isinstance(basis, BasisInput):
            self._basis = basis
        elif isinstance(basis, BasisSet):
            self._basis = deepcopy(basis)
        else:
            raise TypeError("basis must be BasisInput or BasisSet")
        return self

    def set_overlap(self, overlap) -> "MolecularDataBuilder":
        self._overlap = np.array(overlap, dtype=np.float64, copy=True)
        return self

    def set_density(self, *, total=None, alpha=None, beta=None) -> "MolecularDataBuilder":
        self._density_total = None if total is None else np.array(total, dtype=np.float64, copy=True)
        self._density_alpha = None if alpha is None else np.array(alpha, dtype=np.float64, copy=True)
        self._density_beta = None if beta is None else np.array(beta, dtype=np.float64, copy=True)
        return self

    def set_orbitals(self, coefficients, occupations, *, energies=None,
                     spins=None, layout="ao_orbital",
                     representation="contracted_basis") -> "MolecularDataBuilder":
        self._coefficients = np.array(coefficients, dtype=np.float64, copy=True)
        self._occupations = np.array(occupations, dtype=np.float64, copy=True)
        self._energies = None if energies is None else np.array(energies, dtype=np.float64, copy=True)
        self._spins = None if spins is None else list(spins)
        self._coefficient_layout = str(layout)
        self._coefficient_representation = str(representation)
        return self

    def set_matrix(self, name: str, matrix, *, representation="ao_current_basis",
                   symmetric=True, origin="caller_supplied", derivation="") -> "MolecularDataBuilder":
        if not name or name in ("S", "P_total", "P_alpha", "P_beta"):
            raise ValueError("use set_overlap/set_density for the standard matrices")
        self._extra_matrices[str(name)] = (
            np.array(matrix, dtype=np.float64, copy=True),
            str(representation), bool(symmetric), str(origin), str(derivation),
        )
        return self

    def set_angular(self, angular: Optional[AngularObjectMetadata] = None) -> "MolecularDataBuilder":
        self._angular = angular
        return self

    def _build_basis(self) -> BasisSet:
        if isinstance(self._basis, BasisSet):
            return deepcopy(self._basis)
        if not isinstance(self._basis, BasisInput):
            raise QeIncompleteState(6, "basis data is required", "MolecularDataBuilder.build")
        spec = self._basis
        shells: List[Shell] = []
        aos: List[AOFunction] = []
        pc, pt, pex, pco, pnorm, pshell = [], [], [], [], [], []
        global_prim = 0
        global_ao = 0
        shell_index = 0
        saw_spherical = False
        saw_cartesian_df = False

        if spec.aos is not None:
            aos = [deepcopy(a) for a in spec.aos]
            if not aos:
                raise ValueError("basis.aos cannot be empty")
            if spec.shells:
                raise ValueError("provide either shells or a complete aos map, not both")
            nbasis = int(spec.nbasis or len(aos))
            nprims = int(spec.nprims or nbasis)
            if len(aos) != nbasis:
                raise ValueError("basis.aos length does not match nbasis")
            basis = BasisSet(
                nbasis=nbasis, nprims=nprims,
                representation=spec.representation,
                normalization_convention=spec.normalization_convention,
                ao_order=spec.ao_order, shells=[], primitives=spec.primitives,
                aos=aos, angular=spec.angular,
            )
            return basis

        if not spec.shells:
            raise QeIncompleteState(6, "basis shells or AO map is required",
                                    "MolecularDataBuilder.build")
        for sh in spec.shells:
            if not isinstance(sh, ShellInput):
                raise TypeError("basis.shells must contain ShellInput")
            center = int(sh.center)
            l = int(sh.l)
            if center < 1:
                raise ValueError("shell center must be 1-based")
            if l > 3:
                raise ValueError("the current backend supports l=0..3 only")
            ex = np.array(sh.exponents, dtype=np.float64, copy=True)
            co = np.array(sh.coefficients, dtype=np.float64, copy=True)
            if ex.ndim != 1 or co.ndim != 1 or ex.size == 0 or ex.shape != co.shape:
                raise ValueError("shell exponents/coefficients must be equal non-empty 1-D arrays")
            if not np.isfinite(ex).all() or not np.isfinite(co).all():
                raise ValueError("shell exponents/coefficients contain NaN/Inf")
            if np.any(ex <= 0):
                raise ValueError("shell exponents must be positive")
            representation = "cartesian" if l < 2 else str(sh.representation)
            if representation not in ("cartesian", "spherical"):
                raise ValueError("shell representation must be 'cartesian' or 'spherical'")
            names = tuple(sh.component_order or _default_components(l, representation))
            names = tuple(_canonical_component_name(l, n) for n in names)
            codes = tuple(sh.multiwfn_types or _component_codes(l, names, representation))
            if len(codes) != len(names) or any(int(c) == 0 for c in codes):
                raise ValueError("multiwfn_types must be nonzero and match components")
            if l < 2:
                spherical = False
            else:
                spherical = representation == "spherical"
                if l == 3 and not spherical:
                    raise ValueError("Cartesian f is not supported by the validated backend")
                saw_spherical = saw_spherical or spherical
                saw_cartesian_df = saw_cartesian_df or (not spherical and l >= 2)
            shell_index += 1
            first_prim = global_prim + 1
            for comp, code in zip(names, codes):
                if sh.normalization is not None:
                    norm = np.asarray(sh.normalization, dtype=np.float64)
                    if norm.shape != ex.shape:
                        raise ValueError("shell normalization shape mismatch")
                else:
                    norm = None
                for k in range(ex.size):
                    global_prim += 1
                    pc.append(center)
                    pt.append(int(code))
                    pex.append(float(ex[k]))
                    pco.append(float(co[k]))
                    pnorm.append(float(norm[k]) if norm is not None else 1.0)
                    pshell.append(shell_index)
                global_ao += 1
                aos.append(AOFunction(
                    index=global_ao, center=center, shell_index=shell_index,
                    l=l, component=comp, multiwfn_type=int(code),
                    angular_type=l, cartesian=not spherical,
                    source_index=global_ao - 1,
                    contraction_normalization=sh.contraction_normalization,
                ))
            shells.append(Shell(
                index=shell_index, center=center, l=l, shell_type=_SHELL_CHAR[l],
                primitive_start=first_prim, primitive_end=global_prim,
                exponents=ex, coefficients=co,
                normalization=None if sh.normalization is None else np.array(sh.normalization, dtype=np.float64, copy=True),
                contraction_normalization=sh.contraction_normalization,
                cartesian=not spherical, spherical=spherical,
                source_label=sh.source_label or f"shell{shell_index}",
                angular=sh.angular,
            ))
        primitives = PrimitiveTable(
            center=np.asarray(pc, dtype=np.int32),
            type=np.asarray(pt, dtype=np.int32),
            exponent=np.asarray(pex, dtype=np.float64),
            coefficient=np.asarray(pco, dtype=np.float64),
            normalization=np.asarray(pnorm, dtype=np.float64),
            shell_index=np.asarray(pshell, dtype=np.int32),
        )
        representation = spec.representation
        if representation == "unspecified":
            if saw_spherical and saw_cartesian_df:
                representation = "mixed"
            elif saw_spherical:
                representation = "spherical"
            elif saw_cartesian_df:
                representation = "cartesian"
            else:
                representation = "cartesian"
        basis = BasisSet(
            nbasis=len(aos), nprims=len(primitives.center),
            nindbasis=spec.nindbasis,
            nbasis_cartesian=spec.nbasis_cartesian,
            nbasis_spherical=spec.nbasis_spherical,
            representation=representation,
            normalization_convention=spec.normalization_convention,
            ao_order=spec.ao_order, shells=shells, primitives=primitives,
            aos=aos, angular=spec.angular,
        )
        return basis

    def _normalization_metadata(self, model: MolecularSystemV1) -> None:
        if model.matrices.S is not None and model.basis.shells and model.basis.primitives is not None:
            attach_normalization(model)
            return
        convention = model.basis.normalization_convention
        if convention == "source_normalized":
            for ao in model.basis.aos:
                ao.source_self_overlap = 1.0
                ao.contraction_normalization = 1.0
                ao.normalization_convention = "source_normalized"
            if model.basis.primitives is not None and model.basis.primitives.normalization is None:
                model.basis.primitives.normalization = np.ones(model.nprims, dtype=np.float64)

    def _derive_density(self, model: MolecularSystemV1, C, occupations, spins):
        if model.matrices.S is None:
            return None, None, None
        wf = model.electronic.wfntype
        if wf == 0:
            occupied = occupations > 1e-8
            if not np.allclose(occupations[occupied], 2.0, atol=1e-8, rtol=0.0):
                raise ValueError("RHF occupations must be 0 or 2")
            P = 2.0 * (C[:, occupied] @ C[:, occupied].T)
            return P, None, None
        if wf == 1:
            if spins is None:
                raise ValueError("UHF requires explicit spin labels or alpha/beta blocks")
            groups = {"alpha": [], "beta": []}
            for i, s in enumerate(spins):
                if s in groups:
                    groups[s].append(i)
            for label in ("alpha", "beta"):
                if not groups[label]:
                    raise ValueError(f"UHF missing {label} orbitals")
                occ = occupations[groups[label]]
                if not np.all((occ < 1e-8) | np.isclose(occ, 1.0, atol=1e-8)):
                    raise ValueError(f"UHF {label} occupations must be 0 or 1")
            Pa = (C[:, groups["alpha"]] * occupations[groups["alpha"]]) @ C[:, groups["alpha"]].T
            Pb = (C[:, groups["beta"]] * occupations[groups["beta"]]) @ C[:, groups["beta"]].T
            return Pa + Pb, Pa, Pb
        if wf == 2:
            if len(occupations) != C.shape[1]:
                raise ValueError("ROHF occupations must match spatial orbitals")
            if not np.all((occupations < 1e-8) |
                          np.isclose(occupations, 1.0, atol=1e-8) |
                          np.isclose(occupations, 2.0, atol=1e-8)):
                raise ValueError("ROHF occupations must be 0, 1 or 2")
            alpha = occupations > 0.5
            beta = occupations > 1.5
            Pa = C[:, alpha] @ C[:, alpha].T
            Pb = C[:, beta] @ C[:, beta].T
            return Pa + Pb, Pa, Pb
        raise ValueError("post-HF density derivation is not supported")

    def build(self, *, validate: bool = True,
              attach_normalization_metadata: bool = True) -> MolecularSystemV1:
        if self._z is None or self._coordinates is None:
            raise QeIncompleteState(6, "geometry is required", "MolecularDataBuilder.build")
        if self._electronic is None:
            raise QeIncompleteState(6, "electronic state is required", "MolecularDataBuilder.build")
        if self._basis is None:
            raise QeIncompleteState(6, "basis is required", "MolecularDataBuilder.build")
        z = np.array(self._z, dtype=np.int32, copy=True)
        symbols = list(self._symbols or [symbol_from_z(int(x)) for x in z])
        geom = Geometry.from_source(np.array(self._coordinates, copy=True), self._coordinate_unit)
        e = dict(self._electronic)
        charge = int(e["charge"])
        ne = e["nelectron"]
        if ne is None:
            ne = int(z.sum()) - charge
        ne = int(ne)
        wf = int(e["wfntype"])
        mult = int(e["multiplicity"])
        na = e["naelectron"]
        nb = e["nbelectron"]
        if wf in (1, 2):
            if na is None or nb is None:
                na = (ne + mult - 1) // 2
                nb = ne - na
            na, nb = int(na), int(nb)
            if na < 0 or nb < 0 or na + nb != ne:
                raise ValueError("alpha + beta electron counts must equal nelectron")
            if na - nb != mult - 1:
                raise ValueError("alpha - beta electron counts are inconsistent with multiplicity")
        electronic = ElectronicState(
            wfntype=wf, charge=charge, multiplicity=mult, nelectron=ne,
            naelectron=na if wf in (1, 2) else None,
            nbelectron=nb if wf in (1, 2) else None,
        )
        basis = self._build_basis()
        if basis.nbasis != len(basis.aos):
            raise ValueError("basis.nbasis does not match the AO map")
        canonical_angular = (
            self.schema_version == SCHEMA_VERSION_1_2
            and basis.angular is not None
            and basis.angular.state == "canonical"
        )
        record_angular = self._angular
        if record_angular is None and canonical_angular:
            record_angular = AngularObjectMetadata(
                state="canonical", convention_id=basis.angular.convention_id)
        orbitals = None
        if self._coefficients is not None:
            if self._occupations is None:
                raise ValueError("occupations are required with coefficients")
            C = np.array(self._coefficients, copy=True)
            occ = np.array(self._occupations, copy=True)
            if self._coefficient_layout == "ao_orbital":
                nmo = C.shape[1]
                Cb = C
            elif self._coefficient_layout == "orbital_ao":
                nmo = C.shape[0]
                Cb = C.T
            else:
                raise ValueError("coefficient layout must be 'ao_orbital' or 'orbital_ao'")
            if Cb.shape[0] != basis.nbasis:
                raise ValueError("coefficient rows must match nbasis")
            if occ.shape != (nmo,) or not np.isfinite(occ).all() or np.any(occ < 0):
                raise ValueError("occupations must be a finite nonnegative vector of nmo")
            energies = (np.zeros(nmo) if self._energies is None
                        else np.array(self._energies, copy=True))
            if energies.shape != (nmo,):
                raise ValueError("energies must have length nmo")
            spins = self._spins
            if spins is None:
                if wf in (0, 2):
                    spins = ["both"] * nmo
                elif wf == 1 and nmo == 2 * basis.nbasis:
                    spins = ["alpha"] * basis.nbasis + ["beta"] * basis.nbasis
            if spins is None:
                raise ValueError("spin labels are required for open-shell orbitals")
            if len(spins) != nmo:
                raise ValueError("spin labels must have length nmo")
            orbitals = OrbitalSet(
                coefficients=C, coefficient_representation=self._coefficient_representation,
                coefficient_layout=self._coefficient_layout, energies=energies,
                occupations=occ, spin=list(spins),
                orbital_indices=np.arange(1, nmo + 1, dtype=np.int32),
                angular=record_angular,
            )
        if orbitals is not None and (not basis.shells or basis.primitives is None):
            raise QeIncompleteState(
                6, "full-state builder requires shells and a primitive table",
                "MolecularDataBuilder.build")
        matrices = MatrixBundle()
        if self._overlap is not None:
            matrices.S = MatrixRecord(
                data=np.array(self._overlap, copy=True),
                representation="ao_current_basis",
                origin="caller_supplied", derivation="builder overlap", angular=record_angular,
            )
        if self._density_total is not None:
            matrices.P_total = MatrixRecord(
                data=np.array(self._density_total, copy=True),
                representation="ao_current_basis",
                origin="caller_supplied", derivation="builder total density", angular=record_angular,
            )
        if self._density_alpha is not None:
            matrices.P_alpha = MatrixRecord(
                data=np.array(self._density_alpha, copy=True),
                representation="ao_current_basis",
                origin="caller_supplied", derivation="builder alpha density", angular=record_angular,
            )
        if self._density_beta is not None:
            matrices.P_beta = MatrixRecord(
                data=np.array(self._density_beta, copy=True),
                representation="ao_current_basis",
                origin="caller_supplied", derivation="builder beta density", angular=record_angular,
            )
        for name, (data, rep, sym, origin, derivation) in self._extra_matrices.items():
            matrices.extra[name] = MatrixRecord(
                data=np.array(data, copy=True), representation=rep,
                symmetric=sym, origin=origin, derivation=derivation,
                angular=record_angular,
            )
        prov = self.provenance or Provenance(
            source_program="python", source_format="arrays",
            adapter_name="qe_multiwfn.builder",
            adapter_version="1.0.0",
            coordinate_unit_source=self._coordinate_unit,
            conversion_factor=(1.0 if self._coordinate_unit == "bohr" else 1.0 / 0.529177210903),
            normalization_steps=[],
        )
        model = MolecularSystemV1(
            provenance=prov, atoms=Atoms(z=z, symbols=symbols), geometry=geom,
            electronic=electronic, basis=basis,
            wavefunction=Wavefunction(orbitals=orbitals) if orbitals is not None else None,
            matrices=matrices, periodicity=Periodicity(),
            schema_version=self.schema_version,
        )
        if orbitals is not None and matrices.P_total is None and matrices.S is not None:
            Cb = orbitals.coefficients if orbitals.coefficient_layout == "ao_orbital" else orbitals.coefficients.T
            P, Pa, Pb = self._derive_density(model, Cb, orbitals.occupations, orbitals.spin)
            model.matrices.P_total = MatrixRecord(
                data=P, representation="ao_current_basis",
                origin="derived_from_orbitals", derivation="builder density derivation",
                angular=record_angular)
            if Pa is not None:
                model.matrices.P_alpha = MatrixRecord(
                    data=Pa, representation="ao_current_basis",
                    origin="derived_from_orbitals", derivation="builder alpha density derivation",
                    angular=record_angular)
                model.matrices.P_beta = MatrixRecord(
                    data=Pb, representation="ao_current_basis",
                    origin="derived_from_orbitals", derivation="builder beta density derivation",
                    angular=record_angular)
        if self._angular is not None and model.wavefunction is not None:
            model.wavefunction.orbitals.angular = self._angular
        if attach_normalization_metadata:
            self._normalization_metadata(model)
        if (model.wavefunction is not None
                and model.matrices.P_total is None):
            missing = [
                ao.index for ao in model.basis.aos
                if (ao.source_self_overlap is None
                    or ao.contraction_normalization is None
                    or ao.normalization_convention is None)
            ]
            if missing:
                raise QeIncompleteState(
                    6,
                    "full-state builder requires normalization metadata; "
                    f"missing AO indices {missing[:8]}",
                    "MolecularDataBuilder.build",
                )
        if self.schema_version == SCHEMA_VERSION_1_2:
            if model.basis.angular is None:
                raise ValueError("schema 1.2 requires explicit canonical basis angular metadata")
            for sh in model.basis.shells:
                if sh.angular is None:
                    raise ValueError("schema 1.2 requires angular metadata on every shell")
        if validate:
            strict = model.matrices.S is not None and model.matrices.P_total is not None
            model.validate(strict=strict)
        return model


def build_molecular_system(*, atomic_numbers=None, symbols=None, coordinates,
                           coordinate_unit=None, charge=0, multiplicity=1,
                           nelectron=None, wfntype=None, basis=None,
                           overlap=None, density_total=None, density_alpha=None,
                           density_beta=None, coefficients=None, occupations=None,
                           energies=None, spins=None, coefficient_layout="ao_orbital",
                           coefficient_representation="contracted_basis",
                           schema_version=SCHEMA_VERSION_1_1,
                           provenance=None, validate=True) -> MolecularSystemV1:
    """Convenience wrapper around MolecularDataBuilder for NumPy input."""
    builder = MolecularDataBuilder(schema_version=schema_version, provenance=provenance)
    builder.set_geometry(atomic_numbers=atomic_numbers, symbols=symbols,
                         coordinates=coordinates, unit=coordinate_unit)
    builder.set_electronic_state(wfntype=wfntype, charge=charge,
                                  multiplicity=multiplicity, nelectron=nelectron)
    if basis is not None:
        builder.set_basis(basis)
    if overlap is not None:
        builder.set_overlap(overlap)
    if any(x is not None for x in (density_total, density_alpha, density_beta)):
        builder.set_density(total=density_total, alpha=density_alpha, beta=density_beta)
    if coefficients is not None:
        builder.set_orbitals(coefficients, occupations, energies=energies,
                             spins=spins, layout=coefficient_layout,
                             representation=coefficient_representation)
    return builder.build(validate=validate)


from_numpy = build_molecular_system

__all__ = [
    "ShellInput", "BasisInput", "MolecularDataBuilder",
    "build_molecular_system", "from_numpy",
]
