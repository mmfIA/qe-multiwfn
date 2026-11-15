# ====================================================================
# DetectBLAS.cmake — find a BLAS implementation
#
# Multiwfn's matmul_blas() only calls DGEMM. Any standard BLAS works.
# We prefer OpenBLAS (which is what we install via conda-forge), but
# also accept the system BLAS or Intel MKL if present.
# ====================================================================

# Try find_package first (modern CMake)
find_package(BLAS QUIET)

if(BLAS_FOUND)
    set(QE_BLAS_LIBRARIES ${BLAS_LIBRARIES})
    message(STATUS "BLAS: found via find_package(BLAS): ${BLAS_LIBRARIES}")
else()
    # Fall back to manual library search
    find_library(QE_OPENBLAS_LIB NAMES openblas PATHS ${CMAKE_Fortran_IMPLICIT_LINK_DIRS})
    if(QE_OPENBLAS_LIB)
        set(QE_BLAS_LIBRARIES ${QE_OPENBLAS_LIB})
        message(STATUS "BLAS: OpenBLAS found at ${QE_OPENBLAS_LIB}")
    else()
        find_library(QE_BLAS_LIB NAMES blas PATHS ${CMAKE_Fortran_IMPLICIT_LINK_DIRS})
        if(QE_BLAS_LIB)
            set(QE_BLAS_LIBRARIES ${QE_BLAS_LIB})
            message(STATUS "BLAS: generic libblas found at ${QE_BLAS_LIB}")
        else()
            message(FATAL_ERROR "BLAS not found. Install libblas-dev or libopenblas-dev.")
        endif()
    endif()
endif()

# Make sure linker can find the BLAS library directory
foreach(_lib ${QE_BLAS_LIBRARIES})
    get_filename_component(_libdir ${_lib} DIRECTORY)
    if(_libdir)
        link_directories(${_libdir})
    endif()
endforeach()

message(STATUS "BLAS libraries used by QE-Multiwfn: ${QE_BLAS_LIBRARIES}")
