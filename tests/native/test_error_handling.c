/*
 * test_error_handling.c — invalid inputs must return error codes,
 * never crash the process.
 */
#include "qe_multiwfn.h"
#include <stdio.h>

int main(void) {
    int status;
    char errbuf[1024];

    status = qe_initialize();
    if (status != QE_SUCCESS) { printf("FAIL: init\n"); return 1; }

    /* NULL pointer in qe_set_atomic_data */
    int n = 1;
    int atnums[1] = {1};
    status = qe_set_atomic_data(1, NULL, NULL);
    /* Engine is not even in SYSTEM_LOADED, so this should fail with INVALID_STATE. */
    if (status == QE_SUCCESS) {
        printf("FAIL: NULL pointer accepted without system loaded\n");
        return 1;
    }
    qe_get_last_error(errbuf, sizeof(errbuf));
    printf("  (expected) error: %s\n", errbuf);

    /* Try begin_system with bad dimensions */
    status = qe_begin_system(0, 3, 3, 0);  /* ncenter=0 */
    if (status == QE_SUCCESS) {
        printf("FAIL: begin_system with ncenter=0 accepted\n");
        return 1;
    }

    status = qe_begin_system(2, 0, 0, 0);  /* nbasis=0 */
    if (status == QE_SUCCESS) {
        printf("FAIL: begin_system with nbasis=0 accepted\n");
        return 1;
    }

    status = qe_begin_system(2, 3, 2, 0);  /* nprims<nbasis */
    if (status == QE_SUCCESS) {
        printf("FAIL: begin_system with nprims<nbasis accepted\n");
        return 1;
    }

    status = qe_begin_system(2, 3, 3, 99);  /* bad wfntype */
    if (status == QE_SUCCESS) {
        printf("FAIL: begin_system with wfntype=99 accepted\n");
        return 1;
    }

    /* Now a valid begin_system, then prepare without setting data */
    status = qe_begin_system(2, 3, 3, 0);
    if (status != QE_SUCCESS) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: valid begin_system rejected: %s\n", err);
        return 1;
    }

    status = qe_prepare_system();  /* missing data */
    if (status == QE_SUCCESS) {
        printf("FAIL: prepare accepted incomplete system\n");
        return 1;
    }
    qe_get_last_error(errbuf, sizeof(errbuf));
    printf("  (expected) incomplete-state error: %s\n", errbuf);

    /* Try qe_calculate_mayer before prepare -> INVALID_STATE */
    status = qe_calculate_mayer();
    if (status == QE_SUCCESS) {
        printf("FAIL: calculate_mayer accepted before prepare\n");
        return 1;
    }

    /* Try qe_get_mayer_dimensions before any result -> INVALID_STATE */
    int dim;
    status = qe_get_mayer_dimensions(&dim);
    if (status == QE_SUCCESS) {
        printf("FAIL: get_mayer_dimensions accepted without result\n");
        return 1;
    }

    /* Try qe_get_last_error with NULL buffer */
    status = qe_get_last_error(NULL, 100);
    if (status == QE_SUCCESS) {
        printf("FAIL: get_last_error accepted NULL buffer\n");
        return 1;
    }

    /* Clean up */
    qe_release_system();
    qe_finalize();

    printf("PASS: test_error_handling\n");
    return 0;
}
