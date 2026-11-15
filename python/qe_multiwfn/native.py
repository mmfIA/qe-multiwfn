"""
qe_multiwfn.native — ctypes bindings to libqe_multiwfn.so.

This module loads the shared library, declares argtypes/restype for every
exported function, and provides a thin wrapper that converts status codes
into Python exceptions.

NO USER-FACING API lives here. Use qe_multiwfn.Engine instead.
"""

from __future__ import annotations

import ctypes
import os
import sys

import numpy as np
from ctypes import (
    c_int, c_double, c_char, c_char_p, c_void_p, POINTER, byref,
    create_string_buffer, cast, sizeof,
)

from .exceptions import (
    QeError, QeUnsupported, STATUS_TO_EXCEPTION, STATUS_NAMES,
)


# Status code constants — mirror include/qe_multiwfn.h
QE_SUCCESS                     = 0
QE_ERROR_INVALID_ARGUMENT     = 1
QE_ERROR_INVALID_STATE        = 2
QE_ERROR_INVALID_DIMENSION    = 3
QE_ERROR_NULL_POINTER         = 4
QE_ERROR_ALLOCATION            = 5
QE_ERROR_INCOMPLETE_STATE     = 6
QE_ERROR_UNSUPPORTED           = 7
QE_ERROR_CALCULATION           = 8
QE_ERROR_INTERNAL              = 9
QE_ERROR_COMPATIBILITY         = 10
QE_ERROR_MEMORY_LAYOUT         = 11
QE_ERROR_NOT_AVAILABLE         = 12

# Engine states
QE_STATE_UNINITIALIZED    = 0
QE_STATE_INITIALIZED      = 1
QE_STATE_SYSTEM_LOADED    = 2
QE_STATE_SYSTEM_PREPARED  = 3
QE_STATE_RESULT_AVAILABLE = 4

# Mayer result IDs
QE_MAYER_TOTAL = 0
QE_MAYER_ALPHA = 1
QE_MAYER_BETA  = 2


# ----------------------------------------------------------------------
# Locate libqe_multiwfn.so
# ----------------------------------------------------------------------

def _find_library() -> str:
    """Search for libqe_multiwfn.so in a few well-known locations."""
    candidates = []

    # 1. QE_MULTIWFN_LIBRARY environment variable (highest priority)
    env = os.environ.get("QE_MULTIWFN_LIBRARY")
    if env:
        candidates.append(env)

    # 2. Directory of this Python package (for installed wheels)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "libqe_multiwfn.so"))
    candidates.append(os.path.join(here, "..", "libqe_multiwfn.so"))
    candidates.append(os.path.join(here, "bin", "libqe_multiwfn.so"))

    # 3. Project-relative path (for development)
    proj_root = os.path.abspath(os.path.join(here, "..", ".."))
    candidates.append(os.path.join(proj_root, "build", "libqe_multiwfn.so"))

    # 4. System library path
    candidates.append("libqe_multiwfn.so")

    for path in candidates:
        if os.path.exists(path):
            return path

    # Last resort: rely on the system loader
    return "libqe_multiwfn.so"


NATIVE_LIBRARY_PATH = _find_library()

# Load the library. Use RTLD_GLOBAL so that BLAS symbols resolve.
try:
    _RTLD = ctypes.RTLD_GLOBAL
except AttributeError:
    _RTLD = 0  # Windows
_lib = ctypes.CDLL(NATIVE_LIBRARY_PATH, mode=ctypes.RTLD_GLOBAL | _RTLD)

# ----------------------------------------------------------------------
# Function signatures
# ----------------------------------------------------------------------

# int qe_initialize(void);
_lib.qe_initialize.argtypes = []
_lib.qe_initialize.restype = c_int

# int qe_finalize(void);
_lib.qe_finalize.argtypes = []
_lib.qe_finalize.restype = c_int

# int qe_get_engine_state(int *state);
_lib.qe_get_engine_state.argtypes = [POINTER(c_int)]
_lib.qe_get_engine_state.restype = c_int

