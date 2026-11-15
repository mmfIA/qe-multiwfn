/*
 * test_v1_abi.c — additive Molecular Data Model 1.0 C ABI.
 *
 * Exercises:
 *   - qe_v1_model_begin / commit / release
 *   - qe_v1_set_atoms (Bohr), qe_v1_set_shells, qe_v1_set_primitives,
 *     qe_v1_set_ao_map, qe_v1_set_density, qe_v1_set_overlap
 *   - readiness bitmask
 *   - the unchanged Mayer result path
 *   - rejection of an invalid unit before any data is accepted
 *
 * H2 fixture (same matrices as the 0.1.1 test):
 *   P = [2/3 2/3; 2/3 2/3], S = [1 .5; .5 1]
 *   The expected Mayer matrix is all ones.
 */
#include "qe_multiwfn.h"
#include "qe_multiwfn_v1.h"

#include <math.h>
#include <stdio.h>

#define CHECK(call)                                                          \
    do {                                                                     \
        int _s = (call);                                                     \
        if (_s != QE_SUCCESS) {                                              \
            char _e[1024];                                                   \
            qe_get_last_error(_e, (int)sizeof(_e));                          \
            printf("FAIL: %s -> status=%d (%s)\n", #call, _s, _e);           \
            return 1;                                                        \
        }                                                                    \
    } while (0)

int main(void) {
    int status;
    char errbuf[1024];

    /* commit before begin must be rejected */
    status = qe_v1_model_commit();
    if (status != QE_ERROR_INVALID_STATE) {
        printf("FAIL: commit before begin was not rejected (status=%d)\n", status);
        return 1;
    }

    CHECK(qe_initialize());
    CHECK(qe_v1_model_begin(2, 2, 6, 0));

    int atnums[2] = {1, 1};
    /* Fortran order (3, ncenter): [x1,y1,z1, x2,y2,z2] */
    double coords[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 1.4};

    /* invalid unit must be rejected without corrupting the model */
    status = qe_v1_set_atoms(2, atnums, coords, 99);
    if (status != QE_ERROR_INVALID_ARGUMENT) {
        printf("FAIL: invalid unit was not rejected (status=%d)\n", status);
        return 1;
    }
    CHECK(qe_v1_set_atoms(2, atnums, coords, QE_V1_UNIT_BOHR));

    CHECK(qe_set_electronic_metadata(0, 1, 2));

    /* shell table: two s shells, 3 primitives each */
    int sh_center[2] = {1, 2};
    int sh_l[2] = {0, 0};
    int sh_ps[2] = {1, 4};
    int sh_pe[2] = {3, 6};
    int sh_cart[2] = {1, 1};
    CHECK(qe_v1_set_shells(2, sh_center, sh_l, sh_ps, sh_pe, sh_cart));

    /* STO-3G hydrogen exponents/coefficients (3 primitives per shell) */
    int pr_center[6] = {1, 1, 1, 2, 2, 2};
    int pr_type[6] = {1, 1, 1, 1, 1, 1};   /* Multiwfn component code 1 = S */
    double pr_exp[6] = {
        3.42525091, 0.62391373, 0.16885540,
        3.42525091, 0.62391373, 0.16885540
    };
    double pr_coef[6] = {
        0.15432897, 0.53532814, 0.44463454,
        0.15432897, 0.53532814, 0.44463454
    };
    int pr_shell[6] = {1, 1, 1, 2, 2, 2};
    CHECK(qe_v1_set_primitives(6, pr_center, pr_type, pr_exp, pr_coef,
                               NULL, pr_shell));

    /* AO map: 2 AOs, one per atom, both s */
    int ao_center[2] = {1, 2};
    int ao_shell[2] = {1, 2};
    int ao_mtype[2] = {1, 1};       /* component S */
    int ao_atype[2] = {0, 0};       /* angular s */
    int ao_source[2] = {0, 1};
    CHECK(qe_v1_set_ao_map(2, ao_center, ao_shell, ao_mtype, ao_atype, ao_source));

    /* P and S, column-major */
    double P[4] = {2.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0};
    double S[4] = {1.0, 0.5, 0.5, 1.0};
    CHECK(qe_v1_set_density(2, QE_V1_REPR_AO_CURRENT_BASIS, P, NULL, NULL));
    CHECK(qe_v1_set_overlap(2, QE_V1_REPR_AO_CURRENT_BASIS, S));

    CHECK(qe_v1_model_commit());

    int flags = 0;
    CHECK(qe_v1_get_readiness(&flags));
    int required = QE_V1_READY_GEOMETRY | QE_V1_READY_BASIS |
                   QE_V1_READY_DENSITY | QE_V1_READY_OVERLAP |
                   QE_V1_READY_SHELLS | QE_V1_READY_PRIMITIVES |
                   QE_V1_READY_AO_MAP | QE_V1_READY_MAYER;
    if ((flags & required) != required) {
        printf("FAIL: readiness flags=0x%x, required=0x%x\n", flags, required);
        return 1;
    }

    CHECK(qe_calculate_mayer());

    int ncenter = 0;
    CHECK(qe_get_mayer_dimensions(&ncenter));
    if (ncenter != 2) {
        printf("FAIL: ncenter=%d\n", ncenter);
        return 1;
    }
    double result[4];
    CHECK(qe_get_mayer_result(QE_MAYER_TOTAL, result, 4));
    for (int i = 0; i < 4; ++i) {
        if (fabs(result[i] - 1.0) > 1e-9) {
            printf("FAIL: result[%d]=%f, expected 1.0\n", i, result[i]);
            return 1;
        }
    }

    /* mutation after commit must still be rejected */
    status = qe_v1_set_density(2, QE_V1_REPR_AO_CURRENT_BASIS, P, NULL, NULL);
    if (status != QE_ERROR_INVALID_STATE) {
        printf("FAIL: v1 mutation after commit was not rejected (status=%d)\n", status);
        return 1;
    }

    CHECK(qe_v1_model_release());
    CHECK(qe_finalize());

    printf("PASS: test_v1_abi (shells/primitives/AO map + Mayer)\n");
    return 0;
}
