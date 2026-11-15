! ===================================================================
!  qe_status.f90
!  Status code definitions mirroring include/qe_multiwfn.h
! ===================================================================
module qe_status
    use, intrinsic :: iso_c_binding
    implicit none
    public

    integer(c_int), parameter :: QE_SUCCESS                     =  0
    integer(c_int), parameter :: QE_ERROR_INVALID_ARGUMENT     =  1
    integer(c_int), parameter :: QE_ERROR_INVALID_STATE        =  2
    integer(c_int), parameter :: QE_ERROR_INVALID_DIMENSION    =  3
    integer(c_int), parameter :: QE_ERROR_NULL_POINTER         =  4
    integer(c_int), parameter :: QE_ERROR_ALLOCATION            =  5
    integer(c_int), parameter :: QE_ERROR_INCOMPLETE_STATE     =  6
    integer(c_int), parameter :: QE_ERROR_UNSUPPORTED           =  7
    integer(c_int), parameter :: QE_ERROR_CALCULATION           =  8
    integer(c_int), parameter :: QE_ERROR_INTERNAL              =  9
    integer(c_int), parameter :: QE_ERROR_COMPATIBILITY         = 10
    integer(c_int), parameter :: QE_ERROR_MEMORY_LAYOUT         = 11
    integer(c_int), parameter :: QE_ERROR_NOT_AVAILABLE         = 12

    ! Engine states
    integer(c_int), parameter :: QE_STATE_UNINITIALIZED    = 0
    integer(c_int), parameter :: QE_STATE_INITIALIZED      = 1
    integer(c_int), parameter :: QE_STATE_SYSTEM_LOADED    = 2
    integer(c_int), parameter :: QE_STATE_SYSTEM_PREPARED  = 3
    integer(c_int), parameter :: QE_STATE_RESULT_AVAILABLE = 4

contains

    ! Convert status code to a short human-readable string.
    function qe_status_name(code) result(name)
        integer(c_int), intent(in) :: code
        character(len=32) :: name
        select case (code)
        case (QE_SUCCESS);                    name = "QE_SUCCESS"
        case (QE_ERROR_INVALID_ARGUMENT);     name = "QE_ERROR_INVALID_ARGUMENT"
        case (QE_ERROR_INVALID_STATE);        name = "QE_ERROR_INVALID_STATE"
        case (QE_ERROR_INVALID_DIMENSION);    name = "QE_ERROR_INVALID_DIMENSION"
        case (QE_ERROR_NULL_POINTER);         name = "QE_ERROR_NULL_POINTER"
        case (QE_ERROR_ALLOCATION);            name = "QE_ERROR_ALLOCATION"
        case (QE_ERROR_INCOMPLETE_STATE);     name = "QE_ERROR_INCOMPLETE_STATE"
        case (QE_ERROR_UNSUPPORTED);           name = "QE_ERROR_UNSUPPORTED"
        case (QE_ERROR_CALCULATION);           name = "QE_ERROR_CALCULATION"
        case (QE_ERROR_INTERNAL);              name = "QE_ERROR_INTERNAL"
        case (QE_ERROR_COMPATIBILITY);         name = "QE_ERROR_COMPATIBILITY"
        case (QE_ERROR_MEMORY_LAYOUT);         name = "QE_ERROR_MEMORY_LAYOUT"
        case (QE_ERROR_NOT_AVAILABLE);         name = "QE_ERROR_NOT_AVAILABLE"
        case default;                          name = "QE_ERROR_UNKNOWN"
        end select
    end function qe_status_name

end module qe_status
