! ===================================================================
!  qe_gensbas.f90
!  Non-interactive adapter for the ORIGINAL Multiwfn genSbas and
!  genSbas_curr routines.
!
!  It builds the Cartesian primitive table (b, primstart/end,
!  primconnorm), the shell table (shtype/shtypeCar/shcen/shcon/
!  primshexp/primshcoeff) and the current-basis ownership arrays
!  from the canonical Molecular Data Model, then calls the original
!  routines. No integral or conversion is reimplemented here.
! ===================================================================
module qe_gensbas
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_limits
    use qe_molecular_state, only: the_mol
    use qe_analysis_state, only: qe_result_clear
    use defvar, only: a, b, basshell, bascen, bastype, &
                      primstart, primend, primconnorm, &
                      shtype, shtypeCar, shcen, shcon, primshexp, primshcoeff, &
                      basstart, basend, shtype2nbas, &
                      nshell, ncenter, nbasis, nbasisCar, nprims, wfntype, &
                      imodwfn, isphergau, ifiletype, ifPBC, Sbas
    implicit none
    private

    public :: qe_gensbas_build
    public :: qe_gensbas_generate
    public :: qe_gensbas_generate_cartesian
    public :: qe_gensbas_get_current
    public :: qe_gensbas_get_cartesian
    public :: qe_gensbas_dimensions
    public :: qe_gensbas_invalidate_cartesian

    real(c_double), allocatable, save :: Sbas_cart_saved(:,:)
    logical, save :: cart_overlap_valid = .false.

