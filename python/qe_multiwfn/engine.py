"""
qe_multiwfn.engine — high-level Python API for the QE-Multiwfn engine.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .native import (
    NativeAPI,
    QE_STATE_UNINITIALIZED, QE_STATE_INITIALIZED,
    QE_STATE_SYSTEM_LOADED, QE_STATE_SYSTEM_PREPARED,
    QE_STATE_RESULT_AVAILABLE,
    QE_MAYER_TOTAL, QE_MAYER_ALPHA, QE_MAYER_BETA,
    QE_V1_UNIT_BOHR, QE_V1_REPR_AO_CURRENT_BASIS,
    QE_V1_COEFF_CONTRACTED, QE_V1_COEFF_PRIMITIVE,
    QE_V1_LAYOUT_ORBITAL_AO, QE_V1_LAYOUT_AO_ORBITAL,
)
from .molecular import MolecularSystem
from .results import MayerResult
from .exceptions import (
    QeError, QeNotAvailable, QeUnsupported, QeIncompleteState, QeCalculation,
)
from .model_v1 import (
    TOL_ELECTRON_COUNT, TOL_IDEMPOTENCY_FACTOR, TOL_SCALE_FLOOR,
    TOL_SYMMETRY,
)


GENERATED_STATE_ELECTRON_TOL = 1.0e-6
GENERATED_STATE_ORTHONORM_TOL = 1.0e-6

STATE_NAMES = {
    QE_STATE_UNINITIALIZED:    "UNINITIALIZED",
    QE_STATE_INITIALIZED:      "INITIALIZED",
    QE_STATE_SYSTEM_LOADED:    "SYSTEM_LOADED",
    QE_STATE_SYSTEM_PREPARED:  "SYSTEM_PREPARED",
    QE_STATE_RESULT_AVAILABLE: "RESULT_AVAILABLE",
}


class Engine:
    """High-level Python engine.

    Use as a context manager:

        with qe.Engine() as engine:
            engine.load_molecule(system)
            result = engine.calculate_mayer()
            print(result.total)
    """

    def __init__(self, *, _api: Optional[NativeAPI] = None):
        # Allow injecting a mock API for testing.
        self._api = _api if _api is not None else NativeAPI()
        self._initialized = False
        self._loaded_system = None
        self._use_v1 = False
        self._prepare_from_orbitals = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Initialize the engine. Must be called once before use."""
        self._api.initialize()
        self._initialized = True

    def finalize(self) -> None:
        """Finalize the engine, releasing all resources."""
        if not self._initialized:
            return
        try:
            self.release_molecule()
        except QeError:
            pass
        self._api.finalize()
        self._initialized = False

    @property
    def state(self) -> str:
        """Human-readable engine state name."""
        s = self._api.get_engine_state()
        return STATE_NAMES.get(s, f"UNKNOWN({s})")

    @property
    def version(self) -> str:
        """Native library version string."""
        return self._api.version

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_molecule(self, system: MolecularSystem) -> None:
        """Load a molecular system into the engine.

        Pushes the canonical MolecularSystem's data into Fortran-owned
        memory via the C ABI. Does NOT call qe_prepare_system() — call
        engine.prepare() explicitly to validate and build internal state.
        """
        if not self._initialized:
            self.initialize()
        # Release any previously loaded system first.
        if self._loaded_system is not None:
            self.release_molecule()
        if self._api.has_v1():
            self._api.enable_open_shell_v1(False)
        self._use_v1 = False

        # Begin a new system with the right dimensions.
        self._api.begin_system(
            ncenter=system.ncenter,
            nbasis=system.nbasis,
            nprims=system.nprims,
            wfntype=system.wfntype,
        )

        # Push atomic data (coordinates in Fortran order: (3, ncenter))
        self._api.set_atomic_data(
            atomic_numbers=system.atomic_numbers,
            coordinates=system._coordinates_fortran,
        )

        # Electronic metadata
        self._api.set_electronic_metadata(
            charge=system.charge,
            mult=system.multiplicity,
            nelec=system.nelectron,
        )

        # Basis data
        self._api.set_basis_data(
            basis_center=system.basis_center,
            basis_type=system.basis_type,
            nprims=system.nprims,
        )

        # Density
        self._api.set_density(
            density_total=system.density_total,
            density_alpha=system.density_alpha,
            density_beta=system.density_beta,
        )

        # Overlap
        self._api.set_overlap(overlap=system.overlap)

        self._loaded_system = system

    def load_molecule_v1(self, system, *, allow_open_shell: bool = False,
                         prepare_from_orbitals: bool = False) -> None:
        """Load a Molecular Data Model 1.0 system through the additive ABI.

        Accepts a ``qe_multiwfn.model_v1.MolecularSystemV1``. The v1 ABI
        carries the full basis description (shells, primitives, AO map) and
        optional orbitals, while the scientific path remains the original
        Multiwfn routine.

        ``allow_open_shell=True`` is required for UHF (wfntype=1) and ROHF
        (wfntype=2). The flag enables the additive open-shell path; post-HF
        remains rejected.
        """
        if not self._initialized:
            self.initialize()
        if not self._api.has_v1():
            raise QeUnsupported(
                7,
                "this libqe_multiwfn.so does not expose the v1 model ABI",
                "Engine.load_molecule_v1",
            )
        # Release any previously loaded system first.
        if self._loaded_system is not None:
            self.release_molecule()

        system.validate(strict=False)
        if not prepare_from_orbitals and self.matrices_missing(system):
            raise QeIncompleteState(
                6, "v1 model needs matrices.S and matrices.P_total or "
                "prepare_from_orbitals=True",
                "Engine.load_molecule_v1",
            )
        if not system.basis.aos:
            raise QeIncompleteState(
                6, "v1 model needs an AO mapping (basis.aos)",
                "Engine.load_molecule_v1",
            )
        if system.periodicity.ifPBC != 0:
            raise QeUnsupported(
                7,
                "periodic systems are not supported by the Mayer path",
                "Engine.load_molecule_v1",
            )
        if (system.core_correction is not None
                and system.core_correction.status == "incomplete"):
            raise QeIncompleteState(
                6, "ECP/EDF data is incomplete",
                "Engine.load_molecule_v1",
            )

        wfntype = int(system.electronic.wfntype)
        if wfntype == 0:
            self._api.enable_open_shell_v1(False)
        else:
            if not allow_open_shell:
                raise QeUnsupported(
                    7,
                    "open-shell execution requires load_molecule_v1(..., "
                    "allow_open_shell=True)",
                    "Engine.load_molecule_v1",
                )
            if wfntype not in (1, 2):
                raise QeUnsupported(
                    7,
                    "the open-shell flag currently enables only UHF (1) and "
                    "ROHF (2); post-HF remains unsupported",
                    "Engine.load_molecule_v1",
                )
            self._api.enable_open_shell_v1(True)

        if not prepare_from_orbitals:
            system.validate(strict=True)

        self._api.begin_system_v1(
            ncenter=system.ncenter,
            nbasis=system.nbasis,
            nprims=system.nprims,
            wfntype=system.electronic.wfntype,
        )
        canonical_angular = (
            getattr(system, "schema_version", "1.1.0") == "1.2.0"
            and getattr(system.basis, "angular", None) is not None
            and system.basis.angular.state == "canonical"
        )
        self._api.set_angular_canonical_v1(canonical_angular)

        # Atoms/geometry: (ncenter,3) -> Fortran (3,ncenter)
        coords_f = np.asfortranarray(system.geometry.coordinates.T)
        self._api.set_atoms_v1(
            system.atoms.z, coords_f, QE_V1_UNIT_BOHR
        )
        self._api.set_electronic_metadata(
            charge=system.electronic.charge,
            mult=system.electronic.multiplicity,
            nelec=system.electronic.nelectron,
        )

        # Optional basis description.
        if system.basis.shells:
            shells = system.basis.shells
            self._api.set_shells_v1(
                [s.center for s in shells],
                [s.l for s in shells],
                [s.primitive_start for s in shells],
                [s.primitive_end for s in shells],
                [1 if s.cartesian else 0 for s in shells],
            )
        if system.basis.primitives is not None:
            pr = system.basis.primitives
            self._api.set_primitives_v1(
                pr.center, pr.type, pr.exponent, pr.coefficient,
                normalization=pr.normalization,
                shell_index=pr.shell_index,
            )

        # Authoritative AO map (also fills legacy basis_center/type).
        aos = system.basis.aos
        self._api.set_ao_map_v1(
            center=[a.center for a in aos],
            shell_index=[a.shell_index if a.shell_index is not None else 0 for a in aos],
            multiwfn_type=[a.multiwfn_type if a.multiwfn_type is not None else 0 for a in aos],
            angular_type=[a.angular_type for a in aos],
            source_index=[a.source_index if a.source_index is not None else i
                          for i, a in enumerate(aos)],
        )

        # MDM 1.1 per-AO normalization metadata (if the model carries it).
        if all(ao.source_self_overlap is not None
               and ao.contraction_normalization is not None
               and ao.normalization_convention is not None
               for ao in aos):
            cmap = {
                "unknown": 0, "source_normalized": 1,
                "cartesian_explicit": 2, "cartesian_source_scaled": 3,
                "cartesian_source_unnormalized": 4,
            }
            self._api.set_ao_normalization_v1(
                [ao.source_self_overlap for ao in aos],
                [ao.contraction_normalization for ao in aos],
                [cmap.get(ao.normalization_convention, 0) for ao in aos],
            )

        # Matrices (ao_current_basis). In the full MDM->original-routines
        # path these are intentionally NOT sent: S and P are generated by
        # genSbas_curr/genP from the canonical basis and orbitals.
        if not prepare_from_orbitals:
            self._api.set_density_v1(
                system.nbasis, QE_V1_REPR_AO_CURRENT_BASIS,
                system.matrices.P_total.data,
                None if system.matrices.P_alpha is None else system.matrices.P_alpha.data,
                None if system.matrices.P_beta is None else system.matrices.P_beta.data,
            )
            self._api.set_overlap_v1(
                system.nbasis, QE_V1_REPR_AO_CURRENT_BASIS,
                system.matrices.S.data,
            )

        # Optional orbital data.
        if system.wavefunction is not None:
            orb = system.wavefunction.orbitals
            if orb.coefficient_representation == "contracted_basis":
                repr_code = QE_V1_COEFF_CONTRACTED
            else:
                repr_code = QE_V1_COEFF_PRIMITIVE
            if orb.coefficient_layout == "orbital_ao":
                layout_code = QE_V1_LAYOUT_ORBITAL_AO
                ncoeff = int(orb.coefficients.shape[1])
            else:
                layout_code = QE_V1_LAYOUT_AO_ORBITAL
                ncoeff = int(orb.coefficients.shape[0])
            spin_map = {"total": 0, "both": 0, "alpha": 1, "beta": 2}
            spin_codes = [spin_map[s] for s in orb.spin]
            self._api.set_orbitals_v1(
                orb.nmo, ncoeff, repr_code, layout_code,
                orb.coefficients, orb.energies, orb.occupations, spin_codes,
            )

        self._loaded_system = system
        self._use_v1 = True
        self._prepare_from_orbitals = bool(prepare_from_orbitals)

    @staticmethod
    def matrices_missing(system) -> bool:
        return system.matrices.S is None or system.matrices.P_total is None

    def prepare(self) -> None:
        """Validate the loaded system and build internal Multiwfn state."""
        if self._loaded_system is None:
            raise QeError(
                2, "no molecular system loaded; call load_molecule() first", "Engine.prepare"
            )
        if self._use_v1:
            if self._prepare_from_orbitals:
                self._require_full_state(self._loaded_system)
                self._api.build_electronic_state_v1()
                self._prepare_from_orbitals = False
                self._validate_generated_state()
            else:
                self._api.commit_v1()
        else:
            self._api.prepare_system()

    @staticmethod
    def _require_full_state(system) -> None:
        if system.wavefunction is None:
            raise QeIncompleteState(6, "full-state path requires orbitals",
                                    "Engine.prepare")
        if not system.basis.shells:
            raise QeIncompleteState(6, "full-state path requires shells",
                                    "Engine.prepare")
        if system.basis.primitives is None:
            raise QeIncompleteState(6, "full-state path requires primitives",
                                    "Engine.prepare")
        if not system.basis.aos:
            raise QeIncompleteState(6, "full-state path requires an AO map",
                                    "Engine.prepare")
        if system.basis.primitives.nprims != system.nprims:
            raise QeIncompleteState(6, "primitive table size is inconsistent",
                                    "Engine.prepare")
        for ao in system.basis.aos:
            if ao.shell_index is None or not (1 <= int(ao.shell_index) <= len(system.basis.shells)):
                raise QeIncompleteState(6, "full-state AO lacks a valid shell index",
                                        "Engine.prepare")
            if ao.multiwfn_type is None:
                raise QeIncompleteState(6, "full-state AO lacks a component code",
                                        "Engine.prepare")
            if (ao.source_self_overlap is None
                    or ao.contraction_normalization is None
                    or ao.normalization_convention is None):
                raise QeIncompleteState(6, "full-state AO normalization metadata missing",
                                        "Engine.prepare")
        C = system.wavefunction.orbitals.coefficients
        if system.wavefunction.orbitals.coefficient_layout == "orbital_ao":
            if C.shape[1] != system.nbasis:
                raise QeIncompleteState(6, "orbital coefficients do not span nbasis",
                                        "Engine.prepare")
        elif C.shape[0] != system.nbasis:
            raise QeIncompleteState(6, "orbital coefficients do not span nbasis",
                                    "Engine.prepare")

    def _validate_generated_state(self) -> None:
        system = self._loaded_system
        S = self.generated_overlap()
        P = self.generated_density(0)
        if S.shape != (system.nbasis, system.nbasis) or P.shape != S.shape:
            raise QeCalculation(8, "generated S/P dimensions are inconsistent",
                                "Engine.prepare")
        if (not np.isfinite(S).all() or not np.isfinite(P).all()
                or np.max(np.abs(S - S.T)) > TOL_SYMMETRY
                or np.max(np.abs(P - P.T)) > TOL_SYMMETRY):
            raise QeCalculation(8, "generated S/P is non-finite or non-symmetric",
                                "Engine.prepare")
        ne = float(system.electronic.nelectron)
        if abs(float(np.trace(P @ S)) - ne) > GENERATED_STATE_ELECTRON_TOL:
            raise QeCalculation(8, "generated P does not reproduce Ne",
                                "Engine.prepare")
        wf = int(system.electronic.wfntype)
        C = system.wavefunction.orbitals.coefficients
        if system.wavefunction.orbitals.coefficient_layout == "ao_orbital":
            Cb = C
        else:
            Cb = C.T
        groups = {}
        for i, spin in enumerate(system.wavefunction.orbitals.spin):
            key = "all" if spin == "both" else spin
            groups.setdefault(key, []).append(i)
        for key, idxs in groups.items():
            Cg = Cb[:, idxs]
            if Cg.shape[1] == 0:
                continue
            err = float(np.max(np.abs(Cg.T @ S @ Cg - np.eye(Cg.shape[1]))))
            if err > GENERATED_STATE_ORTHONORM_TOL:
                raise QeCalculation(
                    8,
                    f"generated overlap does not orthonormalize {key} orbitals "
                    f"(error {err:.3e})",
                    "Engine.prepare",
                )
        if wf == 0:
            scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(2.0 * P))))
            err = float(np.max(np.abs(P @ S @ P - 2.0 * P)))
            if err > TOL_IDEMPOTENCY_FACTOR * scale:
                raise QeCalculation(8, "generated RHF density is not idempotent",
                                    "Engine.prepare")
            return
        if wf in (1, 2):
            Pa = self.generated_density(1)
            Pb = self.generated_density(2)
            if (np.max(np.abs(P - (Pa + Pb))) > 1e-10
                    or abs(float(np.trace(Pa @ S)) - float(system.electronic.naelectron)) > GENERATED_STATE_ELECTRON_TOL
                    or abs(float(np.trace(Pb @ S)) - float(system.electronic.nbelectron)) > GENERATED_STATE_ELECTRON_TOL):
                raise QeCalculation(8, "generated open-shell densities are inconsistent",
                                    "Engine.prepare")
            for label, Ps in (("alpha", Pa), ("beta", Pb)):
                scale = max(TOL_SCALE_FLOOR, float(np.max(np.abs(Ps))))
                err = float(np.max(np.abs(Ps @ S @ Ps - Ps)))
                if err > TOL_IDEMPOTENCY_FACTOR * scale:
                    raise QeCalculation(8, f"generated {label} density is not idempotent",
                                        "Engine.prepare")

    def generate_density(self) -> None:
        """Call the ORIGINAL Multiwfn genP using the loaded orbital data.

        Requires a v1 model with orbitals, loaded and prepared. The
        generated Ptot/Palpha/Pbeta replace the reference density for a
        subsequent Mayer calculation. S is not modified here.
        """
        if self._loaded_system is None:
            raise QeError(2, "no molecular system loaded", "Engine.generate_density")
        if not self._use_v1:
            raise QeError(2, "generate_density requires a v1-loaded system",
                          "Engine.generate_density")
        self._api.generate_density_v1()

    def generated_density(self, result_id: int = 0):
        """Return the density generated by the original genP (total/alpha/beta)."""
        n = self._api.get_generated_density_dimensions_v1()
        return self._api.get_generated_density_v1(result_id, n)

    def generate_overlap(self) -> None:
        """Call the ORIGINAL Multiwfn genSbas_curr using the canonical basis.

        This replaces the reference S with the overlap generated by the
        original routine. The basis is built from the canonical model,
        including Cartesian primitives and, for spherical d/f, the
        original matCar2curr conversion with ifiletype set explicitly.
        """
        if self._loaded_system is None:
            raise QeError(2, "no molecular system loaded", "Engine.generate_overlap")
        if not self._use_v1:
            raise QeError(2, "generate_overlap requires a v1-loaded system",
                          "Engine.generate_overlap")
        self._api.generate_overlap_v1()

    def generated_overlap(self):
        n, _, _ = self._api.get_overlap_dimensions_v1()
        return self._api.get_generated_overlap_v1(n)

    def generate_cartesian_overlap(self) -> None:
        """Run the ORIGINAL genSbas (Cartesian intermediate, diagnostic)."""
        if self._loaded_system is None:
            raise QeError(2, "no molecular system loaded",
                          "Engine.generate_cartesian_overlap")
        if not self._use_v1:
            raise QeError(2, "generate_cartesian_overlap requires a v1-loaded system",
                          "Engine.generate_cartesian_overlap")
        self._api.generate_cartesian_overlap_v1()

    def generated_cartesian_overlap(self):
        _, ncar, _ = self._api.get_overlap_dimensions_v1()
        return self._api.get_generated_cartesian_overlap_v1(ncar)

    def generate_primitive_density(self) -> None:
        """Call the ORIGINAL Multiwfn genPprim.

        The result is a primitive-basis density (nprims x nprims), stored
        separately. It does not replace Ptot/Palpha/Pbeta in the current
        basis, nor the current S.
        """
        if self._loaded_system is None:
            raise QeError(2, "no molecular system loaded",
                          "Engine.generate_primitive_density")
        if not self._use_v1:
            raise QeError(2, "generate_primitive_density requires a v1-loaded system",
                          "Engine.generate_primitive_density")
        self._api.generate_primitive_density_v1()

    def generated_primitive_density(self, result_id: int = 0):
        n = self._api.get_primitive_density_dimensions_v1()
        return self._api.get_generated_primitive_density_v1(result_id, n)

    def generated_primitive_overlap(self):
        """Contracted-primitive overlap S_prim (validation accessor)."""
        n = self._api.get_primitive_density_dimensions_v1()
        return self._api.get_primitive_overlap_v1(n)

    def release_molecule(self) -> None:
        """Release the currently-loaded molecular system."""
        if self._use_v1:
            self._api.release_v1()
        else:
            self._api.release_system()
        if self._api.has_v1():
            try:
                self._api.enable_open_shell_v1(False)
            except Exception:
                pass
        self._loaded_system = None
        self._use_v1 = False
        self._prepare_from_orbitals = False

    # ------------------------------------------------------------------
    # Analyses
    # ------------------------------------------------------------------
    def calculate_mayer(self, system=None, *, allow_open_shell=None) -> MayerResult:
        """Compute Mayer bond order using the original Multiwfn routine.

        If ``system`` is supplied, load and prepare it first.  A
        ``MolecularSystemV1`` with open-shell wavefunction automatically
        enables the open-shell path; a model without S/P uses the full
        basis/orbital path.  The no-argument form preserves the existing API.
        """
        if system is not None:
            wf = int(system.electronic.wfntype)
            if allow_open_shell is None:
                allow_open_shell = wf in (1, 2)
            full_state = self.matrices_missing(system)
            self.load_molecule_v1(
                system, allow_open_shell=allow_open_shell,
                prepare_from_orbitals=full_state,
            )
        # Make sure system is prepared
        if self._loaded_system is None:
            raise QeError(
                2, "no molecular system loaded", "Engine.calculate_mayer"
            )
        if self.state == "SYSTEM_LOADED":
            self.prepare()

        self._api.calculate_mayer()

        # Retrieve results
        ncenter = self._api.get_mayer_dimensions()
        wfn, has_spin = self._api.get_mayer_metadata()

        total = self._api.get_mayer_result(QE_MAYER_TOTAL, ncenter)
        # The native library returns column-major data; since Mayer matrices
        # are symmetric, the layout doesn't matter, but we ensure we hand
        # the user a contiguous NumPy array.
        total = np.ascontiguousarray(total)

        alpha = None
        beta = None
        if has_spin:
            try:
                alpha = np.ascontiguousarray(self._api.get_mayer_result(QE_MAYER_ALPHA, ncenter))
                beta = np.ascontiguousarray(self._api.get_mayer_result(QE_MAYER_BETA, ncenter))
            except QeNotAvailable:
                alpha = None
                beta = None

        return MayerResult(
            total=total,
            alpha=alpha,
            beta=beta,
            metadata={
                "analysis": "Mayer",
                "wavefunction_type": wfn,
                "wavefunction_type_name": {
                    0: "RHF", 1: "UHF", 2: "ROHF",
                    3: "R-post-HF", 4: "U-post-HF",
                }.get(int(wfn), f"UNKNOWN({wfn})"),
                "total_semantics": (
                    "generalized_wiberg_mixed" if has_spin
                    else "closed_shell_mayer"
                ),
                "has_spin_components": has_spin,
                "ncenter": ncenter,
            },
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self) -> "Engine":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()
        return False  # do not suppress exceptions

    def __del__(self):
        try:
            self.finalize()
        except Exception:
            pass
