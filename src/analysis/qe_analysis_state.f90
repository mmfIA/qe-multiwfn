! ===================================================================
!  qe_analysis_state.f90
!  Holds the result matrices produced by scientific analyses.
! ===================================================================
module qe_analysis_state
    use, intrinsic :: iso_c_binding
    use qe_status
    implicit none
    private

    public :: qe_result_t
    public :: qe_result_alloc
    public :: qe_result_clear
    public :: qe_result_get_ptr

    type :: qe_result_t
        ! Mayer bond order matrices
        real(c_double), allocatable :: mayer_total(:,:)
        real(c_double), allocatable :: mayer_alpha(:,:)
        real(c_double), allocatable :: mayer_beta(:,:)
        logical :: mayer_available       = .false.
        logical :: mayer_has_spin        = .false.
        integer(c_int) :: mayer_ncenter = 0
        integer(c_int) :: mayer_wfntype = 0
    end type qe_result_t

    type(qe_result_t), save, target :: the_result

contains

    subroutine qe_result_alloc(ncenter, wfntype)
        integer(c_int), intent(in) :: ncenter, wfntype
        call qe_result_clear_internal()
        if (ncenter <= 0) return

        allocate(the_result%mayer_total(ncenter, ncenter))
        the_result%mayer_total = 0.0_c_double

        if (wfntype == 1 .or. wfntype == 2 .or. wfntype == 4) then
            allocate(the_result%mayer_alpha(ncenter, ncenter))
            allocate(the_result%mayer_beta(ncenter, ncenter))
            the_result%mayer_alpha = 0.0_c_double
            the_result%mayer_beta  = 0.0_c_double
            the_result%mayer_has_spin = .true.
        else
            the_result%mayer_has_spin = .false.
        end if

        the_result%mayer_ncenter = ncenter
        the_result%mayer_wfntype = wfntype
    end subroutine qe_result_alloc

    subroutine qe_result_clear()
        call qe_result_clear_internal()
    end subroutine qe_result_clear

    subroutine qe_result_clear_internal()
        if (allocated(the_result%mayer_total)) deallocate(the_result%mayer_total)
        if (allocated(the_result%mayer_alpha)) deallocate(the_result%mayer_alpha)
        if (allocated(the_result%mayer_beta))  deallocate(the_result%mayer_beta)
        the_result%mayer_available = .false.
        the_result%mayer_has_spin  = .false.
        the_result%mayer_ncenter  = 0
        the_result%mayer_wfntype  = 0
    end subroutine qe_result_clear_internal

    function qe_result_get_ptr() result(p)
        type(qe_result_t), pointer :: p
        p => the_result
    end function qe_result_get_ptr

end module qe_analysis_state
