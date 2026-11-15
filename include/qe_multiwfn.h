/*
 *====================================================================
 *  qe_multiwfn.h — public C ABI for libqe_multiwfn.so
 *
 *  Version: 0.2.0
 *
 *  This header is the ONLY contract between Python and Fortran.
 *  All functions return an int status code (0 = QE_SUCCESS).
 *  Detailed error messages can be retrieved via qe_get_last_error().
 *====================================================================
 */
#ifndef QE_MULTIWFN_H
#define QE_MULTIWFN_H

#include <stddef.h>   /* size_t */
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ----------- Version ----------- */
#define QE_MULTIWFN_VERSION_MAJOR 0
#define QE_MULTIWFN_VERSION_MINOR 2
#define QE_MULTIWFN_VERSION_PATCH 0

/* ----------- Status codes ----------- */
#define QE_SUCCESS                     0
#define QE_ERROR_INVALID_ARGUMENT     1
#define QE_ERROR_INVALID_STATE        2
#define QE_ERROR_INVALID_DIMENSION    3
#define QE_ERROR_NULL_POINTER         4
#define QE_ERROR_ALLOCATION            5
#define QE_ERROR_INCOMPLETE_STATE     6
#define QE_ERROR_UNSUPPORTED           7
#define QE_ERROR_CALCULATION           8
#define QE_ERROR_INTERNAL              9
#define QE_ERROR_COMPATIBILITY         10
#define QE_ERROR_MEMORY_LAYOUT         11
#define QE_ERROR_NOT_AVAILABLE         12

/* ----------- Engine states ----------- */
#define QE_STATE_UNINITIALIZED    0
#define QE_STATE_INITIALIZED      1
#define QE_STATE_SYSTEM_LOADED    2
#define QE_STATE_SYSTEM_PREPARED  3
#define QE_STATE_RESULT_AVAILABLE 4

/* ----------- Mayer result IDs ----------- */
#define QE_MAYER_TOTAL 0
#define QE_MAYER_ALPHA 1
#define QE_MAYER_BETA  2

/* ----------- Memory layout convention -----------
 *
 * All matrices passed between Python and Fortran are column-major
 * (Fortran order). In NumPy:
 *
 *     arr = np.asfortranarray(arr, dtype=np.float64)
 *
 * Matrices:
 *   - coordinates : shape (3, ncenter)        in Fortran order
 *                                       (= (ncenter, 3).T in NumPy)
 *   - density_*   : shape (nbasis, nbasis)
 *   - overlap      : shape (nbasis, nbasis)
 *   - mayer result : shape (ncenter, ncenter)
 *
 * Arrays of integers (atomic numbers, basis center, basis type) are
 * 1-D int32 arrays of length ncenter, nbasis or nprims respectively.
 *
 * The library COPIES all input buffers into Fortran-owned memory.
 * The caller is free to deallocate the input arrays after each call
 * returns. Output buffers (e.g. Mayer results) are WRITTEN into
 * caller-allocated memory; the library does not retain pointers.
 */

/* ============================================================
 *  Lifecycle
 * ============================================================ */

/* Initialize the engine. Must be called once before any other API.
 * Returns QE_SUCCESS or an error code. */
int qe_initialize(void);

/* Finalize the engine, releasing all internal state.
 * After this call the engine is in QE_STATE_UNINITIALIZED. */
int qe_finalize(void);

/* Query the current engine state. *state is set to one of QE_STATE_*. */
int qe_get_engine_state(int *state);

/* Retrieve the last error message. The message is copied into the
 * caller-provided buffer (truncated if longer than buffer_capacity-1).
 * Always null-terminated. Returns QE_SUCCESS on success. */
int qe_get_last_error(char *buffer, int buffer_capacity);

/* ============================================================
 *  System loading (begin / set fields / prepare / release)
 * ============================================================ */

/* Begin a new molecular system. Allocates internal scratch state.
 * Resets any previously-loaded system that was not yet released.
 *
 *   ncenter  - number of atoms (>= 1)
 *   nbasis   - number of basis functions (>= 1)
 *   nprims   - number of primitive Gaussians (>= 1, can equal nbasis)
 *   wfntype  - Multiwfn code; this release accepts only 0 (closed-shell RHF)
 */
int qe_begin_system(int ncenter, int nbasis, int nprims, int wfntype);

