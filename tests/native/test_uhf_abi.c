/*
 * test_uhf_abi.c — additive open-shell flag semantics.
 *
 * The default remains RHF-only. qe_v1_enable_open_shell(1) permits UHF
 * (wfntype=1) only; ROHF/post-HF remain rejected.
 */
#include "qe_multiwfn.h"
#include "qe_multiwfn_v1.h"
#include <stdio.h>

int main(void) {
    int status;
    char err[1024];

    if (qe_initialize() != QE_SUCCESS) { printf("FAIL: init\n"); return 1; }

    /* default: UHF rejected */
    status = qe_v1_model_begin(2, 2, 2, 1);
    if (status != QE_ERROR_UNSUPPORTED) {
        printf("FAIL: default UHF was not rejected (status=%d)\n", status);
        return 1;
    }

    /* invalid enable value */
    status = qe_v1_enable_open_shell(2);
    if (status != QE_ERROR_INVALID_ARGUMENT) {
        printf("FAIL: invalid enable value accepted (status=%d)\n", status);
        return 1;
    }

    /* enable UHF */
    if (qe_v1_enable_open_shell(1) != QE_SUCCESS) {
        printf("FAIL: enable open shell\n"); return 1;
    }

    /* The legacy 0.1.1 entry point stays RHF-only even with the flag. */
    status = qe_begin_system(2, 2, 2, 1);
    if (status != QE_ERROR_UNSUPPORTED) {
        printf("FAIL: legacy begin accepted UHF (status=%d)\n", status);
        return 1;
    }

    /* ROHF is accepted with the flag (state only; no density here) */
    status = qe_v1_model_begin(2, 2, 2, 2);
    if (status != QE_SUCCESS) {
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: ROHF begin: %s\n", err);
        return 1;
    }
    /* Authorization cannot change while a system is loaded. */
    status = qe_v1_enable_open_shell(0);
    if (status != QE_ERROR_INVALID_STATE) {
        printf("FAIL: toggling authorization while loaded was not rejected (status=%d)\n", status);
        return 1;
    }
    if (qe_v1_model_release() != QE_SUCCESS) { printf("FAIL: ROHF release\n"); return 1; }

    /* Release must reset the authorization: no UHF without re-enabling. */
    status = qe_v1_model_begin(2, 2, 2, 1);
    if (status != QE_ERROR_UNSUPPORTED) {
        printf("FAIL: UHF authorization survived release (status=%d)\n", status);
        return 1;
    }

    /* Post-HF remains rejected after re-enabling the flag. */
    if (qe_v1_enable_open_shell(1) != QE_SUCCESS) {
        printf("FAIL: re-enable open shell\n"); return 1;
    }
    status = qe_v1_model_begin(2, 2, 2, 4);
    if (status != QE_ERROR_UNSUPPORTED) {
        printf("FAIL: post-HF was not rejected (status=%d)\n", status);
        return 1;
    }

    /* UHF is accepted now (model starts; no full density here) */
    status = qe_v1_model_begin(2, 2, 2, 1);
    if (status != QE_SUCCESS) {
        qe_get_last_error(err, sizeof(err));
        printf("FAIL: UHF begin: %s\n", err);
        return 1;
    }
    if (qe_v1_model_release() != QE_SUCCESS) { printf("FAIL: release\n"); return 1; }

    /* after release the flag is reset again */
    status = qe_v1_model_begin(2, 2, 2, 1);
    if (status != QE_ERROR_UNSUPPORTED) {
        printf("FAIL: UHF after release was not rejected (status=%d)\n", status);
        return 1;
    }
    if (qe_v1_enable_open_shell(0) != QE_SUCCESS) {
        printf("FAIL: disable open shell\n"); return 1;
    }

    if (qe_finalize() != QE_SUCCESS) { printf("FAIL: finalize\n"); return 1; }
    printf("PASS: test_uhf_abi (open-shell flag semantics)\n");
    return 0;
}
