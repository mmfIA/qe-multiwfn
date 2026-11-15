# ====================================================================
# CompilerOptions.cmake — gfortran flags compatible with Multiwfn source
# ====================================================================

# Base flags that work for both Multiwfn legacy code and our new modules.
set(QE_FORTRAN_FLAGS_BASE
    -cpp                # enable preprocessor (Multiwfn uses #ifdef _WIN32)
    -Wno-cpp            # legacy Fortran comments contain apostrophes / quotes
    -fPIC               # position-independent code (shared lib)
    -std=legacy         # accept real*8, do..end without integer, label-style gotos
    -fallow-argument-mismatch   # Multiwfn has some interfaces that mismatch
    -ffree-line-length-none     # don't enforce 132-col limit on Multiwfn's long lines
)

if(QE_STRICT_LEGACY)
    list(APPEND QE_FORTRAN_FLAGS_BASE -std=legacy)
endif()

# Build-type-specific flags
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(QE_FORTRAN_FLAGS
        ${QE_FORTRAN_FLAGS_BASE}
        -O0
        -g
        -fcheck=all
        -fbacktrace
        -ffpe-trap=invalid,zero,overflow
        -Wall
        -Wextra
        -Wno-unused-dummy-argument
        -Wno-conversion
        -Wno-compare-reals
    )
    message(STATUS "QE Fortran: DEBUG flags with -fcheck=all and -ffpe-trap")
else()
    set(QE_FORTRAN_FLAGS
        ${QE_FORTRAN_FLAGS_BASE}
        -O2
        -Wno-align-commons
        -Wno-unused-dummy-argument
        -Wno-conversion
    )
    message(STATUS "QE Fortran: RELEASE flags -O2")
endif()

# OpenMP is intentionally disabled in v0.1.1 (it would require thread-safety
# work in the Multiwfn globals that we have not yet validated).
if(QE_ENABLE_OPENMP)
    find_package(OpenMP REQUIRED COMPONENTS Fortran)
    list(APPEND QE_FORTRAN_FLAGS ${OpenMP_Fortran_FLAGS})
endif()

# C flags (only used for the 2F2 fallback if we ever need to compile C)
set(QE_C_FLAGS -fPIC -O2 -std=c11)