/* Atomic numbers and Cartesian coordinates.
 *
 *   atomic_numbers : int32[ncenter]
 *   coordinates    : float64[3 * ncenter], Fortran-order (3, ncenter)
 *
 * Coordinates must be in Bohr (consistent with Multiwfn's internal
 * convention). Callers converting from Angstrom should multiply by
 * 1/0.529177210903 before passing. */
int qe_set_atomic_data(int ncenter,
                       const int    *atomic_numbers,
                       const double *coordinates);

/* Electronic metadata: total charge, spin multiplicity, total electron count.
 * If nelectron <= 0 the library will derive it from atomic_numbers and charge. */
int qe_set_electronic_metadata(int charge, int multiplicity, int nelectron);

/* Basis function metadata:
 *
 *   nbasis       - number of basis functions (must match qe_begin_system)
 *   nprims       - number of primitive Gaussians
 *   basis_center : int32[nbasis], 1-based atom index for each basis function
 *   basis_type   : int32[nbasis], Multiwfn type code (0=S, 1=P, 2=D, ...)
 *
 * Optional: caller may pass NULL if not yet known. The state builder
 * will then refuse qe_prepare_system() with QE_ERROR_INCOMPLETE_STATE. */
int qe_set_basis_data(int nbasis, int nprims,
                      const int *basis_center,
                      const int *basis_type);

/* Density matrices.
 *
 *   density_total  : float64[nbasis * nbasis], Fortran order
 *   density_alpha   : float64[nbasis * nbasis] or NULL (RHF/ROHF)
 *   density_beta    : float64[nbasis * nbasis] or NULL (RHF/ROHF)
 *
 * This release accepts only wfntype==0 (RHF); pass NULL for alpha/beta. */
int qe_set_density(int nbasis,
                    const double *density_total,
                    const double *density_alpha,
                    const double *density_beta);

/* Overlap matrix S.
 *
 *   overlap : float64[nbasis * nbasis], Fortran order, symmetric.
 *
 * In v0.1.1 the caller MUST supply S directly; we do not auto-compute
 * it from the basis set (that requires a full integral engine,
 * deferred to a later version). */
int qe_set_overlap(int nbasis, const double *overlap);

/* Validate everything and build internal Multiwfn state.
 * Computes basstart/basend from basis_center, validates dimensions,
 * checks for NaN/Inf, and (for RHF) verifies Tr(P·S) ≈ n_electrons. */
int qe_prepare_system(void);

/* Release the currently-loaded system, freeing molecular state.
 * The engine returns to QE_STATE_INITIALIZED. */
int qe_release_system(void);

/* ============================================================
 *  Mayer bond order analysis
 * ============================================================ */

/* Compute Mayer bond order using the original Multiwfn routine
 * calcMayerbndord(). Requires the system to be in
 * QE_STATE_SYSTEM_PREPARED. On success, transitions to
 * QE_STATE_RESULT_AVAILABLE. */
int qe_calculate_mayer(void);

/* Get the dimension of the Mayer result matrices (= ncenter). */
int qe_get_mayer_dimensions(int *ncenter);

/* Get Mayer metadata:
 *
 *   *wavefunction_type   : 0/1/2/3/4
 *   *has_spin_components : 1 if alpha/beta are populated (wfntype=1,2,4)
 *                          0 if only the total matrix is meaningful
 *                          (wfntype=0,3). For the latter, requesting
 *                          QE_MAYER_ALPHA or QE_MAYER_BETA will return
 *                          a zero-filled matrix and a warning code. */
int qe_get_mayer_metadata(int *wavefunction_type, int *has_spin_components);

/* Retrieve one Mayer result matrix.
 *
 *   result_id        : QE_MAYER_TOTAL / _ALPHA / _BETA
 *   buffer           : caller-allocated, capacity = ncenter*ncenter
 *   buffer_capacity  : number of doubles the buffer can hold
 *
 * Returns:
 *   QE_SUCCESS                 - matrix copied
 *   QE_ERROR_INVALID_STATE     - no result available
 *   QE_ERROR_NOT_AVAILABLE     - alpha/beta requested but wfntype is RHF
 *   QE_ERROR_INVALID_ARGUMENT  - bad result_id
 *   QE_ERROR_INVALID_DIMENSION - buffer too small
 *
 * The matrix is written in Fortran column-major order. */
int qe_get_mayer_result(int result_id, double *buffer, int buffer_capacity);

/* ============================================================
 *  Diagnostics
 * ============================================================ */

/* Returns the version string of the library (static, never NULL). */
const char *qe_get_version(void);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* QE_MULTIWFN_H */
