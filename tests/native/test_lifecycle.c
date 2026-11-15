/*
 * test_lifecycle.c — verify engine create / state / error / destroy
 */
#include "qe_multiwfn.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    int status, state;
    char errbuf[1024];

    /* Query state before initialize -> should fail */
    state = -999;
    status = qe_get_engine_state(&state);
    if (status != QE_SUCCESS) {
        printf("FAIL: qe_get_engine_state before init returned %d\n", status);
        return 1;
    }
    if (state != QE_STATE_UNINITIALIZED) {
        printf("FAIL: expected UNINITIALIZED, got %d\n", state);
        return 1;
    }

    /* Initialize */
    status = qe_initialize();
    if (status != QE_SUCCESS) {
        qe_get_last_error(errbuf, sizeof(errbuf));
        printf("FAIL: qe_initialize returned %d: %s\n", status, errbuf);
        return 1;
    }

    /* Re-initialize -> should fail */
    status = qe_initialize();
    if (status == QE_SUCCESS) {
        printf("FAIL: re-init should have failed\n");
        return 1;
    }

    /* State is now INITIALIZED */
    status = qe_get_engine_state(&state);
    if (state != QE_STATE_INITIALIZED) {
        printf("FAIL: expected INITIALIZED, got %d\n", state);
        return 1;
    }

    /* Try to call prepare without begin_system -> should fail */
    status = qe_prepare_system();
    if (status == QE_SUCCESS) {
        printf("FAIL: prepare without begin_system should have failed\n");
        return 1;
    }
    qe_get_last_error(errbuf, sizeof(errbuf));
    printf("  (expected) prepare-without-system error: %s\n", errbuf);

    /* Finalize */
    status = qe_finalize();
    if (status != QE_SUCCESS) {
        printf("FAIL: qe_finalize returned %d\n", status);
        return 1;
    }

    /* State should be UNINITIALIZED again */
    qe_get_engine_state(&state);
    if (state != QE_STATE_UNINITIALIZED) {
        printf("FAIL: expected UNINITIALIZED after finalize, got %d\n", state);
        return 1;
    }

    /* Re-finalize -> should fail */
    status = qe_finalize();
    if (status == QE_SUCCESS) {
        printf("FAIL: re-finalize should have failed\n");
        return 1;
    }

    /* Version check */
    const char *v = qe_get_version();
    printf("Library version: %s\n", v);

    printf("PASS: test_lifecycle\n");
    return 0;
}