# int qe_get_last_error(char *buffer, int buffer_capacity);
_lib.qe_get_last_error.argtypes = [c_char_p, c_int]
_lib.qe_get_last_error.restype = c_int

# int qe_begin_system(int, int, int, int);
_lib.qe_begin_system.argtypes = [c_int, c_int, c_int, c_int]
_lib.qe_begin_system.restype = c_int

# int qe_set_atomic_data(int, const int*, const double*);
_lib.qe_set_atomic_data.argtypes = [c_int, c_void_p, c_void_p]
_lib.qe_set_atomic_data.restype = c_int

# int qe_set_electronic_metadata(int, int, int);
_lib.qe_set_electronic_metadata.argtypes = [c_int, c_int, c_int]
_lib.qe_set_electronic_metadata.restype = c_int

# int qe_set_basis_data(int, int, const int*, const int*);
_lib.qe_set_basis_data.argtypes = [c_int, c_int, c_void_p, c_void_p]
_lib.qe_set_basis_data.restype = c_int

# int qe_set_density(int, const double*, const double*, const double*);
_lib.qe_set_density.argtypes = [c_int, c_void_p, c_void_p, c_void_p]
_lib.qe_set_density.restype = c_int

# int qe_set_overlap(int, const double*);
_lib.qe_set_overlap.argtypes = [c_int, c_void_p]
_lib.qe_set_overlap.restype = c_int

# int qe_prepare_system(void);
_lib.qe_prepare_system.argtypes = []
_lib.qe_prepare_system.restype = c_int

# int qe_calculate_mayer(void);
_lib.qe_calculate_mayer.argtypes = []
_lib.qe_calculate_mayer.restype = c_int

# int qe_get_mayer_dimensions(int*);
_lib.qe_get_mayer_dimensions.argtypes = [POINTER(c_int)]
_lib.qe_get_mayer_dimensions.restype = c_int

# int qe_get_mayer_metadata(int*, int*);
_lib.qe_get_mayer_metadata.argtypes = [POINTER(c_int), POINTER(c_int)]
_lib.qe_get_mayer_metadata.restype = c_int

# int qe_get_mayer_result(int, double*, int);
_lib.qe_get_mayer_result.argtypes = [c_int, c_void_p, c_int]
_lib.qe_get_mayer_result.restype = c_int

# int qe_release_system(void);
_lib.qe_release_system.argtypes = []
_lib.qe_release_system.restype = c_int

# const char* qe_get_version(void);
_lib.qe_get_version.argtypes = []
_lib.qe_get_version.restype = c_char_p


# ----------------------------------------------------------------------
# Additive Molecular Data Model 1.0 ABI (optional at runtime)
# ----------------------------------------------------------------------
_HAS_V1 = hasattr(_lib, "qe_v1_model_begin")

