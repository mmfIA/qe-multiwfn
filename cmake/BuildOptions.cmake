# ====================================================================
# BuildOptions.cmake — convenience options
# ====================================================================

# Print resolved configuration at configure time
macro(qe_status msg)
    message(STATUS "  ${msg}")
endmacro()
