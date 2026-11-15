/*
 *====================================================================
 *  qe_multiwfn_v1.h — additive C ABI for the Molecular Data Model
 *
 *  Current tree: Python 0.3.0.dev0, MDM 1.1 (schema 1.1.0).
 *  Native ABI: 0.2.0 (intentionally preserved for compatibility).
 *
 *  These functions are ADDITIVE. The original 0.1.1 API in
 *  qe_multiwfn.h keeps its signatures and semantics unchanged.
 *  The current development library exposes 17 legacy symbols plus 27
 *  additive symbols (44 total); 15 symbols were added since the frozen
 *  29-symbol baseline and no legacy symbol was removed.
 *
 *  Memory rules (same as 0.1.1):
 *    - all matrices are column-major (Fortran order);
 *    - the library copies input buffers into Fortran-owned memory;
 *    - no pointer is retained after the call returns.
 *
 *  Index bases:
 *    - atom centers and shell/primitive indices are 1-based;
 *    - AO arrays have length nbasis; primitive arrays have length nprims.
 *====================================================================
 */
#ifndef QE_MULTIWFN_V1_H
#define QE_MULTIWFN_V1_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------- units ---------- */
#define QE_V1_UNIT_BOHR      0
#define QE_V1_UNIT_ANGSTROM  1

/* ---------- matrix representation ---------- */
#define QE_V1_REPR_AO_CURRENT_BASIS 0
#define QE_V1_REPR_PRIMITIVE_GTF    1
#define QE_V1_REPR_AO_CARTESIAN     2

/* ---------- coefficient representation ---------- */
#define QE_V1_COEFF_CONTRACTED 0
#define QE_V1_COEFF_PRIMITIVE  1

/* ---------- coefficient layout ---------- */
#define QE_V1_LAYOUT_ORBITAL_AO 0   /* (nmo, ncoeff) */
#define QE_V1_LAYOUT_AO_ORBITAL 1   /* (ncoeff, nmo) */

/* ---------- spin codes ---------- */
#define QE_V1_SPIN_TOTAL 0
#define QE_V1_SPIN_ALPHA 1
#define QE_V1_SPIN_BETA  2

/* ---------- readiness bitmask ---------- */
#define QE_V1_READY_GEOMETRY       (1 << 0)
#define QE_V1_READY_BASIS          (1 << 1)
#define QE_V1_READY_WAVEFUNCTION   (1 << 2)
#define QE_V1_READY_DENSITY        (1 << 3)
#define QE_V1_READY_OVERLAP        (1 << 4)
#define QE_V1_READY_SHELLS         (1 << 5)
#define QE_V1_READY_PRIMITIVES     (1 << 6)
#define QE_V1_READY_AO_MAP         (1 << 7)
#define QE_V1_READY_MAYER          (1 << 8)

/* ============================================================
 *  Open-shell capability (disabled by default)
 * ============================================================ */

/* Enable/disable additive open-shell execution.
 *   enable = 0 : default RHF-only behavior
 *   enable = 1 : allow UHF (wfntype=1) and ROHF (wfntype=2) if the supplied
 *                spin densities/orbitals pass the corresponding trace and
 *                idempotency validation
 * Post-HF (wfntype 3/4) remains rejected even when enabled.
 */
int qe_v1_enable_open_shell(int enable);

/* ============================================================
 *  Model lifecycle
 * ============================================================ */

/* Begin a v1 model. Requires qe_initialize() and INITIALIZED state. */
int qe_v1_model_begin(int ncenter, int nbasis, int nprims, int wfntype);

/* Validate the optional v1 components and build the Multiwfn state. */
int qe_v1_model_commit(void);

/* Release the current model/system. */
int qe_v1_model_release(void);

/* ============================================================
 *  Atoms / geometry
 *
 *   z       : int32[ncenter]
 *   coords  : double[3*ncenter], Fortran order (3, ncenter)
 *   unit    : QE_V1_UNIT_BOHR or QE_V1_UNIT_ANGSTROM
 *             (angstrom is converted to Bohr inside the library)
 * ============================================================ */
int qe_v1_set_atoms(int ncenter, const int *z, const double *coords, int unit);

/* ============================================================
 *  Basis description (optional for the Mayer path)
 * ============================================================ */

/* Shell table:
 *   center     : int32[nshell], 1-based atom index
 *   l          : int32[nshell], angular momentum (0=s, 1=p, ...)
 *   prim_start : int32[nshell], 1-based first primitive
 *   prim_end   : int32[nshell], 1-based last primitive
 *   cartesian  : int32[nshell], 1=cartesian, 0=spherical
 */
int qe_v1_set_shells(int nshell,
                     const int *center, const int *l,
                     const int *prim_start, const int *prim_end,
                     const int *cartesian);

/* Primitive table:
 *   center      : int32[nprims], 1-based atom index
 *   type        : int32[nprims], Multiwfn component code
 *   exponent    : double[nprims]
 *   coefficient : double[nprims]
 *   normalization : double[nprims] or NULL (defaults to 1.0)
 *   shell_index : int32[nprims] or NULL (0 = unknown)
 */
int qe_v1_set_primitives(int nprims,
                         const int *center, const int *type,
                         const double *exponent, const double *coefficient,
                         const double *normalization, const int *shell_index);

