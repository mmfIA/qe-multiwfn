! ===================================================================
!  qe_c_types.f90
!  Shared C-interoperable type definitions for QE-Multiwfn.
! ===================================================================
module qe_c_types
    use, intrinsic :: iso_c_binding
    implicit none
    public

    ! Re-export the basic interoperable kinds so other modules don't
    ! need to repeat `use, intrinsic :: iso_c_binding`.
    public :: c_int, c_double, c_char, c_size_t, c_ptr, c_null_char

    ! Maximum length of error messages stored in qe_error_handler.
    integer, parameter :: QE_ERRMSG_LEN = 1024

    ! Maximum length of the version string.
    integer, parameter :: QE_VERSION_LEN = 64

    ! Mayer result identifiers — mirror the C header.
    integer(c_int), parameter :: QE_MAYER_TOTAL = 0
    integer(c_int), parameter :: QE_MAYER_ALPHA = 1
    integer(c_int), parameter :: QE_MAYER_BETA  = 2

end module qe_c_types
