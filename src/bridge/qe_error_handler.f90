! ===================================================================
!  qe_error_handler.f90
!  Stores the last error code and message, retrievable via C ABI.
! ===================================================================
module qe_error_handler
    use, intrinsic :: iso_c_binding
    use qe_c_types
    use qe_status
    implicit none
    private

    ! Mutable state. In v0.1.1 we accept that this is process-global
    ! (single-engine model). Documented in docs/LIMITATIONS.md.
    integer(c_int), save        :: last_code = 0
    character(len=QE_ERRMSG_LEN), save :: last_message = " "

    public :: qe_set_error
    public :: qe_clear_error
    public :: qe_get_last_error_code
    public :: qe_get_last_error_message
    public :: qe_get_last_error_c       ! C ABI implementation

contains

    ! Set the last error. routine is a short tag like 'qe_set_atomic_data'.
    ! message is the human-readable description.
    subroutine qe_set_error(code, routine, message)
        integer(c_int), intent(in)         :: code
        character(len=*), intent(in)        :: routine, message
        character(len=64) :: code_name

        last_code = code
        code_name = qe_status_name(code)
        write(last_message, '("[",A,"] ",A,": ",A)') &
            trim(code_name), trim(routine), trim(message)
        ! Truncate to buffer length
        if (len_trim(last_message) > QE_ERRMSG_LEN-1) then
            last_message = last_message(1:QE_ERRMSG_LEN-1)
        end if
    end subroutine qe_set_error

    subroutine qe_clear_error()
        last_code = 0
        last_message = " "
    end subroutine qe_clear_error

    function qe_get_last_error_code() result(code)
        integer(c_int) :: code
        code = last_code
    end function qe_get_last_error_code

    function qe_get_last_error_message() result(msg)
        character(len=QE_ERRMSG_LEN) :: msg
        msg = last_message
    end function qe_get_last_error_message

    ! ---------- C ABI ----------
    ! int qe_get_last_error(char *buffer, int buffer_capacity);
    function qe_get_last_error_c(buffer, buffer_capacity) &
            bind(C, name="qe_get_last_error") result(status)

        type(c_ptr), value           :: buffer
        integer(c_int), value        :: buffer_capacity
        integer(c_int)               :: status

        character(kind=c_char, len=1), pointer :: cbuf(:)
        integer :: i, n

        if (.not. c_associated(buffer)) then
            status = QE_ERROR_NULL_POINTER
            return
        end if
        if (buffer_capacity <= 0) then
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if

        call c_f_pointer(buffer, cbuf, [buffer_capacity])

        n = min(len_trim(last_message), buffer_capacity - 1)
        do i = 1, n
            cbuf(i) = last_message(i:i)
        end do
        cbuf(n+1) = c_null_char

        status = QE_SUCCESS
    end function qe_get_last_error_c

end module qe_error_handler