/* AO map:
 *   center       : int32[nbasis], 1-based atom index
 *   shell_index  : int32[nbasis] or NULL
 *   multiwfn_type: int32[nbasis] or NULL (component code)
 *   angular_type : int32[nbasis] (0=s, 1=p, 2=d, ...)
 *   source_index : int32[nbasis] or NULL (0-based source AO position)
 *
 * This mapping is authoritative for AO ordering and also fills the
 * legacy basis_center/basis_type arrays used by the Mayer path.
 */
int qe_v1_set_ao_map(int nbasis,
                     const int *center, const int *shell_index,
                     const int *multiwfn_type, const int *angular_type,
                     const int *source_index);

/* Per-AO normalization metadata (MDM 1.1).
 *   source_self_overlap : double[nbasis], source S_ii (>0)
 *   contraction_normalization : double[nbasis] (>0)
 *   normalization_convention : int32[nbasis]
 *       0=unknown, 1=source_normalized, 2=cartesian_explicit,
 *       3=cartesian_source_scaled, 4=cartesian_source_unnormalized
 */
int qe_v1_set_ao_normalization(int nbasis,
                               const double *source_self_overlap,
                               const double *contraction_normalization,
                               const int *normalization_convention);

/* Declare whether the loaded model carries canonical MDM 1.2 angular data.
 * The Fortran basis builder has no source metadata; f shells are accepted
 * only when canonical != 0. The default is 0 (legacy/source).
 */
int qe_v1_set_angular_canonical(int canonical);

/* ============================================================
 *  Matrices
 * ============================================================ */

/* Direct P/S path: representation must be QE_V1_REPR_AO_CURRENT_BASIS (0).
 * These matrices are not required when qe_v1_build_electronic_state() is
 * used to construct S/P from the canonical basis/orbitals. */
int qe_v1_set_density(int nbasis, int representation,
                      const double *density_total,
                      const double *density_alpha,
                      const double *density_beta);

int qe_v1_set_overlap(int nbasis, int representation, const double *overlap);

/* ============================================================
 *  Optional orbital data
 *
 *  Stored and validated for the canonical model. In the Phase 6
 *  full-state path these coefficients/occupations feed the original
 *  genP/genPprim adapters. They are optional for the direct P/S path.
 * ============================================================ */
int qe_v1_set_orbitals(int nmo, int ncoeff,
                       int coefficient_representation, int coefficient_layout,
                       const double *coefficients,
                       const double *energies, const double *occupations,
                       const int *spin);

/* ============================================================
 *  Readiness query
 * ============================================================ */
int qe_v1_get_readiness(int *flags);

/* ============================================================
 *  Original-Multiwfn electronic-state preparation
 *
 *  qe_v1_generate_density() builds CObasa/CObasb/MOocc/MOtype from
 *  the canonical model and calls the ORIGINAL genP routine.
 *  Requires the engine in PREPARED state. The generated density
 *  replaces Ptot/Palpha/Pbeta for a subsequent Mayer calculation.
 *
 *  qe_v1_get_generated_density_dimensions() returns nbasis.
 *  qe_v1_get_generated_density(result_id, buffer, capacity) copies
 *  total (0), alpha (1) or beta (2) in Fortran order.
 * ============================================================ */
int qe_v1_generate_density(void);
int qe_v1_get_generated_density_dimensions(int *nbasis);
int qe_v1_get_generated_density(int result_id, double *buffer, int capacity);

/* Original-Multiwfn overlap preparation.
 * qe_v1_generate_overlap() builds the basis tables and calls genSbas_curr.
 * qe_v1_generate_cartesian_overlap() calls genSbas (Cartesian intermediate).
 * Dimensions are returned by qe_v1_get_overlap_dimensions().
 */
int qe_v1_generate_overlap(void);
int qe_v1_generate_cartesian_overlap(void);
int qe_v1_get_overlap_dimensions(int *nbasis, int *nbasisCar, int *nprims);
int qe_v1_get_generated_overlap(double *buffer, int capacity);
int qe_v1_get_generated_cartesian_overlap(double *buffer, int capacity);

/* Full electronic-state construction from the canonical model using the
 * original Multiwfn routines: genSbas_curr + genP. No pre-extracted S/P
 * is required. Requires the engine in LOADED state; on success the engine
 * is PREPARED and Mayer may be calculated.
 */
int qe_v1_build_electronic_state(void);

/* Primitive-basis density from the ORIGINAL genPprim.
 * The primitive density is nprims x nprims and is kept separate from
 * the current-basis Ptot/Palpha/Pbeta. result_id: 0 total, 1 alpha, 2 beta.
 */
int qe_v1_generate_primitive_density(void);
int qe_v1_get_primitive_density_dimensions(int *nprims);
int qe_v1_get_generated_primitive_density(int result_id,
                                          double *buffer, int capacity);
/* Unnormalized-primitive overlap <g_i|g_j> (raw doSint) matching the
 * original genPprim CO convention (CO already includes primconnorm).
 * Used only to validate trace(P_prim*S_prim)=Ne. */
int qe_v1_get_primitive_overlap(double *buffer, int capacity);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* QE_MULTIWFN_V1_H */
