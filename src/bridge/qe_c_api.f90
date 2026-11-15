! ===================================================================
!  qe_c_api.f90
!
!  The PUBLIC C ABI of libqe_multiwfn.so.
!
!  Every function here is bound with `bind(C, name="...")` and is the
!  only entry point Python (or any C caller) is allowed to use.
!
!  Functions return int status codes (0 = QE_SUCCESS).
! ===================================================================
module qe_c_api
    use, intrinsic :: iso_c_binding
    use qe_c_types
    use qe_status
    use qe_error_handler
    use qe_memory, only: qe_pointer_to_real2d
    use qe_limits
    use qe_engine_state
    use qe_engine_lifecycle, only: qe_engine_initialize, qe_engine_finalize, &
                                    qe_engine_get_state_c
    use qe_state_builder, only: qe_state_begin_system, qe_state_set_atomic_data, &
                                qe_state_set_electronic_metadata, &
                                qe_state_set_basis_data, qe_state_set_density, &
                                qe_state_set_overlap, qe_state_set_shells, &
                                qe_state_set_primitives, qe_state_set_ao_map, &
                                qe_state_set_ao_normalization, &
                                qe_state_set_angular_canonical, &
                                qe_state_set_orbitals, qe_state_get_readiness, &
                                qe_state_get_ncenter, &
                                qe_state_prepare, qe_state_release
    use qe_mayer, only: qe_mayer_calculate, qe_mayer_get_dimensions, &
                         qe_mayer_get_metadata, qe_mayer_get_result
    use qe_genp, only: qe_genp_build_orbitals, qe_genp_generate, &
                       qe_genp_get_density, qe_genp_dimensions
    use qe_gensbas, only: qe_gensbas_build, qe_gensbas_generate, &
                          qe_gensbas_generate_cartesian, &
                          qe_gensbas_get_current, qe_gensbas_get_cartesian, &
                          qe_gensbas_dimensions
    use qe_genpprim, only: qe_genpprim_generate, qe_genpprim_get, &
                           qe_genpprim_dimensions, qe_genpprim_overlap
    use qe_electronic_state, only: qe_electronic_prepare_from_model
    implicit none
    private

    ! The C ABI surface is composed of `bind(C)` functions defined in THIS
    ! module plus `bind(C)` functions re-exported from other modules via
    ! `use`. We only need to list the local ones as public.
    public :: qe_initialize
    public :: qe_finalize
    public :: qe_begin_system
    public :: qe_set_atomic_data
    public :: qe_set_electronic_metadata
    public :: qe_set_basis_data
    public :: qe_set_density
    public :: qe_set_overlap
    public :: qe_prepare_system
    public :: qe_calculate_mayer
    public :: qe_get_mayer_dimensions
    public :: qe_get_mayer_metadata
    public :: qe_get_mayer_result
    public :: qe_release_system
    public :: qe_v1_enable_open_shell
    public :: qe_v1_model_begin
    public :: qe_v1_set_atoms
    public :: qe_v1_set_shells
    public :: qe_v1_set_primitives
    public :: qe_v1_set_ao_map
    public :: qe_v1_set_ao_normalization
    public :: qe_v1_set_angular_canonical
    public :: qe_v1_set_density
    public :: qe_v1_set_overlap
    public :: qe_v1_set_orbitals
    public :: qe_v1_model_commit
    public :: qe_v1_model_release
    public :: qe_v1_get_readiness
    public :: qe_v1_generate_density
    public :: qe_v1_generate_overlap
    public :: qe_v1_generate_cartesian_overlap
    public :: qe_v1_get_generated_overlap
    public :: qe_v1_get_generated_cartesian_overlap
    public :: qe_v1_get_overlap_dimensions
    public :: qe_v1_build_electronic_state
    public :: qe_v1_generate_primitive_density
    public :: qe_v1_get_primitive_density_dimensions
    public :: qe_v1_get_generated_primitive_density
    public :: qe_v1_get_primitive_overlap
    public :: qe_v1_get_generated_density
    public :: qe_v1_get_generated_density_dimensions
    public :: qe_get_version

    character(len=QE_VERSION_LEN), parameter :: QE_VERSION_STR = "0.2.0"

