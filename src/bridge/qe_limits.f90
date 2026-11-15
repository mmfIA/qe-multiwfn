! ===================================================================
!  qe_limits.f90
!  Internal checked-dimension helpers for the native bridge.
!
!  These routines validate dimensions and size products BEFORE any
!  allocation, copy, or offset calculation. They are internal to the
!  shared library and are not part of the C ABI.
! ===================================================================
module qe_limits
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    implicit none
    private

    ! Maximum index/size representable by the C/Fortran integer kind used
    ! by the ABI (integer(c_int), 32-bit on the supported targets).
    integer(c_int), parameter, public :: QE_MAX_INDEX = huge(1_c_int)

    public :: qe_check_dimension
    public :: qe_check_product
    public :: qe_check_sum
    public :: qe_check_capacity
    public :: qe_set_allocation_error

contains

    !-----------------------------------------------------------------
    ! Require 0 < n <= QE_MAX_INDEX.
    !-----------------------------------------------------------------
    function qe_check_dimension(n, name, routine, status) result(ok)
        integer(c_int), value, intent(in) :: n
        character(len=*), intent(in) :: name
        character(len=*), intent(in) :: routine
        integer(c_int), intent(out) :: status
        logical :: ok

        ok = .false.
        if (n <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" must be positive")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        if (n > QE_MAX_INDEX) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" exceeds the supported integer range")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        status = QE_SUCCESS
        ok = .true.
    end function qe_check_dimension

    !-----------------------------------------------------------------
    ! Require a > 0, b > 0 and a*b <= QE_MAX_INDEX.
    ! The multiplication is never performed before the bound test.
    !-----------------------------------------------------------------
    function qe_check_product(a, b, name, routine, status) result(ok)
        integer(c_int), value, intent(in) :: a, b
        character(len=*), intent(in) :: name
        character(len=*), intent(in) :: routine
        integer(c_int), intent(out) :: status
        logical :: ok

        ok = .false.
        if (a <= 0 .or. b <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" has a non-positive factor")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        if (a > QE_MAX_INDEX / b) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" exceeds the supported integer range")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        status = QE_SUCCESS
        ok = .true.
    end function qe_check_product

    !-----------------------------------------------------------------
    ! Require a >= 0, b >= 0 and a+b <= QE_MAX_INDEX.
    !-----------------------------------------------------------------
    function qe_check_sum(a, b, name, routine, status) result(ok)
        integer(c_int), value, intent(in) :: a, b
        character(len=*), intent(in) :: name
        character(len=*), intent(in) :: routine
        integer(c_int), intent(out) :: status
        logical :: ok

        ok = .false.
        if (a < 0 .or. b < 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" has a negative term")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        if (a > QE_MAX_INDEX - b) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" exceeds the supported integer range")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        status = QE_SUCCESS
        ok = .true.
    end function qe_check_sum

    !-----------------------------------------------------------------
    ! Require capacity >= n*n, with n*n checked before multiplication.
    !-----------------------------------------------------------------
    function qe_check_capacity(n, capacity, name, routine, status) result(ok)
        integer(c_int), value, intent(in) :: n, capacity
        character(len=*), intent(in) :: name
        character(len=*), intent(in) :: routine
        integer(c_int), intent(out) :: status
        logical :: ok

        ok = .false.
        if (.not. qe_check_product(n, n, name, routine, status)) return
        if (capacity < n * n) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, routine, &
                              trim(name)//" capacity is too small")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        status = QE_SUCCESS
        ok = .true.
    end function qe_check_capacity

    !-----------------------------------------------------------------
    subroutine qe_set_allocation_error(routine, what)
        character(len=*), intent(in) :: routine
        character(len=*), intent(in) :: what
        call qe_set_error(QE_ERROR_ALLOCATION, routine, &
                          "allocation failed for "//trim(what))
    end subroutine qe_set_allocation_error

end module qe_limits
