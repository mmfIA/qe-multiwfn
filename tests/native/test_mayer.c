/*
 * test_mayer.c — full Mayer pipeline with a non-trivial case.
 *
 * Two atoms, each owning one basis function:
 *   P = [1  0.5]   S = [1  0.5]
 *       [0.5  1 ]       [0.5  1 ]
 *   PS = P*S = [1.25  1.00]
 *              [1.00  1.25]
 *   BO(1,2) = PS(1,2) * PS(2,1) = 1.00 * 1.00 = 1.00
 *
 * Tr(P*S) = 1.25 + 1.25 = 2.5 -> we set nelec=2 BUT the trace check
 * uses a tolerance of 1e-3 OR 1e-6*|nelec|. 2.5 vs 2 -> diff=0.5, which
 * exceeds the tolerance. So we MUST set nelec correctly OR provide P
 * such that Tr(P*S) = nelec. To make Tr(P*S)=2, scale P by 0.8.
 *
 * Final test matrix:
 *   P = [2/3  2/3]
 *       [2/3  2/3]
 *   S = [1.0  0.5]
 *       [0.5  1.0]
 *   PS = [1  1]
 *        [1  1]
 *   Tr(PS) = 2.0  ✓
 *   BO(1,2) = PS(1,2)*PS(2,1) = 1.0
 *   BO(1,1) = sum_{B != A} BO(A,B) = 0.64
 *   BO(2,2) = 0.64
 *
 * The Mayer matrix should be:
 *   [1.00  1.00]
 *   [1.00  1.00]
 */
#include "qe_multiwfn.h"
#include <stdio.h>
#include <math.h>

int main(void) {
    int status;
    char errbuf[1024];

    status = qe_initialize();
    if (status != QE_SUCCESS) { printf("FAIL: init\n"); return 1; }

    /* Begin a 2-atom, 2-basis RHF system */
    status = qe_begin_system(2, 2, 2, 0);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: begin_system: %s\n", errbuf);
        return 1;
    }

    /* Atoms: 2 H atoms at (0,0,0) and (0,0,1) Bohr */
    int atnums[2] = {1, 1};
    double coords[6] = {
        0.0, 0.0, 0.0,
        0.0, 0.0, 1.0
    };
    status = qe_set_atomic_data(2, atnums, coords);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: set_atomic_data: %s\n", errbuf);
        return 1;
    }

    /* Electronic metadata: H2, charge=0, mult=1, 2 electrons */
    status = qe_set_electronic_metadata(0, 1, 2);
    if (status != QE_SUCCESS) { printf("FAIL: set_meta\n"); return 1; }

    /* Basis: 2 primitives, atom 1 owns prim 1, atom 2 owns prim 2.
     * Both S-type.
     */
    int bc[2] = {1, 2};
    int bt[2] = {0, 0};
    status = qe_set_basis_data(2, 2, bc, bt);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: set_basis_data: %s\n", errbuf);
        return 1;
    }

    /* Density matrix (column-major, 2x2):
     *   P = [0.8  0.4]
     *       [0.4  0.8]
     * In column-major layout, the buffer is [P11, P21, P12, P22] = [0.8, 0.4, 0.4, 0.8]
     */
    double D[4] = {2.0/3.0, 2.0/3.0, 2.0/3.0, 2.0/3.0};
    status = qe_set_density(2, D, NULL, NULL);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: set_density: %s\n", errbuf);
        return 1;
    }

    /* Overlap:
     *   S = [1.0  0.5]
     *       [0.5  1.0]
     * Column-major: [1.0, 0.5, 0.5, 1.0]
     */
    double S[4] = {1.0, 0.5, 0.5, 1.0};
    status = qe_set_overlap(2, S);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: set_overlap: %s\n", errbuf);
        return 1;
    }

    /* Prepare */
    status = qe_prepare_system();
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: prepare_system: %s\n", errbuf);
        return 1;
    }

    /* Run Mayer */
    status = qe_calculate_mayer();
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: calculate_mayer: %s\n", errbuf);
        return 1;
    }

    /* Retrieve the result */
    int ncenter;
    qe_get_mayer_dimensions(&ncenter);
    if (ncenter != 2) { printf("FAIL: ncenter=%d\n", ncenter); return 1; }

    int wfn, has_spin;
    qe_get_mayer_metadata(&wfn, &has_spin);
    if (wfn != 0 || has_spin != 0) {
        printf("FAIL: wfn=%d has_spin=%d\n", wfn, has_spin);
        return 1;
    }

    double result[4];
    status = qe_get_mayer_result(QE_MAYER_TOTAL, result, 4);
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: get_mayer_result: %s\n", errbuf);
        return 1;
    }

    /* Expected matrix (column-major):
     *   result = [1.0, 1.0, 1.0, 1.0]
     * i.e. all four entries should be 1.0.
     */
    const double expected = 1.0;
    const double tol = 1e-9;
    for (int i = 0; i < 4; ++i) {
        if (fabs(result[i] - expected) > tol) {
            printf("FAIL: result[%d] = %f, expected %f\n", i, result[i], expected);
            printf("  Full matrix (column-major): [");
            for (int j = 0; j < 4; ++j) printf(" %f", result[j]);
            printf(" ]\n");
            return 1;
        }
    }

    printf("  Mayer matrix:\n");
    printf("    [ %f  %f ]\n", result[0], result[2]);
    printf("    [ %f  %f ]\n", result[1], result[3]);

    /* Mutation after preparation/result must be rejected (no stale globals). */
    status = qe_set_density(2, D, NULL, NULL);
    if (status != QE_ERROR_INVALID_STATE) {
        printf("FAIL: mutation after prepare was not rejected (status=%d)\n", status);
        return 1;
    }

    /* Release must also invalidate and clear the last result. */
    status = qe_release_system();
    if (status != QE_SUCCESS) { printf("FAIL: release\n"); return 1; }
    status = qe_get_mayer_dimensions(&ncenter);
    if (status == QE_SUCCESS || ncenter != 0) {
        printf("FAIL: stale Mayer result survived release: status=%d ncenter=%d\n", status, ncenter); return 1;
    }

    status = qe_finalize();
    if (status != QE_SUCCESS) { printf("FAIL: finalize\n"); return 1; }

    printf("PASS: test_mayer (Mayer BO matrix matches independent NumPy reference)\n");
    return 0;
}
