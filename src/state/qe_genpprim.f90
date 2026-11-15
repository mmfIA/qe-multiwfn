! ===================================================================
!  qe_genpprim.f90
!  Non-interactive adapter for the ORIGINAL Multiwfn genPprim.
!
!  CO is built in the CARTESIAN PRIMITIVE representation (nmo,nprims):
!    CO(imo,ip) = C_cart(ao(ip),imo) * primconnorm(ip)
!  For spherical current shells, C is expanded to Cartesian with the
!  original gensphcartab maps (Molden/ORCA order, iprog=2). The primitive
!  density Ptot_prim is stored separately and never replaces Ptot.
! ===================================================================
module qe_genpprim
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_molecular_state, only: the_mol
    use qe_genp, only: qe_genp_build_orbitals
    use qe_gensbas, only: qe_gensbas_build
    use defvar, only: CO, CObasa, CObasb, MOocc, MOtype, &
                      nmo, nbasis, nbasisCar, nprims, wfntype, &
                      naelec, nbelec, imodwfn, primstart, primend, primconnorm, &
                      Ptot_prim, Palpha_prim, Pbeta_prim, shtype2nbas
    implicit none
    private

    public :: qe_genpprim_generate
    public :: qe_genpprim_get
    public :: qe_genpprim_dimensions
    public :: qe_genpprim_overlap
    public :: qe_genpprim_invalidate

    logical, save :: prim_density_valid = .false.

