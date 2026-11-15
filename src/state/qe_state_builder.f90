! ===================================================================
!  qe_state_builder.f90
!
!  Validates the canonical molecular model and pushes its contents
!  into Multiwfn's global state (module defvar in define.f90).
!
!  The bridge to Multiwfn globals is intentionally narrow:
!  we touch only what calcMayerbndord needs:
!
!     ncenter, nbasis, wfntype
!     basstart(:), basend(:)
!     Ptot, Palpha, Pbeta, Sbas
!     a(:) (atomtype array, allocated to satisfy other routines)
!
!  We do NOT call readinfile, genP, genSbas_curr, init_PBC, init_func,
!  ask_sbas_pbc, or any other interactive routine. The caller (Python)
!  supplies all required data directly.
! ===================================================================
module qe_state_builder
    use, intrinsic :: iso_c_binding
    use qe_status
    use qe_error_handler
    use qe_engine_state, only: qe_open_shell_get
    use qe_memory
    use qe_limits
    use qe_analysis_state, only: qe_result_clear
    use defvar, only: ncenter, nbasis, nprims, wfntype, &
                     a, basstart, basend, &
                     Ptot, Palpha, Pbeta, Sbas, &
                     nelec, naelec, nbelec, &
                     nmo, imodwfn
    use qe_molecular_state, only: qe_mol_t, the_mol
    use qe_gensbas, only: qe_gensbas_invalidate_cartesian
    use qe_genpprim, only: qe_genpprim_invalidate
    implicit none
    private

    public :: qe_state_begin_system
    public :: qe_state_set_atomic_data
    public :: qe_state_set_electronic_metadata
    public :: qe_state_set_basis_data
    public :: qe_state_set_density
    public :: qe_state_set_overlap
    public :: qe_state_set_shells
    public :: qe_state_set_primitives
    public :: qe_state_set_ao_map
    public :: qe_state_set_ao_normalization
    public :: qe_state_set_angular_canonical
    public :: qe_state_set_orbitals
    public :: qe_state_get_readiness
    public :: qe_state_get_ncenter
    public :: qe_state_prepare
    public :: qe_state_release

