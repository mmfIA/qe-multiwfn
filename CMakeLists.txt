# ====================================================================
# QE-Multiwfn 0.3.0-dev — top-level CMakeLists.txt
#
# Builds libqe_multiwfn.so: a C-ABI-exposed Fortran library that wraps
# the scientific core of Multiwfn 2026.11.3 for in-memory use from Python.
#
# The native ABI/soname remains 0.2.0 intentionally; the Python package in
# this development tree is 0.3.0.dev0 and the canonical model is MDM 1.1.
# The original Multiwfn sources are kept verbatim under vendor/.
# The Phase 6 closure compiles the original genP/genPprim/genSbas/
# genSbas_curr dependencies; the full source distribution remains vendored.
# ====================================================================

cmake_minimum_required(VERSION 3.20)

project(qe_multiwfn
    VERSION 0.2.0
    DESCRIPTION "QuantumEngine-Multiwfn: Multiwfn as an in-memory Fortran library"
    LANGUAGES Fortran C)

# -------------------- Options --------------------
option(QE_BUILD_TESTS       "Build C ABI tests"                       ON)
option(QE_BUILD_EXAMPLES    "Build small example drivers"             OFF)
option(QE_ENABLE_OPENMP    "Enable OpenMP parallelism (NOT enabled in 0.1.x)" OFF)
option(QE_STRICT_LEGACY    "Use -std=legacy (needed for Multiwfn)"    ON)
option(QE_VERBOSE_MAKEFILE "Verbose build output"                     OFF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_Fortran_STANDARD 2008)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# -------------------- Module / output dirs --------------------
set(QE_MOD_DIR    ${CMAKE_BINARY_DIR}/mod)
set(QE_VENDOR_DIR ${CMAKE_SOURCE_DIR}/vendor/Multiwfn_2026.11.3_src_Linux)

file(MAKE_DIRECTORY ${QE_MOD_DIR})

# -------------------- Helpers --------------------
list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

include(CompilerOptions)
include(DetectBLAS)
include(FortranSources)

# -------------------- Fortran module search path --------------------
# Multiwfn sources use 'use X' for modules compiled elsewhere; we provide
# both the project mod dir and the vendor source dirs on the include path.
set(QE_FORTRAN_INCLUDES
    ${QE_MOD_DIR}
    ${QE_VENDOR_DIR}
    ${QE_VENDOR_DIR}/ext
    ${QE_VENDOR_DIR}/libreta_hybrid
    ${QE_VENDOR_DIR}/noGUI
    ${CMAKE_SOURCE_DIR}/src/bridge
    ${CMAKE_SOURCE_DIR}/src/engine
    ${CMAKE_SOURCE_DIR}/src/state
    ${CMAKE_SOURCE_DIR}/src/analysis
)

# -------------------- Multiwfn object library --------------------
# We compile each Multiwfn source into a separate .o so that the linker
# can pick only the symbols actually needed. This also lets us control
# the order of module compilation.
add_library(qe_multiwfn_objects OBJECT ${QE_MULTIWFN_SOURCES})

set_target_properties(qe_multiwfn_objects PROPERTIES
    Fortran_MODULE_DIRECTORY ${QE_MOD_DIR}
    POSITION_INDEPENDENT_CODE ON
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

target_include_directories(qe_multiwfn_objects PRIVATE ${QE_FORTRAN_INCLUDES})
target_compile_options(qe_multiwfn_objects PRIVATE ${QE_FORTRAN_FLAGS} -ffunction-sections -fdata-sections)

if(QE_VERBOSE_MAKEFILE)
    set_target_properties(qe_multiwfn_objects PROPERTIES VERBOSE 1)
endif()

# -------------------- QE bridge / engine / state / analysis sources --------------------
add_library(qe_bridge_objects OBJECT
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_c_types.f90
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_status.f90
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_error_handler.f90
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_memory.f90
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_hyp2f2_stub.f90
    ${CMAKE_SOURCE_DIR}/src/engine/qe_engine_state.f90
    ${CMAKE_SOURCE_DIR}/src/engine/qe_engine_lifecycle.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_molecular_state.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_state_builder.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_genp.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_gensbas.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_genpprim.f90
    ${CMAKE_SOURCE_DIR}/src/state/qe_electronic_state.f90
    ${CMAKE_SOURCE_DIR}/src/analysis/qe_analysis_state.f90
    ${CMAKE_SOURCE_DIR}/src/analysis/qe_mayer.f90
    ${CMAKE_SOURCE_DIR}/src/bridge/qe_c_api.f90
)

set_target_properties(qe_bridge_objects PROPERTIES
    Fortran_MODULE_DIRECTORY ${QE_MOD_DIR}
    POSITION_INDEPENDENT_CODE ON
)

target_include_directories(qe_bridge_objects PRIVATE ${QE_FORTRAN_INCLUDES})
target_compile_options(qe_bridge_objects PRIVATE ${QE_FORTRAN_FLAGS})

# -------------------- Shared library --------------------
add_library(qe_multiwfn SHARED $<TARGET_OBJECTS:qe_multiwfn_objects>
                                $<TARGET_OBJECTS:qe_bridge_objects>)

set_target_properties(qe_multiwfn PROPERTIES
    OUTPUT_NAME qe_multiwfn
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    Fortran_MODULE_DIRECTORY ${QE_MOD_DIR}
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

target_include_directories(qe_multiwfn PUBLIC
    ${QE_FORTRAN_INCLUDES}
    ${CMAKE_SOURCE_DIR}/include
)

find_package(LAPACK REQUIRED)
target_link_libraries(qe_multiwfn PUBLIC ${QE_BLAS_LIBRARIES} ${LAPACK_LIBRARIES})
if(UNIX AND NOT APPLE)
    target_link_options(qe_multiwfn PRIVATE
        "LINKER:--gc-sections"
        "LINKER:--version-script=${CMAKE_SOURCE_DIR}/cmake/qe_multiwfn.map")
endif()

# Make sure libgfortran is found at runtime
set_target_properties(qe_multiwfn PROPERTIES
    BUILD_RPATH ""
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "$ORIGIN"
)

# -------------------- Install --------------------
include(GNUInstallDirs)

install(TARGETS qe_multiwfn
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(FILES
    ${CMAKE_SOURCE_DIR}/include/qe_multiwfn.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# -------------------- Tests --------------------
if(QE_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# -------------------- Status summary --------------------
message(STATUS "")
message(STATUS "================ QE-Multiwfn ================")
message(STATUS "  Version            : ${PROJECT_VERSION}")
message(STATUS "  Build type         : ${CMAKE_BUILD_TYPE}")
message(STATUS "  Fortran compiler   : ${CMAKE_Fortran_COMPILER}")
message(STATUS "  Fortran flags      : ${QE_FORTRAN_FLAGS}")
message(STATUS "  BLAS libraries     : ${QE_BLAS_LIBRARIES}")
message(STATUS "  Multiwfn sources   : ${QE_MULTIWFN_COUNT} files")
message(STATUS "  Module output dir  : ${QE_MOD_DIR}")
message(STATUS "  Shared library     : libqe_multiwfn.so")
message(STATUS "=============================================")
message(STATUS "")
