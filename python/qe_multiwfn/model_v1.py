"""
qe_multiwfn.model_v1 — Molecular Data Model 1.0 (canonical, in-memory).

This module is the Python reference implementation of
``docs/MOLECULAR_DATA_MODEL_1.0.md``. It is intentionally independent of
the 0.1.1 ``MolecularSystem`` so that the legacy API keeps working
unchanged, while a richer model can be built incrementally.

Design constraints (see the specification):

- explicit units, index bases, layouts and representations;
- every optional component is actually optional and carries readiness;
- strict validation never relaxes tolerances;
- ``from_legacy`` / ``to_legacy`` provide exact 0.1.1 compatibility.

The module does NOT call Multiwfn, compute integrals, or generate S/P.
It only represents, validates and normalises data.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np

from .molecular import (
    MolecularSystem,
    WFNTYPE_RHF,
    WFNTYPE_NAMES,
    ANGSTROM_TO_BOHR,
    BOHR_TO_ANGSTROM,
)
from .angular import (
    AngularBasisMetadata,
    AngularConvention,
    AngularObjectMetadata,
    AngularTransformRecord,
    AngularUnsupportedError,
    validate_1_2_angular,
)

SCHEMA_VERSION = "1.1.0"
SCHEMA_VERSION_1_1 = "1.1.0"
SCHEMA_VERSION_1_2 = "1.2.0"
SUPPORTED_SCHEMA_VERSIONS = (SCHEMA_VERSION_1_1, SCHEMA_VERSION_1_2)

# ----------------------------------------------------------------------
# Canonical enumerations (strings kept explicit for serialization)
# ----------------------------------------------------------------------
WAVEFUNCTION_TYPES = {
    0: "RHF",
    1: "UHF",
    2: "ROHF",
    3: "R-post-HF",
    4: "U-post-HF",
}

LENGTH_UNITS = ("bohr", "angstrom")
BASIS_REPRESENTATIONS = ("cartesian", "spherical", "mixed", "unspecified")
COEFFICIENT_REPRESENTATIONS = ("contracted_basis", "primitive_gtf")
COEFFICIENT_LAYOUTS = ("orbital_ao", "ao_orbital")
MATRIX_REPRESENTATIONS = ("ao_current_basis", "primitive_gtf", "ao_cartesian")
DENSITY_ORIGINS = ("caller_supplied", "derived_from_orbitals", "post_hf", "unknown")
SPIN_COMPONENTS = ("total", "alpha", "beta", "both")
ECP_EDF_STATUSES = (
    "none",
    "ecp_with_edf",
    "ecp_without_edf",
    "edf_reconstructed",
    "incomplete",
)

NORMALIZATION_CONVENTIONS = (
    "unknown",
    "source_normalized",          # source S/C already normalized
    "cartesian_explicit",         # Cartesian primitive/contraction factors stored
    "cartesian_source_scaled",    # Cartesian source AO self-overlap != 1; scale stored
    "cartesian_source_unnormalized",  # source uses unnormalized primitives
    "mixed",
)

# Tolerance profile 1.0 — strict, never relaxed at runtime.
TOL_ORTHONORM = 1.0e-10
TOL_ELECTRON_COUNT = 1.0e-8
TOL_IDEMPOTENCY_FACTOR = 1.0e-6
TOL_SYMMETRY = 1.0e-10
TOL_SCALE_FLOOR = 1.0

_PERIODIC_TABLE = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]


def symbol_from_z(z: int) -> str:
    if not 1 <= int(z) <= len(_PERIODIC_TABLE):
        raise ValueError(f"atomic number out of range: {z}")
    return _PERIODIC_TABLE[int(z) - 1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _as_int32(a: Iterable[int], name: str) -> np.ndarray:
    arr = np.asarray(a, dtype=np.int32)
    return arr


def _as_float64(a: Iterable[float], name: str, shape: Optional[tuple] = None) -> np.ndarray:
    arr = np.asarray(a, dtype=np.float64)
    if shape is not None and arr.shape != shape:
        raise ValueError(f"{name} shape {arr.shape} != {shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} contains NaN/Inf")
    return arr


def _is_symmetric(a: np.ndarray, tol: float = TOL_SYMMETRY) -> bool:
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        return False
    return bool(np.max(np.abs(a - a.T)) <= tol)


# ----------------------------------------------------------------------
# Provenance
# ----------------------------------------------------------------------
@dataclass
class FileRecord:
    role: str
    relative_path: str
    sha256: str
    size: int = 0
    mtime_utc: str = ""

    def validate(self) -> None:
        if not self.role or not self.relative_path:
            raise ValueError("FileRecord requires role and relative_path")
        if self.sha256 and len(self.sha256) != 64:
            raise ValueError("FileRecord.sha256 must be a SHA-256 hex digest")


@dataclass
class Provenance:
    source_program: str = "python"
    source_version: str = ""
    source_format: str = "arrays"
    input_files: List[FileRecord] = field(default_factory=list)
    created_utc: str = field(default_factory=_utc_now)
    adapter_name: str = "qe_multiwfn.model_v1"
    adapter_version: str = "1.0.0"
    coordinate_unit_source: str = "bohr"
    conversion_factor: float = 1.0
    normalization_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hashes: Dict[str, str] = field(default_factory=dict)
    angular_transforms: List[AngularTransformRecord] = field(default_factory=list)

    def validate(self) -> None:
        if not self.source_program:
            raise ValueError("provenance.source_program is required")
        if not self.source_format:
            raise ValueError("provenance.source_format is required")
        if self.coordinate_unit_source not in LENGTH_UNITS:
            raise ValueError("provenance.coordinate_unit_source must be bohr or angstrom")
        for f in self.input_files:
            f.validate()

    def to_dict(self) -> dict:
        return {
            "source_program": self.source_program,
            "source_version": self.source_version,
            "source_format": self.source_format,
            "input_files": [vars(f) for f in self.input_files],
            "created_utc": self.created_utc,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "coordinate_unit_source": self.coordinate_unit_source,
            "conversion_factor": self.conversion_factor,
            "normalization_steps": list(self.normalization_steps),
            "warnings": list(self.warnings),
            "hashes": dict(self.hashes),
            "angular_transforms": [t.to_dict() for t in self.angular_transforms],
        }


# ----------------------------------------------------------------------
# Atoms / geometry / electronic state
# ----------------------------------------------------------------------
@dataclass
class Atoms:
    z: np.ndarray
    symbols: List[str] = field(default_factory=list)
    nuclear_charge: Optional[np.ndarray] = None
    effective_nuclear_charge: Optional[np.ndarray] = None
    labels: Optional[List[str]] = None
    residue: Optional[np.ndarray] = None
    resname: Optional[List[str]] = None
    ghost: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.z = np.asarray(self.z, dtype=np.int32)
        if self.z.ndim != 1 or self.z.size == 0:
            raise ValueError("atoms.z must be a non-empty 1-D array")
        if np.any(self.z < 1) or np.any(self.z > 118):
            raise ValueError("atoms.z entries must be in [1, 118]")
        if not self.symbols:
            self.symbols = [symbol_from_z(int(z)) for z in self.z]
        if len(self.symbols) != self.z.size:
            raise ValueError("atoms.symbols length must match atoms.z")
        for z, sym in zip(self.z, self.symbols):
            if symbol_from_z(int(z)) != sym:
                raise ValueError(f"atoms.symbols inconsistent with Z={int(z)}: {sym}")
        if self.nuclear_charge is None:
            self.nuclear_charge = self.z.astype(np.float64)
        else:
            self.nuclear_charge = _as_float64(
                self.nuclear_charge, "atoms.nuclear_charge", (self.z.size,)
            )
        if self.effective_nuclear_charge is not None:
            self.effective_nuclear_charge = _as_float64(
                self.effective_nuclear_charge,
                "atoms.effective_nuclear_charge",
                (self.z.size,),
            )
        if self.ghost is not None:
            self.ghost = np.asarray(self.ghost, dtype=bool)
            if self.ghost.shape != (self.z.size,):
                raise ValueError("atoms.ghost shape must match atoms.z")

    @property
    def ncenter(self) -> int:
        return int(self.z.size)


@dataclass
class Geometry:
    coordinates: np.ndarray                 # (ncenter, 3) in Bohr
    unit_internal: str = "bohr"
    unit_source: str = "bohr"
    cell_vectors: Optional[np.ndarray] = None
    cell_vectors_effective: Optional[np.ndarray] = None
    periodic_directions: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.coordinates = _as_float64(self.coordinates, "geometry.coordinates")
        if self.coordinates.ndim != 2 or self.coordinates.shape[1] != 3:
            raise ValueError("geometry.coordinates must have shape (ncenter, 3)")
        if self.unit_internal != "bohr":
            raise ValueError("geometry.unit_internal must be 'bohr'")
        if self.unit_source not in LENGTH_UNITS:
            raise ValueError("geometry.unit_source must be 'bohr' or 'angstrom'")
        if self.cell_vectors is not None:
            self.cell_vectors = _as_float64(
                self.cell_vectors, "geometry.cell_vectors", (3, 3)
            )
        if self.cell_vectors_effective is not None:
            self.cell_vectors_effective = _as_float64(
                self.cell_vectors_effective, "geometry.cell_vectors_effective", (3, 3)
            )
        if self.periodic_directions is not None:
            self.periodic_directions = np.asarray(self.periodic_directions, dtype=bool)
            if self.periodic_directions.shape != (3,):
                raise ValueError("geometry.periodic_directions must have shape (3,)")

    @classmethod
    def from_source(cls, coordinates, unit: str) -> "Geometry":
        coords = _as_float64(coordinates, "coordinates")
        if unit not in LENGTH_UNITS:
            raise ValueError(f"unit must be one of {LENGTH_UNITS}")
        if unit == "angstrom":
            coords = np.ascontiguousarray(coords * ANGSTROM_TO_BOHR)
        return cls(coordinates=coords, unit_internal="bohr", unit_source=unit)


@dataclass
class ElectronicState:
    wfntype: int
    charge: int
    multiplicity: int
    nelectron: int
    naelectron: Optional[int] = None
    nbelectron: Optional[int] = None
    imodwfn: int = 0
    total_energy: Optional[float] = None
    virial_ratio: Optional[float] = None
    ecp_core_electrons: Optional[int] = None

    def __post_init__(self) -> None:
        self.wfntype = int(self.wfntype)
        if self.wfntype not in WAVEFUNCTION_TYPES:
            raise ValueError(f"wfntype must be in {sorted(WAVEFUNCTION_TYPES)}")
        self.charge = int(self.charge)
        self.multiplicity = int(self.multiplicity)
        self.nelectron = int(self.nelectron)
        if self.multiplicity < 1:
            raise ValueError("multiplicity must be >= 1")
        if self.nelectron <= 0:
            raise ValueError("nelectron must be positive")
        if self.wfntype == WFNTYPE_RHF:
            if self.multiplicity != 1:
                raise ValueError("RHF requires multiplicity=1")
            if self.nelectron % 2 != 0:
                raise ValueError("RHF requires an even electron count")
        if self.naelectron is not None:
            self.naelectron = int(self.naelectron)
            if self.naelectron < 0:
                raise ValueError("naelectron must be >= 0")
        if self.nbelectron is not None:
            self.nbelectron = int(self.nbelectron)
            if self.nbelectron < 0:
                raise ValueError("nbelectron must be >= 0")

    def validate_against(self, nuclear_charge_sum: int) -> None:
        expected = int(nuclear_charge_sum) - int(self.charge)
        if expected != self.nelectron:
            raise ValueError(
                f"nelectron={self.nelectron} inconsistent with "
                f"sum(Z)-charge={expected}"
            )
        if self.naelectron is not None and self.nbelectron is not None:
            if self.naelectron + self.nbelectron != self.nelectron:
                raise ValueError("naelectron + nbelectron != nelectron")


# ----------------------------------------------------------------------
# Basis
# ----------------------------------------------------------------------
# Legacy 0.1.1 ``basis_type`` uses angular-momentum codes 0/1/2/3.
# This is NOT the Multiwfn ``bastype`` component code (1=S, 2..4=p, ...).
LEGACY_BASIS_TYPE_ANGULAR = {0: 0, 1: 1, 2: 2, 3: 3}


@dataclass
class Shell:
    index: int
    center: int
    l: int
    shell_type: str
    primitive_start: int
    primitive_end: int
    exponents: np.ndarray
    coefficients: np.ndarray
    normalization: Optional[np.ndarray] = None
    contraction_normalization: Optional[float] = None
    cartesian: bool = True
    spherical: bool = False
    source_label: Optional[str] = None
    multipole: bool = False
    angular: Optional[AngularConvention] = None

    def __post_init__(self) -> None:
        self.index = int(self.index)
        self.center = int(self.center)
        self.l = int(self.l)
        if self.index < 1:
            raise ValueError("shell.index must be 1-based")
        if self.center < 1:
            raise ValueError("shell.center must be 1-based")
        if self.l < 0:
            raise ValueError("shell.l must be >= 0")
        if self.primitive_start < 1 or self.primitive_end < self.primitive_start:
            raise ValueError("shell primitive range is invalid")
        self.exponents = _as_float64(self.exponents, "shell.exponents")
        self.coefficients = _as_float64(self.coefficients, "shell.coefficients")
        if self.exponents.shape != self.coefficients.shape:
            raise ValueError("shell exponents/coefficients shape mismatch")
        if self.exponents.size == 0:
            raise ValueError("shell must contain at least one primitive")
        if np.any(self.exponents <= 0.0):
            raise ValueError("shell exponents must be positive")
        if self.normalization is not None:
            self.normalization = _as_float64(
                self.normalization, "shell.normalization"
            )
            if self.normalization.shape != self.exponents.shape:
                raise ValueError("shell.normalization shape mismatch")
        if bool(self.cartesian) == bool(self.spherical):
            raise ValueError("shell must be either cartesian or spherical")
        if self.contraction_normalization is not None:
            self.contraction_normalization = float(self.contraction_normalization)
        if self.angular is not None:
            if not isinstance(self.angular, AngularConvention):
                raise ValueError("shell.angular must be AngularConvention or None")
            if self.angular.l != self.l:
                raise ValueError("shell.angular.l must equal shell.l")
            if self.l >= 2 and self.spherical and self.angular.representation != "spherical_real":
                raise ValueError("spherical shell requires spherical_real angular metadata")
            if self.l >= 2 and self.cartesian and self.angular.representation != "cartesian":
                raise ValueError("Cartesian shell requires cartesian angular metadata")


@dataclass
class PrimitiveTable:
    center: np.ndarray
    type: np.ndarray
    exponent: np.ndarray
    coefficient: np.ndarray
    normalization: Optional[np.ndarray] = None
    shell_index: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        self.center = np.asarray(self.center, dtype=np.int32)
        self.type = np.asarray(self.type, dtype=np.int32)
        self.exponent = _as_float64(self.exponent, "primitive.exponent")
        self.coefficient = _as_float64(self.coefficient, "primitive.coefficient")
        n = self.center.size
        for name, arr in (
            ("type", self.type),
            ("exponent", self.exponent),
            ("coefficient", self.coefficient),
        ):
            if arr.shape != (n,):
                raise ValueError(f"primitive.{name} shape must be ({n},)")
        if n == 0:
            raise ValueError("primitive table cannot be empty")
        if np.any(self.center < 1):
            raise ValueError("primitive.center must be 1-based")
        if np.any(self.exponent <= 0.0):
            raise ValueError("primitive.exponent must be positive")
        if self.normalization is not None:
            self.normalization = _as_float64(
                self.normalization, "primitive.normalization", (n,)
            )
        if self.shell_index is not None:
            self.shell_index = np.asarray(self.shell_index, dtype=np.int32)
            if self.shell_index.shape != (n,):
                raise ValueError("primitive.shell_index shape mismatch")
            if np.any(self.shell_index < 1):
                raise ValueError("primitive.shell_index must be 1-based")

    @property
    def nprims(self) -> int:
        return int(self.center.size)


@dataclass
class AOFunction:
    index: int
    center: int
    shell_index: Optional[int] = None
    l: Optional[int] = None
    component: Optional[str] = None
    multiwfn_type: Optional[int] = None       # Multiwfn bastype (1=S, 2..4=p, ...)
    angular_type: Optional[int] = None        # 0=s, 1=p, 2=d, 3=f
    legacy_basis_type: Optional[int] = None   # 0.1.1 value (angular code)
    cartesian: Optional[bool] = None
    source_label: Optional[str] = None
    source_index: Optional[int] = None
    contraction_normalization: Optional[float] = None
    source_self_overlap: Optional[float] = None
    normalization_convention: Optional[str] = None

    def __post_init__(self) -> None:
        self.index = int(self.index)
        self.center = int(self.center)
        if self.index < 1:
            raise ValueError("ao.index must be 1-based")
        if self.center < 1:
            raise ValueError("ao.center must be 1-based")
        if self.l is not None and int(self.l) < 0:
            raise ValueError("ao.l must be >= 0")
        if self.shell_index is not None and int(self.shell_index) < 1:
            raise ValueError("ao.shell_index must be 1-based")
        # A legacy AO always carries an angular code; keep the alias coherent.
        if self.legacy_basis_type is None and self.angular_type is not None:
            self.legacy_basis_type = int(self.angular_type)
        if self.angular_type is None and self.legacy_basis_type is not None:
            self.angular_type = int(self.legacy_basis_type)
        if self.source_index is not None and int(self.source_index) < 0:
            raise ValueError("ao.source_index must be >= 0")
        if (self.normalization_convention is not None
                and self.normalization_convention not in NORMALIZATION_CONVENTIONS):
            raise ValueError(
                f"invalid AO normalization_convention: {self.normalization_convention}"
            )
        if self.contraction_normalization is not None:
            self.contraction_normalization = float(self.contraction_normalization)
            if not np.isfinite(self.contraction_normalization) or self.contraction_normalization <= 0:
                raise ValueError("ao.contraction_normalization must be positive and finite")
        if self.source_self_overlap is not None:
            self.source_self_overlap = float(self.source_self_overlap)
            if not np.isfinite(self.source_self_overlap):
                raise ValueError("ao.source_self_overlap must be finite")


@dataclass
class BasisSet:
    nbasis: int
    nprims: int
    nindbasis: Optional[int] = None
    nbasis_cartesian: Optional[int] = None
    nbasis_spherical: Optional[int] = None
    representation: str = "unspecified"
    normalization_convention: str = "unknown"
    ao_order: str = "source"
    shells: List[Shell] = field(default_factory=list)
    primitives: Optional[PrimitiveTable] = None
    aos: List[AOFunction] = field(default_factory=list)
    angular: Optional[AngularBasisMetadata] = None

    def __post_init__(self) -> None:
        self.nbasis = int(self.nbasis)
        self.nprims = int(self.nprims)
        if self.nbasis < 1:
            raise ValueError("basis.nbasis must be >= 1")
        if self.nprims < self.nbasis:
            raise ValueError("basis.nprims must be >= basis.nbasis")
        if self.representation not in BASIS_REPRESENTATIONS:
            raise ValueError(
                f"basis.representation must be one of {BASIS_REPRESENTATIONS}"
            )
        if self.normalization_convention not in NORMALIZATION_CONVENTIONS:
            raise ValueError(
                f"basis.normalization_convention must be one of "
                f"{NORMALIZATION_CONVENTIONS}"
            )
        if self.aos:
            if len(self.aos) != self.nbasis:
                raise ValueError("basis.aos length must equal basis.nbasis")
            for i, ao in enumerate(self.aos, start=1):
                if ao.index != i:
                    raise ValueError("basis.aos indexes must be 1..nbasis in order")
        if self.primitives is not None:
            if self.primitives.nprims != self.nprims:
                raise ValueError("primitive table size does not match basis.nprims")
        if self.shells:
            for sh in self.shells:
                if sh.primitive_end > self.nprims:
                    raise ValueError("shell primitive range exceeds nprims")
        if self.angular is not None and not isinstance(self.angular, AngularBasisMetadata):
            raise ValueError("basis.angular must be AngularBasisMetadata or None")

    def center_array(self) -> np.ndarray:
        if not self.aos:
            raise ValueError("basis.aos is empty; center mapping unavailable")
        return np.array([ao.center for ao in self.aos], dtype=np.int32)

    def angular_type_array(self) -> np.ndarray:
        if not self.aos:
            raise ValueError("basis.aos is empty; angular mapping unavailable")
        out = []
        for ao in self.aos:
            if ao.angular_type is None:
                raise ValueError("AO is missing angular_type")
            out.append(ao.angular_type)
        return np.array(out, dtype=np.int32)

    def contiguity_ok(self) -> bool:
        centers = self.center_array()
        seen = set()
        prev = None
        for c in centers:
            if c != prev:
                if c in seen:
                    return False
                seen.add(c)
            prev = c
        return True

    @classmethod
    def from_legacy(
        cls, nbasis: int, nprims: int, basis_center: np.ndarray, basis_type: np.ndarray
    ) -> "BasisSet":
        bc = np.asarray(basis_center, dtype=np.int32)
        bt = np.asarray(basis_type, dtype=np.int32)
        if bc.shape != (nbasis,) or bt.shape != (nbasis,):
            raise ValueError("legacy basis_center/basis_type must have length nbasis")
        aos = [
            AOFunction(
                index=i + 1,
                center=int(bc[i]),
                angular_type=int(bt[i]),
                legacy_basis_type=int(bt[i]),
                multiwfn_type=None,
                component=None,
                shell_index=None,
                cartesian=None,
            )
            for i in range(nbasis)
        ]
        return cls(
            nbasis=nbasis,
            nprims=nprims,
            representation="unspecified",
            ao_order="source",
            aos=aos,
        )


# ----------------------------------------------------------------------
# Wavefunction / matrices
# ----------------------------------------------------------------------
@dataclass
class OrbitalSet:
    coefficients: np.ndarray
    coefficient_representation: str
    coefficient_layout: str
    energies: np.ndarray
    occupations: np.ndarray
    spin: List[str]
    symmetry_labels: Optional[List[str]] = None
    orbital_indices: Optional[np.ndarray] = None
    homo_index: Optional[int] = None
    lumo_index: Optional[int] = None
    nocc: Optional[int] = None
    angular: Optional[AngularObjectMetadata] = None

    def __post_init__(self) -> None:
        self.coefficients = _as_float64(self.coefficients, "orbitals.coefficients")
        if self.coefficient_representation not in COEFFICIENT_REPRESENTATIONS:
            raise ValueError(
                "coefficient_representation must be one of "
                f"{COEFFICIENT_REPRESENTATIONS}"
            )
        if self.coefficient_layout not in COEFFICIENT_LAYOUTS:
            raise ValueError(
                f"coefficient_layout must be one of {COEFFICIENT_LAYOUTS}"
            )
        self.energies = _as_float64(self.energies, "orbitals.energies")
        self.occupations = _as_float64(self.occupations, "orbitals.occupations")
        if self.energies.ndim != 1 or self.occupations.ndim != 1:
            raise ValueError("energies/occupations must be 1-D")
        nmo = self.energies.size
        if self.occupations.size != nmo:
            raise ValueError("occupations length must match energies")
        if np.any(self.occupations < 0.0):
            raise ValueError("occupations must be >= 0")
        if len(self.spin) != nmo:
            raise ValueError("spin list length must match number of orbitals")
        for s in self.spin:
            if s not in SPIN_COMPONENTS:
                raise ValueError(f"invalid spin component: {s}")
        # Accept either orientation only if it matches the declared layout.
        if self.coefficient_layout == "orbital_ao":
            if self.coefficients.shape[0] != nmo:
                raise ValueError(
                    "coefficients layout 'orbital_ao' requires shape (nmo, nao)"
                )
        else:
            if self.coefficients.shape[1] != nmo:
                raise ValueError(
                    "coefficients layout 'ao_orbital' requires shape (nao, nmo)"
                )
        if self.orbital_indices is None:
            self.orbital_indices = np.arange(1, nmo + 1, dtype=np.int32)
        else:
            self.orbital_indices = np.asarray(self.orbital_indices, dtype=np.int32)
        if self.angular is not None and not isinstance(self.angular, AngularObjectMetadata):
            raise ValueError("orbitals.angular must be AngularObjectMetadata or None")

    @property
    def nmo(self) -> int:
        return int(self.energies.size)

    @property
    def has_alpha_beta(self) -> bool:
        return any(s in ("alpha", "beta") for s in self.spin)


@dataclass
class Wavefunction:
    orbitals: OrbitalSet
    total_energy: Optional[float] = None


@dataclass
class MatrixRecord:
    data: np.ndarray
    representation: str
    layout: str = "ao_ao"
    symmetric: bool = True
    origin: str = "caller_supplied"
    derivation: str = ""
    tolerance_profile: str = "model_v1_strict"
    sha256: str = ""
    angular: Optional[AngularObjectMetadata] = None

    def __post_init__(self) -> None:
        self.data = _as_float64(self.data, "matrix.data")
        if self.data.ndim != 2 or self.data.shape[0] != self.data.shape[1]:
            raise ValueError("matrix must be square")
        if self.representation not in MATRIX_REPRESENTATIONS:
            raise ValueError(
                f"matrix representation must be one of {MATRIX_REPRESENTATIONS}"
            )
        if self.origin not in DENSITY_ORIGINS and self.origin != "reconstructed":
            raise ValueError(f"invalid matrix origin: {self.origin}")
        if not self.sha256:
            self.sha256 = _sha256_array(self.data)
        if self.angular is not None and not isinstance(self.angular, AngularObjectMetadata):
            raise ValueError("matrix.angular must be AngularObjectMetadata or None")


@dataclass
class MatrixBundle:
    S: Optional[MatrixRecord] = None
    P_total: Optional[MatrixRecord] = None
    P_alpha: Optional[MatrixRecord] = None
    P_beta: Optional[MatrixRecord] = None
    P_total_prim: Optional[MatrixRecord] = None
    extra: Dict[str, MatrixRecord] = field(default_factory=dict)


@dataclass
class CoreCorrection:
    status: str = "none"
    ecp_elements: List[int] = field(default_factory=list)
    effective_nuclear_charges: Optional[np.ndarray] = None
    core_electrons_per_atom: Optional[np.ndarray] = None
    core_electron_count: int = 0
    edf_primitives: Optional[PrimitiveTable] = None
    edf_coefficients: Optional[np.ndarray] = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.status not in ECP_EDF_STATUSES:
            raise ValueError(f"invalid ECP/EDF status: {self.status}")
        if self.effective_nuclear_charges is not None:
            self.effective_nuclear_charges = _as_float64(
                self.effective_nuclear_charges, "core_correction.effective_nuclear_charges"
            )
        if self.core_electrons_per_atom is not None:
            self.core_electrons_per_atom = np.asarray(
                self.core_electrons_per_atom, dtype=np.int32
            )
        if self.edf_coefficients is not None:
            self.edf_coefficients = _as_float64(
                self.edf_coefficients, "core_correction.edf_coefficients"
            )


@dataclass
class Periodicity:
    ifPBC: int = 0
    directions: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=bool))
    cell_vectors: Optional[np.ndarray] = None
    cell_vectors_effective: Optional[np.ndarray] = None
    neighbor_cells: Optional[np.ndarray] = None
    overlap_pbc: Optional[MatrixRecord] = None

    def __post_init__(self) -> None:
        self.ifPBC = int(self.ifPBC)
        if self.ifPBC not in (0, 1, 2, 3):
            raise ValueError("ifPBC must be 0..3")
        self.directions = np.asarray(self.directions, dtype=bool)
        if self.directions.shape != (3,):
            raise ValueError("periodicity.directions must have shape (3,)")
        if self.cell_vectors is not None:
            self.cell_vectors = _as_float64(
                self.cell_vectors, "periodicity.cell_vectors", (3, 3)
            )
        if self.cell_vectors_effective is not None:
            self.cell_vectors_effective = _as_float64(
                self.cell_vectors_effective,
                "periodicity.cell_vectors_effective",
                (3, 3),
            )
        if self.neighbor_cells is not None:
            self.neighbor_cells = np.asarray(self.neighbor_cells, dtype=np.int32)


@dataclass
class ReadinessFlags:
    geometry_ready: bool = False
    basis_ready: bool = False
    wavefunction_ready: bool = False
    density_ready: bool = False
    overlap_ready: bool = False
    ecp_ready: bool = False
    integrals_ready: bool = False
    analysis_ready: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "geometry_ready": self.geometry_ready,
            "basis_ready": self.basis_ready,
            "wavefunction_ready": self.wavefunction_ready,
            "density_ready": self.density_ready,
            "overlap_ready": self.overlap_ready,
            "ecp_ready": self.ecp_ready,
            "integrals_ready": self.integrals_ready,
            "analysis_ready": dict(self.analysis_ready),
        }


# ----------------------------------------------------------------------
# Root model
# ----------------------------------------------------------------------
@dataclass
class MolecularSystemV1:
    provenance: Provenance
    atoms: Atoms
    geometry: Geometry
    electronic: ElectronicState
    basis: BasisSet
    wavefunction: Optional[Wavefunction] = None
    matrices: MatrixBundle = field(default_factory=MatrixBundle)
    core_correction: Optional[CoreCorrection] = None
    periodicity: Periodicity = field(default_factory=Periodicity)
    schema_version: str = SCHEMA_VERSION
    legacy: bool = False
    readiness: ReadinessFlags = field(default_factory=ReadinessFlags, init=False)

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"unsupported schema_version {self.schema_version!r}; "
                f"expected one of {SUPPORTED_SCHEMA_VERSIONS}"
            )
        self.validate(strict=False)

    @property
    def ncenter(self) -> int:
        return self.atoms.ncenter

    @property
    def nbasis(self) -> int:
        return self.basis.nbasis

    @property
    def nprims(self) -> int:
        return self.basis.nprims

    # ------------------------------------------------------------------
    def compute_readiness(self) -> ReadinessFlags:
        r = ReadinessFlags()
        r.geometry_ready = (
            self.atoms.z.size > 0
            and self.geometry.coordinates.shape == (self.atoms.z.size, 3)
        )
        r.basis_ready = (
            self.basis.nbasis >= 1
            and bool(self.basis.aos)
            and self._ao_centers_valid()
        )
        r.wavefunction_ready = self.wavefunction is not None
        r.overlap_ready = self.matrices.S is not None
        r.density_ready = (
            self.matrices.P_total is not None
            and (self.electronic.wfntype == 0
                 or (self.matrices.P_alpha is not None
                     and self.matrices.P_beta is not None))
        )
        r.ecp_ready = (
            self.core_correction is None
            or self.core_correction.status in ("none", "ecp_with_edf")
        )
        r.analysis_ready["mayer"] = (
            r.geometry_ready
            and r.basis_ready
            and r.density_ready
            and r.overlap_ready
            and self.periodicity.ifPBC == 0
            and self.electronic.wfntype in (0, 1, 2)
        )
        return r

    def _ao_centers_valid(self) -> bool:
        try:
            centers = self.basis.center_array()
        except ValueError:
            return False
        if centers.size != self.nbasis:
            return False
        return bool(np.all(centers >= 1) and np.all(centers <= self.ncenter))

    # ------------------------------------------------------------------
    def validate(self, strict: bool = False) -> None:
        self.provenance.validate()
        if self.atoms.ncenter != self.geometry.coordinates.shape[0]:
            raise ValueError(
                "atoms.z length does not match geometry.coordinates rows"
            )
        if self.core_correction is None or self.core_correction.status == "none":
            self.electronic.validate_against(int(np.sum(self.atoms.z)))
        else:
            # With ECP/EDF the wavefunction Ne is not derived from Z alone.
            # Only the intrinsic consistency (alpha+beta) is enforced here.
            if (self.electronic.naelectron is not None
                    and self.electronic.nbelectron is not None
                    and self.electronic.naelectron + self.electronic.nbelectron
                    != self.electronic.nelectron):
                raise ValueError("naelectron + nbelectron != nelectron")
        if self.basis.aos:
            centers = self.basis.center_array()
            if centers.min() < 1 or centers.max() > self.ncenter:
                raise ValueError("basis AO center out of range")
            for ao in self.basis.aos:
                if ao.angular_type is None:
                    raise ValueError("every AO must declare angular_type")
        if self.basis.primitives is not None:
            if self.basis.primitives.center.max() > self.ncenter:
                raise ValueError("primitive center out of range")
            if np.any(self.basis.primitives.center < 1):
                raise ValueError("primitive center must be 1-based")
        if self.periodicity.ifPBC > 0 and self.periodicity.cell_vectors is None:
            raise ValueError("periodic system requires cell_vectors")

        for rec_name in ("S", "P_total", "P_alpha", "P_beta"):
            rec = getattr(self.matrices, rec_name)
            if rec is None:
                continue
            if rec.data.shape != (self.nbasis, self.nbasis):
                raise ValueError(
                    f"{rec_name} shape {rec.data.shape} != "
                    f"({self.nbasis}, {self.nbasis})"
                )
            if rec.symmetric and not _is_symmetric(rec.data):
                raise ValueError(f"{rec_name} is not symmetric")

        self.readiness = self.compute_readiness()
        validate_1_2_angular(self)

        if not strict:
            return

        if self.matrices.S is None:
            raise ValueError("strict validation requires matrices.S")
        if self.matrices.P_total is None:
            raise ValueError("strict validation requires matrices.P_total")
        S = self.matrices.S.data
        P = self.matrices.P_total.data
        if self.matrices.S.representation != "ao_current_basis":
            raise ValueError("S must be represented in ao_current_basis")
        if self.matrices.P_total.representation != "ao_current_basis":
            raise ValueError("P_total must be represented in ao_current_basis")

        trPS = float(np.trace(P @ S))
        ne = float(self.electronic.nelectron)
        if abs(trPS - ne) > TOL_ELECTRON_COUNT:
            raise ValueError(
                f"Tr(P*S)={trPS:.15g} does not match Ne={ne:.15g} "
                f"(tol={TOL_ELECTRON_COUNT})"
            )
        if self.electronic.wfntype == WFNTYPE_RHF:
            scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(2.0 * P))))
            err = float(np.max(np.abs(P @ S @ P - 2.0 * P)))
            if err > TOL_IDEMPOTENCY_FACTOR * scale:
                raise ValueError(
                    f"PSP-2P error {err:.3e} exceeds "
                    f"{TOL_IDEMPOTENCY_FACTOR * scale:.3e}"
                )
        if self.wavefunction is not None:
            orb = self.wavefunction.orbitals
            if orb.coefficient_layout == "ao_orbital":
                Cb = orb.coefficients          # (nbasis, nmo)
            else:
                Cb = orb.coefficients.T        # (nbasis, nmo)
            if Cb.shape[0] == self.nbasis:
                groups: Dict[str, List[int]] = {}
                for i, spin in enumerate(orb.spin):
                    key = "all" if spin == "both" else spin
                    groups.setdefault(key, []).append(i)
                for key, idxs in groups.items():
                    Cg = Cb[:, idxs]
                    if Cg.shape[1] == 0:
                        continue
                    err = float(np.max(np.abs(Cg.T @ S @ Cg - np.eye(Cg.shape[1]))))
                    if err > TOL_ORTHONORM:
                        raise ValueError(
                            f"C^T S C orthonormality error ({key}) {err:.3e} "
                            f"exceeds {TOL_ORTHONORM}"
                        )

        if self.electronic.wfntype in (1, 2, 4):
            if self.matrices.P_alpha is None or self.matrices.P_beta is None:
                raise ValueError(
                    "spin-resolved wavefunction requires P_alpha and P_beta"
                )
            Pa = self.matrices.P_alpha.data
            Pb = self.matrices.P_beta.data
            na = self.electronic.naelectron
            nb = self.electronic.nbelectron
            if na is None or nb is None:
                na = (self.electronic.nelectron
                      + self.electronic.multiplicity - 1) // 2
                nb = self.electronic.nelectron - na
            tr_a = float(np.trace(Pa @ S))
            tr_b = float(np.trace(Pb @ S))
            if abs(tr_a - na) > TOL_ELECTRON_COUNT:
                raise ValueError(
                    f"Tr(P_alpha*S)={tr_a:.12g} != N_alpha={na}"
                )
            if abs(tr_b - nb) > TOL_ELECTRON_COUNT:
                raise ValueError(
                    f"Tr(P_beta*S)={tr_b:.12g} != N_beta={nb}"
                )
            if np.max(np.abs(P - (Pa + Pb))) > 1e-10:
                raise ValueError("P_total must equal P_alpha + P_beta")
            if self.electronic.wfntype in (1, 2):
                for label, Ps in (("alpha", Pa), ("beta", Pb)):
                    scale = max(TOL_SCALE_FLOOR,
                                float(np.max(np.abs(Ps))))
                    err = float(np.max(np.abs(Ps @ S @ Ps - Ps)))
                    if err > TOL_IDEMPOTENCY_FACTOR * scale:
                        raise ValueError(
                            f"UHF {label} density is not idempotent: "
                            f"error {err:.3e}"
                        )

    # ------------------------------------------------------------------
    # 0.1.1 compatibility
    # ------------------------------------------------------------------
    @classmethod
    def from_legacy(
        cls, ms: MolecularSystem, *, strict: bool = True
    ) -> "MolecularSystemV1":
        if not isinstance(ms, MolecularSystem):
            raise TypeError("from_legacy expects a MolecularSystem")
        atoms = Atoms(z=np.asarray(ms.atomic_numbers, dtype=np.int32))
        geometry = Geometry(
            coordinates=np.asarray(ms.coordinates, dtype=np.float64).copy(),
            unit_internal="bohr",
            unit_source="bohr",
        )
        electronic = ElectronicState(
            wfntype=int(ms.wfntype),
            charge=int(ms.charge),
            multiplicity=int(ms.multiplicity),
            nelectron=int(ms.nelectron),
        )
        basis = BasisSet.from_legacy(
            nbasis=int(ms.nbasis),
            nprims=int(ms.nprims),
            basis_center=np.asarray(ms.basis_center, dtype=np.int32),
            basis_type=np.asarray(ms.basis_type, dtype=np.int32),
        )
        S = MatrixRecord(
            data=np.asarray(ms.overlap, dtype=np.float64).copy(),
            representation="ao_current_basis",
            origin="caller_supplied",
            derivation="legacy MolecularSystem.overlap",
        )
        P = MatrixRecord(
            data=np.asarray(ms.density_total, dtype=np.float64).copy(),
            representation="ao_current_basis",
            origin="caller_supplied",
            derivation="legacy MolecularSystem.density_total",
        )
        prov = Provenance(
            source_program=ms.source_program or "python",
            source_version="0.1.1",
            source_format=ms.source_format or "arrays",
            coordinate_unit_source="bohr",
            conversion_factor=1.0,
            normalization_steps=["legacy->v1 (no conversion)"],
            hashes={
                "S": S.sha256,
                "P_total": P.sha256,
                "coordinates": _sha256_array(geometry.coordinates),
            },
        )
        model = cls(
            provenance=prov,
            atoms=atoms,
            geometry=geometry,
            electronic=electronic,
            basis=basis,
            matrices=MatrixBundle(S=S, P_total=P),
            periodicity=Periodicity(),
            legacy=True,
        )
        model.validate(strict=strict)
        return model

    def legacy_blockers(self) -> List[str]:
        blockers: List[str] = []
        if self.schema_version == SCHEMA_VERSION_1_2:
            blockers.append("schema 1.2 angular metadata is not representable in 0.1.1")
        if self.electronic.wfntype != WFNTYPE_RHF:
            blockers.append("0.1.1 supports only RHF (wfntype=0)")
        if self.electronic.multiplicity != 1:
            blockers.append("0.1.1 requires multiplicity=1")
        if self.electronic.nelectron <= 0 or self.electronic.nelectron % 2:
            blockers.append("0.1.1 requires a positive even electron count")
        if self.periodicity.ifPBC != 0:
            blockers.append("0.1.1 Mayer path rejects periodic systems (ifPBC>0)")
        if self.core_correction is not None and self.core_correction.status != "none":
            blockers.append("ECP/EDF metadata cannot be represented in 0.1.1")
        if self.matrices.S is None:
            blockers.append("missing matrices.S")
        if self.matrices.P_total is None:
            blockers.append("missing matrices.P_total")
        if not self.basis.aos:
            blockers.append("missing AO mapping (basis.aos)")
        if self.basis.aos:
            for ao in self.basis.aos:
                if ao.angular_type is None:
                    blockers.append("AO without angular_type")
                    break
            if not self.basis.contiguity_ok():
                blockers.append(
                    "basis functions per atom are not contiguous; "
                    "reorder AOs before to_legacy()"
                )
        if self.matrices.S is not None and self.matrices.S.representation != "ao_current_basis":
            blockers.append("S is not in ao_current_basis")
        if self.matrices.P_total is not None and self.matrices.P_total.representation != "ao_current_basis":
            blockers.append("P_total is not in ao_current_basis")
        return blockers

    def is_legacy_representable(self) -> bool:
        return not self.legacy_blockers()

    def to_legacy(self) -> MolecularSystem:
        blockers = self.legacy_blockers()
        if blockers:
            raise ValueError(
                "state is not representable as MolecularSystem 0.1.1: "
                + "; ".join(blockers)
            )
        bc = self.basis.center_array()
        bt = self.basis.angular_type_array()
        return MolecularSystem.from_arrays(
            atomic_numbers=np.asarray(self.atoms.z, dtype=np.int32),
            coordinates=np.asarray(self.geometry.coordinates, dtype=np.float64),
            basis_center=bc,
            basis_type=bt,
            density_total=self.matrices.P_total.data,
            overlap=self.matrices.S.data,
            wfntype=int(self.electronic.wfntype),
            charge=int(self.electronic.charge),
            multiplicity=int(self.electronic.multiplicity),
            nelectron=int(self.electronic.nelectron),
            nprims=int(self.basis.nprims),
            coordinates_unit="bohr",
        )

    # ------------------------------------------------------------------
    # AO permutation (normalisation helper, no scientific math)
    # ------------------------------------------------------------------
    def with_ao_order(self, order: Sequence[int]) -> "MolecularSystemV1":
        """Return a copy with AOs permuted by ``order`` (0-based old indices).

        The same permutation is applied to S, P_total, P_alpha, P_beta,
        the AO list and the wavefunction coefficients. Shells/primitives are
        not touched (they are primitive-level data).
        """
        if self.schema_version == SCHEMA_VERSION_1_2:
            raise ValueError("with_ao_order is not supported for schema 1.2 angular metadata")
        order = list(order)
        if sorted(order) != list(range(self.nbasis)):
            raise ValueError("order must be a permutation of 0..nbasis-1")
        idx = np.array(order, dtype=int)
        matrices = MatrixBundle(
            S=_permute_matrix(self.matrices.S, idx),
            P_total=_permute_matrix(self.matrices.P_total, idx),
            P_alpha=_permute_matrix(self.matrices.P_alpha, idx),
            P_beta=_permute_matrix(self.matrices.P_beta, idx),
            P_total_prim=self.matrices.P_total_prim,
            extra=dict(self.matrices.extra),
        )
        wavefunction = None
        if self.wavefunction is not None:
            orb = self.wavefunction.orbitals
            if orb.coefficient_layout == "orbital_ao":
                coeff = orb.coefficients[:, idx]
            else:
                coeff = orb.coefficients[idx, :]
            new_orbitals = OrbitalSet(
                coefficients=np.ascontiguousarray(coeff),
                coefficient_representation=orb.coefficient_representation,
                coefficient_layout=orb.coefficient_layout,
                energies=orb.energies,
                occupations=orb.occupations,
                spin=list(orb.spin),
                symmetry_labels=orb.symmetry_labels,
                orbital_indices=orb.orbital_indices,
                homo_index=orb.homo_index,
                lumo_index=orb.lumo_index,
                nocc=orb.nocc,
            )
            wavefunction = Wavefunction(
                orbitals=new_orbitals, total_energy=self.wavefunction.total_energy
            )
        new_aos = []
        for new_index, old_i in enumerate(idx, start=1):
            new_aos.append(replace(self.basis.aos[int(old_i)], index=new_index))
        basis = BasisSet(
            nbasis=self.basis.nbasis,
            nprims=self.basis.nprims,
            nindbasis=self.basis.nindbasis,
            nbasis_cartesian=self.basis.nbasis_cartesian,
            nbasis_spherical=self.basis.nbasis_spherical,
            representation=self.basis.representation,
            ao_order="permuted",
            shells=list(self.basis.shells),
            primitives=self.basis.primitives,
            aos=new_aos,
        )
        prov = replace(
            self.provenance,
            input_files=[replace(f) for f in self.provenance.input_files],
            normalization_steps=list(self.provenance.normalization_steps)
            + ["permute_ao_order"],
        )
        model = MolecularSystemV1(
            provenance=prov,
            atoms=self.atoms,
            geometry=self.geometry,
            electronic=self.electronic,
            basis=basis,
            wavefunction=wavefunction,
            matrices=matrices,
            core_correction=self.core_correction,
            periodicity=self.periodicity,
            legacy=self.legacy,
        )
        model.validate(strict=False)
        return model

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "legacy": self.legacy,
            "ncenter": self.ncenter,
            "nbasis": self.nbasis,
            "nprims": self.nprims,
            "wfntype": self.electronic.wfntype,
            "charge": self.electronic.charge,
            "multiplicity": self.electronic.multiplicity,
            "nelectron": self.electronic.nelectron,
            "basis_representation": self.basis.representation,
            "normalization_convention": self.basis.normalization_convention,
            "ao_order": self.basis.ao_order,
            "angular": {
                "basis": self.basis.angular.to_dict() if self.basis.angular is not None else None,
                "shells": {
                    str(sh.index): sh.angular.to_dict()
                    for sh in self.basis.shells if sh.angular is not None
                },
                "orbitals": (self.wavefunction.orbitals.angular.to_dict()
                             if self.wavefunction is not None
                             and self.wavefunction.orbitals.angular is not None else None),
                "matrices": {
                    name: getattr(self.matrices, name).angular.to_dict()
                    for name in ("S", "P_total", "P_alpha", "P_beta")
                    if getattr(self.matrices, name) is not None
                    and getattr(self.matrices, name).angular is not None
                },
            },
            "has_wavefunction": self.wavefunction is not None,
            "has_S": self.matrices.S is not None,
            "has_P_total": self.matrices.P_total is not None,
            "ifPBC": self.periodicity.ifPBC,
            "readiness": self.readiness.to_dict(),
            "provenance": self.provenance.to_dict(),
        }


def _permute_matrix(rec: Optional[MatrixRecord], idx: np.ndarray) -> Optional[MatrixRecord]:
    if rec is None:
        return None
    return MatrixRecord(
        data=np.ascontiguousarray(rec.data[np.ix_(idx, idx)]),
        representation=rec.representation,
        layout=rec.layout,
        symmetric=rec.symmetric,
        origin=rec.origin,
        derivation=rec.derivation + " + ao_permutation",
        tolerance_profile=rec.tolerance_profile,
    )


def derive_rhf_density(model: MolecularSystemV1, *, overwrite: bool = False) -> MolecularSystemV1:
    """Derive an RHF density matrix from orbital coefficients (adapter-side).

    This is a documented *data preparation* step, not a replacement for the
    Multiwfn scientific routines. It is used by external adapters when the
    source provides C/occupations but not P.

    Rules:
      - closed-shell RHF only;
      - occupied orbitals must be doubly occupied (2.0 each);
      - P = 2 * C_occ C_occ^T in the ao_current_basis representation;
      - Tr(P*S)=Ne and P*S*P=2P are verified with the strict profile.
    """
    if model.electronic.wfntype != WFNTYPE_RHF:
        raise ValueError("derive_rhf_density requires closed-shell RHF")
    if model.wavefunction is None:
        raise ValueError("derive_rhf_density requires wavefunction coefficients")
    if model.matrices.S is None:
        raise ValueError("derive_rhf_density requires matrices.S")
    if model.matrices.P_total is not None and not overwrite:
        return model

    orb = model.wavefunction.orbitals
    C = orb.coefficients
    if orb.coefficient_layout == "ao_orbital":
        Cb = C
    else:
        Cb = C.T
    if Cb.shape[0] != model.nbasis:
        raise ValueError("coefficients do not span nbasis")
    occ = orb.occupations
    occupied = occ > 1e-8
    if np.any(occ[occupied] <= 0.0):
        raise ValueError("invalid occupations")
    if not np.allclose(occ[occupied], 2.0, atol=1e-8, rtol=0.0):
        raise ValueError(
            "derive_rhf_density only supports doubly occupied RHF orbitals"
        )
    Cocc = Cb[:, occupied]
    P = 2.0 * (Cocc @ Cocc.T)

    S = model.matrices.S.data
    trps = float(np.trace(P @ S))
    if abs(trps - float(model.electronic.nelectron)) > TOL_ELECTRON_COUNT:
        raise ValueError(
            f"derived P has Tr(P*S)={trps:.12g}, expected Ne={model.electronic.nelectron}"
        )
    scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(2.0 * P))))
    err = float(np.max(np.abs(P @ S @ P - 2.0 * P)))
    if err > TOL_IDEMPOTENCY_FACTOR * scale:
        raise ValueError(f"derived P is not RHF-idempotent: {err:.3e}")

    rec = MatrixRecord(
        data=P,
        representation="ao_current_basis",
        origin="derived_from_orbitals",
        derivation="P = 2 * C_occ C_occ^T (RHF, adapter-side)",
    )
    matrices = replace(model.matrices, P_total=rec)
    hashes = dict(model.provenance.hashes)
    hashes["P_total"] = rec.sha256
    prov = replace(
        model.provenance,
        hashes=hashes,
        normalization_steps=list(model.provenance.normalization_steps)
        + ["derive P = 2 * C_occ C_occ^T"],
    )
    out = replace(model, matrices=matrices, provenance=prov)
    out.validate(strict=True)
    return out


def wavefunction_report(model: MolecularSystemV1) -> dict:
    """Independent PASS/FAIL/INCOMPLETE report for the wavefunction data."""
    report: Dict[str, Any] = {}

    def add(name, value, limit, detail=""):
        report[name] = {
            "value": None if value is None else float(value),
            "limit": float(limit),
            "passed": None if value is None else bool(value <= limit),
            "detail": detail,
        }

    S = None if model.matrices.S is None else model.matrices.S.data
    P = None if model.matrices.P_total is None else model.matrices.P_total.data

    # symmetry
    if P is not None:
        add("symmetry_P", float(np.max(np.abs(P - P.T))), TOL_SYMMETRY)
    else:
        add("symmetry_P", None, TOL_SYMMETRY, "P missing")
    if S is not None:
        add("symmetry_S", float(np.max(np.abs(S - S.T))), TOL_SYMMETRY)
    else:
        add("symmetry_S", None, TOL_SYMMETRY, "S missing")

    # positivity of S
    if S is not None:
        mn = float(np.linalg.eigvalsh(S).min())
        report["positivity_S"] = {
            "value": mn, "limit": 0.0, "passed": bool(mn > 0.0),
            "detail": "minimum eigenvalue of S",
        }
    else:
        add("positivity_S", None, 0.0, "S missing")

    # electron count and idempotency
    if P is not None and S is not None:
        add("electron_count_TrPS",
            abs(float(np.trace(P @ S)) - float(model.electronic.nelectron)),
            TOL_ELECTRON_COUNT)
        if model.electronic.wfntype == WFNTYPE_RHF:
            scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(2.0 * P))))
            add("idempotency_PSP",
                float(np.max(np.abs(P @ S @ P - 2.0 * P))),
                TOL_IDEMPOTENCY_FACTOR * scale)
    else:
        add("electron_count_TrPS", None, TOL_ELECTRON_COUNT, "P/S missing")
        if model.electronic.wfntype == WFNTYPE_RHF:
            add("idempotency_PSP", None, TOL_IDEMPOTENCY_FACTOR, "P/S missing")

    # spin-resolved checks (UHF/ROHF/post-HF)
    if model.electronic.wfntype in (1, 2, 4):
        Pa = None if model.matrices.P_alpha is None else model.matrices.P_alpha.data
        Pb = None if model.matrices.P_beta is None else model.matrices.P_beta.data
        na = model.electronic.naelectron
        nb = model.electronic.nbelectron
        if na is None or nb is None:
            na = (model.electronic.nelectron
                  + model.electronic.multiplicity - 1) // 2
            nb = model.electronic.nelectron - na
        if Pa is not None and S is not None:
            add("electron_count_TrPS_alpha",
                abs(float(np.trace(Pa @ S)) - float(na)), TOL_ELECTRON_COUNT)
            if model.electronic.wfntype in (1, 2):
                scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(Pa))))
                add("idempotency_PSP_alpha",
                    float(np.max(np.abs(Pa @ S @ Pa - Pa))),
                    TOL_IDEMPOTENCY_FACTOR * scale)
        else:
            add("electron_count_TrPS_alpha", None, TOL_ELECTRON_COUNT,
                "P_alpha missing")
        if Pb is not None and S is not None:
            add("electron_count_TrPS_beta",
                abs(float(np.trace(Pb @ S)) - float(nb)), TOL_ELECTRON_COUNT)
            if model.electronic.wfntype in (1, 2):
                scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(Pb))))
                add("idempotency_PSP_beta",
                    float(np.max(np.abs(Pb @ S @ Pb - Pb))),
                    TOL_IDEMPOTENCY_FACTOR * scale)
        else:
            add("electron_count_TrPS_beta", None, TOL_ELECTRON_COUNT,
                "P_beta missing")
        if P is not None and Pa is not None and Pb is not None:
            add("total_vs_spin_sum",
                float(np.max(np.abs(P - (Pa + Pb)))), 1e-10)

    # orthonormality, grouped by spin
    if model.wavefunction is not None and S is not None:
        orb = model.wavefunction.orbitals
        Cb = orb.coefficients if orb.coefficient_layout == "ao_orbital" else orb.coefficients.T
        groups: Dict[str, List[int]] = {}
        for i, spin in enumerate(orb.spin):
            key = "all" if spin == "both" else spin
            groups.setdefault(key, []).append(i)
        max_err = 0.0
        for key, idxs in groups.items():
            Cg = Cb[:, idxs]
            if Cg.shape[1]:
                max_err = max(max_err, float(np.max(
                    np.abs(Cg.T @ S @ Cg - np.eye(Cg.shape[1])))))
        add("orthonormality_CtSC", max_err, TOL_ORTHONORM)
    else:
        add("orthonormality_CtSC", None, TOL_ORTHONORM, "coefficients missing")

    states = [v["passed"] for v in report.values()]
    if any(v is False for v in states):
        report["status"] = "FAIL"
    elif any(v is None for v in states):
        report["status"] = "INCOMPLETE"
    else:
        report["status"] = "PASS"
    return report


def legacy_representable(ms: MolecularSystem) -> bool:
    """Convenience wrapper: can this 0.1.1 system enter the v1 model?"""
    try:
        MolecularSystemV1.from_legacy(ms, strict=False)
    except Exception:
        return False
    return True


__all__ = [
    "SCHEMA_VERSION",
    "SCHEMA_VERSION_1_1",
    "SCHEMA_VERSION_1_2",
    "SUPPORTED_SCHEMA_VERSIONS",
    "WAVEFUNCTION_TYPES",
    "LENGTH_UNITS",
    "BASIS_REPRESENTATIONS",
    "COEFFICIENT_REPRESENTATIONS",
    "COEFFICIENT_LAYOUTS",
    "MATRIX_REPRESENTATIONS",
    "DENSITY_ORIGINS",
    "SPIN_COMPONENTS",
    "ECP_EDF_STATUSES",
    "NORMALIZATION_CONVENTIONS",
    "FileRecord",
    "Provenance",
    "Atoms",
    "Geometry",
    "ElectronicState",
    "Shell",
    "PrimitiveTable",
    "AOFunction",
    "BasisSet",
    "OrbitalSet",
    "Wavefunction",
    "MatrixRecord",
    "MatrixBundle",
    "CoreCorrection",
    "Periodicity",
    "ReadinessFlags",
    "MolecularSystemV1",
    "derive_rhf_density",
    "wavefunction_report",
    "legacy_representable",
]
