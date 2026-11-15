! ===================================================================
!  qe_engine_state.f90
!  Holds the global engine state machine.
!
!  v0.1.1: process-global. Single engine instance per process.
!  Documented as NOT thread-safe in docs/LIMITATIONS.md.
! ===================================================================
module qe_engine_state
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    implicit none
    private

    integer(c_int), save :: engine_state = QE_STATE_UNINITIALIZED

    ! Additive v1 capability flag. Disabled by default: the core keeps the
    ! validated 0.1.1 RHF restriction unless the caller explicitly enables
    ! open-shell execution. UHF (wfntype=1) is the only enabled case.
    logical, save :: open_shell_enabled = .false.

    public :: qe_state_get
    public :: qe_state_set
    public :: qe_state_require
    public :: qe_state_transition
    public :: qe_open_shell_set
    public :: qe_open_shell_get

contains

    subroutine qe_open_shell_set(enable)
        logical, intent(in) :: enable
        open_shell_enabled = enable
    end subroutine qe_open_shell_set

    function qe_open_shell_get() result(enabled)
        logical :: enabled
        enabled = open_shell_enabled
    end function qe_open_shell_get

    function qe_state_get() result(s)
        integer(c_int) :: s
        s = engine_state
    end function qe_state_get

    subroutine qe_state_set(new_state)
        integer(c_int), intent(in) :: new_state
        engine_state = new_state
    end subroutine qe_state_set

    ! Check that the engine is in one of the allowed states.
    ! If not, set an error and return .false.
    function qe_state_require(allowed_states, n, routine_name) result(ok)
        integer(c_int), intent(in) :: allowed_states(:)
        integer, intent(in) :: n
        character(len=*), intent(in) :: routine_name
        logical :: ok
        integer :: i
        character(len=32) :: state_str

        ok = .false.
        do i = 1, n
            if (engine_state == allowed_states(i)) then
                ok = .true.
                exit
            end if
        end do
        if (.not. ok) then
            write(state_str, '("state=",I0)') engine_state
            call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                              "engine state not allowed: "//trim(state_str))
        end if
    end function qe_state_require

    subroutine qe_state_transition(new_state, routine_name, status)
        integer(c_int), intent(in) :: new_state
        character(len=*), intent(in) :: routine_name
        integer(c_int), intent(out) :: status

        ! Validated transitions only
        select case (engine_state)
        case (QE_STATE_UNINITIALIZED)
            if (new_state == QE_STATE_INITIALIZED) then
                engine_state = new_state
                status = QE_SUCCESS
            else
                call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                                  "engine not initialized")
                status = QE_ERROR_INVALID_STATE
            end if
        case (QE_STATE_INITIALIZED)
            if (new_state == QE_STATE_SYSTEM_LOADED .or. &
                new_state == QE_STATE_UNINITIALIZED) then
                engine_state = new_state
                status = QE_SUCCESS
            else
                call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                                  "invalid transition from INITIALIZED")
                status = QE_ERROR_INVALID_STATE
            end if
        case (QE_STATE_SYSTEM_LOADED)
            if (new_state == QE_STATE_SYSTEM_PREPARED .or. &
                new_state == QE_STATE_INITIALIZED) then
                engine_state = new_state
                status = QE_SUCCESS
            else
                call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                                  "invalid transition from SYSTEM_LOADED")
                status = QE_ERROR_INVALID_STATE
            end if
        case (QE_STATE_SYSTEM_PREPARED)
            if (new_state == QE_STATE_RESULT_AVAILABLE .or. &
                new_state == QE_STATE_INITIALIZED .or. &
                new_state == QE_STATE_SYSTEM_LOADED) then
                engine_state = new_state
                status = QE_SUCCESS
            else
                call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                                  "invalid transition from SYSTEM_PREPARED")
                status = QE_ERROR_INVALID_STATE
            end if
        case (QE_STATE_RESULT_AVAILABLE)
            if (new_state == QE_STATE_SYSTEM_PREPARED .or. &
                new_state == QE_STATE_INITIALIZED) then
                engine_state = new_state
                status = QE_SUCCESS
            else
                call qe_set_error(QE_ERROR_INVALID_STATE, routine_name, &
                                  "invalid transition from RESULT_AVAILABLE")
                status = QE_ERROR_INVALID_STATE
            end if
        case default
            call qe_set_error(QE_ERROR_INTERNAL, routine_name, &
                              "unknown engine state")
            status = QE_ERROR_INTERNAL
        end select
    end subroutine qe_state_transition

end module qe_engine_state