contains

    !-----------------------------------------------------------------
    function qe_prepared_or_result() result(ok)
        logical :: ok
        ok = (qe_state_get() == QE_STATE_SYSTEM_PREPARED .or. &
              qe_state_get() == QE_STATE_RESULT_AVAILABLE)
    end function qe_prepared_or_result

    !-----------------------------------------------------------------
    function qe_initialize() bind(C, name="qe_initialize") result(status)
        integer(c_int) :: status
        status = qe_engine_initialize()
    end function qe_initialize

    !-----------------------------------------------------------------
    function qe_finalize() bind(C, name="qe_finalize") result(status)
        integer(c_int) :: status
        ! Release any loaded system first (this resets Multiwfn globals).
        if (qe_state_get() /= 1) then  ! not already INITIALIZED
            block
                integer(c_int) :: s
                s = qe_state_release()
            end block
        end if
        status = qe_engine_finalize()
    end function qe_finalize

    !-----------------------------------------------------------------
    function qe_begin_system(ncenter_, nbasis_, nprims_, wfntype_) &
            bind(C, name="qe_begin_system") result(status)
        integer(c_int), value :: ncenter_, nbasis_, nprims_, wfntype_
        integer(c_int) :: status

        ! Require INITIALIZED state
        if (qe_state_get() /= QE_STATE_INITIALIZED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_begin_system", &
                              "engine not in INITIALIZED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ! The legacy 0.1.1 ABI is RHF-only. Open-shell execution must use
        ! the additive v1 entry point.
        if (wfntype_ /= 0) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_begin_system", &
                              "legacy 0.1.1 API is RHF-only; use qe_v1_model_begin for open-shell")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        status = qe_state_begin_system(ncenter_, nbasis_, nprims_, wfntype_)
        if (status == QE_SUCCESS) then
            call qe_state_set(QE_STATE_SYSTEM_LOADED)
        end if
    end function qe_begin_system

    !-----------------------------------------------------------------
    function qe_set_atomic_data(ncenter_, atnum_ptr, coor_ptr) &
            bind(C, name="qe_set_atomic_data") result(status)
        integer(c_int), value :: ncenter_
        type(c_ptr), value    :: atnum_ptr, coor_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_set_atomic_data")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_atomic_data(ncenter_, atnum_ptr, coor_ptr)
    end function qe_set_atomic_data

    !-----------------------------------------------------------------
    function qe_set_electronic_metadata(charge, mult, nelec) &
            bind(C, name="qe_set_electronic_metadata") result(status)
        integer(c_int), value :: charge, mult, nelec
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_set_electronic_metadata")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_electronic_metadata(charge, mult, nelec)
    end function qe_set_electronic_metadata

    !-----------------------------------------------------------------
    function qe_set_basis_data(nbasis_, nprims_, bc_ptr, bt_ptr) &
            bind(C, name="qe_set_basis_data") result(status)
        integer(c_int), value :: nbasis_, nprims_
        type(c_ptr), value    :: bc_ptr, bt_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_set_basis_data")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_basis_data(nbasis_, nprims_, bc_ptr, bt_ptr)
    end function qe_set_basis_data

    !-----------------------------------------------------------------
    function qe_set_density(nbasis_, dt_ptr, da_ptr, db_ptr) &
            bind(C, name="qe_set_density") result(status)
        integer(c_int), value :: nbasis_
        type(c_ptr), value    :: dt_ptr, da_ptr, db_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_set_density")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_density(nbasis_, dt_ptr, da_ptr, db_ptr)
    end function qe_set_density

    !-----------------------------------------------------------------
    function qe_set_overlap(nbasis_, ov_ptr) &
            bind(C, name="qe_set_overlap") result(status)
        integer(c_int), value :: nbasis_
        type(c_ptr), value    :: ov_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_set_overlap")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_overlap(nbasis_, ov_ptr)
    end function qe_set_overlap

    !-----------------------------------------------------------------
    function qe_prepare_system() bind(C, name="qe_prepare_system") result(status)
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_SYSTEM_LOADED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_prepare_system", &
                              "engine not in SYSTEM_LOADED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_prepare()
        if (status == QE_SUCCESS) then
            call qe_state_set(QE_STATE_SYSTEM_PREPARED)
        end if
    end function qe_prepare_system

    !-----------------------------------------------------------------
    function qe_calculate_mayer() bind(C, name="qe_calculate_mayer") result(status)
        integer(c_int) :: status
        status = qe_mayer_calculate()
    end function qe_calculate_mayer

    !-----------------------------------------------------------------
    function qe_get_mayer_dimensions(ncenter_ptr) &
            bind(C, name="qe_get_mayer_dimensions") result(status)
        type(c_ptr), value :: ncenter_ptr
        integer(c_int) :: status, n
        if (.not. c_associated(ncenter_ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_get_mayer_dimensions", &
                              "ncenter pointer is null")
            status = QE_ERROR_NULL_POINTER; return
        end if
        block
            integer(c_int), pointer :: p
            call c_f_pointer(ncenter_ptr, p)
            p = 0_c_int
        end block
        status = qe_mayer_get_dimensions(n)
        if (status == QE_SUCCESS) then
            block
                integer(c_int), pointer :: p
                call c_f_pointer(ncenter_ptr, p)
                p = n
            end block
        end if
    end function qe_get_mayer_dimensions

    !-----------------------------------------------------------------
    function qe_get_mayer_metadata(wfntype_ptr, has_spin_ptr) &
            bind(C, name="qe_get_mayer_metadata") result(status)
        type(c_ptr), value :: wfntype_ptr, has_spin_ptr
        integer(c_int) :: status, wt, hs
        if (.not. c_associated(wfntype_ptr) .or. .not. c_associated(has_spin_ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_get_mayer_metadata", &
                              "pointer is null")
            status = QE_ERROR_NULL_POINTER; return
        end if
        status = qe_mayer_get_metadata(wt, hs)
        if (status == QE_SUCCESS) then
            block
                integer(c_int), pointer :: p1, p2
                call c_f_pointer(wfntype_ptr, p1)
                call c_f_pointer(has_spin_ptr, p2)
                p1 = wt
                p2 = hs
            end block
        end if
    end function qe_get_mayer_metadata

    !-----------------------------------------------------------------
    function qe_get_mayer_result(result_id, buffer, capacity) &
            bind(C, name="qe_get_mayer_result") result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value    :: buffer
        integer(c_int) :: status
        status = qe_mayer_get_result(result_id, buffer, capacity)
    end function qe_get_mayer_result

    !-----------------------------------------------------------------
    function qe_release_system() bind(C, name="qe_release_system") result(status)
        integer(c_int) :: status
        integer(c_int) :: s

        if (qe_state_get() == QE_STATE_INITIALIZED .or. &
            qe_state_get() == QE_STATE_UNINITIALIZED) then
            ! Nothing to release
            status = QE_SUCCESS
            return
        end if

        status = qe_state_release()
        call qe_open_shell_set(.false.)
        call qe_state_set(QE_STATE_INITIALIZED)
    end function qe_release_system

    !=================================================================
    !  Additive v1 model API (Molecular Data Model 1.0)
    !  These functions do not change the semantics of the 0.1.x API.
    !=================================================================

    !-----------------------------------------------------------------
    function qe_v1_enable_open_shell(enable) &
            bind(C, name="qe_v1_enable_open_shell") result(status)
        integer(c_int), value :: enable
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_INITIALIZED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_enable_open_shell", &
                              "open-shell authorization can only change in INITIALIZED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (enable == 0) then
            call qe_open_shell_set(.false.)
        else if (enable == 1) then
            call qe_open_shell_set(.true.)
        else
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, &
                              "qe_v1_enable_open_shell", "enable must be 0 or 1")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if
        status = QE_SUCCESS
    end function qe_v1_enable_open_shell

    !-----------------------------------------------------------------
    function qe_v1_model_begin(ncenter_, nbasis_, nprims_, wfntype_) &
            bind(C, name="qe_v1_model_begin") result(status)
        integer(c_int), value :: ncenter_, nbasis_, nprims_, wfntype_
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_INITIALIZED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_model_begin", &
                              "engine not in INITIALIZED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_begin_system(ncenter_, nbasis_, nprims_, wfntype_)
        if (status == QE_SUCCESS) call qe_state_set(QE_STATE_SYSTEM_LOADED)
    end function qe_v1_model_begin

    !-----------------------------------------------------------------
    function qe_v1_set_atoms(ncenter_, z_ptr, coords_ptr, unit) &
            bind(C, name="qe_v1_set_atoms") result(status)
        integer(c_int), value :: ncenter_, unit
        type(c_ptr), value    :: z_ptr, coords_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        real(c_double), pointer :: xyz(:,:)
        real(c_double), allocatable, target :: xyz_bohr(:,:)
        real(c_double), parameter :: BOHR_PER_ANGSTROM = 0.529177210903_c_double
        logical :: ok
        integer :: i, j, istat

        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_atoms")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (unit /= 0 .and. unit /= 1) then
            call qe_set_error(QE_ERROR_INVALID_ARGUMENT, "qe_v1_set_atoms", &
                              "unit must be 0 (bohr) or 1 (angstrom)")
            status = QE_ERROR_INVALID_ARGUMENT; return
        end if
        if (ncenter_ /= qe_state_get_ncenter()) then
            call qe_set_error(QE_ERROR_INVALID_DIMENSION, "qe_v1_set_atoms", &
                              "ncenter does not match qe_v1_model_begin")
            status = QE_ERROR_INVALID_DIMENSION; return
        end if
        if (unit == 0) then
            status = qe_state_set_atomic_data(ncenter_, z_ptr, coords_ptr)
            return
        end if
        if (.not. qe_check_product(3_c_int, ncenter_, "3*ncenter", &
                                   "qe_v1_set_atoms", status)) return
        ok = qe_pointer_to_real2d(coords_ptr, 3_c_int, ncenter_, xyz, status)
        if (.not. ok) return
        allocate(xyz_bohr(3, ncenter_), stat=istat)
        if (istat /= 0) then
            call qe_set_allocation_error("qe_v1_set_atoms", "xyz_bohr")
            status = QE_ERROR_ALLOCATION; return
        end if
        do j = 1, ncenter_
            do i = 1, 3
                xyz_bohr(i,j) = xyz(i,j) / BOHR_PER_ANGSTROM
            end do
        end do
        status = qe_state_set_atomic_data(ncenter_, z_ptr, c_loc(xyz_bohr))
        deallocate(xyz_bohr)
    end function qe_v1_set_atoms

    !-----------------------------------------------------------------
    function qe_v1_set_shells(nshell, center_ptr, l_ptr, ps_ptr, pe_ptr, cart_ptr) &
            bind(C, name="qe_v1_set_shells") result(status)
        integer(c_int), value :: nshell
        type(c_ptr), value    :: center_ptr, l_ptr, ps_ptr, pe_ptr, cart_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_shells")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_shells(nshell, center_ptr, l_ptr, ps_ptr, pe_ptr, cart_ptr)
    end function qe_v1_set_shells

    !-----------------------------------------------------------------
    function qe_v1_set_primitives(nprims, center_ptr, type_ptr, exp_ptr, &
                                  coeff_ptr, norm_ptr, shell_ptr) &
            bind(C, name="qe_v1_set_primitives") result(status)
        integer(c_int), value :: nprims
        type(c_ptr), value    :: center_ptr, type_ptr, exp_ptr, coeff_ptr
        type(c_ptr), value    :: norm_ptr, shell_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_primitives")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_primitives(nprims, center_ptr, type_ptr, exp_ptr, &
                                         coeff_ptr, norm_ptr, shell_ptr)
    end function qe_v1_set_primitives

    !-----------------------------------------------------------------
    function qe_v1_set_ao_map(nbasis, center_ptr, shell_ptr, mtype_ptr, &
                              atype_ptr, source_ptr) &
            bind(C, name="qe_v1_set_ao_map") result(status)
        integer(c_int), value :: nbasis
        type(c_ptr), value    :: center_ptr, shell_ptr, mtype_ptr, atype_ptr, source_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_ao_map")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_ao_map(nbasis, center_ptr, shell_ptr, mtype_ptr, &
                                     atype_ptr, source_ptr)
    end function qe_v1_set_ao_map

    !-----------------------------------------------------------------
    function qe_v1_set_ao_normalization(nbasis, self_ptr, contraction_ptr, &
                                        convention_ptr) &
            bind(C, name="qe_v1_set_ao_normalization") result(status)
        integer(c_int), value :: nbasis
        type(c_ptr), value    :: self_ptr, contraction_ptr, convention_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_ao_normalization")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_ao_normalization(nbasis, self_ptr, contraction_ptr, &
                                               convention_ptr)
    end function qe_v1_set_ao_normalization

    !-----------------------------------------------------------------
    function qe_v1_set_angular_canonical(canonical) &
            bind(C, name="qe_v1_set_angular_canonical") result(status)
        integer(c_int), value :: canonical
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_SYSTEM_LOADED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_set_angular_canonical", &
                              "engine not in SYSTEM_LOADED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_angular_canonical(canonical)
    end function qe_v1_set_angular_canonical

    !-----------------------------------------------------------------
    function qe_v1_set_density(nbasis, representation, dt_ptr, da_ptr, db_ptr) &
            bind(C, name="qe_v1_set_density") result(status)
        integer(c_int), value :: nbasis, representation
        type(c_ptr), value    :: dt_ptr, da_ptr, db_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_density")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (representation /= 0) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_v1_set_density", &
                              "only representation 0 (ao_current_basis) is accepted")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        status = qe_state_set_density(nbasis, dt_ptr, da_ptr, db_ptr)
    end function qe_v1_set_density

    !-----------------------------------------------------------------
    function qe_v1_set_overlap(nbasis, representation, ov_ptr) &
            bind(C, name="qe_v1_set_overlap") result(status)
        integer(c_int), value :: nbasis, representation
        type(c_ptr), value    :: ov_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_overlap")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (representation /= 0) then
            call qe_set_error(QE_ERROR_UNSUPPORTED, "qe_v1_set_overlap", &
                              "only representation 0 (ao_current_basis) is accepted")
            status = QE_ERROR_UNSUPPORTED; return
        end if
        status = qe_state_set_overlap(nbasis, ov_ptr)
    end function qe_v1_set_overlap

    !-----------------------------------------------------------------
    function qe_v1_set_orbitals(nmo, ncoeff, repr, layout, coeff_ptr, &
                                ene_ptr, occ_ptr, spin_ptr) &
            bind(C, name="qe_v1_set_orbitals") result(status)
        integer(c_int), value :: nmo, ncoeff, repr, layout
        type(c_ptr), value    :: coeff_ptr, ene_ptr, occ_ptr, spin_ptr
        integer(c_int) :: status
        integer(c_int) :: ALLOWED(1)
        ALLOWED = [QE_STATE_SYSTEM_LOADED]
        if (.not. qe_state_require(ALLOWED, 1, "qe_v1_set_orbitals")) then
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_set_orbitals(nmo, ncoeff, repr, layout, coeff_ptr, &
                                       ene_ptr, occ_ptr, spin_ptr)
    end function qe_v1_set_orbitals

    !-----------------------------------------------------------------
    function qe_v1_model_commit() bind(C, name="qe_v1_model_commit") result(status)
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_SYSTEM_LOADED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_model_commit", &
                              "engine not in SYSTEM_LOADED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_state_prepare()
        if (status == QE_SUCCESS) call qe_state_set(QE_STATE_SYSTEM_PREPARED)
    end function qe_v1_model_commit

    !-----------------------------------------------------------------
    function qe_v1_model_release() bind(C, name="qe_v1_model_release") result(status)
        integer(c_int) :: status
        status = qe_release_system()
    end function qe_v1_model_release

    !-----------------------------------------------------------------
    function qe_v1_get_readiness(flags_ptr) bind(C, name="qe_v1_get_readiness") &
            result(status)
        type(c_ptr), value :: flags_ptr
        integer(c_int) :: status
        integer(c_int), pointer :: p
        if (.not. c_associated(flags_ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, "qe_v1_get_readiness", &
                              "flags pointer is null")
            status = QE_ERROR_NULL_POINTER; return
        end if
        call c_f_pointer(flags_ptr, p)
        p = qe_state_get_readiness()
        status = QE_SUCCESS
    end function qe_v1_get_readiness

    !-----------------------------------------------------------------
    function qe_v1_generate_density() bind(C, name="qe_v1_generate_density") &
            result(status)
        integer(c_int) :: status
        logical :: ok
        if (qe_state_get() /= QE_STATE_SYSTEM_PREPARED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_generate_density", &
                              "engine not in SYSTEM_PREPARED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ok = qe_genp_build_orbitals(status)
        if (.not. ok) return
        ok = qe_genp_generate(status)
    end function qe_v1_generate_density

    !-----------------------------------------------------------------
    function qe_v1_generate_overlap() bind(C, name="qe_v1_generate_overlap") &
            result(status)
        integer(c_int) :: status
        logical :: ok
        if (qe_state_get() /= QE_STATE_SYSTEM_PREPARED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_generate_overlap", &
                              "engine not in SYSTEM_PREPARED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ok = qe_gensbas_build(status)
        if (.not. ok) return
        ok = qe_gensbas_generate(status)
    end function qe_v1_generate_overlap

    !-----------------------------------------------------------------
    function qe_v1_generate_cartesian_overlap() &
            bind(C, name="qe_v1_generate_cartesian_overlap") result(status)
        integer(c_int) :: status
        logical :: ok
        if (qe_state_get() /= QE_STATE_SYSTEM_PREPARED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_generate_cartesian_overlap", &
                              "engine not in SYSTEM_PREPARED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ok = qe_gensbas_build(status)
        if (.not. ok) return
        ok = qe_gensbas_generate_cartesian(status)
    end function qe_v1_generate_cartesian_overlap

    !-----------------------------------------------------------------
    function qe_v1_get_overlap_dimensions(nbasis_ptr, nbasisCar_ptr, nprims_ptr) &
            bind(C, name="qe_v1_get_overlap_dimensions") result(status)
        type(c_ptr), value :: nbasis_ptr, nbasisCar_ptr, nprims_ptr
        integer(c_int) :: status, n, nc, np
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_overlap_dimensions", &
                              "engine has no prepared basis")
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (.not. c_associated(nbasis_ptr) .or. &
            .not. c_associated(nbasisCar_ptr) .or. &
            .not. c_associated(nprims_ptr)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        status = qe_gensbas_dimensions(n, nc, np)
        if (status == QE_SUCCESS) then
            block
                integer(c_int), pointer :: p1, p2, p3
                call c_f_pointer(nbasis_ptr, p1); p1 = n
                call c_f_pointer(nbasisCar_ptr, p2); p2 = nc
                call c_f_pointer(nprims_ptr, p3); p3 = np
            end block
        end if
    end function qe_v1_get_overlap_dimensions

    !-----------------------------------------------------------------
    function qe_v1_get_generated_overlap(buffer, capacity) &
            bind(C, name="qe_v1_get_generated_overlap") result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_generated_overlap", &
                              "engine has no prepared overlap")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_gensbas_get_current(buffer, capacity)
    end function qe_v1_get_generated_overlap

    !-----------------------------------------------------------------
    function qe_v1_get_generated_cartesian_overlap(buffer, capacity) &
            bind(C, name="qe_v1_get_generated_cartesian_overlap") result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_generated_cartesian_overlap", &
                              "engine has no prepared basis")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_gensbas_get_cartesian(buffer, capacity)
    end function qe_v1_get_generated_cartesian_overlap

    !-----------------------------------------------------------------
    function qe_v1_build_electronic_state() &
            bind(C, name="qe_v1_build_electronic_state") result(status)
        integer(c_int) :: status
        logical :: ok
        if (qe_state_get() /= QE_STATE_SYSTEM_LOADED) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_build_electronic_state", &
                              "engine not in SYSTEM_LOADED state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ok = qe_electronic_prepare_from_model(status)
        if (ok) call qe_state_set(QE_STATE_SYSTEM_PREPARED)
    end function qe_v1_build_electronic_state

    !-----------------------------------------------------------------
    function qe_v1_generate_primitive_density() &
            bind(C, name="qe_v1_generate_primitive_density") result(status)
        integer(c_int) :: status
        logical :: ok
        if (qe_state_get() /= QE_STATE_SYSTEM_PREPARED .and. &
            qe_state_get() /= QE_STATE_RESULT_AVAILABLE) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_generate_primitive_density", &
                              "engine not in PREPARED/RESULT_AVAILABLE state")
            status = QE_ERROR_INVALID_STATE; return
        end if
        ok = qe_genpprim_generate(status)
    end function qe_v1_generate_primitive_density

    !-----------------------------------------------------------------
    function qe_v1_get_primitive_density_dimensions(nprims_ptr) &
            bind(C, name="qe_v1_get_primitive_density_dimensions") result(status)
        type(c_ptr), value :: nprims_ptr
        integer(c_int) :: status, n
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_primitive_density_dimensions", &
                              "engine has no prepared basis")
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (.not. c_associated(nprims_ptr)) then
            status = QE_ERROR_NULL_POINTER; return
        end if
        status = qe_genpprim_dimensions(n)
        if (status == QE_SUCCESS) then
            block
                integer(c_int), pointer :: p
                call c_f_pointer(nprims_ptr, p); p = n
            end block
        end if
    end function qe_v1_get_primitive_density_dimensions

    !-----------------------------------------------------------------
    function qe_v1_get_generated_primitive_density(result_id, buffer, capacity) &
            bind(C, name="qe_v1_get_generated_primitive_density") result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value :: buffer
        integer(c_int) :: status
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_generated_primitive_density", &
                              "engine has no prepared basis")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_genpprim_get(result_id, buffer, capacity)
    end function qe_v1_get_generated_primitive_density

    !-----------------------------------------------------------------
    function qe_v1_get_primitive_overlap(buffer, capacity) &
            bind(C, name="qe_v1_get_primitive_overlap") result(status)
        type(c_ptr), value :: buffer
        integer(c_int), value :: capacity
        integer(c_int) :: status
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_primitive_overlap", &
                              "engine has no prepared basis")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_genpprim_overlap(buffer, capacity)
    end function qe_v1_get_primitive_overlap

    !-----------------------------------------------------------------
    function qe_v1_get_generated_density_dimensions(nbasis_ptr) &
            bind(C, name="qe_v1_get_generated_density_dimensions") result(status)
        type(c_ptr), value :: nbasis_ptr
        integer(c_int) :: status, n
        if (.not. qe_prepared_or_result()) then
            call qe_set_error(QE_ERROR_INVALID_STATE, &
                              "qe_v1_get_generated_density_dimensions", &
                              "engine has no prepared density")
            status = QE_ERROR_INVALID_STATE; return
        end if
        if (.not. c_associated(nbasis_ptr)) then
            call qe_set_error(QE_ERROR_NULL_POINTER, &
                              "qe_v1_get_generated_density_dimensions", &
                              "null pointer")
            status = QE_ERROR_NULL_POINTER; return
        end if
        status = qe_genp_dimensions(n)
        if (status == QE_SUCCESS) then
            block
                integer(c_int), pointer :: p
                call c_f_pointer(nbasis_ptr, p)
                p = n
            end block
        end if
    end function qe_v1_get_generated_density_dimensions

    !-----------------------------------------------------------------
    function qe_v1_get_generated_density(result_id, buffer, capacity) &
            bind(C, name="qe_v1_get_generated_density") result(status)
        integer(c_int), value :: result_id, capacity
        type(c_ptr), value    :: buffer
        integer(c_int) :: status
        if (qe_state_get() /= QE_STATE_SYSTEM_PREPARED .and. &
            qe_state_get() /= QE_STATE_RESULT_AVAILABLE) then
            call qe_set_error(QE_ERROR_INVALID_STATE, "qe_v1_get_generated_density", &
                              "engine has no prepared density")
            status = QE_ERROR_INVALID_STATE; return
        end if
        status = qe_genp_get_density(result_id, buffer, capacity)
    end function qe_v1_get_generated_density

    !-----------------------------------------------------------------
    function qe_get_version() bind(C, name="qe_get_version") result(cstr)
        type(c_ptr) :: cstr
        character(kind=c_char, len=1), save, target :: buf(QE_VERSION_LEN)
        integer :: i, n
        n = len_trim(QE_VERSION_STR)
        do i = 1, n
            buf(i) = QE_VERSION_STR(i:i)
        end do
        buf(n+1) = c_null_char
        cstr = c_loc(buf(1))
    end function qe_get_version

end module qe_c_api