contains

    !-----------------------------------------------------------------
    function qe_gensbas_build(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        integer :: s, i, j, k, ip, iao, iao_cart, ncomp, ncart, nprim_comp
        integer :: start, finish, l, center, typ, nprimshell_total, istat
        integer(c_int) :: nprim_add
        real(c_double) :: scale, coeff, expo
        real(c_double), external :: normgau
        logical :: spherical, any_spherical
        character(len=256) :: msg

        ok = .false.; status = QE_ERROR_INCOMPLETE_STATE
        ! A rebuild invalidates the diagnostic Cartesian overlap for the
        ! previous basis, even if the new build later fails.
        call qe_gensbas_invalidate_cartesian()
        if (.not. the_mol%has_atoms) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_gensbas_build", &
                              "atomic data missing")
            return
        end if
        if (.not. the_mol%has_basis .or. the_mol%nbasis <= 0) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_gensbas_build", &
                              "basis data missing")
            return
        end if
        if (.not. the_mol%has_ao_normalization) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_gensbas_build", &
                              "per-AO normalization metadata missing")
            return
        end if
        if (the_mol%nshell <= 0) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_gensbas_build", &
                              "shell table missing")
            return
        end if
        if (.not. qe_check_dimension(the_mol%ncenter, "ncenter", &
                                     "qe_gensbas_build", status)) return
        if (.not. qe_check_dimension(the_mol%nbasis, "nbasis", &
                                     "qe_gensbas_build", status)) return
        if (.not. qe_check_dimension(the_mol%nprims, "nprims", &
                                     "qe_gensbas_build", status)) return
        if (.not. qe_check_dimension(the_mol%nshell, "nshell", &
                                     "qe_gensbas_build", status)) return

        ncenter = the_mol%ncenter
        nbasis = the_mol%nbasis
        wfntype = the_mol%wfntype
        imodwfn = 0
        ifPBC = 0
        ifiletype = 9   ! Molden spherical conversion table (ORCA/Molden order)
        nshell = the_mol%nshell

        ! Atoms
        if (allocated(a)) deallocate(a)
        allocate(a(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "a")
            status = QE_ERROR_ALLOCATION; return
        end if
        do i = 1, ncenter
            a(i)%index = the_mol%atomic_numbers(i)
            a(i)%charge = real(the_mol%atomic_numbers(i), 8)
            a(i)%x = the_mol%coordinates(1, i)
            a(i)%y = the_mol%coordinates(2, i)
            a(i)%z = the_mol%coordinates(3, i)
            a(i)%resid = 1
            a(i)%resname = " "
        end do

        ! Count Cartesian AOs and primitives, and primitive-shell total.
        nbasisCar = 0
        nprims = 0
        do s = 1, nshell
            l = the_mol%shell_l(s)
            if (l > 3) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_gensbas_build", &
                                  "angular momentum above f is not supported")
                status = QE_ERROR_UNSUPPORTED
                return
            end if
            if (l == 3 .and. .not. the_mol%has_canonical_angular) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_gensbas_build", &
                                  "f shells require a canonical MDM 1.2 angular state")
                status = QE_ERROR_UNSUPPORTED
                return
            end if
            if (l == 3 .and. the_mol%shell_cartesian(s) /= 0) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_gensbas_build", &
                                  "Cartesian f is not validated in Phase 8B; use spherical f")
                status = QE_ERROR_UNSUPPORTED
                return
            end if
            ncomp = 0
            do i = 1, nbasis
                if (the_mol%ao_shell(i) == s) ncomp = ncomp + 1
            end do
            if (ncomp <= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_gensbas_build", &
                                  "shell has no AO mapping")
                status = QE_ERROR_INVALID_ARGUMENT
                return
            end if
            if (mod(the_mol%shell_prim_end(s) - the_mol%shell_prim_start(s) + 1, &
                    ncomp) /= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_gensbas_build", &
                                  "shell primitive range is not divisible by component count")
                status = QE_ERROR_INVALID_ARGUMENT
                return
            end if
            nprim_comp = (the_mol%shell_prim_end(s) - the_mol%shell_prim_start(s) + 1) / ncomp
            ncart = shtype2nbas(l)
            if (ncart <= 0) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_gensbas_build", &
                                  "unsupported angular momentum")
                status = QE_ERROR_UNSUPPORTED
                return
            end if
            if (the_mol%shell_cartesian(s) == 0 .and. l >= 2) then
                ! spherical current shell: ncomp must be the spherical count
                if (ncomp /= shtype2nbas(-l)) then
                    write(msg,'("spherical shell ",i0," l=",i0," cart=",i0, &
                        &" ncomp=",i0," ncart5D=",i0)') s, l, &
                        the_mol%shell_cartesian(s), ncomp, shtype2nbas(-l)
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_gensbas_build", &
                                      trim(msg))
                    status = QE_ERROR_INVALID_ARGUMENT
                    return
                end if
            else
                if (ncomp /= ncart) then
                    write(msg,'("Cartesian shell ",i0," l=",i0," cart=",i0, &
                        &" ncomp=",i0," ncart=",i0)') s, l, &
                        the_mol%shell_cartesian(s), ncomp, ncart
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_gensbas_build", &
                                      trim(msg))
                    status = QE_ERROR_INVALID_ARGUMENT
                    return
                end if
            end if
            if (.not. qe_check_product(ncart, nprim_comp, "ncart*nprim_comp", &
                                       "qe_gensbas_build", status)) return
            nprim_add = ncart * nprim_comp
            if (.not. qe_check_sum(nbasisCar, ncart, "nbasisCar+ncart", &
                                   "qe_gensbas_build", status)) return
            nbasisCar = nbasisCar + ncart
            if (.not. qe_check_sum(nprims, nprim_add, "nprims+nprim_add", &
                                   "qe_gensbas_build", status)) return
            nprims = nprims + nprim_add
        end do
        if (.not. qe_check_product(nbasisCar, nbasisCar, "nbasisCar*nbasisCar", &
                                   "qe_gensbas_build", status)) return

        if (allocated(b)) deallocate(b)
        if (allocated(primstart)) deallocate(primstart)
        if (allocated(primend)) deallocate(primend)
        if (allocated(primconnorm)) deallocate(primconnorm)
        if (allocated(basshell)) deallocate(basshell)
        if (allocated(bascen)) deallocate(bascen)
        if (allocated(bastype)) deallocate(bastype)
        if (allocated(basstart)) deallocate(basstart)
        if (allocated(basend)) deallocate(basend)
        if (allocated(shtype)) deallocate(shtype)
        if (allocated(shtypeCar)) deallocate(shtypeCar)
        if (allocated(shcen)) deallocate(shcen)
        if (allocated(shcon)) deallocate(shcon)
        if (allocated(primshexp)) deallocate(primshexp)
        if (allocated(primshcoeff)) deallocate(primshcoeff)

        allocate(b(nprims), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "b")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(primstart(nbasisCar), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "primstart")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(primend(nbasisCar), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "primend")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(primconnorm(nprims), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "primconnorm")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(basshell(nbasis), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "basshell")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(bascen(nbasis), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "bascen")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(bastype(nbasis), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "bastype")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(basstart(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "basstart")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(basend(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "basend")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(shtype(nshell), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "shtype")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(shtypeCar(nshell), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "shtypeCar")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(shcen(nshell), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "shcen")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(shcon(nshell), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "shcon")
            status = QE_ERROR_ALLOCATION; return
        end if
        nprimshell_total = 0
        do s = 1, nshell
            ncomp = count(the_mol%ao_shell == s)
            if (ncomp <= 0) then
                call qe_gensbas_clear_all()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_gensbas_build", &
                                  "shell has no AO mapping")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            nprim_add = (the_mol%shell_prim_end(s) - the_mol%shell_prim_start(s) + 1) / ncomp
            if (.not. qe_check_sum(nprimshell_total, nprim_add, &
                                   "nprimshell_total", "qe_gensbas_build", status)) then
                call qe_gensbas_clear_all()
                return
            end if
            nprimshell_total = nprimshell_total + nprim_add
        end do
        allocate(primshexp(nprimshell_total), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "primshexp")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(primshcoeff(nprimshell_total), stat=istat)
        if (istat /= 0) then
            call qe_gensbas_clear_all()
            call qe_set_allocation_error("qe_gensbas_build", "primshcoeff")
            status = QE_ERROR_ALLOCATION; return
        end if

        ! Current-basis ownership
        do i = 1, nbasis
            basshell(i) = the_mol%ao_shell(i)
            bascen(i) = the_mol%basis_center(i)
            bastype(i) = the_mol%ao_multiwfn_type(i)
        end do
        basstart = 0; basend = 0
        do i = 1, nbasis
            s = bascen(i)
            if (basstart(s) == 0) basstart(s) = i
            basend(s) = i
        end do

        any_spherical = .false.
        ip = 1
        iao_cart = 1
        iao = 1
        j = 0
        do s = 1, nshell
            center = the_mol%shell_center(s)
            l = the_mol%shell_l(s)
            spherical = the_mol%shell_cartesian(s) == 0 .and. l >= 2
            ncomp = count(the_mol%ao_shell == s)
            nprim_comp = (the_mol%shell_prim_end(s) - the_mol%shell_prim_start(s) + 1) / ncomp
            start = the_mol%shell_prim_start(s)
            finish = the_mol%shell_prim_end(s)

            shtype(s) = merge(-l, l, spherical)
            shtypeCar(s) = l
            shcen(s) = center
            shcon(s) = nprim_comp
            ! one primitive-shell record: first component of this shell
            if (s == 1) then
                k = 1
            else
                k = 1
                do i = 1, s-1
                    k = k + (the_mol%shell_prim_end(i)-the_mol%shell_prim_start(i)+1) / &
                        max(1,count(the_mol%ao_shell==i))
                end do
            end if
            primshexp(k:k+nprim_comp-1) = the_mol%prim_exponent(start:start+nprim_comp-1)
            primshcoeff(k:k+nprim_comp-1) = the_mol%prim_coefficient(start:start+nprim_comp-1)

            if (spherical) then
                any_spherical = .true.
                ncart = shtype2nbas(l)
                do j = 1, ncart
                    typ = cart_type(l, j)
                    primstart(iao_cart) = ip
                    do k = 1, nprim_comp
                        expo = the_mol%prim_exponent(start + k - 1)
                        coeff = the_mol%prim_coefficient(start + k - 1)
                        b(ip)%center = center
                        b(ip)%type = typ
                        b(ip)%exp = expo
                        primconnorm(ip) = coeff * normgau(typ, expo)
                        ip = ip + 1
                    end do
                    primend(iao_cart) = ip - 1
                    iao_cart = iao_cart + 1
                end do
                iao = iao + ncomp
            else
                ncart = shtype2nbas(l)
                do j = 1, ncomp
                    typ = the_mol%ao_multiwfn_type(iao)
                    scale = sqrt(the_mol%ao_source_self_overlap(iao))
                    primstart(iao_cart) = ip
                    do k = 1, nprim_comp
                        expo = the_mol%prim_exponent(start + (j-1)*nprim_comp + k - 1)
                        coeff = the_mol%prim_coefficient(start + (j-1)*nprim_comp + k - 1)
                        b(ip)%center = center
                        b(ip)%type = typ
                        b(ip)%exp = expo
                        primconnorm(ip) = coeff * normgau(typ, expo) * scale
                        ip = ip + 1
                    end do
                    primend(iao_cart) = ip - 1
                    iao_cart = iao_cart + 1
                    iao = iao + 1
                end do
            end if
        end do

        if (iao_cart - 1 /= nbasisCar .or. ip - 1 /= nprims) then
            call qe_gensbas_clear_all()
            call qe_set_error(QE_ERROR_INTERNAL, "qe_gensbas_build", &
                              "Cartesian AO/primitive count mismatch")
            status = QE_ERROR_INTERNAL
            return
        end if
        isphergau = merge(1, 0, any_spherical)
        ok = .true.; status = QE_SUCCESS
    end function qe_gensbas_build

    !-----------------------------------------------------------------
    function qe_gensbas_generate(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        external :: genSbas_curr
        ok = .false.
        if (.not. allocated(b)) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_gensbas_generate", &
                              "basis arrays are not built")
            status = QE_ERROR_INCOMPLETE_STATE
            return
        end if
        if (allocated(Sbas)) deallocate(Sbas)
        call qe_result_clear()
        call genSbas_curr
        if (.not. allocated(Sbas)) then
            call qe_set_error(QE_ERROR_CALCULATION, "qe_gensbas_generate", &
                              "genSbas_curr did not allocate Sbas")
            status = QE_ERROR_CALCULATION
            return
        end if
        ok = .true.; status = QE_SUCCESS
    end function qe_gensbas_generate

    !-----------------------------------------------------------------
    function qe_gensbas_generate_cartesian(status) result(ok)
        integer(c_int), intent(out) :: status
        logical :: ok
        external :: genSbas
        real(c_double), allocatable :: Sbas_keep(:,:)
        logical :: had_sbas
        integer :: istat

        ok = .false.
        if (.not. qe_check_product(nbasisCar, nbasisCar, "nbasisCar*nbasisCar", &
                                   "qe_gensbas_generate_cartesian", status)) return
        call qe_gensbas_invalidate_cartesian()
        had_sbas = allocated(Sbas)
        if (had_sbas) then
            allocate(Sbas_keep(size(Sbas,1), size(Sbas,2)), stat=istat)
            if (istat /= 0) then
                call qe_set_allocation_error("qe_gensbas_generate_cartesian", "Sbas_keep")
                status = QE_ERROR_ALLOCATION; return
            end if
            Sbas_keep = Sbas
            deallocate(Sbas)
        end if
        allocate(Sbas(nbasisCar, nbasisCar), stat=istat)
        if (istat /= 0) then
            if (allocated(Sbas_keep)) deallocate(Sbas_keep)
            call qe_set_allocation_error("qe_gensbas_generate_cartesian", "Sbas")
            status = QE_ERROR_ALLOCATION; return
        end if
        call qe_result_clear()
        call genSbas
        if (.not. allocated(Sbas)) then
            call qe_set_error(QE_ERROR_CALCULATION, &
                              "qe_gensbas_generate_cartesian", &
                              "genSbas did not allocate Sbas")
            if (had_sbas) then
                allocate(Sbas(size(Sbas_keep,1), size(Sbas_keep,2)), stat=istat)
                if (istat == 0) Sbas = Sbas_keep
                deallocate(Sbas_keep)
            end if
            status = QE_ERROR_CALCULATION
            return
        end if
        if (allocated(Sbas_cart_saved)) deallocate(Sbas_cart_saved)
        allocate(Sbas_cart_saved(nbasisCar, nbasisCar), stat=istat)
        if (istat /= 0) then
            if (had_sbas .and. allocated(Sbas_keep)) then
                deallocate(Sbas)
                allocate(Sbas(size(Sbas_keep,1), size(Sbas_keep,2)), stat=istat)
                if (istat == 0) Sbas = Sbas_keep
            else
                deallocate(Sbas)
            end if
            if (allocated(Sbas_keep)) deallocate(Sbas_keep)
            cart_overlap_valid = .false.
            call qe_set_allocation_error("qe_gensbas_generate_cartesian", "Sbas_cart_saved")
            status = QE_ERROR_ALLOCATION
            return
        end if
        Sbas_cart_saved = Sbas
        cart_overlap_valid = .true.

        ! Restore the current-basis Sbas (diagnostic call must not corrupt state).
        deallocate(Sbas)
        if (had_sbas) then
            allocate(Sbas(size(Sbas_keep,1), size(Sbas_keep,2)), stat=istat)
            if (istat /= 0) then
                deallocate(Sbas_keep)
                call qe_set_allocation_error("qe_gensbas_generate_cartesian", &
                                             "Sbas restore")
                status = QE_ERROR_ALLOCATION
                return
            end if
            Sbas = Sbas_keep
            deallocate(Sbas_keep)
        end if
        ok = .true.; status = QE_SUCCESS
    end function qe_gensbas_generate_cartesian

    !-----------------------------------------------------------------
    function qe_gensbas_dimensions(nbasis_out, nbasisCar_out, nprims_out) result(status)
        integer(c_int), intent(out) :: nbasis_out, nbasisCar_out, nprims_out
        integer(c_int) :: status
        nbasis_out = nbasis; nbasisCar_out = nbasisCar; nprims_out = nprims
        status = QE_SUCCESS
    end function qe_gensbas_dimensions

    !-----------------------------------------------------------------
    function qe_gensbas_get_current(buffer, capacity) result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        real(c_double), pointer :: out(:,:)
        integer :: n
        if (.not. c_associated(buffer)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        if (.not. allocated(Sbas)) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_gensbas_get_current", &
                              "Sbas not available")
            status = QE_ERROR_INVALID_STATE; return
        end if
        n = size(Sbas,1)
        if (.not. qe_check_capacity(n, capacity, "overlap result", &
                                    "qe_gensbas_get_current", status)) return
        call c_f_pointer(buffer, out, [n, n])
        out = Sbas
        status = QE_SUCCESS
    end function qe_gensbas_get_current

    !-----------------------------------------------------------------
    function qe_gensbas_get_cartesian(buffer, capacity) result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        real(c_double), pointer :: out(:,:)
        integer :: n
        if (.not. c_associated(buffer)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        if (.not. cart_overlap_valid .or. .not. allocated(Sbas_cart_saved)) then
            call qe_set_error(QE_ERROR_NOT_AVAILABLE, "qe_gensbas_get_cartesian", &
                              "Cartesian overlap not generated for the current basis")
            status = QE_ERROR_NOT_AVAILABLE; return
        end if
        n = size(Sbas_cart_saved,1)
        if (n /= nbasisCar) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_gensbas_get_cartesian", &
                              "Cartesian overlap dimensions are stale")
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (.not. qe_check_capacity(n, capacity, "Cartesian overlap result", &
                                    "qe_gensbas_get_cartesian", status)) return
        call c_f_pointer(buffer, out, [n, n])
        out = Sbas_cart_saved
        status = QE_SUCCESS
    end function qe_gensbas_get_cartesian

    !-----------------------------------------------------------------
    ! Fail-closed cleanup of all basis globals built by qe_gensbas_build.
    !-----------------------------------------------------------------
    subroutine qe_gensbas_clear_all()
        if (allocated(a))           deallocate(a)
        if (allocated(b))           deallocate(b)
        if (allocated(primstart))   deallocate(primstart)
        if (allocated(primend))     deallocate(primend)
        if (allocated(primconnorm)) deallocate(primconnorm)
        if (allocated(basshell))    deallocate(basshell)
        if (allocated(bascen))      deallocate(bascen)
        if (allocated(bastype))     deallocate(bastype)
        if (allocated(basstart))    deallocate(basstart)
        if (allocated(basend))      deallocate(basend)
        if (allocated(shtype))      deallocate(shtype)
        if (allocated(shtypeCar))   deallocate(shtypeCar)
        if (allocated(shcen))       deallocate(shcen)
        if (allocated(shcon))       deallocate(shcon)
        if (allocated(primshexp))   deallocate(primshexp)
        if (allocated(primshcoeff)) deallocate(primshcoeff)
        if (allocated(Sbas))        deallocate(Sbas)
        call qe_gensbas_invalidate_cartesian()
        call qe_result_clear()
        nbasisCar = 0
        nprims = 0
        nshell = 0
    end subroutine qe_gensbas_clear_all

    !-----------------------------------------------------------------
    subroutine qe_gensbas_invalidate_cartesian()
        if (allocated(Sbas_cart_saved)) deallocate(Sbas_cart_saved)
        cart_overlap_valid = .false.
    end subroutine qe_gensbas_invalidate_cartesian

    !-----------------------------------------------------------------
    function cart_type(l, j) result(typ)
        integer, intent(in) :: l, j
        integer :: typ
        select case (l)
        case (0); typ = 1
        case (1); typ = 1 + j                 ! 2,3,4 = X,Y,Z
        case (2); typ = 4 + j                 ! 5..10 = XX,YY,ZZ,XY,XZ,YZ
        case (3)
            select case (j)                   ! s2f(3,1:10)
            case (1); typ = 11
            case (2); typ = 12
            case (3); typ = 13
            case (4); typ = 17
            case (5); typ = 14
            case (6); typ = 15
            case (7); typ = 18
            case (8); typ = 19
            case (9); typ = 16
            case (10); typ = 20
            case default; typ = 0
            end select
        case default
            typ = 0
        end select
    end function cart_type

end module qe_gensbas
