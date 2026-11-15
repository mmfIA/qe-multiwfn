! ===================================================================
!  qe_electronic_state.f90
!  Full non-interactive state construction from the Molecular Data
!  Model using the original Multiwfn routines:
!    basis -> genSbas_curr (S) -> genP (P) -> validation
!  No pre-extracted P/S from the source program is consulted.
! ===================================================================
module qe_electronic_state
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_molecular_state, only: the_mol
    use qe_gensbas, only: qe_gensbas_build, qe_gensbas_generate
    use qe_genp, only: qe_genp_build_orbitals, qe_genp_generate
    use defvar, only: Ptot, Palpha, Pbeta, Sbas, wfntype, nelec
    implicit none
    private

    public :: qe_electronic_prepare_from_model

contains

    function qe_electronic_prepare_from_model(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        real(c_double) :: trps, target, tol_trace, sym_p, sym_s, sym_sum
        real(c_double) :: idem, scale
        character(len=256) :: msg

        ok = .false.; status = QE_ERROR_INCOMPLETE_STATE

        if (.not. the_mol%has_orbitals) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, &
                              "qe_electronic_prepare_from_model", &
                              "orbital data required for the full state")
            return
        end if

        ! 1) Canonical basis -> original genSbas_curr
        ok = qe_gensbas_build(status)
        if (.not. ok) return

        ! 2) Canonical orbitals -> CObasa/CObasb/MOocc/MOtype
        ok = qe_genp_build_orbitals(status)
        if (.not. ok) return

        ! 3) Original overlap and density
        ok = qe_gensbas_generate(status)
        if (.not. ok) return
        ok = qe_genp_generate(status)
        if (.not. ok) return

        if (.not. allocated(Ptot) .or. .not. allocated(Sbas)) then
            call qe_set_error(QE_ERROR_CALCULATION, &
                              "qe_electronic_prepare_from_model", &
                              "original routines did not allocate P/S")
            status = QE_ERROR_CALCULATION
            return
        end if

        ! 4) Fail-closed scientific validation of the constructed state.
        target = real(the_mol%nelectron, c_double)
        tol_trace = 1.0e-6_c_double * max(1.0_c_double, abs(target))
        trps = sum(Ptot * Sbas)
        if (abs(trps - target) > tol_trace) then
            write(msg,'("Tr(P*S)=",es24.16," Ne=",es24.16," tol=",es12.4)') &
                trps, target, tol_trace
            call qe_set_error(QE_ERROR_CALCULATION, &
                              "qe_electronic_prepare_from_model", trim(msg))
            status = QE_ERROR_CALCULATION
            return
        end if

        sym_p = maxval(abs(Ptot - transpose(Ptot)))
        sym_s = maxval(abs(Sbas - transpose(Sbas)))
        if (sym_p > 1.0e-10_c_double .or. sym_s > 1.0e-10_c_double) then
            write(msg,'("P/S asymmetry: P=",es12.4," S=",es12.4)') sym_p, sym_s
            call qe_set_error(QE_ERROR_CALCULATION, &
                              "qe_electronic_prepare_from_model", trim(msg))
            status = QE_ERROR_CALCULATION
            return
        end if

        if (wfntype == 1 .or. wfntype == 2) then
            if (.not. allocated(Palpha) .or. .not. allocated(Pbeta)) then
                call qe_set_error(QE_ERROR_CALCULATION, &
                                  "qe_electronic_prepare_from_model", &
                                  "open-shell densities are missing")
                status = QE_ERROR_CALCULATION
                return
            end if
            sym_sum = maxval(abs(Ptot - Palpha - Pbeta))
            if (sym_sum > 1.0e-10_c_double) then
                write(msg,'("Ptotal-(Palpha+Pbeta)=",es12.4)') sym_sum
                call qe_set_error(QE_ERROR_CALCULATION, &
                                  "qe_electronic_prepare_from_model", trim(msg))
                status = QE_ERROR_CALCULATION
                return
            end if
        end if

        scale = max(1.0_c_double, maxval(abs(Ptot)))
        if (wfntype == 0) then
            idem = maxval(abs(matmul(matmul(Ptot, Sbas), Ptot) - 2.0_c_double * Ptot))
            if (idem > 1.0e-6_c_double * scale) then
                write(msg,'("RHF PSP-2P residual=",es12.4)') idem
                call qe_set_error(QE_ERROR_CALCULATION, &
                                  "qe_electronic_prepare_from_model", trim(msg))
                status = QE_ERROR_CALCULATION
                return
            end if
        else if (wfntype == 1) then
            idem = max(maxval(abs(matmul(matmul(Palpha, Sbas), Palpha) - Palpha)), &
                       maxval(abs(matmul(matmul(Pbeta, Sbas), Pbeta) - Pbeta)))
            if (idem > 1.0e-6_c_double * scale) then
                write(msg,'("UHF idempotency residual=",es12.4)') idem
                call qe_set_error(QE_ERROR_CALCULATION, &
                                  "qe_electronic_prepare_from_model", trim(msg))
                status = QE_ERROR_CALCULATION
                return
            end if
        end if

        ! nelec is left as set by the electronic metadata/orbital adapter.
        ok = .true.; status = QE_SUCCESS
    end function qe_electronic_prepare_from_model

end module qe_electronic_state
