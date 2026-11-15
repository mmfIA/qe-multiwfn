! ===================================================================
!  qe_engine_lifecycle.f90
!  Implements qe_initialize / qe_finalize / qe_get_engine_state.
! ===================================================================
module qe_engine_lifecycle
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_engine_state
    implicit none
    private

    public :: qe_engine_initialize
    public :: qe_engine_finalize
    public :: qe_engine_get_state_c

    logical, save :: initialized = .false.

contains

    function qe_engine_initialize() result(status)
        integer(c_int) :: status

        if (initialized) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_initialize", &
                              "engine already initialized")
            status = QE_ERROR_INVALID_STATE
            return
        end if

        call qe_clear_error()
        call qe_open_shell_set(.false.)
        call qe_state_set(QE_STATE_INITIALIZED)
        initialized = .true.
        status = QE_SUCCESS
    end function qe_engine_initialize

    function qe_engine_finalize() result(status)
        integer(c_int) :: status
        integer :: i

        if (.not. initialized) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_finalize", &
                              "engine not initialized")
            status = QE_ERROR_INVALID_STATE
            return
        end if

        ! Release any loaded molecular state via qe_release_system()
        ! if still loaded. We do this by calling the C-ABI release function
        ! indirectly through the state machine.
        select case (qe_state_get())
        case (QE_STATE_SYSTEM_LOADED, QE_STATE_SYSTEM_PREPARED, &
              QE_STATE_RESULT_AVAILABLE)
            ! The C ABI release path (in qe_c_api) handles the actual
            ! deallocation. We just reset the state machine here.
            call qe_state_set(QE_STATE_INITIALIZED)
        end select

        call qe_open_shell_set(.false.)
        call qe_state_set(QE_STATE_UNINITIALIZED)
        initialized = .false.
        status = QE_SUCCESS
    end function qe_engine_finalize

    function qe_engine_get_state_c(state_ptr) result(status) &
            bind(C, name="qe_get_engine_state")
        type(c_ptr), value :: state_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: s

        if (.not. c_associated(state_ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_get_engine_state", &
                              "state pointer is null")
            status = QE_ERROR_NULL_POINTER
            return
        end if
        call c_f_pointer(state_ptr, s)
        s = qe_state_get()
        status = QE_SUCCESS
    end function qe_engine_get_state_c

end module qe_engine_lifecycle
