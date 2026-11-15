/*
 * test_abi_negative.c — permanent negative ABI tests.
 *
 * Covers:
 *   E3  output-buffer capacity (with guard sentinels)
 *   E4  NULL pointers in required arguments
 *   E5  invalid result_id / unavailable spin component
 *   E6  invalid dimensions and dimension-product overflow
 *   E2b allocation failure propagation (RLIMIT_AS, Linux only)
 *
 * The overflow cases are rejected BEFORE any large allocation. The
 * allocation-failure case lowers RLIMIT_AS and requests a matrix that
 * cannot fit, then verifies that the engine stays usable.
 */
#include "qe_multiwfn.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#if defined(__linux__)
#include <sys/resource.h>
#endif

static int expect_status(const char *label, int got, int expected) {
    if (got != expected) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: %s: got status %d, expected %d (%s)\n",
               label, got, expected, err);
        return 1;
    }
    return 0;
}

static int fill_h2(void) {
    int status;
    int atnums[2] = {1, 1};
    double coords[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
    int bc[2] = {1, 2};
    int bt[2] = {0, 0};
    double P[4] = {2.0/3.0, 2.0/3.0, 2.0/3.0, 2.0/3.0};
    double S[4] = {1.0, 0.5, 0.5, 1.0};

    status = qe_set_atomic_data(2, atnums, coords);
    if (status != QE_SUCCESS) return status;
    status = qe_set_electronic_metadata(0, 1, 2);
    if (status != QE_SUCCESS) return status;
    status = qe_set_basis_data(2, 2, bc, bt);
    if (status != QE_SUCCESS) return status;
    status = qe_set_density(2, P, NULL, NULL);
    if (status != QE_SUCCESS) return status;
    status = qe_set_overlap(2, S);
    if (status != QE_SUCCESS) return status;
    return qe_prepare_system();
}

static int test_dimensions_and_null(void) {
    int status, state;
    int wfn, spin;
    int atnums[2] = {1, 1};
    double coords[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 1.0};
    int bc[2] = {1, 2};
    int bt[2] = {0, 0};
    double P[4] = {2.0/3.0, 2.0/3.0, 2.0/3.0, 2.0/3.0};
    double S[4] = {1.0, 0.5, 0.5, 1.0};
    double buf[6];
    int i;

    if (qe_initialize() != QE_SUCCESS) {
        printf("FAIL: initialize\n");
        return 1;
    }

    /* E6: invalid dimensions and checked products. */
    if (expect_status("negative ncenter",
                      qe_begin_system(-1, 1, 1, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("zero ncenter",
                      qe_begin_system(0, 1, 1, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("zero nbasis",
                      qe_begin_system(1, 0, 1, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("nprims < nbasis",
                      qe_begin_system(1, 2, 1, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("nbasis*nbasis overflow",
                      qe_begin_system(1, 50000, 50000, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("ncenter*ncenter overflow",
                      qe_begin_system(50000, 1, 1, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    if (expect_status("INT_MAX products",
                      qe_begin_system(1, INT_MAX, INT_MAX, 0),
                      QE_ERROR_INVALID_DIMENSION)) return 1;

    /* Failed dimension checks must not disturb the state machine. */
    state = -1;
    if (qe_get_engine_state(&state) != QE_SUCCESS ||
        state != QE_STATE_INITIALIZED) {
        printf("FAIL: state after rejected dimensions is %d\n", state);
        return 1;
    }

    if (expect_status("valid begin after rejections",
                      qe_begin_system(2, 2, 2, 0), QE_SUCCESS)) return 1;

    /* E4: required null pointers while SYSTEM_LOADED. */
    if (expect_status("set_atomic_data NULL",
                      qe_set_atomic_data(2, NULL, NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("set_basis_data NULL",
                      qe_set_basis_data(2, 2, NULL, NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("set_density NULL",
                      qe_set_density(2, NULL, NULL, NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("set_overlap NULL",
                      qe_set_overlap(2, NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("get_mayer_dimensions NULL",
                      qe_get_mayer_dimensions(NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("get_mayer_metadata NULL first",
                      qe_get_mayer_metadata(NULL, &spin),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("get_mayer_metadata NULL second",
                      qe_get_mayer_metadata(&wfn, NULL),
                      QE_ERROR_NULL_POINTER)) return 1;
    if (expect_status("get_last_error NULL",
                      qe_get_last_error(NULL, 100),
                      QE_ERROR_NULL_POINTER)) return 1;

    /* Valid data after the rejected NULLs. */
    if (qe_set_atomic_data(2, atnums, coords) != QE_SUCCESS) return 1;
    if (qe_set_electronic_metadata(0, 1, 2) != QE_SUCCESS) return 1;
    if (qe_set_basis_data(2, 2, bc, bt) != QE_SUCCESS) return 1;
    if (qe_set_density(2, P, NULL, NULL) != QE_SUCCESS) return 1;
    if (qe_set_overlap(2, S) != QE_SUCCESS) return 1;
    if (expect_status("prepare", qe_prepare_system(), QE_SUCCESS)) return 1;
    if (expect_status("calculate", qe_calculate_mayer(), QE_SUCCESS)) return 1;

    /* E3: capacity too small must not write anything, including guards. */
    for (i = 0; i < 6; ++i) buf[i] = 12345.0 + i;
    if (expect_status("capacity 3",
                      qe_get_mayer_result(QE_MAYER_TOTAL, buf, 3),
                      QE_ERROR_INVALID_DIMENSION)) return 1;
    for (i = 0; i < 6; ++i) {
        if (buf[i] != 12345.0 + i) {
            printf("FAIL: capacity rejection wrote buffer[%d]=%f\n", i, buf[i]);
            return 1;
        }
    }
    if (expect_status("capacity 4",
                      qe_get_mayer_result(QE_MAYER_TOTAL, buf, 4),
                      QE_SUCCESS)) return 1;
    for (i = 0; i < 4; ++i) {
        if (fabs(buf[i] - 1.0) > 1e-9) {
            printf("FAIL: Mayer result[%d]=%f\n", i, buf[i]);
            return 1;
        }
    }

    /* E5: invalid/unavailable result identifiers. */
    if (expect_status("invalid result_id",
                      qe_get_mayer_result(99, buf, 4),
                      QE_ERROR_INVALID_ARGUMENT)) return 1;
    if (expect_status("alpha unavailable",
                      qe_get_mayer_result(QE_MAYER_ALPHA, buf, 4),
                      QE_ERROR_NOT_AVAILABLE)) return 1;
    if (expect_status("result NULL with result available",
                      qe_get_mayer_result(QE_MAYER_TOTAL, NULL, 4),
                      QE_ERROR_NULL_POINTER)) return 1;

    if (qe_release_system() != QE_SUCCESS) return 1;
    if (qe_finalize() != QE_SUCCESS) return 1;
    printf("PASS: test_abi_negative (dimensions/NULL/capacity/result_id)\n");
    return 0;
}

static int test_allocation_failure(void) {
#if defined(__linux__)
    struct rlimit old_lim, low_lim;
    int status, state;

    if (qe_initialize() != QE_SUCCESS) {
        printf("FAIL: initialize for allocation test\n");
        return 1;
    }
    if (getrlimit(RLIMIT_AS, &old_lim) != 0) {
        printf("SKIP: getrlimit(RLIMIT_AS) unavailable\n");
        qe_finalize();
        return 0;
    }
    low_lim = old_lim;
    low_lim.rlim_cur = 256u * 1024u * 1024u;
    if (low_lim.rlim_max != RLIM_INFINITY && low_lim.rlim_cur > low_lim.rlim_max)
        low_lim.rlim_cur = low_lim.rlim_max;
    if (setrlimit(RLIMIT_AS, &low_lim) != 0) {
        printf("SKIP: setrlimit(RLIMIT_AS) unavailable\n");
        qe_finalize();
        return 0;
    }

    /* 20000^2 doubles (~3.2 GB) cannot fit under the lowered limit.
     * The checked product (400,000,000) is below INT_MAX, so this
     * reaches the allocation path, which must fail with STAT= and be
     * propagated as QE_ERROR_ALLOCATION. */
    status = qe_begin_system(1, 20000, 20000, 0);
    (void)setrlimit(RLIMIT_AS, &old_lim);

    if (status != QE_ERROR_ALLOCATION) {
        char err[1024];
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: expected QE_ERROR_ALLOCATION, got %d (%s)\n", status, err);
        qe_finalize();
        return 1;
    }
    state = -1;
    qe_get_engine_state(&state);
    if (state != QE_STATE_INITIALIZED) {
        printf("FAIL: state after allocation failure is %d\n", state);
        qe_finalize();
        return 1;
    }

    /* A subsequent valid system must work after the failed allocation. */
    if (expect_status("valid begin after allocation failure",
                      qe_begin_system(2, 2, 2, 0), QE_SUCCESS)) {
        qe_finalize();
        return 1;
    }
    if (expect_status("prepare after allocation failure",
                      fill_h2(), QE_SUCCESS)) {
        qe_finalize();
        return 1;
    }
    if (qe_release_system() != QE_SUCCESS) return 1;
    if (qe_finalize() != QE_SUCCESS) return 1;
    printf("PASS: test_abi_negative (allocation failure propagated)\n");
    return 0;
#else
    printf("SKIP: allocation failure test is Linux-only\n");
    return 0;
#endif
}

int main(void) {
    if (test_dimensions_and_null() != 0) return 1;
    if (test_allocation_failure() != 0) return 1;
    printf("PASS: test_abi_negative\n");
    return 0;
}