if _HAS_V1:
    _lib.qe_v1_enable_open_shell.argtypes = [c_int]
    _lib.qe_v1_enable_open_shell.restype = c_int

    _lib.qe_v1_model_begin.argtypes = [c_int, c_int, c_int, c_int]
    _lib.qe_v1_model_begin.restype = c_int

    _lib.qe_v1_set_atoms.argtypes = [c_int, c_void_p, c_void_p, c_int]
    _lib.qe_v1_set_atoms.restype = c_int

    _lib.qe_v1_set_shells.argtypes = [c_int, c_void_p, c_void_p, c_void_p,
                                      c_void_p, c_void_p]
    _lib.qe_v1_set_shells.restype = c_int

    _lib.qe_v1_set_primitives.argtypes = [c_int, c_void_p, c_void_p, c_void_p,
                                          c_void_p, c_void_p, c_void_p]
    _lib.qe_v1_set_primitives.restype = c_int

    _lib.qe_v1_set_ao_map.argtypes = [c_int, c_void_p, c_void_p, c_void_p,
                                      c_void_p, c_void_p]
    _lib.qe_v1_set_ao_map.restype = c_int

    _lib.qe_v1_set_ao_normalization.argtypes = [c_int, c_void_p, c_void_p, c_void_p]
    _lib.qe_v1_set_ao_normalization.restype = c_int

    _lib.qe_v1_set_angular_canonical.argtypes = [c_int]
    _lib.qe_v1_set_angular_canonical.restype = c_int

    _lib.qe_v1_set_density.argtypes = [c_int, c_int, c_void_p, c_void_p, c_void_p]
    _lib.qe_v1_set_density.restype = c_int

    _lib.qe_v1_set_overlap.argtypes = [c_int, c_int, c_void_p]
    _lib.qe_v1_set_overlap.restype = c_int

    _lib.qe_v1_set_orbitals.argtypes = [c_int, c_int, c_int, c_int,
                                        c_void_p, c_void_p, c_void_p, c_void_p]
    _lib.qe_v1_set_orbitals.restype = c_int

    _lib.qe_v1_model_commit.argtypes = []
    _lib.qe_v1_model_commit.restype = c_int

    _lib.qe_v1_model_release.argtypes = []
    _lib.qe_v1_model_release.restype = c_int

    _lib.qe_v1_get_readiness.argtypes = [POINTER(c_int)]
    _lib.qe_v1_get_readiness.restype = c_int

    _lib.qe_v1_generate_density.argtypes = []
    _lib.qe_v1_generate_density.restype = c_int

    _lib.qe_v1_get_generated_density_dimensions.argtypes = [POINTER(c_int)]
    _lib.qe_v1_get_generated_density_dimensions.restype = c_int

    _lib.qe_v1_get_generated_density.argtypes = [c_int, c_void_p, c_int]
    _lib.qe_v1_get_generated_density.restype = c_int

    _lib.qe_v1_generate_overlap.argtypes = []
    _lib.qe_v1_generate_overlap.restype = c_int

    _lib.qe_v1_generate_cartesian_overlap.argtypes = []
    _lib.qe_v1_generate_cartesian_overlap.restype = c_int

    _lib.qe_v1_get_overlap_dimensions.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(c_int)]
    _lib.qe_v1_get_overlap_dimensions.restype = c_int

    _lib.qe_v1_get_generated_overlap.argtypes = [c_void_p, c_int]
    _lib.qe_v1_get_generated_overlap.restype = c_int

    _lib.qe_v1_get_generated_cartesian_overlap.argtypes = [c_void_p, c_int]
    _lib.qe_v1_get_generated_cartesian_overlap.restype = c_int

    _lib.qe_v1_build_electronic_state.argtypes = []
    _lib.qe_v1_build_electronic_state.restype = c_int

    _lib.qe_v1_generate_primitive_density.argtypes = []
    _lib.qe_v1_generate_primitive_density.restype = c_int

    _lib.qe_v1_get_primitive_density_dimensions.argtypes = [POINTER(c_int)]
    _lib.qe_v1_get_primitive_density_dimensions.restype = c_int

    _lib.qe_v1_get_generated_primitive_density.argtypes = [c_int, c_void_p, c_int]
    _lib.qe_v1_get_generated_primitive_density.restype = c_int

    _lib.qe_v1_get_primitive_overlap.argtypes = [c_void_p, c_int]
    _lib.qe_v1_get_primitive_overlap.restype = c_int

# v1 constants (mirror include/qe_multiwfn_v1.h)
QE_V1_UNIT_BOHR = 0
QE_V1_UNIT_ANGSTROM = 1
QE_V1_REPR_AO_CURRENT_BASIS = 0
QE_V1_REPR_PRIMITIVE_GTF = 1
QE_V1_COEFF_CONTRACTED = 0
QE_V1_COEFF_PRIMITIVE = 1
QE_V1_LAYOUT_ORBITAL_AO = 0
QE_V1_LAYOUT_AO_ORBITAL = 1
QE_V1_SPIN_TOTAL = 0
QE_V1_SPIN_ALPHA = 1
QE_V1_SPIN_BETA = 2
QE_V1_READY_GEOMETRY = 1 << 0
QE_V1_READY_BASIS = 1 << 1
QE_V1_READY_WAVEFUNCTION = 1 << 2
QE_V1_READY_DENSITY = 1 << 3
QE_V1_READY_OVERLAP = 1 << 4
QE_V1_READY_SHELLS = 1 << 5
QE_V1_READY_PRIMITIVES = 1 << 6
QE_V1_READY_AO_MAP = 1 << 7
QE_V1_READY_MAYER = 1 << 8