contains

    !-----------------------------------------------------------------
    ! Allocate the canonical model with given dimensions.
    !-----------------------------------------------------------------
    function qe_state_begin_system(ncenter_, nbasis_, nprims_, wfntype_) &
            result(status)
        integer(c_int), value :: ncenter_, nbasis_, nprims_, wfntype_
        integer(c_int) :: status
        integer :: istat
        logical :: ok

        call qe_clear_error()

        if (ncenter_ <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_begin_system", &
                              "ncenter must be positive")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        if (nbasis_ <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_begin_system", &
                              "nbasis must be positive")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        if (nprims_ < nbasis_) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_begin_system", &
                              "nprims must be >= nbasis")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ! Check every dimension and every size product BEFORE any allocation.
        ok = qe_check_dimension(ncenter_, "ncenter", "qe_begin_system", status)
        if (.not. ok) return
        ok = qe_check_dimension(nbasis_, "nbasis", "qe_begin_system", status)
        if (.not. ok) return
        ok = qe_check_dimension(nprims_, "nprims", "qe_begin_system", status)
        if (.not. ok) return
        ok = qe_check_product(nbasis_, nbasis_, "nbasis*nbasis", &
                              "qe_begin_system", status)
        if (.not. ok) return
        ok = qe_check_product(ncenter_, ncenter_, "ncenter*ncenter", &
                              "qe_begin_system", status)
        if (.not. ok) return
        ok = qe_check_product(3_c_int, ncenter_, "3*ncenter", &
                              "qe_begin_system", status)
        if (.not. ok) return
        if (wfntype_ < 0 .or. wfntype_ > 4) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_begin_system", &
                              "wfntype must be in [0,4]")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        ! The validated 0.1.x Mayer pipeline is restricted closed-shell RHF
        ! unless the caller explicitly enables the additive open-shell path.
        if (wfntype_ /= 0) then
            if (.not. qe_open_shell_get()) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_begin_system", &
                                  "closed-shell RHF is the default; call "// &
                                  "qe_v1_enable_open_shell(1) to enable UHF (wfntype=1)")
                status = QE_ERROR_UNSUPPORTED; return
            end if
            if (wfntype_ /= 1 .and. wfntype_ /= 2) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_begin_system", &
                                  "open-shell flag currently enables only UHF (1) "// &
                                  "and ROHF (2); post-HF remains unsupported")
                status = QE_ERROR_UNSUPPORTED; return
            end if
        end if

        ! Release any previously-loaded system.
        block
            integer(c_int) :: rel_status
            rel_status = qe_state_release()
        end block
        ! No derived overlap/density cache may survive into a new system.
        call qe_gensbas_invalidate_cartesian()
        call qe_genpprim_invalidate()

        the_mol%ncenter = ncenter_
        the_mol%nbasis  = nbasis_
        the_mol%nprims  = nprims_
        the_mol%wfntype = wfntype_

        allocate(the_mol%atomic_numbers(ncenter_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("atomic_numbers")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(the_mol%coordinates(3, ncenter_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("coordinates")
            status = QE_ERROR_ALLOCATION; return
        end if
        the_mol%atomic_numbers = 0
        the_mol%coordinates = 0.0_c_double

        allocate(the_mol%basis_center(nbasis_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("basis_center")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(the_mol%basis_type(nbasis_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("basis_type")
            status = QE_ERROR_ALLOCATION; return
        end if
        the_mol%basis_center = 0
        the_mol%basis_type = 0

        allocate(the_mol%density_total(nbasis_, nbasis_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("density_total")
            status = QE_ERROR_ALLOCATION; return
        end if
        the_mol%density_total = 0.0_c_double

        if (wfntype_ == 1 .or. wfntype_ == 2 .or. wfntype_ == 4) then
            allocate(the_mol%density_alpha(nbasis_, nbasis_), stat=istat)
            if (istat /= 0) then
                call qe_begin_alloc_fail("density_alpha")
                status = QE_ERROR_ALLOCATION; return
            end if
            allocate(the_mol%density_beta(nbasis_, nbasis_), stat=istat)
            if (istat /= 0) then
                call qe_begin_alloc_fail("density_beta")
                status = QE_ERROR_ALLOCATION; return
            end if
            the_mol%density_alpha = 0.0_c_double
            the_mol%density_beta  = 0.0_c_double
        end if

        allocate(the_mol%overlap(nbasis_, nbasis_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("overlap")
            status = QE_ERROR_ALLOCATION; return
        end if
        the_mol%overlap = 0.0_c_double

        allocate(the_mol%basstart(ncenter_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("basstart")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(the_mol%basend(ncenter_), stat=istat)
        if (istat /= 0) then
            call qe_begin_alloc_fail("basend")
            status = QE_ERROR_ALLOCATION; return
        end if
        the_mol%basstart = 0
        the_mol%basend   = 0

        status = QE_SUCCESS
    end function qe_state_begin_system

    !-----------------------------------------------------------------
    function qe_state_set_atomic_data(ncenter_, atnum_ptr, coor_ptr) &
            result(status)
        integer(c_int), value :: ncenter_
        type(c_ptr), value    :: atnum_ptr, coor_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: atnum(:)
        real(c_double), pointer :: coor(:,:)
        logical :: ok
        integer :: i

        if (ncenter_ /= the_mol%ncenter) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_atomic_data", &
                              "ncenter does not match qe_begin_system")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if

        ok = qe_pointer_to_int1d(atnum_ptr, ncenter_, atnum, status)
        if (.not. ok) return
        ok = qe_pointer_to_real2d(coor_ptr, 3_c_int, ncenter_, coor, status)
        if (.not. ok) return

        ! Validate atomic numbers (1..118)
        do i = 1, ncenter_
            if (atnum(i) < 0 .or. atnum(i) > 118) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_atomic_data", &
                                  "atomic number out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end do

        the_mol%atomic_numbers = atnum
        the_mol%coordinates = coor
        the_mol%has_atoms = .true.
        status = QE_SUCCESS
    end function qe_state_set_atomic_data

    !-----------------------------------------------------------------
    function qe_state_set_electronic_metadata(charge, mult, nelec) &
            result(status)
        integer(c_int), value :: charge, mult, nelec
        integer(c_int) :: status
        integer(c_int) :: electron_count

        if (nelec <= 0 .and. .not. the_mol%has_atoms) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_set_electronic_metadata", &
                              "atomic data must be set before deriving electron count")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if
        if (nelec > 0) then
            electron_count = nelec
        else
            electron_count = sum(the_mol%atomic_numbers) - charge
        end if
        if (the_mol%wfntype == 0) then
            if (mult /= 1) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_set_electronic_metadata", &
                                  "closed-shell RHF requires multiplicity=1")
                status = QE_ERROR_UNSUPPORTED; return
            end if
            if (electron_count <= 0 .or. mod(electron_count, 2) /= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                  "qe_set_electronic_metadata", &
                                  "closed-shell RHF requires a positive even electron count")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        else
            if (.not. qe_open_shell_get()) then
                call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_set_electronic_metadata", &
                                  "open-shell metadata requires the open-shell flag")
                status = QE_ERROR_UNSUPPORTED; return
            end if
            if (mult < 2) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                  "qe_set_electronic_metadata", &
                                  "open-shell requires multiplicity >= 2")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (electron_count <= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                  "qe_set_electronic_metadata", &
                                  "electron count must be positive")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end if
        the_mol%charge = charge
        the_mol%multiplicity = mult
        the_mol%nelectron = electron_count
        the_mol%has_metadata = .true.
        status = QE_SUCCESS
    end function qe_state_set_electronic_metadata

    !-----------------------------------------------------------------
    function qe_state_set_basis_data(nbasis_, nprims_, bc_ptr, bt_ptr) &
            result(status)
        integer(c_int), value :: nbasis_, nprims_
        type(c_ptr), value    :: bc_ptr, bt_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: bc(:), bt(:)
        logical :: ok
        integer :: i

        if (nbasis_ /= the_mol%nbasis) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_basis_data", &
                              "nbasis mismatch")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        if (nprims_ /= the_mol%nprims) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_basis_data", &
                              "nprims mismatch")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if

        ! basstart/basend partition basis FUNCTIONS, not primitive Gaussians.
        ! Therefore these arrays have length nbasis even when nprims > nbasis.
        ok = qe_pointer_to_int1d(bc_ptr, nbasis_, bc, status)
        if (.not. ok) return
        ok = qe_pointer_to_int1d(bt_ptr, nbasis_, bt, status)
        if (.not. ok) return

        ! Validate basis center (1..ncenter)
        do i = 1, nbasis_
            if (bc(i) < 1 .or. bc(i) > the_mol%ncenter) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_basis_data", &
                                  "basis_center out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end do

        the_mol%basis_center = bc
        the_mol%basis_type = bt
        the_mol%has_basis = .true.
        status = QE_SUCCESS
    end function qe_state_set_basis_data

    !-----------------------------------------------------------------
    function qe_state_set_density(nbasis_, dt_ptr, da_ptr, db_ptr) &
            result(status)
        integer(c_int), value :: nbasis_
        type(c_ptr), value    :: dt_ptr, da_ptr, db_ptr
        integer(c_int) :: status
        real(c_double), pointer :: dt(:,:)
        logical :: ok
        logical :: has_alpha_beta

        if (nbasis_ /= the_mol%nbasis) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_density", &
                              "nbasis mismatch")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if

        ok = qe_pointer_to_real2d(dt_ptr, nbasis_, nbasis_, dt, status)
        if (.not. ok) return
        ok = qe_validate_real_finite(dt, "density_total", status)
        if (.not. ok) return

        ! Check symmetry (within tolerance)
        if (.not. matrix_is_symmetric(dt, 1.0e-9_c_double)) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_density", &
                              "density_total is not symmetric")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if
        the_mol%density_total = dt

        has_alpha_beta = (the_mol%wfntype == 1 .or. &
                          the_mol%wfntype == 2 .or. &
                          the_mol%wfntype == 4)

        if (has_alpha_beta) then
            if (.not. c_associated(da_ptr) .or. .not. c_associated(db_ptr)) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_density", &
                                  "alpha/beta density required for this wfntype")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            ok = qe_pointer_to_real2d(da_ptr, nbasis_, nbasis_, dt, status)
            if (.not. ok) return
            ok = qe_validate_real_finite(dt, "density_alpha", status)
            if (.not. ok) return
            if (.not. matrix_is_symmetric(dt, 1.0e-9_c_double)) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_density", &
                                  "density_alpha is not symmetric")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            the_mol%density_alpha = dt

            ok = qe_pointer_to_real2d(db_ptr, nbasis_, nbasis_, dt, status)
            if (.not. ok) return
            ok = qe_validate_real_finite(dt, "density_beta", status)
            if (.not. ok) return
            if (.not. matrix_is_symmetric(dt, 1.0e-9_c_double)) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_density", &
                                  "density_beta is not symmetric")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            the_mol%density_beta = dt

            if (maxval(abs(the_mol%density_total - &
                           (the_mol%density_alpha + the_mol%density_beta))) > 1.0e-10_c_double) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_density", &
                                  "Ptotal must equal P_alpha + P_beta")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end if

        the_mol%has_density = .true.
        status = QE_SUCCESS
    end function qe_state_set_density

    !-----------------------------------------------------------------
    function qe_state_set_overlap(nbasis_, ov_ptr) result(status)
        integer(c_int), value :: nbasis_
        type(c_ptr), value    :: ov_ptr
        integer(c_int) :: status
        real(c_double), pointer :: ov(:,:)
        logical :: ok

        if (nbasis_ /= the_mol%nbasis) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_overlap", &
                              "nbasis mismatch")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ok = qe_pointer_to_real2d(ov_ptr, nbasis_, nbasis_, ov, status)
        if (.not. ok) return
        ok = qe_validate_real_finite(ov, "overlap", status)
        if (.not. ok) return
        if (.not. matrix_is_symmetric(ov, 1.0e-9_c_double)) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_overlap", &
                              "overlap matrix is not symmetric")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if

        the_mol%overlap = ov
        the_mol%has_overlap = .true.
        status = QE_SUCCESS
    end function qe_state_set_overlap

    !-----------------------------------------------------------------
    ! v1: optional shell table.
    !-----------------------------------------------------------------
    function qe_state_set_shells(nshell, center_ptr, l_ptr, ps_ptr, pe_ptr, cart_ptr) &
            result(status)
        integer(c_int), value :: nshell
        type(c_ptr), value    :: center_ptr, l_ptr, ps_ptr, pe_ptr, cart_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: center(:), l(:), ps(:), pe(:), cart(:)
        integer(c_int), allocatable :: center_tmp(:), l_tmp(:), prim_start_tmp(:)
        integer(c_int), allocatable :: prim_end_tmp(:), cart_tmp(:)
        logical :: ok
        integer :: i, istat

        if (.not. qe_check_dimension(nshell, "nshell", "qe_set_shells", status)) return
        if (nshell <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_shells", &
                              "nshell must be positive")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ok = qe_pointer_to_int1d(center_ptr, nshell, center, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(l_ptr, nshell, l, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(ps_ptr, nshell, ps, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(pe_ptr, nshell, pe, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(cart_ptr, nshell, cart, status); if (.not. ok) return

        do i = 1, nshell
            if (center(i) < 1 .or. center(i) > the_mol%ncenter) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_shells", &
                                  "shell center out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (l(i) < 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_shells", &
                                  "shell angular momentum must be >= 0")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (ps(i) < 1 .or. pe(i) < ps(i)) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_shells", &
                                  "invalid primitive range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (cart(i) /= 0 .and. cart(i) /= 1) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_shells", &
                                  "shell_cartesian must be 0 or 1")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end do

        allocate(center_tmp(nshell), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_set_shells", "shell_center")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(l_tmp(nshell), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp)
            call qe_set_allocation_error("qe_set_shells", "shell_l")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(prim_start_tmp(nshell), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, l_tmp)
            call qe_set_allocation_error("qe_set_shells", "shell_prim_start")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(prim_end_tmp(nshell), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, l_tmp, prim_start_tmp)
            call qe_set_allocation_error("qe_set_shells", "shell_prim_end")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(cart_tmp(nshell), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, l_tmp, prim_start_tmp, prim_end_tmp)
            call qe_set_allocation_error("qe_set_shells", "shell_cartesian")
            status = QE_ERROR_ALLOCATION; return
        end if
        center_tmp = center
        l_tmp = l
        prim_start_tmp = ps
        prim_end_tmp = pe
        cart_tmp = cart
        call move_alloc(center_tmp, the_mol%shell_center)
        call move_alloc(l_tmp, the_mol%shell_l)
        call move_alloc(prim_start_tmp, the_mol%shell_prim_start)
        call move_alloc(prim_end_tmp, the_mol%shell_prim_end)
        call move_alloc(cart_tmp, the_mol%shell_cartesian)
        the_mol%nshell = nshell
        the_mol%has_shells = .true.
        status = QE_SUCCESS
    end function qe_state_set_shells

    !-----------------------------------------------------------------
    ! v1: optional primitive (GTF) table.
    !-----------------------------------------------------------------
    function qe_state_set_primitives(nprims, center_ptr, type_ptr, exp_ptr, &
                                     coeff_ptr, norm_ptr, shell_ptr) result(status)
        integer(c_int), value :: nprims
        type(c_ptr), value    :: center_ptr, type_ptr, exp_ptr, coeff_ptr
        type(c_ptr), value    :: norm_ptr, shell_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: center(:), type_(:), shell(:)
        real(c_double), pointer :: expo(:), coeff(:), norm(:)
        integer(c_int), allocatable :: center_tmp(:), type_tmp(:), shell_tmp(:)
        real(c_double), allocatable :: expo_tmp(:), coeff_tmp(:), norm_tmp(:)
        logical :: ok, has_norm, has_shell
        integer :: i, istat

        if (nprims /= the_mol%nprims) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_primitives", &
                              "nprims does not match qe_begin_system")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ok = qe_pointer_to_int1d(center_ptr, nprims, center, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(type_ptr, nprims, type_, status); if (.not. ok) return
        ok = qe_pointer_to_real1d(exp_ptr, nprims, expo, status); if (.not. ok) return
        ok = qe_pointer_to_real1d(coeff_ptr, nprims, coeff, status); if (.not. ok) return
        ok = qe_validate_real_finite_1d(expo, "primitive.exponent", status); if (.not. ok) return
        ok = qe_validate_real_finite_1d(coeff, "primitive.coefficient", status); if (.not. ok) return

        has_norm = c_associated(norm_ptr)
        if (has_norm) then
            ok = qe_pointer_to_real1d(norm_ptr, nprims, norm, status); if (.not. ok) return
            ok = qe_validate_real_finite_1d(norm, "primitive.normalization", status); if (.not. ok) return
        end if
        has_shell = c_associated(shell_ptr)
        if (has_shell) then
            ok = qe_pointer_to_int1d(shell_ptr, nprims, shell, status); if (.not. ok) return
        end if

        do i = 1, nprims
            if (center(i) < 1 .or. center(i) > the_mol%ncenter) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_primitives", &
                                  "primitive center out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (expo(i) <= 0.0_c_double) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_primitives", &
                                  "primitive exponent must be positive")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (has_shell) then
                if (shell(i) < 0 .or. shell(i) > the_mol%nshell) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_primitives", &
                                      "primitive shell index out of range")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
            end if
        end do

        allocate(center_tmp(nprims), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_set_primitives", "prim_center")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(type_tmp(nprims), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp)
            call qe_set_allocation_error("qe_set_primitives", "prim_type")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(shell_tmp(nprims), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, type_tmp)
            call qe_set_allocation_error("qe_set_primitives", "prim_shell")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(expo_tmp(nprims), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, type_tmp, shell_tmp)
            call qe_set_allocation_error("qe_set_primitives", "prim_exponent")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(coeff_tmp(nprims), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, type_tmp, shell_tmp, expo_tmp)
            call qe_set_allocation_error("qe_set_primitives", "prim_coefficient")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(norm_tmp(nprims), stat=istat)
        if (istat /= 0) then
            deallocate(center_tmp, type_tmp, shell_tmp, expo_tmp, coeff_tmp)
            call qe_set_allocation_error("qe_set_primitives", "prim_normalization")
            status = QE_ERROR_ALLOCATION; return
        end if
        center_tmp = center
        type_tmp = type_
        expo_tmp = expo
        coeff_tmp = coeff
        if (has_norm) then
            norm_tmp = norm
        else
            norm_tmp = 1.0_c_double
        end if
        if (has_shell) then
            shell_tmp = shell
        else
            shell_tmp = 0
        end if
        call move_alloc(center_tmp, the_mol%prim_center)
        call move_alloc(type_tmp, the_mol%prim_type)
        call move_alloc(shell_tmp, the_mol%prim_shell)
        call move_alloc(expo_tmp, the_mol%prim_exponent)
        call move_alloc(coeff_tmp, the_mol%prim_coefficient)
        call move_alloc(norm_tmp, the_mol%prim_normalization)
        the_mol%has_primitives = .true.
        status = QE_SUCCESS
    end function qe_state_set_primitives

    !-----------------------------------------------------------------
    ! v1: optional AO -> (center, shell, component) mapping.
    ! This is the authoritative AO order for v1. It also fills the legacy
    ! basis_center/basis_type arrays so the existing Mayer path works.
    !-----------------------------------------------------------------
    function qe_state_set_ao_map(nbasis, center_ptr, shell_ptr, mtype_ptr, &
                                 atype_ptr, source_ptr) result(status)
        integer(c_int), value :: nbasis
        type(c_ptr), value    :: center_ptr, shell_ptr, mtype_ptr, atype_ptr, source_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: center(:), shell(:), mtype(:), atype(:), source(:)
        integer(c_int), allocatable :: shell_tmp(:), mtype_tmp(:), atype_tmp(:), source_tmp(:)
        logical :: ok
        integer :: i, istat

        if (nbasis /= the_mol%nbasis) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_ao_map", &
                              "nbasis does not match qe_begin_system")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ok = qe_pointer_to_int1d(center_ptr, nbasis, center, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(atype_ptr, nbasis, atype, status); if (.not. ok) return
        if (c_associated(shell_ptr)) then
            ok = qe_pointer_to_int1d(shell_ptr, nbasis, shell, status); if (.not. ok) return
        end if
        if (c_associated(mtype_ptr)) then
            ok = qe_pointer_to_int1d(mtype_ptr, nbasis, mtype, status); if (.not. ok) return
        end if
        if (c_associated(source_ptr)) then
            ok = qe_pointer_to_int1d(source_ptr, nbasis, source, status); if (.not. ok) return
        end if

        do i = 1, nbasis
            if (center(i) < 1 .or. center(i) > the_mol%ncenter) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_ao_map", &
                                  "AO center out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (atype(i) < 0 .or. atype(i) > 10) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_ao_map", &
                                  "AO angular_type out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (c_associated(shell_ptr)) then
                if (shell(i) < 0 .or. shell(i) > the_mol%nshell) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_ao_map", &
                                      "AO shell index out of range")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
            end if
        end do

        allocate(shell_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_set_ao_map", "ao_shell")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(mtype_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            deallocate(shell_tmp)
            call qe_set_allocation_error("qe_set_ao_map", "ao_multiwfn_type")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(atype_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            deallocate(shell_tmp, mtype_tmp)
            call qe_set_allocation_error("qe_set_ao_map", "ao_angular_type")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(source_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            deallocate(shell_tmp, mtype_tmp, atype_tmp)
            call qe_set_allocation_error("qe_set_ao_map", "ao_source_index")
            status = QE_ERROR_ALLOCATION; return
        end if
        if (c_associated(shell_ptr)) then
            shell_tmp = shell
        else
            shell_tmp = 0
        end if
        if (c_associated(mtype_ptr)) then
            mtype_tmp = mtype
        else
            mtype_tmp = 0
        end if
        if (c_associated(source_ptr)) then
            source_tmp = source
        else
            source_tmp = 0
        end if
        atype_tmp = atype
        call move_alloc(shell_tmp, the_mol%ao_shell)
        call move_alloc(mtype_tmp, the_mol%ao_multiwfn_type)
        call move_alloc(atype_tmp, the_mol%ao_angular_type)
        call move_alloc(source_tmp, the_mol%ao_source_index)

        ! The legacy Mayer path consumes basis_center/basis_type; fill them
        ! from the authoritative v1 AO map.
        the_mol%basis_center = center
        the_mol%basis_type = atype
        the_mol%has_basis = .true.
        the_mol%has_ao_map = .true.
        status = QE_SUCCESS
    end function qe_state_set_ao_map

    !-----------------------------------------------------------------
    ! v1: per-AO normalization metadata used by the original genSbas
    ! and genPprim adapters.
    !-----------------------------------------------------------------
    function qe_state_set_ao_normalization(nbasis, self_ptr, contraction_ptr, &
                                            convention_ptr) result(status)
        integer(c_int), value :: nbasis
        type(c_ptr), value    :: self_ptr, contraction_ptr, convention_ptr
        integer(c_int) :: status
        real(c_double), pointer :: self_overlap(:), contraction(:)
        integer(c_int), pointer :: convention(:)
        real(c_double), allocatable :: self_tmp(:), contraction_tmp(:)
        integer(c_int), allocatable :: convention_tmp(:)
        logical :: ok
        integer :: i, istat

        if (nbasis /= the_mol%nbasis) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_ao_normalization", &
                              "nbasis mismatch")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        ok = qe_pointer_to_real1d(self_ptr, nbasis, self_overlap, status)
        if (.not. ok) return
        ok = qe_pointer_to_real1d(contraction_ptr, nbasis, contraction, status)
        if (.not. ok) return
        ok = qe_pointer_to_int1d(convention_ptr, nbasis, convention, status)
        if (.not. ok) return
        do i = 1, nbasis
            if (self_overlap(i) <= 0.0_c_double .or. &
                .not. (self_overlap(i) == self_overlap(i))) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                  "qe_set_ao_normalization", &
                                  "source_self_overlap must be positive and finite")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (contraction(i) <= 0.0_c_double .or. &
                .not. (contraction(i) == contraction(i))) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                  "qe_set_ao_normalization", &
                                  "contraction_normalization must be positive and finite")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end do
        allocate(self_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_set_ao_normalization", "source_self_overlap")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(contraction_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            deallocate(self_tmp)
            call qe_set_allocation_error("qe_set_ao_normalization", "contraction_normalization")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(convention_tmp(nbasis), stat=istat)
        if (istat /= 0) then
            deallocate(self_tmp, contraction_tmp)
            call qe_set_allocation_error("qe_set_ao_normalization", "normalization_convention")
            status = QE_ERROR_ALLOCATION; return
        end if
        self_tmp = self_overlap
        contraction_tmp = contraction
        convention_tmp = convention
        call move_alloc(self_tmp, the_mol%ao_source_self_overlap)
        call move_alloc(contraction_tmp, the_mol%ao_contraction_norm)
        call move_alloc(convention_tmp, the_mol%ao_normalization_convention)
        the_mol%has_ao_normalization = .true.
        status = QE_SUCCESS
    end function qe_state_set_ao_normalization

    !-----------------------------------------------------------------
    ! v1: explicit angular canonical state. The Fortran routines do not
    ! receive source metadata, so the Python boundary must declare whether
    ! l=3 data is canonical before any basis-building routine is called.
    !-----------------------------------------------------------------
    function qe_state_set_angular_canonical(canonical) result(status)
        integer(c_int), value :: canonical
        integer(c_int) :: status
        if (canonical /= 0 .and. canonical /= 1) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                              "qe_set_angular_canonical", &
                              "canonical must be 0 or 1")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if
        the_mol%has_canonical_angular = (canonical == 1)
        status = QE_SUCCESS
    end function qe_state_set_angular_canonical

    !-----------------------------------------------------------------
    ! v1: optional orbital data (not used by the 0.1.x Mayer path).
    ! layout: 0 = (nmo, ncoeff), 1 = (ncoeff, nmo)
    ! repr:   0 = contracted basis, 1 = primitive GTF
    ! spin:   0 = total/both, 1 = alpha, 2 = beta
    !-----------------------------------------------------------------
    function qe_state_set_orbitals(nmo, ncoeff, repr, layout, coeff_ptr, &
                                   ene_ptr, occ_ptr, spin_ptr) result(status)
        integer(c_int), value :: nmo, ncoeff, repr, layout
        type(c_ptr), value    :: coeff_ptr, ene_ptr, occ_ptr, spin_ptr
        integer(c_int) :: status
        real(c_double), pointer :: coeff(:,:), ene(:), occ(:)
        integer(c_int), pointer :: spin(:)
        real(c_double), allocatable :: coeff_tmp(:,:), ene_tmp(:), occ_tmp(:)
        integer(c_int), allocatable :: spin_tmp(:)
        logical :: ok
        integer :: i, istat
        integer(c_int) :: m, n

        if (.not. qe_check_dimension(nmo, "nmo", "qe_set_orbitals", status)) return
        if (.not. qe_check_dimension(ncoeff, "ncoeff", "qe_set_orbitals", status)) return
        if (nmo <= 0) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_orbitals", &
                              "nmo must be positive")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        if (repr /= 0 .and. repr /= 1) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_set_orbitals", &
                              "coefficient representation must be 0 or 1")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        if (layout /= 0 .and. layout /= 1) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_set_orbitals", &
                              "coefficient layout must be 0 or 1")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        if (repr == 0) then
            if (ncoeff /= the_mol%nbasis) then
                call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_orbitals", &
                                  "contracted coefficients require ncoeff=nbasis")
                status = QE_ERROR_INVALID_DIMENSION; return
            end if
        else
            if (ncoeff /= the_mol%nprims) then
                call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_set_orbitals", &
                                  "primitive coefficients require ncoeff=nprims")
                status = QE_ERROR_INVALID_DIMENSION; return
            end if
        end if

        if (layout == 0) then
            m = nmo; n = ncoeff
        else
            m = ncoeff; n = nmo
        end if
        if (.not. qe_check_product(m, n, "nmo*ncoeff", "qe_set_orbitals", status)) return
        ok = qe_pointer_to_real2d(coeff_ptr, m, n, coeff, status); if (.not. ok) return
        ok = qe_pointer_to_real1d(ene_ptr, nmo, ene, status); if (.not. ok) return
        ok = qe_pointer_to_real1d(occ_ptr, nmo, occ, status); if (.not. ok) return
        ok = qe_pointer_to_int1d(spin_ptr, nmo, spin, status); if (.not. ok) return
        ok = qe_validate_real_finite(coeff, "orbitals.coefficients", status); if (.not. ok) return
        ok = qe_validate_real_finite_1d(ene, "orbitals.energies", status); if (.not. ok) return
        ok = qe_validate_real_finite_1d(occ, "orbitals.occupations", status); if (.not. ok) return
        do i = 1, nmo
            if (occ(i) < 0.0_c_double) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_orbitals", &
                                  "occupations must be >= 0")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (spin(i) < 0 .or. spin(i) > 2) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_set_orbitals", &
                                  "spin code must be 0, 1 or 2")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end do

        allocate(coeff_tmp(m, n), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_set_orbitals", "orb_coefficients")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(ene_tmp(nmo), stat=istat)
        if (istat /= 0) then
            deallocate(coeff_tmp)
            call qe_set_allocation_error("qe_set_orbitals", "orb_energies")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(occ_tmp(nmo), stat=istat)
        if (istat /= 0) then
            deallocate(coeff_tmp, ene_tmp)
            call qe_set_allocation_error("qe_set_orbitals", "orb_occupations")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(spin_tmp(nmo), stat=istat)
        if (istat /= 0) then
            deallocate(coeff_tmp, ene_tmp, occ_tmp)
            call qe_set_allocation_error("qe_set_orbitals", "orb_spin")
            status = QE_ERROR_ALLOCATION; return
        end if
        coeff_tmp = coeff
        ene_tmp = ene
        occ_tmp = occ
        spin_tmp = spin
        call move_alloc(coeff_tmp, the_mol%orb_coefficients)
        call move_alloc(ene_tmp, the_mol%orb_energies)
        call move_alloc(occ_tmp, the_mol%orb_occupations)
        call move_alloc(spin_tmp, the_mol%orb_spin)
        the_mol%nmo_v1 = nmo
        the_mol%orb_coefficient_representation = repr
        the_mol%orb_coefficient_layout = layout
        the_mol%has_orbitals = .true.
        status = QE_SUCCESS
    end function qe_state_set_orbitals

    !-----------------------------------------------------------------
    ! v1 readiness bitmask (see qe_multiwfn_v1.h).
    !-----------------------------------------------------------------
    function qe_state_get_readiness() result(flags)
        integer(c_int) :: flags
        flags = 0
        if (the_mol%has_atoms)      flags = ior(flags, 1)
        if (the_mol%has_basis)      flags = ior(flags, 2)
        if (the_mol%has_orbitals)   flags = ior(flags, 4)
        if (the_mol%has_density)    flags = ior(flags, 8)
        if (the_mol%has_overlap)    flags = ior(flags, 16)
        if (the_mol%has_shells)     flags = ior(flags, 32)
        if (the_mol%has_primitives) flags = ior(flags, 64)
        if (the_mol%has_ao_map)     flags = ior(flags, 128)
        if (the_mol%has_atoms .and. the_mol%has_basis .and. &
            the_mol%has_density .and. the_mol%has_overlap .and. &
            the_mol%has_metadata) flags = ior(flags, 256)
    end function qe_state_get_readiness

    !-----------------------------------------------------------------
    ! Final preparation: validate completeness, compute basstart/basend,
    ! push everything into Multiwfn globals.
    !-----------------------------------------------------------------
    function qe_state_prepare() result(status)
        integer(c_int) :: status
        integer :: i, istat
        logical :: ok
        real(c_double) :: trPS, nelec_check, idempotency_error, density_scale
        real(c_double) :: trPSa, trPSb, na_check, nb_check, uhf_error, uhf_scale
        real(c_double), allocatable :: psp(:,:)

        call qe_clear_error()

        ! --- Completeness ---
        if (.not. the_mol%has_atoms) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_prepare_system", &
                              "atomic data not set")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if
        if (.not. the_mol%has_metadata) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_prepare_system", &
                              "electronic metadata not set")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if
        if (.not. the_mol%has_density) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_prepare_system", &
                              "density not set")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if
        if (.not. the_mol%has_overlap) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_prepare_system", &
                              "overlap not set")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if

        ! --- Compute basstart/basend from basis_center ---
        ! If basis_center wasn't provided, we cannot partition the basis
        ! by atom, and Mayer can't be computed.
        if (.not. the_mol%has_basis) then
            call qe_set_error(QE_ERROR_INCOMPLETE_STATE, "qe_prepare_system", &
                              "basis_center/basis_type not set; cannot derive basstart/basend")
            status = QE_ERROR_INCOMPLETE_STATE; return
        end if

        call compute_bas_ranges(the_mol, status)
        if (status /= QE_SUCCESS) return

        ! --- v1 optional components consistency (does not affect Mayer) ---
        call validate_v1_state(status)
        if (status /= QE_SUCCESS) return

        ! --- Validate Tr(P·S) ≈ n_electrons (sanity check) ---
        trPS = 0.0_c_double
        do i = 1, the_mol%nbasis
            trPS = trPS + sum(the_mol%density_total(:,i) * the_mol%overlap(i,:))
        end do
        nelec_check = real(the_mol%nelectron, c_double)
        if (abs(trPS - nelec_check) > max(1.0e-3_c_double, 1.0e-6_c_double * abs(nelec_check))) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                              "Tr(P*S) does not match n_electrons")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if

        ! For a closed-shell single-determinant RHF density in Multiwfn's
        ! spin-summed convention, P*S*P = 2*P. This rejects arbitrary
        ! symmetric matrices that happen to have the right trace but are
        ! not valid idempotent RHF density matrices.
        if (the_mol%wfntype == 0) then
            if (.not. qe_check_product(the_mol%nbasis, the_mol%nbasis, &
                                       "nbasis*nbasis", "qe_prepare_system", status)) return
            allocate(psp(the_mol%nbasis, the_mol%nbasis), stat=istat)
            if (istat /= 0) then
                call qe_set_allocation_error("qe_prepare_system", "idempotency scratch")
                status = QE_ERROR_ALLOCATION; return
            end if
            psp = matmul(matmul(the_mol%density_total, the_mol%overlap), &
                         the_mol%density_total)
            idempotency_error = maxval(abs(psp - 2.0_c_double * the_mol%density_total))
            density_scale = max(1.0_c_double, &
                                maxval(abs(2.0_c_double * the_mol%density_total)))
            deallocate(psp)
            if (idempotency_error > 1.0e-6_c_double * density_scale) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "RHF density is not idempotent: P*S*P must equal 2*P")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end if

        ! --- Push into Multiwfn globals ---
        ncenter = the_mol%ncenter
        nbasis  = the_mol%nbasis
        nprims  = the_mol%nprims
        wfntype = the_mol%wfntype
        nelec   = the_mol%nelectron

        ! Spin-specific electron counts (rough, for completeness)
        if (wfntype == 0 .or. wfntype == 3) then
            naelec = the_mol%nelectron / 2
            nbelec  = the_mol%nelectron / 2
        else
            ! Unpaired = multiplicity - 1
            naelec = (the_mol%nelectron + (the_mol%multiplicity - 1)) / 2
            nbelec  = the_mol%nelectron - naelec
        end if

        nmo = nbasis  ! not strictly needed for Mayer
        imodwfn = 0   ! wavefunction is unmodified

        ! --- Allocate and fill a(:) (atomtype) ---
        ! Multiwfn's atomtype has fields: name, index, x, y, z, charge, resid, resname
        if (allocated(a)) deallocate(a)
        allocate(a(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_prepare_clear_globals()
            call qe_set_allocation_error("qe_prepare_system", "a")
            status = QE_ERROR_ALLOCATION; return
        end if
        do i = 1, ncenter
            a(i)%index   = the_mol%atomic_numbers(i)
            a(i)%charge  = real(the_mol%atomic_numbers(i), 8)
            a(i)%x       = the_mol%coordinates(1, i)
            a(i)%y       = the_mol%coordinates(2, i)
            a(i)%z       = the_mol%coordinates(3, i)
            a(i)%resid   = 1
            a(i)%resname = " "
        end do

        ! --- basstart / basend ---
        if (allocated(basstart)) deallocate(basstart)
        if (allocated(basend))   deallocate(basend)
        allocate(basstart(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_prepare_clear_globals()
            call qe_set_allocation_error("qe_prepare_system", "basstart")
            status = QE_ERROR_ALLOCATION; return
        end if
        allocate(basend(ncenter), stat=istat)
        if (istat /= 0) then
            call qe_prepare_clear_globals()
            call qe_set_allocation_error("qe_prepare_system", "basend")
            status = QE_ERROR_ALLOCATION; return
        end if
        basstart = the_mol%basstart
        basend   = the_mol%basend

        ! --- Density matrices ---
        if (allocated(Ptot)) deallocate(Ptot)
        allocate(Ptot(nbasis, nbasis), stat=istat)
        if (istat /= 0) then
            call qe_prepare_clear_globals()
            call qe_set_allocation_error("qe_prepare_system", "Ptot")
            status = QE_ERROR_ALLOCATION; return
        end if
        Ptot = the_mol%density_total

        if (wfntype == 1 .or. wfntype == 2 .or. wfntype == 4) then
            if (allocated(Palpha)) deallocate(Palpha)
            if (allocated(Pbeta))  deallocate(Pbeta)
            allocate(Palpha(nbasis, nbasis), stat=istat)
            if (istat /= 0) then
                call qe_prepare_clear_globals()
                call qe_set_allocation_error("qe_prepare_system", "Palpha")
                status = QE_ERROR_ALLOCATION; return
            end if
            allocate(Pbeta(nbasis, nbasis), stat=istat)
            if (istat /= 0) then
                call qe_prepare_clear_globals()
                call qe_set_allocation_error("qe_prepare_system", "Pbeta")
                status = QE_ERROR_ALLOCATION; return
            end if
            Palpha = the_mol%density_alpha
            Pbeta  = the_mol%density_beta
        end if

        ! --- Overlap matrix ---
        if (allocated(Sbas)) deallocate(Sbas)
        allocate(Sbas(nbasis, nbasis), stat=istat)
        if (istat /= 0) then
            call qe_prepare_clear_globals()
            call qe_set_allocation_error("qe_prepare_system", "Sbas")
            status = QE_ERROR_ALLOCATION; return
        end if
        Sbas = the_mol%overlap

        ! --- UHF spin-resolved validation (only on the opt-in path) ---
        if (wfntype == 1 .or. wfntype == 2) then
            na_check = real(naelec, c_double)
            nb_check = real(nbelec, c_double)
            trPSa = 0.0_c_double
            trPSb = 0.0_c_double
            do i = 1, nbasis
                trPSa = trPSa + sum(the_mol%density_alpha(:,i) * the_mol%overlap(i,:))
                trPSb = trPSb + sum(the_mol%density_beta(:,i) * the_mol%overlap(i,:))
            end do
            if (abs(trPSa - na_check) > 1.0e-8_c_double * max(1.0_c_double, abs(na_check))) then
                call qe_prepare_clear_globals()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "Tr(P_alpha*S) does not match N_alpha")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (abs(trPSb - nb_check) > 1.0e-8_c_double * max(1.0_c_double, abs(nb_check))) then
                call qe_prepare_clear_globals()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "Tr(P_beta*S) does not match N_beta")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (maxval(abs(the_mol%density_total - &
                           (the_mol%density_alpha + the_mol%density_beta))) > 1.0e-10_c_double) then
                call qe_prepare_clear_globals()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "Ptotal must equal P_alpha + P_beta")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (.not. qe_check_product(nbasis, nbasis, "nbasis*nbasis", &
                                       "qe_prepare_system", status)) then
                call qe_prepare_clear_globals()
                return
            end if
            allocate(psp(nbasis, nbasis), stat=istat)
            if (istat /= 0) then
                call qe_prepare_clear_globals()
                call qe_set_allocation_error("qe_prepare_system", "spin idempotency scratch")
                status = QE_ERROR_ALLOCATION; return
            end if
            psp = matmul(matmul(the_mol%density_alpha, the_mol%overlap), &
                         the_mol%density_alpha)
            uhf_error = maxval(abs(psp - the_mol%density_alpha))
            uhf_scale = max(1.0_c_double, maxval(abs(the_mol%density_alpha)))
            if (uhf_error > 1.0e-6_c_double * uhf_scale) then
                call qe_prepare_clear_globals()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "spin-resolved alpha density is not idempotent: P_a*S*P_a = P_a")
                status = QE_ERROR_INVALID_ARGUMENT; deallocate(psp); return
            end if
            psp = matmul(matmul(the_mol%density_beta, the_mol%overlap), &
                         the_mol%density_beta)
            uhf_error = maxval(abs(psp - the_mol%density_beta))
            uhf_scale = max(1.0_c_double, maxval(abs(the_mol%density_beta)))
            if (uhf_error > 1.0e-6_c_double * uhf_scale) then
                call qe_prepare_clear_globals()
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_prepare_system", &
                                  "spin-resolved beta density is not idempotent: P_b*S*P_b = P_b")
                status = QE_ERROR_INVALID_ARGUMENT; deallocate(psp); return
            end if
            deallocate(psp)
        end if

        status = QE_SUCCESS
    end function qe_state_prepare

    !-----------------------------------------------------------------
    ! Release the currently loaded system, freeing all Multiwfn globals
    ! that were allocated by qe_state_prepare.
    !-----------------------------------------------------------------
    function qe_state_release() result(status)
        integer(c_int) :: status

        ! Results belong to the released system and must never survive it.
        call qe_result_clear()

        ! Free canonical-model allocations
        if (allocated(the_mol%atomic_numbers))  deallocate(the_mol%atomic_numbers)
        if (allocated(the_mol%coordinates))     deallocate(the_mol%coordinates)
        if (allocated(the_mol%basis_center))   deallocate(the_mol%basis_center)
        if (allocated(the_mol%basis_type))     deallocate(the_mol%basis_type)
        if (allocated(the_mol%density_total))  deallocate(the_mol%density_total)
        if (allocated(the_mol%density_alpha))  deallocate(the_mol%density_alpha)
        if (allocated(the_mol%density_beta))   deallocate(the_mol%density_beta)
        if (allocated(the_mol%overlap))        deallocate(the_mol%overlap)
        if (allocated(the_mol%basstart))       deallocate(the_mol%basstart)
        if (allocated(the_mol%basend))         deallocate(the_mol%basend)

        ! Reset Multiwfn globals (only those we allocated ourselves).
        ! We do NOT call dealloall() — that would require pulling in
        ! additional dependencies (topo, basin, etc.) that we have not
        ! yet validated. We release only what qe_state_prepare allocated.
        if (allocated(a))        deallocate(a)
        if (allocated(basstart)) deallocate(basstart)
        if (allocated(basend))   deallocate(basend)
        if (allocated(Ptot))    deallocate(Ptot)
        if (allocated(Palpha))   deallocate(Palpha)
        if (allocated(Pbeta))    deallocate(Pbeta)
        if (allocated(Sbas))     deallocate(Sbas)

        ! v1 optional components
        if (allocated(the_mol%shell_center))      deallocate(the_mol%shell_center)
        if (allocated(the_mol%shell_l))           deallocate(the_mol%shell_l)
        if (allocated(the_mol%shell_prim_start))  deallocate(the_mol%shell_prim_start)
        if (allocated(the_mol%shell_prim_end))    deallocate(the_mol%shell_prim_end)
        if (allocated(the_mol%shell_cartesian))   deallocate(the_mol%shell_cartesian)
        if (allocated(the_mol%prim_center))       deallocate(the_mol%prim_center)
        if (allocated(the_mol%prim_type))         deallocate(the_mol%prim_type)
        if (allocated(the_mol%prim_shell))        deallocate(the_mol%prim_shell)
        if (allocated(the_mol%prim_exponent))     deallocate(the_mol%prim_exponent)
        if (allocated(the_mol%prim_coefficient))  deallocate(the_mol%prim_coefficient)
        if (allocated(the_mol%prim_normalization)) deallocate(the_mol%prim_normalization)
        if (allocated(the_mol%ao_shell))          deallocate(the_mol%ao_shell)
        if (allocated(the_mol%ao_multiwfn_type))  deallocate(the_mol%ao_multiwfn_type)
        if (allocated(the_mol%ao_angular_type))   deallocate(the_mol%ao_angular_type)
        if (allocated(the_mol%ao_source_index))   deallocate(the_mol%ao_source_index)
        if (allocated(the_mol%ao_source_self_overlap)) deallocate(the_mol%ao_source_self_overlap)
        if (allocated(the_mol%ao_contraction_norm))    deallocate(the_mol%ao_contraction_norm)
        if (allocated(the_mol%ao_normalization_convention)) deallocate(the_mol%ao_normalization_convention)
        if (allocated(the_mol%orb_coefficients))  deallocate(the_mol%orb_coefficients)
        if (allocated(the_mol%orb_energies))      deallocate(the_mol%orb_energies)
        if (allocated(the_mol%orb_occupations))   deallocate(the_mol%orb_occupations)
        if (allocated(the_mol%orb_spin))          deallocate(the_mol%orb_spin)

        ! Reset scalar counters
        ncenter = 0
        nbasis  = 0
        nprims  = 0
        nmo     = 0
        nelec   = 0
        naelec  = 0
        nbelec  = 0
        wfntype = 0
        imodwfn = 0

        call qe_mol_reset_internal()

        status = QE_SUCCESS
    end function qe_state_release

    ! --- Helpers ---

    !-----------------------------------------------------------------
    ! Fail-closed cleanup for a partially completed qe_begin_system.
    !-----------------------------------------------------------------
    subroutine qe_begin_alloc_fail(what)
        character(len=*), intent(in) :: what
        integer(c_int) :: rel_status
        call qe_set_allocation_error("qe_begin_system", what)
        rel_status = qe_state_release()
    end subroutine qe_begin_alloc_fail

    !-----------------------------------------------------------------
    ! Fail-closed cleanup of the Multiwfn globals pushed by a partially
    ! completed qe_state_prepare. The canonical model is preserved so the
    ! caller can retry or release it.
    !-----------------------------------------------------------------
    subroutine qe_prepare_clear_globals()
        call qe_result_clear()
        if (allocated(a))        deallocate(a)
        if (allocated(basstart)) deallocate(basstart)
        if (allocated(basend))   deallocate(basend)
        if (allocated(Ptot))     deallocate(Ptot)
        if (allocated(Palpha))   deallocate(Palpha)
        if (allocated(Pbeta))    deallocate(Pbeta)
        if (allocated(Sbas))     deallocate(Sbas)
        ncenter = 0
        nbasis  = 0
        nprims  = 0
        nmo     = 0
        nelec   = 0
        naelec  = 0
        nbelec  = 0
        wfntype = 0
        imodwfn = 0
    end subroutine qe_prepare_clear_globals

    !-----------------------------------------------------------------
    function qe_state_get_ncenter() result(n)
        integer(c_int) :: n
        n = the_mol%ncenter
    end function qe_state_get_ncenter

    !-----------------------------------------------------------------
    ! Validate the optional v1 components. This is additive: an absent
    ! component never blocks the legacy Mayer path.
    !-----------------------------------------------------------------
    subroutine validate_v1_state(status)
        integer(c_int), intent(out) :: status
        integer :: i
        real(c_double) :: occ_sum, ne

        status = QE_SUCCESS

        if (the_mol%has_shells) then
            if (the_mol%nshell <= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                  "shell table is inconsistent")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            do i = 1, the_mol%nshell
                if (the_mol%shell_center(i) < 1 .or. &
                    the_mol%shell_center(i) > the_mol%ncenter) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "shell center out of range")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
                if (the_mol%shell_l(i) < 0) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "shell l must be >= 0")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
                if (the_mol%shell_prim_start(i) < 1 .or. &
                    the_mol%shell_prim_end(i) < the_mol%shell_prim_start(i) .or. &
                    the_mol%shell_prim_end(i) > the_mol%nprims) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "shell primitive range out of bounds")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
            end do
        end if

        if (the_mol%has_primitives) then
            do i = 1, the_mol%nprims
                if (the_mol%prim_center(i) < 1 .or. &
                    the_mol%prim_center(i) > the_mol%ncenter) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "primitive center out of range")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
                if (the_mol%prim_exponent(i) <= 0.0_c_double) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "primitive exponent must be positive")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
                if (the_mol%has_shells) then
                    if (the_mol%prim_shell(i) < 0 .or. &
                        the_mol%prim_shell(i) > the_mol%nshell) then
                        call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                          "primitive shell index out of range")
                        status = QE_ERROR_INVALID_ARGUMENT; return
                    end if
                end if
            end do
        end if

        if (the_mol%has_ao_map) then
            do i = 1, the_mol%nbasis
                if (the_mol%ao_angular_type(i) < 0 .or. &
                    the_mol%ao_angular_type(i) > 10) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                      "AO angular_type out of range")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
                if (the_mol%has_shells) then
                    if (the_mol%ao_shell(i) < 0 .or. &
                        the_mol%ao_shell(i) > the_mol%nshell) then
                        call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                          "AO shell index out of range")
                        status = QE_ERROR_INVALID_ARGUMENT; return
                    end if
                    if (the_mol%ao_shell(i) > 0) then
                        if (the_mol%shell_center(the_mol%ao_shell(i)) /= &
                            the_mol%basis_center(i)) then
                            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                              "validate_v1_state", &
                                              "AO center disagrees with shell center")
                            status = QE_ERROR_INVALID_ARGUMENT; return
                        end if
                        if (the_mol%shell_l(the_mol%ao_shell(i)) /= &
                            the_mol%ao_angular_type(i)) then
                            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                                              "validate_v1_state", &
                                              "AO angular_type disagrees with shell l")
                            status = QE_ERROR_INVALID_ARGUMENT; return
                        end if
                    end if
                end if
            end do
        end if

        if (the_mol%has_orbitals) then
            if (the_mol%nmo_v1 <= 0) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                  "orbital count must be positive")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (the_mol%orb_coefficient_layout == 0) then
                if (size(the_mol%orb_coefficients, 1) /= the_mol%nmo_v1) then
                    call qe_set_error(QE_ERROR_INVALID_DIMENSION, "validate_v1_state", &
                                      "orbital coefficient rows do not match nmo")
                    status = QE_ERROR_INVALID_DIMENSION; return
                end if
            else
                if (size(the_mol%orb_coefficients, 2) /= the_mol%nmo_v1) then
                    call qe_set_error(QE_ERROR_INVALID_DIMENSION, "validate_v1_state", &
                                      "orbital coefficient columns do not match nmo")
                    status = QE_ERROR_INVALID_DIMENSION; return
                end if
            end if
            occ_sum = sum(the_mol%orb_occupations)
            ne = real(the_mol%nelectron, c_double)
            if (abs(occ_sum - ne) > 1.0e-6_c_double * max(1.0_c_double, abs(ne))) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "validate_v1_state", &
                                  "orbital occupations do not sum to nelectron")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
        end if
    end subroutine validate_v1_state

    subroutine qe_mol_reset_internal()
        the_mol%ncenter      = 0
        the_mol%nbasis       = 0
        the_mol%nprims       = 0
        the_mol%wfntype      = 0
        the_mol%charge       = 0
        the_mol%multiplicity = 1
        the_mol%nelectron    = 0
        the_mol%nshell       = 0
        the_mol%nmo_v1       = 0
        the_mol%orb_coefficient_representation = 0
        the_mol%orb_coefficient_layout = 0
        the_mol%has_atoms      = .false.
        the_mol%has_basis      = .false.
        the_mol%has_density    = .false.
        the_mol%has_overlap    = .false.
        the_mol%has_metadata   = .false.
        the_mol%has_shells     = .false.
        the_mol%has_primitives = .false.
        the_mol%has_ao_map     = .false.
        the_mol%has_ao_normalization = .false.
        the_mol%has_canonical_angular = .false.
        the_mol%has_orbitals   = .false.
    end subroutine qe_mol_reset_internal

    ! Compute basstart/basend from basis_center.
    ! Each atom's [basstart, basend] is the [min, max] basis-function index
    ! among basis functions centered on that atom. If an atom has no basis
    ! functions, basstart=basend=0 (Multiwfn convention). Primitive count is
    ! independent: contracted basis sets commonly have nprims > nbasis.
    subroutine compute_bas_ranges(m, status)
        type(qe_mol_t), intent(inout) :: m
        integer(c_int), intent(out) :: status
        integer :: i, ic, previous_center
        m%basstart = 0
        m%basend   = 0
        previous_center = 0
        do i = 1, m%nbasis
            ic = m%basis_center(i)
            if (ic < 1 .or. ic > m%ncenter) then
                call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "compute_bas_ranges", &
                                  "basis_center out of range")
                status = QE_ERROR_INVALID_ARGUMENT; return
            end if
            if (i > 1 .and. ic /= previous_center) then
                if (any(m%basis_center(1:i-1) == ic)) then
                    call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "compute_bas_ranges", &
                                      "basis functions for each atom must form one contiguous block")
                    status = QE_ERROR_INVALID_ARGUMENT; return
                end if
            end if
            if (m%basstart(ic) == 0) m%basstart(ic) = i
            m%basend(ic) = i
            previous_center = ic
        end do
        status = QE_SUCCESS
    end subroutine compute_bas_ranges

    function matrix_is_symmetric(a, tol) result(ok)
        real(c_double), intent(in) :: a(:,:)
        real(c_double), intent(in) :: tol
        logical :: ok
        integer :: i, j, n
        n = size(a, 1)
        if (size(a, 2) /= n) then
            ok = .false.; return
        end if
        ok = .true.
        do j = 1, n
            do i = j+1, n
                if (abs(a(i,j) - a(j,i)) > tol) then
                    ok = .false.; return
                end if
            end do
        end do
    end function matrix_is_symmetric

end module qe_state_builder
