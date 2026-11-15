! ===================================================================
!  qe_mayer.f90
!  Adapter for the original Multiwfn routine calcMayerbndord.
!
!  This module:
!    - Validates that the engine is in SYSTEM_PREPARED state
!    - Allocates result matrices
!    - Calls the original calcMayerbndord from bondorder.f90
!    - Stores results for retrieval via C ABI
! ===================================================================
module qe_mayer
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_limits
    use qe_engine_state, only: qe_open_shell_get, qe_state_require, qe_state_set
    use defvar, only: ncenter, nbasis, wfntype
    use qe_analysis_state, only: qe_result_t, qe_result_alloc, qe_result_clear, qe_result_get_ptr
    implicit none
    private

    public :: qe_mayer_calculate
    public :: qe_mayer_get_dimensions
    public :: qe_mayer_get_metadata
    public :: qe_mayer_get_result

contains

    !-----------------------------------------------------------------
    function qe_mayer_calculate() result(status)
        integer(c_int) :: status
        type(qe_result_t), pointer :: res
        real(c_double), allocatable :: bndmattot(:,:), bndmata(:,:), bndmatb(:,:)
        integer :: istat
        integer(c_int), parameter :: ALLOWED(1) = [3]  ! QE_STATE_SYSTEM_PREPARED

        if (.not. qe_state_require(ALLOWED, 1, "qe_calculate_mayer")) then
            status = QE_ERROR_INVALID_STATE; return
        end if

        ! RHF is the default. UHF (wfntype=1) is allowed only when the
        ! additive open-shell flag is explicitly enabled and the UHF state
        ! was validated during qe_state_prepare. ROHF/post-HF remain blocked.
        if (wfntype /= 0) then
            if (.not. qe_open_shell_get()) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_calculate_mayer", &
                                  "closed-shell RHF is the default; open-shell execution is disabled")
                status = QE_ERROR_UNSUPPORTED; return
            end if
            if (wfntype /= 1 .and. wfntype /= 2) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_calculate_mayer", &
                                  "open-shell flag currently enables only UHF (1) and ROHF (2)")
                status = QE_ERROR_UNSUPPORTED; return
            end if
        end if

        ! Allocate result and temporary matrices
        call qe_result_alloc(ncenter, wfntype, status)
        if (status /= QE_SUCCESS) return
        res => qe_result_get_ptr()

        if (.not. qe_check_product(ncenter, ncenter, "ncenter*ncenter", &
                                   "qe_calculate_mayer", status)) then
            call qe_result_clear()
            return
        end if
        allocate(bndmattot(ncenter, ncenter), stat=istat)
        if (istat /= 0) then
            call qe_result_clear()
            call qe_set_allocation_error("qe_calculate_mayer", "bndmattot")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(bndmata(ncenter, ncenter), stat=istat)
        if (istat /= 0) then
            deallocate(bndmattot)
            call qe_result_clear()
            call qe_set_allocation_error("qe_calculate_mayer", "bndmata")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(bndmatb(ncenter, ncenter), stat=istat)
        if (istat /= 0) then
            deallocate(bndmattot, bndmata)
            call qe_result_clear()
            call qe_set_allocation_error("qe_calculate_mayer", "bndmatb")
            status = QE_ERROR_ALLOCATION; return
        end if
        bndmattot = 0.0_c_double
        bndmata   = 0.0_c_double
        bndmatb   = 0.0_c_double

        ! ----- Call the ORIGINAL Multiwfn routine -----
        ! bondorder.f90 defines: subroutine calcMayerbndord(bndmattot,bndmata,bndmatb)
        ! It uses globals ncenter, nbasis, wfntype, Ptot, Palpha, Pbeta, Sbas,
        ! basstart, basend — all set by qe_state_prepare.
        call calcMayerbndord(bndmattot, bndmata, bndmatb)

        ! Store results
        res%mayer_total = bndmattot
        if (res%mayer_has_spin) then
            res%mayer_alpha = bndmata
            res%mayer_beta  = bndmatb
        end if
        res%mayer_available = .true.

        deallocate(bndmattot, bndmata, bndmatb)

        call qe_state_set(4)  ! QE_STATE_RESULT_AVAILABLE
        status = QE_SUCCESS
    end function qe_mayer_calculate

    !-----------------------------------------------------------------
    function qe_mayer_get_dimensions(ncenter_out) result(status)
        integer(c_int), intent(out) :: ncenter_out
        integer(c_int) :: status
        type(qe_result_t), pointer :: res

        res => qe_result_get_ptr()
        if (.not. res%mayer_available) then
            ncenter_out = 0
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_get_mayer_dimensions", &
                              "no Mayer result available")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ncenter_out = res%mayer_ncenter
        status = QE_SUCCESS
    end function qe_mayer_get_dimensions

    !-----------------------------------------------------------------
    function qe_mayer_get_metadata(wfntype_out, has_spin_out) result(status)
        integer(c_int), intent(out) :: wfntype_out, has_spin_out
        integer(c_int) :: status
        type(qe_result_t), pointer :: res

        res => qe_result_get_ptr()
        if (.not. res%mayer_available) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_get_mayer_metadata", &
                              "no Mayer result available")
            status = QE_ERROR_INVALID_STATE; return
        end if
        wfntype_out  = res%mayer_wfntype
        has_spin_out = 0
        if (res%mayer_has_spin) has_spin_out = 1
        status = QE_SUCCESS
    end function qe_mayer_get_metadata

    !-----------------------------------------------------------------
    function qe_mayer_get_result(result_id, buffer, capacity) result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value    :: buffer
        integer(c_int) :: status
        type(qe_result_t), pointer :: res
        real(c_double), pointer :: buf(:,:)
        integer :: n

        res => qe_result_get_ptr()
        if (.not. res%mayer_available) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_get_mayer_result", &
                              "no Mayer result available")
            status = QE_ERROR_INVALID_STATE; return
        end if

        n = res%mayer_ncenter
        if (.not. qe_check_capacity(n, capacity, "Mayer result", &
                                    "qe_get_mayer_result", status)) return
        if (.not. c_associated(buffer)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_get_mayer_result", &
                              "buffer pointer is null")
            status = QE_ERROR_NULL_POINTER; return
        end if

        call c_f_pointer(buffer, buf, [n, n])

        select case (result_id)
        case (0)  ! QE_MAYER_TOTAL
            buf = res%mayer_total
            status = QE_SUCCESS
        case (1)  ! QE_MAYER_ALPHA
            if (res%mayer_has_spin) then
                buf = res%mayer_alpha
                status = QE_SUCCESS
            else
                buf = 0.0_c_double
                call qe_set_error(QE_ERROR_NOT_AVAILABLE, "qe_get_mayer_result", &
                                  "alpha not available for this wfntype")
                status = QE_ERROR_NOT_AVAILABLE
            end if
        case (2)  ! QE_MAYER_BETA
            if (res%mayer_has_spin) then
                buf = res%mayer_beta
                status = QE_SUCCESS
            else
                buf = 0.0_c_double
                call qe_set_error(QE_ERROR_NOT_AVAILABLE, "qe_get_mayer_result", &
                                  "beta not available for this wfntype")
                status = QE_ERROR_NOT_AVAILABLE
            end if
        case default
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_get_mayer_result", &
                              "invalid result_id")
            status = QE_ERROR_INVALID_ARGUMENT
        end select
    end function qe_mayer_get_result

end module qe_mayer
