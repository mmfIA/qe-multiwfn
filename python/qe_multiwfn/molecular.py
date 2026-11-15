"""
qe_multiwfn.molecular — canonical molecular data model.

A MolecularSystem is a pure-Python container for the inputs needed by
the Fortran backend. It is a snapshot of the data; once passed to
engine.load_molecule(), the data is COPIED into Fortran-owned memory
and the Python object can be modified or deleted without affecting
the running analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


# Bohr -> Angstrom (2018 CODATA, same as Multiwfn's b2a)
BOHR_TO_ANGSTROM = 0.529177210903
ANGSTROM_TO_BOHR = 1.0 / BOHR_TO_ANGSTROM


# Wavefunction type codes (mirror Multiwfn's wfntype)
WFNTYPE_RHF       = 0
WFNTYPE_UHF       = 1
WFNTYPE_ROHF      = 2
WFNTYPE_R_POSTHF  = 3
WFNTYPE_U_POSTHF  = 4

WFNTYPE_NAMES = {
    WFNTYPE_RHF:       "RHF",
    WFNTYPE_UHF:       "UHF",
    WFNTYPE_ROHF:      "ROHF",
    WFNTYPE_R_POSTHF:  "R-post-HF",
    WFNTYPE_U_POSTHF:  "U-post-HF",
}


@dataclass
class MolecularSystem:
    """Canonical molecular data model.

    Required fields:
        ncenter, nbasis, nprims, wfntype
        atomic_numbers  : int32 array of shape (ncenter,)
        coordinates      : float64 array of shape (ncenter, 3), in Bohr
        basis_center    : int32 array of shape (nbasis,), 1-based atom index for each basis function
        basis_type      : int32 array of shape (nbasis,), Multiwfn type code for each basis function
        density_total   : float64 array of shape (nbasis, nbasis), symmetric
        overlap          : float64 array of shape (nbasis, nbasis), symmetric

    Optional fields:
        density_alpha / density_beta : required when wfntype ∈ {1,2,4}
        charge, multiplicity, nelectron : electronic metadata
    """

    ncenter: int
    nbasis: int
    nprims: int
    wfntype: int

    atomic_numbers: np.ndarray   # (ncenter,) int32
    coordinates: np.ndarray      # (ncenter, 3) float64, in Bohr

    basis_center: np.ndarray     # (nbasis,) int32, 1-based
    basis_type: np.ndarray       # (nbasis,) int32

    density_total: np.ndarray    # (nbasis, nbasis) float64
    overlap: np.ndarray           # (nbasis, nbasis) float64

    density_alpha: Optional[np.ndarray] = None  # (nbasis, nbasis) float64
    density_beta:  Optional[np.ndarray] = None  # (nbasis, nbasis) float64

    charge: int = 0
    multiplicity: int = 1
    nelectron: Optional[int] = None  # if None, derived from atomic_numbers - charge

    # Provenance
    source_format: str = "python"
    source_program: str = ""

    def __post_init__(self):
        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        # Dimensions
        if self.ncenter <= 0:
            raise ValueError(f"ncenter must be > 0 (got {self.ncenter})")
        if self.nbasis <= 0:
            raise ValueError(f"nbasis must be > 0 (got {self.nbasis})")
        if self.nprims <= 0:
            raise ValueError(f"nprims must be > 0 (got {self.nprims})")
        if self.nprims < self.nbasis:
            raise ValueError(
                f"nprims ({self.nprims}) must be >= nbasis ({self.nbasis}); "
                f"nprims must be >= nbasis; contracted basis sets may have nprims > nbasis"
            )
        if self.wfntype != WFNTYPE_RHF:
            raise ValueError(
                f"v0.1.1 supports only closed-shell RHF (wfntype=0); got {self.wfntype}"
            )

        # Atomic numbers
        an = np.asarray(self.atomic_numbers, dtype=np.int32)
        if an.shape != (self.ncenter,):
            raise ValueError(
                f"atomic_numbers shape {an.shape} != ({self.ncenter},)"
            )
        if (an < 0).any() or (an > 118).any():
            raise ValueError("atomic_numbers must be in [0, 118]")
        self.atomic_numbers = an

        # Coordinates: stored as (ncenter, 3) in Python, transferred as (3, ncenter) Fortran
        coor = np.asarray(self.coordinates, dtype=np.float64)
        if coor.shape != (self.ncenter, 3):
            raise ValueError(
                f"coordinates shape {coor.shape} != ({self.ncenter}, 3)"
            )
        if not np.isfinite(coor).all():
            raise ValueError("coordinates contain NaN/Inf")
        self.coordinates = coor

        # Basis
        bc = np.asarray(self.basis_center, dtype=np.int32)
        bt = np.asarray(self.basis_type, dtype=np.int32)
        if bc.shape != (self.nbasis,):
            raise ValueError(
                f"basis_center shape {bc.shape} != ({self.nbasis},); one center is required per basis function"
            )
        if bt.shape != (self.nbasis,):
            raise ValueError(
                f"basis_type shape {bt.shape} != ({self.nbasis},); one type is required per basis function"
            )
        if (bc < 1).any() or (bc > self.ncenter).any():
            raise ValueError(
                f"basis_center must be in [1, {self.ncenter}]"
            )
        self.basis_center = bc
        self.basis_type = bt

        # Density
        P = np.asfortranarray(self.density_total, dtype=np.float64)
        if P.shape != (self.nbasis, self.nbasis):
            raise ValueError(
                f"density_total shape {P.shape} != ({self.nbasis}, {self.nbasis})"
            )
        if not np.isfinite(P).all():
            raise ValueError("density_total contains NaN/Inf")
        if not _is_symmetric(P):
            raise ValueError("density_total is not symmetric")
        self.density_total = P

        S = np.asfortranarray(self.overlap, dtype=np.float64)
        if S.shape != (self.nbasis, self.nbasis):
            raise ValueError(
                f"overlap shape {S.shape} != ({self.nbasis}, {self.nbasis})"
            )
        if not np.isfinite(S).all():
            raise ValueError("overlap contains NaN/Inf")
        if not _is_symmetric(S):
            raise ValueError("overlap is not symmetric")
        self.overlap = S

        # Spin densities
        if self.wfntype in (WFNTYPE_UHF, WFNTYPE_ROHF, WFNTYPE_U_POSTHF):
            if self.density_alpha is None or self.density_beta is None:
                raise ValueError(
                    f"density_alpha and density_beta are required for "
                    f"wfntype={self.wfntype} ({WFNTYPE_NAMES[self.wfntype]})"
                )
            Pa = np.asfortranarray(self.density_alpha, dtype=np.float64)
            Pb = np.asfortranarray(self.density_beta, dtype=np.float64)
            for arr, name in [(Pa, "density_alpha"), (Pb, "density_beta")]:
                if arr.shape != (self.nbasis, self.nbasis):
                    raise ValueError(
                        f"{name} shape {arr.shape} != ({self.nbasis}, {self.nbasis})"
                    )
                if not np.isfinite(arr).all():
                    raise ValueError(f"{name} contains NaN/Inf")
                if not _is_symmetric(arr):
                    raise ValueError(f"{name} is not symmetric")
            self.density_alpha = Pa
            self.density_beta  = Pb

        # Closed-shell RHF metadata
        if self.multiplicity != 1:
            raise ValueError("closed-shell RHF requires multiplicity=1")
        if self.nelectron is None:
            self.nelectron = int(an.sum()) - self.charge
        self.nelectron = int(self.nelectron)
        if self.nelectron <= 0 or self.nelectron % 2:
            raise ValueError("closed-shell RHF requires a positive even electron count")

        # Multiwfn's spin-summed RHF density convention is P*S*P = 2*P.
        psp = P @ S @ P
        scale = max(1.0, float(np.max(np.abs(2.0 * P))))
        if float(np.max(np.abs(psp - 2.0 * P))) > 1.0e-6 * scale:
            raise ValueError("RHF density is not idempotent: P*S*P must equal 2*P")

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_arrays(
        cls,
        atomic_numbers,
        coordinates,
        basis_center,
        basis_type,
        density_total,
        overlap,
        *,
        wfntype: int = WFNTYPE_RHF,
        density_alpha=None,
        density_beta=None,
        charge: int = 0,
        multiplicity: int = 1,
        nelectron=None,
        nprims=None,
        coordinates_unit: str = "bohr",
    ) -> "MolecularSystem":
        """Build a MolecularSystem from raw NumPy-compatible arrays.

        coordinates_unit: "bohr" or "angstrom". If "angstrom", coordinates
        are converted to Bohr internally before storage.
        """
        an = np.asarray(atomic_numbers, dtype=np.int32)
        coor = np.asarray(coordinates, dtype=np.float64)
        if coordinates_unit.lower() == "angstrom":
            coor = coor * ANGSTROM_TO_BOHR
        elif coordinates_unit.lower() != "bohr":
            raise ValueError(
                f"coordinates_unit must be 'bohr' or 'angstrom', got {coordinates_unit!r}"
            )

        return cls(
            ncenter=an.shape[0],
            nbasis=np.asarray(density_total).shape[0],
            nprims=(int(nprims) if nprims is not None else np.asarray(basis_center).shape[0]),
            wfntype=wfntype,
            atomic_numbers=an,
            coordinates=coor,
            basis_center=np.asarray(basis_center, dtype=np.int32),
            basis_type=np.asarray(basis_type, dtype=np.int32),
            density_total=density_total,
            overlap=overlap,
            density_alpha=density_alpha,
            density_beta=density_beta,
            charge=charge,
            multiplicity=multiplicity,
            nelectron=nelectron,
        )

    # ------------------------------------------------------------------
    # Internal accessors used by the Engine
    # ------------------------------------------------------------------
    @property
    def _coordinates_fortran(self) -> np.ndarray:
        """Coordinates as a Fortran-order (3, ncenter) array."""
        return np.asfortranarray(self.coordinates.T, dtype=np.float64)

    def __repr__(self) -> str:
        return (
            f"MolecularSystem(ncenter={self.ncenter}, nbasis={self.nbasis}, "
            f"nprims={self.nprims}, wfntype={self.wfntype} "
            f"({WFNTYPE_NAMES.get(self.wfntype, '?')}), "
            f"nelec={self.nelectron}, mult={self.multiplicity})"
        )


def _is_symmetric(arr: np.ndarray, tol: float = 1e-9) -> bool:
    """Check that a 2D array is symmetric within tolerance."""
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        return False
    return np.allclose(arr, arr.T, atol=tol, rtol=0.0)
