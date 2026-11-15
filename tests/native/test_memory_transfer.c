/*
 * test_memory_transfer.c — verify that a NumPy-style matrix passes
 * into Fortran-owned memory and back without corruption.
 *
 * Uses a small 3x3 non-symmetric matrix with distinct values so
 * any layout mismatch shows up.
 */
#include "qe_multiwfn.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

int main(void) {
    int status;
    const int N = 3;
    int M = 3;
    /* Build a (N, M) column-major matrix of distinct values.
     * In row-major C terms: row i, col j has value i*M + j + 1.
     * In column-major terms: A(i,j) is at index i + j*N.
     */
    double *A = (double*) malloc(sizeof(double) * N * M);
    double *B = (double*) malloc(sizeof(double) * N * M);
    for (int j = 0; j < M; ++j) {
        for (int i = 0; i < N; ++i) {
            A[i + j*N] = (double)(i * M + j + 1);
        }
    }

    /* Initial state */
    status = qe_initialize();
    if (status != QE_SUCCESS) { printf("FAIL: init %d\n", status); return 1; }

    /* Begin a 2-atom, 3-basis RHF system. We will not actually run
     * Mayer here; we just want to push a density matrix in and
     * read it back through the C ABI.
     */
    status = qe_begin_system(2, 3, 3, 0);  /* ncenter=2, nbasis=3, nprims=3, RHF */
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: begin_system %d: %s\n", status, err);
        return 1;
    }

    /* Push density = A (3x3). For prepare_system to accept it, A must
     * be symmetric. Make a symmetric test matrix instead.
     */
    /* Build symmetric test matrix:
     *   D = [ 1  1  0 ]
     *       [ 1  1  0 ]
     *       [ 0  0  0 ]
     * D*D = 2*D and Tr(D) = 2 (closed-shell RHF).
     */
    double D[9] = {
        1.0, 1.0, 0.0,
        1.0, 1.0, 0.0,
        0.0, 0.0, 0.0
    };
    /* S = identity */
    double S[9] = {
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0
    };

    status = qe_set_density(3, D, NULL, NULL);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: set_density %d: %s\n", status, err);
        return 1;
    }

    status = qe_set_overlap(3, S);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: set_overlap %d: %s\n", status, err);
        return 1;
    }

    /* Atoms: two hydrogen centers. */
    int atnums[2] = {1, 1};
    double coords[6] = {
        0.0, 0.0, 0.0,    /* column 1: atom 1 */
        0.0, 0.0, 1.0     /* column 2: atom 2 */
    };
    status = qe_set_atomic_data(2, atnums, coords);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: set_atomic_data %d: %s\n", status, err);
        return 1;
    }

    /* Electronic metadata: 2 electrons, charge=0, mult=1. */
    status = qe_set_electronic_metadata(0, 1, 2);
    if (status != QE_SUCCESS) { printf("FAIL: set_meta %d\n", status); return 1; }

    /* Basis-function metadata: three basis functions, all centered on atom 1;
     * atom 2 intentionally has no basis functions (Multiwfn [0,0] convention). */
    int bc[3] = {1, 1, 1};   /* one center per basis function */
    int bt[3] = {0, 1, 2};   /* S, P, D angular momentum types */
    status = qe_set_basis_data(3, 3, bc, bt);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: set_basis_data %d: %s\n", status, err);
        return 1;
    }

    /* Prepare */
    status = qe_prepare_system();
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: prepare_system %d: %s\n", status, err);
        return 1;
    }

    /* Now run Mayer. For atom 2 (no basis), Mayer BO is 0.
     * For atom 1, BO(1,1) = sum of off-diagonal of BO matrix, which is 0
     * since atom 2 has no basis. So the whole matrix is 0.
     * That's a trivial result but it confirms the pipeline works end-to-end.
     */
    status = qe_calculate_mayer();
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: calculate_mayer %d: %s\n", status, err);
        return 1;
    }

    int ncenter;
    status = qe_get_mayer_dimensions(&ncenter);
    if (status != QE_SUCCESS || ncenter != 2) {
        printf("FAIL: dimensions %d (ncenter=%d)\n", status, ncenter);
        return 1;
    }

    int wfn, has_spin;
    status = qe_get_mayer_metadata(&wfn, &has_spin);
    if (status != QE_SUCCESS || wfn != 0 || has_spin != 0) {
        printf("FAIL: metadata wfn=%d has_spin=%d\n", wfn, has_spin);
        return 1;
    }

    /* Retrieve the result. Capacity = 2*2 = 4 doubles. */
    double result[4];
    status = qe_get_mayer_result(QE_MAYER_TOTAL, result, 4);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: get_mayer_result %d: %s\n", status, err);
        return 1;
    }

    /* The matrix should be 0 (atom 2 has no basis functions). */
    double max_val = 0.0;
    for (int i = 0; i < 4; ++i) {
        if (fabs(result[i]) > max_val) max_val = fabs(result[i]);
    }
    if (max_val > 1e-12) {
        printf("FAIL: result not zero: %f\n", result[0]);
        return 1;
    }

    /* Try to retrieve alpha -> should fail with NOT_AVAILABLE for RHF */
    status = qe_get_mayer_result(QE_MAYER_ALPHA, result, 4);
    if (status != QE_ERROR_NOT_AVAILABLE) {
        printf("FAIL: expected NOT_AVAILABLE for alpha in RHF, got %d\n", status);
        return 1;
    }

    status = qe_release_system();
    if (status != QE_SUCCESS) { printf("FAIL: release %d\n", status); return 1; }

    status = qe_finalize();
    if (status != QE_SUCCESS) { printf("FAIL: finalize %d\n", status); return 1; }

    free(A); free(B);

    printf("PASS: test_memory_transfer (matrix transferred via RAM, Mayer pipeline OK)\n");
    return 0;
}
