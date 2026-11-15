# ====================================================================
# tests/CMakeLists.txt — C-side tests for the C ABI
# ====================================================================

enable_language(C)

# ---- C ABI test: lifecycle, error handling ----
add_executable(test_lifecycle_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_lifecycle.c
)
target_link_libraries(test_lifecycle_c qe_multiwfn)
target_include_directories(test_lifecycle_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME lifecycle_c COMMAND test_lifecycle_c)

# ---- C ABI test: matrix transfer RAM-to-RAM ----
add_executable(test_memory_transfer_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_memory_transfer.c
)
target_link_libraries(test_memory_transfer_c qe_multiwfn)
target_include_directories(test_memory_transfer_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME memory_transfer_c COMMAND test_memory_transfer_c)

# ---- C ABI test: invalid-input handling ----
add_executable(test_error_handling_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_error_handling.c
)
target_link_libraries(test_error_handling_c qe_multiwfn)
target_include_directories(test_error_handling_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME error_handling_c COMMAND test_error_handling_c)

# ---- C ABI test: full Mayer pipeline ----
add_executable(test_mayer_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_mayer.c
)
target_link_libraries(test_mayer_c qe_multiwfn)
target_include_directories(test_mayer_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME mayer_c COMMAND test_mayer_c)

# ---- C ABI test: additive Molecular Data Model 1.0 API ----
add_executable(test_v1_abi_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_v1_abi.c
)
target_link_libraries(test_v1_abi_c qe_multiwfn)
target_include_directories(test_v1_abi_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME v1_abi_c COMMAND test_v1_abi_c)

# ---- C ABI test: additive open-shell flag (UHF opt-in) ----
add_executable(test_uhf_abi_c
    ${CMAKE_CURRENT_SOURCE_DIR}/native/test_uhf_abi.c
)
target_link_libraries(test_uhf_abi_c qe_multiwfn)
target_include_directories(test_uhf_abi_c PRIVATE ${CMAKE_SOURCE_DIR}/include)
add_test(NAME uhf_abi_c COMMAND test_uhf_abi_c)