# ----------------------------------------------------------------------
# Status / error checking
# ----------------------------------------------------------------------

def get_last_error_message() -> str:
    """Retrieve the last error message from the library."""
    buf = create_string_buffer(1024)
    status = _lib.qe_get_last_error(buf, 1024)
    if status != 0:
        return f"(could not retrieve error message: status={status})"
    return buf.value.decode("utf-8", errors="replace")


def _check_status(status: int, routine: str = "") -> None:
    """Raise a Python exception if status is not QE_SUCCESS."""
    if status == QE_SUCCESS:
        return
    exc_class = STATUS_TO_EXCEPTION.get(status, QeError)
    message = get_last_error_message()
    raise exc_class(status, message, routine)


# ----------------------------------------------------------------------
# Public low-level wrapper
# ----------------------------------------------------------------------

class NativeAPI:
    """Thin wrapper around the ctypes calls. The Engine class delegates
    to this object so the binding can be mocked in tests."""

    def __init__(self):
        self.lib = _lib

    def initialize(self) -> None:
        status = _lib.qe_initialize()
        _check_status(status, "qe_initialize")

    def finalize(self) -> None:
        status = _lib.qe_finalize()
        _check_status(status, "qe_finalize")

    def get_engine_state(self) -> int:
        state = c_int(-1)
        status = _lib.qe_get_engine_state(byref(state))
        _check_status(status, "qe_get_engine_state")
        return state.value

    def begin_system(self, ncenter: int, nbasis: int, nprims: int, wfntype: int) -> None:
        status = _lib.qe_begin_system(ncenter, nbasis, nprims, wfntype)
        _check_status(status, "qe_begin_system")

    def set_atomic_data(self, atomic_numbers, coordinates) -> None:
        """atomic_numbers: int32 array (ncenter,)
        coordinates: float64 Fortran-order array (3, ncenter)"""
        n = len(atomic_numbers)
        atnum_ptr = atomic_numbers.ctypes.data_as(c_void_p)
        coor_ptr = coordinates.ctypes.data_as(c_void_p)
        status = _lib.qe_set_atomic_data(n, atnum_ptr, coor_ptr)
        _check_status(status, "qe_set_atomic_data")

    def set_electronic_metadata(self, charge: int, mult: int, nelec: int) -> None:
        status = _lib.qe_set_electronic_metadata(charge, mult, nelec)
        _check_status(status, "qe_set_electronic_metadata")

    def set_basis_data(self, basis_center, basis_type, *, nprims: int) -> None:
        nbasis = len(basis_center)
        bc_ptr = basis_center.ctypes.data_as(c_void_p)
        bt_ptr = basis_type.ctypes.data_as(c_void_p)
        status = _lib.qe_set_basis_data(nbasis, int(nprims), bc_ptr, bt_ptr)
        _check_status(status, "qe_set_basis_data")

    def set_density(self, density_total, density_alpha=None, density_beta=None) -> None:
        n = density_total.shape[0]
        dt_ptr = density_total.ctypes.data_as(c_void_p)
        da_ptr = density_alpha.ctypes.data_as(c_void_p) if density_alpha is not None else None
        db_ptr = density_beta.ctypes.data_as(c_void_p) if density_beta is not None else None
        status = _lib.qe_set_density(n, dt_ptr, da_ptr, db_ptr)
        _check_status(status, "qe_set_density")

    def set_overlap(self, overlap) -> None:
        n = overlap.shape[0]
        ov_ptr = overlap.ctypes.data_as(c_void_p)
        status = _lib.qe_set_overlap(n, ov_ptr)
        _check_status(status, "qe_set_overlap")

    def prepare_system(self) -> None:
        status = _lib.qe_prepare_system()
        _check_status(status, "qe_prepare_system")

    def calculate_mayer(self) -> None:
        status = _lib.qe_calculate_mayer()
        _check_status(status, "qe_calculate_mayer")

    def get_mayer_dimensions(self) -> int:
        n = c_int(0)
        status = _lib.qe_get_mayer_dimensions(byref(n))
        _check_status(status, "qe_get_mayer_dimensions")
        return n.value

    def get_mayer_metadata(self):
        wfn = c_int(0)
        has_spin = c_int(0)
        status = _lib.qe_get_mayer_metadata(byref(wfn), byref(has_spin))
        _check_status(status, "qe_get_mayer_metadata")
        return wfn.value, bool(has_spin.value)

    def get_mayer_result(self, result_id: int, ncenter: int):
        import numpy as np
        buf = np.empty((ncenter, ncenter), dtype=np.float64, order="F")
        status = _lib.qe_get_mayer_result(result_id, buf.ctypes.data_as(c_void_p), buf.size)
        _check_status(status, "qe_get_mayer_result")
        return buf

    def release_system(self) -> None:
        status = _lib.qe_release_system()
        _check_status(status, "qe_release_system")

    # ------------------------------------------------------------------
    # Molecular Data Model 1.0 (additive)
    # ------------------------------------------------------------------
    @staticmethod
    def has_v1() -> bool:
        return _HAS_V1

    def _require_v1(self) -> None:
        if not _HAS_V1:
            raise QeUnsupported(
                7,
                "this libqe_multiwfn.so does not expose the v1 model ABI",
                "NativeAPI.v1",
            )

    def enable_open_shell_v1(self, enable: bool) -> None:
        self._require_v1()
        status = _lib.qe_v1_enable_open_shell(1 if enable else 0)
        _check_status(status, "qe_v1_enable_open_shell")

    def begin_system_v1(self, ncenter: int, nbasis: int, nprims: int,
                        wfntype: int) -> None:
        self._require_v1()
        status = _lib.qe_v1_model_begin(ncenter, nbasis, nprims, wfntype)
        _check_status(status, "qe_v1_model_begin")

    def set_atoms_v1(self, atomic_numbers, coordinates_fortran, unit: int) -> None:
        self._require_v1()
        z = np.asarray(atomic_numbers, dtype=np.int32)
        coords = np.asfortranarray(coordinates_fortran, dtype=np.float64)
        status = _lib.qe_v1_set_atoms(
            int(z.size), z.ctypes.data_as(c_void_p),
            coords.ctypes.data_as(c_void_p), int(unit),
        )
        _check_status(status, "qe_v1_set_atoms")

    def set_shells_v1(self, center, l, prim_start, prim_end, cartesian) -> None:
        self._require_v1()
        arrays = [np.asarray(a, dtype=np.int32) for a in
                  (center, l, prim_start, prim_end, cartesian)]
        n = int(arrays[0].size)
        ptrs = [a.ctypes.data_as(c_void_p) for a in arrays]
        status = _lib.qe_v1_set_shells(n, *ptrs)
        _check_status(status, "qe_v1_set_shells")

    def set_primitives_v1(self, center, type_, exponent, coefficient,
                          normalization=None, shell_index=None) -> None:
        self._require_v1()
        ci = np.asarray(center, dtype=np.int32)
        ti = np.asarray(type_, dtype=np.int32)
        ex = np.asarray(exponent, dtype=np.float64)
        co = np.asarray(coefficient, dtype=np.float64)
        no = None if normalization is None else np.asarray(normalization, dtype=np.float64)
        si = None if shell_index is None else np.asarray(shell_index, dtype=np.int32)
        status = _lib.qe_v1_set_primitives(
            int(ci.size),
            ci.ctypes.data_as(c_void_p),
            ti.ctypes.data_as(c_void_p),
            ex.ctypes.data_as(c_void_p),
            co.ctypes.data_as(c_void_p),
            None if no is None else no.ctypes.data_as(c_void_p),
            None if si is None else si.ctypes.data_as(c_void_p),
        )
        _check_status(status, "qe_v1_set_primitives")

    def set_ao_map_v1(self, center, shell_index=None, multiwfn_type=None,
                      angular_type=None, source_index=None) -> None:
        self._require_v1()
        def _p(a):
            return None if a is None else np.asarray(a, dtype=np.int32).ctypes.data_as(c_void_p)
        ci = np.asarray(center, dtype=np.int32)
        at = np.asarray(angular_type, dtype=np.int32)
        status = _lib.qe_v1_set_ao_map(
            int(ci.size), ci.ctypes.data_as(c_void_p),
            _p(shell_index), _p(multiwfn_type), at.ctypes.data_as(c_void_p),
            _p(source_index),
        )
        _check_status(status, "qe_v1_set_ao_map")

    def set_angular_canonical_v1(self, canonical: bool) -> None:
        self._require_v1()
        status = _lib.qe_v1_set_angular_canonical(1 if canonical else 0)
        _check_status(status, "qe_v1_set_angular_canonical")

    def set_ao_normalization_v1(self, source_self_overlap, contraction_normalization,
                                convention) -> None:
        self._require_v1()
        so = np.asarray(source_self_overlap, dtype=np.float64)
        cn = np.asarray(contraction_normalization, dtype=np.float64)
        cv = np.asarray(convention, dtype=np.int32)
        status = _lib.qe_v1_set_ao_normalization(
            int(so.size), so.ctypes.data_as(c_void_p),
            cn.ctypes.data_as(c_void_p), cv.ctypes.data_as(c_void_p)
        )
        _check_status(status, "qe_v1_set_ao_normalization")

    def set_density_v1(self, nbasis: int, representation: int,
                       density_total, density_alpha=None, density_beta=None) -> None:
        self._require_v1()
        dt = np.asfortranarray(density_total, dtype=np.float64)
        da = None if density_alpha is None else np.asfortranarray(density_alpha, dtype=np.float64)
        db = None if density_beta is None else np.asfortranarray(density_beta, dtype=np.float64)
        status = _lib.qe_v1_set_density(
            int(nbasis), int(representation),
            dt.ctypes.data_as(c_void_p),
            None if da is None else da.ctypes.data_as(c_void_p),
            None if db is None else db.ctypes.data_as(c_void_p),
        )
        _check_status(status, "qe_v1_set_density")

    def set_overlap_v1(self, nbasis: int, representation: int, overlap) -> None:
        self._require_v1()
        ov = np.asfortranarray(overlap, dtype=np.float64)
        status = _lib.qe_v1_set_overlap(
            int(nbasis), int(representation), ov.ctypes.data_as(c_void_p)
        )
        _check_status(status, "qe_v1_set_overlap")

    def set_orbitals_v1(self, nmo: int, ncoeff: int, representation: int,
                        layout: int, coefficients, energies, occupations,
                        spin) -> None:
        self._require_v1()
        cf = np.asfortranarray(coefficients, dtype=np.float64)
        en = np.asarray(energies, dtype=np.float64)
        oc = np.asarray(occupations, dtype=np.float64)
        sp = np.asarray(spin, dtype=np.int32)
        status = _lib.qe_v1_set_orbitals(
            int(nmo), int(ncoeff), int(representation), int(layout),
            cf.ctypes.data_as(c_void_p), en.ctypes.data_as(c_void_p),
            oc.ctypes.data_as(c_void_p), sp.ctypes.data_as(c_void_p),
        )
        _check_status(status, "qe_v1_set_orbitals")

    def commit_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_model_commit()
        _check_status(status, "qe_v1_model_commit")

    def release_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_model_release()
        _check_status(status, "qe_v1_model_release")

    def generate_density_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_generate_density()
        _check_status(status, "qe_v1_generate_density")

    def get_generated_density_dimensions_v1(self) -> int:
        self._require_v1()
        n = c_int(0)
        status = _lib.qe_v1_get_generated_density_dimensions(byref(n))
        _check_status(status, "qe_v1_get_generated_density_dimensions")
        return int(n.value)

    def get_generated_density_v1(self, result_id: int, nbasis: int):
        self._require_v1()
        buf = np.empty((nbasis, nbasis), dtype=np.float64, order="F")
        status = _lib.qe_v1_get_generated_density(
            int(result_id), buf.ctypes.data_as(c_void_p), int(buf.size)
        )
        _check_status(status, "qe_v1_get_generated_density")
        return buf

    def generate_overlap_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_generate_overlap()
        _check_status(status, "qe_v1_generate_overlap")

    def generate_cartesian_overlap_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_generate_cartesian_overlap()
        _check_status(status, "qe_v1_generate_cartesian_overlap")

    def get_overlap_dimensions_v1(self):
        self._require_v1()
        n = c_int(0); nc = c_int(0); np = c_int(0)
        status = _lib.qe_v1_get_overlap_dimensions(byref(n), byref(nc), byref(np))
        _check_status(status, "qe_v1_get_overlap_dimensions")
        return int(n.value), int(nc.value), int(np.value)

    def get_generated_overlap_v1(self, n: int):
        self._require_v1()
        buf = np.empty((n, n), dtype=np.float64, order="F")
        status = _lib.qe_v1_get_generated_overlap(
            buf.ctypes.data_as(c_void_p), int(buf.size)
        )
        _check_status(status, "qe_v1_get_generated_overlap")
        return buf

    def get_generated_cartesian_overlap_v1(self, n: int):
        self._require_v1()
        buf = np.empty((n, n), dtype=np.float64, order="F")
        status = _lib.qe_v1_get_generated_cartesian_overlap(
            buf.ctypes.data_as(c_void_p), int(buf.size)
        )
        _check_status(status, "qe_v1_get_generated_cartesian_overlap")
        return buf

    def build_electronic_state_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_build_electronic_state()
        _check_status(status, "qe_v1_build_electronic_state")

    def generate_primitive_density_v1(self) -> None:
        self._require_v1()
        status = _lib.qe_v1_generate_primitive_density()
        _check_status(status, "qe_v1_generate_primitive_density")

    def get_primitive_density_dimensions_v1(self) -> int:
        self._require_v1()
        n = c_int(0)
        status = _lib.qe_v1_get_primitive_density_dimensions(byref(n))
        _check_status(status, "qe_v1_get_primitive_density_dimensions")
        return int(n.value)

    def get_generated_primitive_density_v1(self, result_id: int, nprims: int):
        self._require_v1()
        buf = np.empty((nprims, nprims), dtype=np.float64, order="F")
        status = _lib.qe_v1_get_generated_primitive_density(
            int(result_id), buf.ctypes.data_as(c_void_p), int(buf.size)
        )
        _check_status(status, "qe_v1_get_generated_primitive_density")
        return buf

    def get_primitive_overlap_v1(self, nprims: int):
        self._require_v1()
        buf = np.empty((nprims, nprims), dtype=np.float64, order="F")
        status = _lib.qe_v1_get_primitive_overlap(
            buf.ctypes.data_as(c_void_p), int(buf.size)
        )
        _check_status(status, "qe_v1_get_primitive_overlap")
        return buf

    def get_readiness_v1(self) -> int:
        self._require_v1()
        flags = c_int(0)
        status = _lib.qe_v1_get_readiness(byref(flags))
        _check_status(status, "qe_v1_get_readiness")
        return int(flags.value)

    @property
    def version(self) -> str:
        v = _lib.qe_get_version()
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="replace")
        return str(v)


NATIVE_LIBRARY_VERSION = NativeAPI().version
