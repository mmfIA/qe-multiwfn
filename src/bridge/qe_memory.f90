! ===================================================================
!  qe_memory.f90
!  Safe helpers for converting C pointers to Fortran pointers,
!  copying data into Fortran-owned memory, and validating buffers.
! ===================================================================
module qe_memory
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    implicit none
    private

    public :: qe_pointer_to_real2d       ! c_ptr -> real(8), pointer (:,:)
    public :: qe_pointer_to_real1d       ! c_ptr -> real(8), pointer (:)
    public :: qe_pointer_to_int1d        ! c_ptr -> integer(4), pointer (:)
    public :: qe_copy_real2d
    public :: qe_copy_int1d
    public :: qe_validate_real_finite
    public :: qe_validate_real_finite_1d

contains

    !-----------------------------------------------------------------
    ! Map a C pointer to a Fortran real(c_double), pointer of shape (m,n).
    ! Returns .true. on success. Sets status on failure.
    !-----------------------------------------------------------------
    function qe_pointer_to_real2d(ptr, m, n, fptr, status) result(ok)
        type(c_ptr), value, intent(in)      :: ptr
        integer(c_int), value, intent(in)   :: m, n
        real(c_double), pointer, intent(out) :: fptr(:,:)
        integer(c_int), intent(out)         :: status
        logical :: ok

        if (.not. c_associated(ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_pointer_to_real2d", &
                              "null C pointer received")
            status = QE_ERROR_NULL_POINTER
            ok = .false.
            return
        end if
        if (m <= 0 .or. n <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_pointer_to_real2d", &
                              "non-positive dimension")
            status = QE_ERROR_INVALID_DIMENSION
            ok = .false.
            return
        end if
        call c_f_pointer(ptr, fptr, [m, n])
        status = QE_SUCCESS
        ok = .true.
    end function qe_pointer_to_real2d

    !-----------------------------------------------------------------
    function qe_pointer_to_real1d(ptr, n, fptr, status) result(ok)
        type(c_ptr), value, intent(in)      :: ptr
        integer(c_int), value, intent(in)   :: n
        real(c_double), pointer, intent(out) :: fptr(:)
        integer(c_int), intent(out)         :: status
        logical :: ok

        if (.not. c_associated(ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_pointer_to_real1d", &
                              "null C pointer received")
            status = QE_ERROR_NULL_POINTER
            ok = .false.
            return
        end if
        if (n <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_pointer_to_real1d", &
                              "non-positive dimension")
            status = QE_ERROR_INVALID_DIMENSION
            ok = .false.
            return
        end if
        call c_f_pointer(ptr, fptr, [n])
        status = QE_SUCCESS
        ok = .true.
    end function qe_pointer_to_real1d

    !-----------------------------------------------------------------
    function qe_pointer_to_int1d(ptr, n, fptr, status) result(ok)
        type(c_ptr), value, intent(in)      :: ptr
        integer(c_int), value, intent(in)   :: n
        integer(c_int), pointer, intent(out) :: fptr(:)
        integer(c_int), intent(out)         :: status
        logical :: ok

        if (.not. c_associated(ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_pointer_to_int1d", &
                              "null C pointer received")
            status = QE_ERROR_NULL_POINTER
            ok = .false.
            return
        end if
        if (n <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_pointer_to_int1d", &
                              "non-positive dimension")
            status = QE_ERROR_INVALID_DIMENSION
            ok = .false.
            return
        end if
        call c_f_pointer(ptr, fptr, [n])
        status = QE_SUCCESS
        ok = .true.
    end function qe_pointer_to_int1d

    !-----------------------------------------------------------------
    ! Copy a real(8) buffer of shape (m,n) from a C-side array into
    ! a Fortran-owned allocatable.
    !-----------------------------------------------------------------
    subroutine qe_copy_real2d(src_ptr, m, n, dest, status)
        type(c_ptr), value, intent(in)      :: src_ptr
        integer(c_int), value, intent(in)   :: m, n
        real(c_double), allocatable, intent(inout) :: dest(:,:)
        integer(c_int), intent(out)         :: status

        real(c_double), pointer :: tmp(:,:)
        integer :: istat
        logical :: ok

        ok = qe_pointer_to_real2d(src_ptr, m, n, tmp, status)
        if (.not. ok) return

        if (allocated(dest)) deallocate(dest)
        allocate(dest(m, n), stat=istat)
        if (istat /= 0) then
            call qe_set_error(QE_ERROR_ALLOCATION, "qe_copy_real2d", &
                              "allocation failed")
            status = QE_ERROR_ALLOCATION
            return
        end if
        dest = tmp
        status = QE_SUCCESS
    end subroutine qe_copy_real2d

    subroutine qe_copy_int1d(src_ptr, n, dest, status)
        type(c_ptr), value, intent(in)      :: src_ptr
        integer(c_int), value, intent(in)   :: n
        integer(c_int), allocatable, intent(inout) :: dest(:)
        integer(c_int), intent(out)         :: status

        integer(c_int), pointer :: tmp(:)
        integer :: istat
        logical :: ok

        ok = qe_pointer_to_int1d(src_ptr, n, tmp, status)
        if (.not. ok) return

        if (allocated(dest)) deallocate(dest)
        allocate(dest(n), stat=istat)
        if (istat /= 0) then
            call qe_set_error(QE_ERROR_ALLOCATION, "qe_copy_int1d", &
                              "allocation failed")
            status = QE_ERROR_ALLOCATION
            return
        end if
        dest = tmp
        status = QE_SUCCESS
    end subroutine qe_copy_int1d

    !-----------------------------------------------------------------
    ! Validate that every element of a real(8) matrix is finite.
    !-----------------------------------------------------------------
    function qe_validate_real_finite(arr, name, status) result(ok)
        real(c_double), intent(in) :: arr(:,:)
        character(len=*), intent(in) :: name
        integer(c_int), intent(out) :: status
        logical :: ok
        integer :: i, j, cnt

        ok = .true.
        status = QE_SUCCESS
        cnt = 0
        do j = 1, size(arr, 2)
            do i = 1, size(arr, 1)
                if (.not. (arr(i,j) == arr(i,j))) then  ! NaN check
                    cnt = cnt + 1
                elseif (abs(arr(i,j)) > huge(1.0_c_double)) then
                    cnt = cnt + 1
                end if
            end do
        end do
        if (cnt > 0) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_validate_real_finite", &
                              trim(name)//" contains NaN/Inf")
            status = QE_ERROR_INVALID_ARGUMENT
            ok = .false.
        end if
    end function qe_validate_real_finite

    !-----------------------------------------------------------------
    ! Validate that every element of a real(8) 1-D array is finite.
    !-----------------------------------------------------------------
    function qe_validate_real_finite_1d(arr, name, status) result(ok)
        real(c_double), intent(in) :: arr(:)
        character(len=*), intent(in) :: name
        integer(c_int), intent(out) :: status
        logical :: ok
        integer :: i, cnt

        ok = .true.
        status = QE_SUCCESS
        cnt = 0
        do i = 1, size(arr)
            if (.not. (arr(i) == arr(i))) then
                cnt = cnt + 1
            elseif (abs(arr(i)) > huge(1.0_c_double)) then
                cnt = cnt + 1
            end if
        end do
        if (cnt > 0) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_validate_real_finite_1d", &
                              trim(name)//" contains NaN/Inf")
            status = QE_ERROR_INVALID_ARGUMENT
            ok = .false.
        end if
    end function qe_validate_real_finite_1d

end module qe_memory