contains

    function qe_genpprim_generate(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        integer :: s, i, j, k, iao, iao_c, ip, l, ncomp, ncart, nprim_comp
        integer :: start, cur_start
        real(c_double), allocatable :: Ccart_a(:,:), Ccart_b(:,:)
        real(c_double) :: conv5d6d(6,5), conv7f10f(10,7)
        real(c_double) :: conv9g15g(15,9), conv11h21h(21,11)
        logical :: has_beta
        external :: genPprim, gensphcartab

        ok = .false.; status = QE_ERROR_INCOMPLETE_STATE
        ! Clear any primitive density from a previous system/attempt.
        call qe_genpprim_invalidate()

        ! Build orbital globals (CObasa/CObasb/MOocc/MOtype/nmo/naelec/nbelec)
        ok = qe_genp_build_orbitals(status)
        if (.not. ok) return

        ! Build the Cartesian primitive table (b, primstart/end, primconnorm)
        ok = qe_gensbas_build(status)
        if (.not. ok) return

        has_beta = (wfntype == 1)

        allocate(Ccart_a(nbasisCar, nbasis))
        Ccart_a = 0.0_c_double
        if (has_beta) then
            allocate(Ccart_b(nbasisCar, nbasis))
            Ccart_b = 0.0_c_double
        end if

        ! Conversion maps used by the original reader (Molden/ORCA = 2).
        call gensphcartab(2, conv5d6d, conv7f10f, conv9g15g, conv11h21h)

        iao = 1       ! current-basis AO
        iao_c = 1     ! Cartesian AO
        do s = 1, the_mol%nshell
            l = the_mol%shell_l(s)
            if (l > 3) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_genpprim_generate", &
                                  "angular momentum above f is not supported")
                status = QE_ERROR_UNSUPPORTED
                return
            end if
            ncomp = count(the_mol%ao_shell == s)
            ncart = shtype2nbas(l)
            cur_start = iao
            if (the_mol%shell_cartesian(s) == 0 .and. l >= 2) then
                if (l == 2) then
                    Ccart_a(iao_c:iao_c+5, 1:nbasis) = &
                        matmul(conv5d6d, CObasa(cur_start:cur_start+4, 1:nbasis))
                    if (has_beta) Ccart_b(iao_c:iao_c+5, 1:nbasis) = &
                        matmul(conv5d6d, CObasb(cur_start:cur_start+4, 1:nbasis))
                else if (l == 3) then
                    Ccart_a(iao_c:iao_c+9, 1:nbasis) = &
                        matmul(conv7f10f, CObasa(cur_start:cur_start+6, 1:nbasis))
                    if (has_beta) Ccart_b(iao_c:iao_c+9, 1:nbasis) = &
                        matmul(conv7f10f, CObasb(cur_start:cur_start+6, 1:nbasis))
                end if
            else
                Ccart_a(iao_c:iao_c+ncart-1, 1:nbasis) = &
                    CObasa(cur_start:cur_start+ncomp-1, 1:nbasis)
                if (has_beta) Ccart_b(iao_c:iao_c+ncart-1, 1:nbasis) = &
                    CObasb(cur_start:cur_start+ncomp-1, 1:nbasis)
            end if
            iao = iao + ncomp
            iao_c = iao_c + ncart
        end do

        if (allocated(CO)) deallocate(CO)
        allocate(CO(nmo, nprims))
        CO = 0.0_c_double
        do iao_c = 1, nbasisCar
            do ip = primstart(iao_c), primend(iao_c)
                do i = 1, nbasis
                    CO(i, ip) = Ccart_a(iao_c, i) * primconnorm(ip)
                end do
                if (has_beta) then
                    do i = 1, nbasis
                        CO(nbasis+i, ip) = Ccart_b(iao_c, i) * primconnorm(ip)
                    end do
                end if
            end do
        end do

        ! Original genPprim: Ptot_prim/Palpha_prim/Pbeta_prim (nprims,nprims)
        call genPprim
        if (.not. allocated(Ptot_prim) .or. size(Ptot_prim,1) /= nprims) then
            call qe_set_error(QE_ERROR_CALCULATION, "qe_genpprim_generate", &
                              "genPprim did not allocate a consistent Ptot_prim")
            status = QE_ERROR_CALCULATION
            return
        end if
        prim_density_valid = .true.
        ok = .true.; status = QE_SUCCESS
    end function qe_genpprim_generate

    !-----------------------------------------------------------------
    function qe_genpprim_dimensions(nprims_out) result(status)
        integer(c_int), intent(out) :: nprims_out
        integer(c_int) :: status
        nprims_out = nprims
        status = QE_SUCCESS
    end function qe_genpprim_dimensions

    !-----------------------------------------------------------------
    ! Overlap of the UNNORMALIZED primitive GTFs, which is the basis in
    ! which the original genPprim CO lives: CO already contains
    ! primconnorm = contraction*normgau, so the matching overlap is the
    ! raw doSint (without primconnorm). The original doSint is used; this
    ! is a validation accessor, not a replacement for genSbas.
    !-----------------------------------------------------------------
    function qe_genpprim_overlap(buffer, capacity) result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        real(c_double), pointer :: out(:,:)
        real(c_double), allocatable :: Sp(:,:)
        real(c_double), external :: doSint
        integer :: i, j, n
        if (.not. c_associated(buffer)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        n = nprims
        if (n <= 0 .or. capacity < n*n) then
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        allocate(Sp(n,n))
        do j = 1, n
            do i = 1, n
                Sp(i,j) = doSint(i,j)
            end do
        end do
        call c_f_pointer(buffer, out, [n,n])
        out = Sp
        deallocate(Sp)
        status = QE_SUCCESS
    end function qe_genpprim_overlap

    !-----------------------------------------------------------------
    subroutine qe_genpprim_invalidate()
        if (allocated(Ptot_prim)) deallocate(Ptot_prim)
        if (allocated(Palpha_prim)) deallocate(Palpha_prim)
        if (allocated(Pbeta_prim)) deallocate(Pbeta_prim)
        prim_density_valid = .false.
    end subroutine qe_genpprim_invalidate

    !-----------------------------------------------------------------
    function qe_genpprim_get(result_id, buffer, capacity) result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value :: buffer
        integer(c_int) :: status
        real(c_double), pointer :: out(:,:)
        integer :: n
        if (.not. c_associated(buffer)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        n = nprims
        if (.not. prim_density_valid .or. .not. allocated(Ptot_prim)) then
            status = QE_ERROR_NOT_AVAILABLE; return
        end if
        if (size(Ptot_prim,1) /= n) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (n <= 0 .or. capacity < n*n) then
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        call c_f_pointer(buffer, out, [n, n])
        select case (result_id)
        case (0)
            if (.not. allocated(Ptot_prim)) then
                status = QE_ERROR_NOT_AVAILABLE; return
            end if
            out = Ptot_prim; status = QE_SUCCESS
        case (1)
            if (.not. allocated(Palpha_prim)) then
                status = QE_ERROR_NOT_AVAILABLE; return
            end if
            out = Palpha_prim; status = QE_SUCCESS
        case (2)
            if (.not. allocated(Pbeta_prim)) then
                status = QE_ERROR_NOT_AVAILABLE; return
            end if
            out = Pbeta_prim; status = QE_SUCCESS
        case default
            status = QE_ERROR_INVALID_ARGUMENT
        end select
    end function qe_genpprim_get

end module qe_genpprim
