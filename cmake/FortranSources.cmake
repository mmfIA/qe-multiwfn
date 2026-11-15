# Build the upstream dependency closure required by the exposed scientific
# paths. The full, pristine Multiwfn source tree remains vendored.
#
# 0.2.0 minimal closure: define, util, bondorder.
# 0.3.0-dev (Phase 6): add sub, integral, function, PBC and their scientific
# dependencies so the original genP/genPprim/genSbas/genSbas_curr can be
# called without modifying vendor/.
set(QE_VENDOR_DIR ${CMAKE_SOURCE_DIR}/vendor/Multiwfn_2026.11.3_src_Linux)
set(QE_LIBRETA_DIR ${QE_VENDOR_DIR}/libreta_hybrid)

set(QE_MULTIWFN_SOURCES
    ${QE_VENDOR_DIR}/define.f90
    ${QE_VENDOR_DIR}/util.f90
    ${QE_VENDOR_DIR}/Bspline.f90
    ${QE_VENDOR_DIR}/ext/2F2.f90
    ${QE_LIBRETA_DIR}/boysfunc.f90
    ${QE_LIBRETA_DIR}/hrr_012345.f90
    ${QE_LIBRETA_DIR}/blockhrr_012345.f90
    ${QE_LIBRETA_DIR}/eanvrr_012345.f90
    ${QE_LIBRETA_DIR}/ean.f90
    ${QE_LIBRETA_DIR}/libreta.f90
    ${QE_LIBRETA_DIR}/ryspoly.f90
    ${QE_LIBRETA_DIR}/naiveeri.f90
    ${QE_VENDOR_DIR}/function.f90
    ${QE_VENDOR_DIR}/sub.f90
    ${QE_VENDOR_DIR}/integral.f90
    ${QE_VENDOR_DIR}/PBC.f90
    ${QE_VENDOR_DIR}/bondorder.f90
)
list(LENGTH QE_MULTIWFN_SOURCES QE_MULTIWFN_COUNT)
message(STATUS "Multiwfn dependency-closure sources in library: ${QE_MULTIWFN_COUNT} files")
