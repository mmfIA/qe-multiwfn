! ===================================================================
!  qe_genp.f90
!  Non-interactive adapter for the ORIGINAL Multiwfn genP routine.
!
!  It builds CObasa / CObasb / MOocc / MOtype / naelec / nbelec from
!  the canonical Molecular Data Model and calls the original genP.
!  No matrix is reimplemented here: the density is produced by the
!  original vendor routine, which is only given its required globals.
! ===================================================================
module qe_genp
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_molecular_state, only: the_mol
    use qe_analysis_state, only: qe_result_clear
    use defvar, only: CObasa, CObasb, MOocc, MOtype, &
                      nmo, naelec, nbelec, wfntype, nbasis, imodwfn, &
                      Ptot, Palpha, Pbeta, nelec
    implicit none
    private

    public :: qe_genp_build_orbitals
    public :: qe_genp_generate
    public :: qe_genp_get_density
    public :: qe_genp_dimensions

contains

    !-----------------------------------------------------------------
    ! Copy the canonical model's coefficients/occupations to the
    ! Multiwfn globals used by genP.
    !-----------------------------------------------------------------
    function qe_genp_build_orbitals(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        integer :: i, j, k, n, nalpha, nbeta, ndouble, nsingle, nempty
        integer, allocatable :: alpha_idx(:), beta_idx(:), order(:)
        real(c_double) :: occ
        logical :: has_alpha, has_beta

        ok = .false.
        status = QE_ERROR_INCOMPLETE_STATE

        if (.not. the_mol%has_orbitals) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_genp_build_orbitals", &
                              "canonical model has no orbital data")
            return
        end if
        if (the_mol%orb_coefficient_representation /= 0) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_genp_build_orbitals", &
                              "genP adapter requires contracted-basis coefficients")
            status = QE_ERROR_UNSUPPORTED
            return
        end if
        if (the_mol%nmo_v1 <= 0 .or. the_mol%nbasis <= 0) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_genp_build_orbitals", &
                              "invalid orbital/basis dimensions")
            return
        end if

        ! Allocate the coefficient arrays. genP for RHF/ROHF uses
        ! CObasa(:,1:naelec/by nbelec); UHF uses CObasa/CObasb.
        if (allocated(CObasa)) deallocate(CObasa)
        if (allocated(CObasb)) deallocate(CObasb)
        if (allocated(MOocc)) deallocate(MOocc)
        if (allocated(MOtype)) deallocate(MOtype)

        wfntype = the_mol%wfntype
        nbasis = the_mol%nbasis
        imodwfn = 0

        if (wfntype == 0) then
            ! RHF: nmo = nbasis, doubly occupied
            nmo = nbasis
            allocate(CObasa(nbasis, nmo))
            allocate(MOocc(nmo), MOtype(nmo))
            MOocc = 0.0_c_double
            MOtype = 0
            do i = 1, nmo
                do j = 1, nbasis
                    CObasa(j, i) = coeff_at(j, i)
                end do
                MOocc(i) = the_mol%orb_occupations(i)
            end do
            naelec = the_mol%nelectron / 2
            nbelec = naelec
            ok = .true.
            status = QE_SUCCESS
            return
        end if

        if (wfntype == 1) then
            ! UHF: alpha and beta coefficient blocks selected by spin code.
            n = the_mol%nmo_v1
            allocate(alpha_idx(n), beta_idx(n))
            nalpha = 0; nbeta = 0
            do i = 1, n
                if (the_mol%orb_spin(i) == 1) then
                    nalpha = nalpha + 1; alpha_idx(nalpha) = i
                else if (the_mol%orb_spin(i) == 2) then
                    nbeta = nbeta + 1; beta_idx(nbeta) = i
                end if
            end do
            if (nalpha /= nbasis .or. nbeta /= nbasis) then
                call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_genp_build_orbitals", &
                                  "UHF requires nbasis alpha and nbasis beta orbitals")
                status = QE_ERROR_INCOMPLETE_STATE
                deallocate(alpha_idx, beta_idx)
                return
            end if
            nmo = 2 * nbasis
            allocate(CObasa(nbasis, nbasis), CObasb(nbasis, nbasis))
            allocate(MOocc(nmo), MOtype(nmo))
            MOocc = 0.0_c_double
            MOtype = 0
            do i = 1, nbasis
                do j = 1, nbasis
                    CObasa(j, i) = coeff_at(j, alpha_idx(i))
                    CObasb(j, i) = coeff_at(j, beta_idx(i))
                end do
                MOocc(i) = the_mol%orb_occupations(alpha_idx(i))
                MOocc(nbasis + i) = the_mol%orb_occupations(beta_idx(i))
                MOtype(i) = 1
                MOtype(nbasis + i) = 2
            end do
            naelec = count(MOocc(1:nbasis) > 1.0e-8_c_double)
            nbelec = count(MOocc(nbasis+1:nmo) > 1.0e-8_c_double)
            deallocate(alpha_idx, beta_idx)
            ok = .true.
            status = QE_SUCCESS
            return
        end if

        if (wfntype == 2) then
            ! ROHF: reorder spatial orbitals so that the first nbelec are
            ! doubly occupied, followed by the singly occupied ones, as
            ! required by the original genP ROHF branch.
            n = the_mol%nmo_v1
            if (n /= nbasis) then
                call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_genp_build_orbitals", &
                                  "ROHF requires one spatial orbital set of size nbasis")
                status = QE_ERROR_INCOMPLETE_STATE
                return
            end if
            ndouble = 0; nsingle = 0; nempty = 0
            do i = 1, n
                occ = the_mol%orb_occupations(i)
                if (occ > 1.5_c_double) then
                    ndouble = ndouble + 1
                else if (occ > 0.5_c_double) then
                    nsingle = nsingle + 1
                else
                    nempty = nempty + 1
                end if
            end do
            allocate(order(n))
            k = 0
            do i = 1, n
                if (the_mol%orb_occupations(i) > 1.5_c_double) then
                    k = k + 1; order(k) = i
                end if
            end do
            do i = 1, n
                if (the_mol%orb_occupations(i) > 0.5_c_double .and. &
                    the_mol%orb_occupations(i) <= 1.5_c_double) then
                    k = k + 1; order(k) = i
                end if
            end do
            do i = 1, n
                if (the_mol%orb_occupations(i) <= 0.5_c_double) then
                    k = k + 1; order(k) = i
                end if
            end do
            nmo = nbasis
            allocate(CObasa(nbasis, nmo))
            allocate(MOocc(nmo), MOtype(nmo))
            MOocc = 0.0_c_double
            MOtype = 0
            do i = 1, nmo
                do j = 1, nbasis
                    CObasa(j, i) = coeff_at(j, order(i))
                end do
                MOocc(i) = the_mol%orb_occupations(order(i))
                if (MOocc(i) > 1.5_c_double) then
                    MOtype(i) = 0
                else if (MOocc(i) > 0.5_c_double) then
                    MOtype(i) = 1
                else
                    MOtype(i) = 0
                end if
            end do
            naelec = ndouble + nsingle
            nbelec = ndouble
            deallocate(order)
            ok = .true.
            status = QE_SUCCESS
            return
        end if

        call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_genp_build_orbitals", &
                          "genP adapter supports wfntype 0, 1 and 2")
        status = QE_ERROR_UNSUPPORTED
    end function qe_genp_build_orbitals

    !-----------------------------------------------------------------
    ! Call the ORIGINAL genP routine. Requires the globals populated by
    ! qe_genp_build_orbitals.
    !-----------------------------------------------------------------
    function qe_genp_generate(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        external :: genP

        ok = .false.
        if (.not. allocated(CObasa)) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_genp_generate", &
                              "orbital globals are not built")
            status = QE_ERROR_INCOMPLETE_STATE
            return
        end if
        ! Clear stale analysis results before replacing the density.
        call qe_result_clear()
        call genP
        if (.not. allocated(Ptot)) then
            call qe_set_error(QE_ERROR_CALCULATION, "qe_genp_generate", &
                              "original genP did not allocate Ptot")
            status = QE_ERROR_CALCULATION
            return
        end if
        ok = .true.
        status = QE_SUCCESS
    end function qe_genp_generate

    !-----------------------------------------------------------------
    function qe_genp_dimensions(nbasis_out) result(status)
        integer(c_int), intent(out) :: nbasis_out
        integer(c_int) :: status
        nbasis_out = nbasis
        status = QE_SUCCESS
    end function qe_genp_dimensions

    !-----------------------------------------------------------------
    ! Copy a generated density matrix to a caller buffer (current basis).
    ! result_id: 0 total, 1 alpha, 2 beta.
    !-----------------------------------------------------------------
    function qe_genp_get_density(result_id, buffer, capacity) result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value :: buffer
        integer(c_int) :: status
        real(c_double), pointer :: out(:,:)
        integer :: n

        if (.not. c_associated(buffer)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_genp_get_density", &
                              "null buffer")
            status = QE_ERROR_NULL_POINTER
            return
        end if
        n = nbasis
        if (n <= 0 .or. capacity < n * n) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_genp_get_density", &
                              "buffer too small or system not prepared")
            status = QE_ERROR_INVALID_DIMENSION
            return
        end if
        call c_f_pointer(buffer, out, [n, n])
        select case (result_id)
        case (0)
            if (.not. allocated(Ptot)) then
                status = QE_ERROR_INVALID_STATE; return
            end if
            out = Ptot
            status = QE_SUCCESS
        case (1)
            if (.not. allocated(Palpha)) then
                status = QE_ERROR_NOT_AVAILABLE; return
            end if
            out = Palpha
            status = QE_SUCCESS
        case (2)
            if (.not. allocated(Pbeta)) then
                status = QE_ERROR_NOT_AVAILABLE; return
            end if
            out = Pbeta
            status = QE_SUCCESS
        case default
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_genp_get_density", &
                              "invalid result_id")
            status = QE_ERROR_INVALID_ARGUMENT
        end select
    end function qe_genp_get_density

    !-----------------------------------------------------------------
    function coeff_at(ao, imo) result(v)
        integer, intent(in) :: ao, imo
        real(c_double) :: v
        if (the_mol%orb_coefficient_layout == 0) then  ! orbital_ao
            v = the_mol%orb_coefficients(imo, ao)
        else                                            ! ao_orbital
            v = the_mol%orb_coefficients(ao, imo)
        end if
    end function coeff_at

end module qe_genp
