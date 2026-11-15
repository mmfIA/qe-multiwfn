! ===================================================================
!  qe_molecular_state.f90
!
!  Canonical molecular data model. Holds Python-supplied molecular
!  data in Fortran-owned memory before it is pushed into Multiwfn's
!  global state (defvar) by qe_state_builder.
! ===================================================================
module qe_molecular_state
    use, intrinsic :: iso_c_binding
    use qe_status
    implicit none
    private

    public :: qe_mol_t
    public :: qe_mol_create
    public :: qe_mol_destroy
    public :: qe_mol_reset
    public :: the_mol

    ! v0.1.1 model: hold the inputs needed for Mayer.
    ! In later versions this grows to include orbital coefficients,
    ! basis set details, ECP/EDF, PBC, etc.
    type :: qe_mol_t
        ! --- Dimensions ---
        integer(c_int) :: ncenter  = 0
        integer(c_int) :: nbasis   = 0
        integer(c_int) :: nprims   = 0
        integer(c_int) :: wfntype = 0

        ! --- Atoms ---
        integer(c_int), allocatable :: atomic_numbers(:)   ! (ncenter)
        real(c_double),  allocatable :: coordinates(:,:)     ! (3, ncenter) in Bohr

        ! --- Electronic metadata ---
        integer(c_int) :: charge       = 0
        integer(c_int) :: multiplicity = 1
        integer(c_int) :: nelectron   = 0

        ! --- Basis-function ownership metadata (one entry per AO) ---
        integer(c_int), allocatable :: basis_center(:)  ! (nbasis), one center per basis function
        integer(c_int), allocatable :: basis_type(:)    ! (nbasis), one type per basis function

        ! --- Matrices (Fortran order) ---
        ! density_total : (nbasis, nbasis), always required
        ! density_alpha  : reserved for future spin-resolved support
        ! density_beta   : reserved for future spin-resolved support
        ! overlap        : (nbasis, nbasis), always required
        real(c_double), allocatable :: density_total(:,:)
        real(c_double), allocatable :: density_alpha(:,:)
        real(c_double), allocatable :: density_beta(:,:)
        real(c_double), allocatable :: overlap(:,:)

        ! --- Derived: per-atom basis function ranges (computed by
        !     qe_state_builder; not set by the user directly) ---
        integer(c_int), allocatable :: basstart(:)  ! (ncenter)
        integer(c_int), allocatable :: basend(:)    ! (ncenter)

        ! --- v1 basis description (all optional for the Mayer path) ---
        integer(c_int), allocatable :: shell_center(:)       ! (nshell)
        integer(c_int), allocatable :: shell_l(:)            ! (nshell)
        integer(c_int), allocatable :: shell_prim_start(:)   ! (nshell)
        integer(c_int), allocatable :: shell_prim_end(:)     ! (nshell)
        integer(c_int), allocatable :: shell_cartesian(:)    ! (nshell), 0/1
        integer(c_int), allocatable :: prim_center(:)        ! (nprims)
        integer(c_int), allocatable :: prim_type(:)          ! (nprims)
        integer(c_int), allocatable :: prim_shell(:)         ! (nprims)
        real(c_double),  allocatable :: prim_exponent(:)     ! (nprims)
        real(c_double),  allocatable :: prim_coefficient(:)  ! (nprims)
        real(c_double),  allocatable :: prim_normalization(:) ! (nprims)
        integer(c_int), allocatable :: ao_shell(:)           ! (nbasis)
        integer(c_int), allocatable :: ao_multiwfn_type(:)   ! (nbasis)
        integer(c_int), allocatable :: ao_angular_type(:)    ! (nbasis)
        integer(c_int), allocatable :: ao_source_index(:)    ! (nbasis)
        real(c_double),  allocatable :: ao_source_self_overlap(:) ! (nbasis)
        real(c_double),  allocatable :: ao_contraction_norm(:)    ! (nbasis)
        integer(c_int), allocatable :: ao_normalization_convention(:) ! (nbasis)
        integer(c_int) :: nshell = 0

        ! --- v1 optional orbital data (not used by Mayer 0.1.x) ---
        integer(c_int) :: nmo_v1 = 0
        integer(c_int) :: orb_coefficient_representation = 0  ! 0=contracted, 1=primitive
        integer(c_int) :: orb_coefficient_layout = 0           ! 0=orbital_ao, 1=ao_orbital
        real(c_double),  allocatable :: orb_coefficients(:,:)  ! (n1,n2)
        real(c_double),  allocatable :: orb_energies(:)        ! (nmo)
        real(c_double),  allocatable :: orb_occupations(:)     ! (nmo)
        integer(c_int), allocatable :: orb_spin(:)            ! (nmo): 0=total,1=alpha,2=beta

        ! --- Bookkeeping ---
        logical :: has_atoms      = .false.
        logical :: has_basis      = .false.
        logical :: has_density    = .false.
        logical :: has_overlap    = .false.
        logical :: has_metadata   = .false.
        logical :: has_shells     = .false.
        logical :: has_primitives = .false.
        logical :: has_ao_map     = .false.
        logical :: has_ao_normalization = .false.
        logical :: has_canonical_angular = .false.
        logical :: has_orbitals   = .false.
    end type qe_mol_t

    ! Single global instance (process-global in v0.1.1)
    type(qe_mol_t), save, target :: the_mol

contains

    function qe_mol_create() result(p)
        type(qe_mol_t), pointer :: p
        call qe_mol_reset(the_mol)
        p => the_mol
    end function qe_mol_create

    subroutine qe_mol_destroy(m)
        type(qe_mol_t), intent(inout) :: m
        if (allocated(m%atomic_numbers))  deallocate(m%atomic_numbers)
        if (allocated(m%coordinates))     deallocate(m%coordinates)
        if (allocated(m%basis_center))   deallocate(m%basis_center)
        if (allocated(m%basis_type))     deallocate(m%basis_type)
        if (allocated(m%density_total))  deallocate(m%density_total)
        if (allocated(m%density_alpha))  deallocate(m%density_alpha)
        if (allocated(m%density_beta))   deallocate(m%density_beta)
        if (allocated(m%overlap))        deallocate(m%overlap)
        if (allocated(m%basstart))       deallocate(m%basstart)
        if (allocated(m%basend))         deallocate(m%basend)
        if (allocated(m%shell_center))      deallocate(m%shell_center)
        if (allocated(m%shell_l))           deallocate(m%shell_l)
        if (allocated(m%shell_prim_start))  deallocate(m%shell_prim_start)
        if (allocated(m%shell_prim_end))    deallocate(m%shell_prim_end)
        if (allocated(m%shell_cartesian))   deallocate(m%shell_cartesian)
        if (allocated(m%prim_center))       deallocate(m%prim_center)
        if (allocated(m%prim_type))         deallocate(m%prim_type)
        if (allocated(m%prim_shell))        deallocate(m%prim_shell)
        if (allocated(m%prim_exponent))     deallocate(m%prim_exponent)
        if (allocated(m%prim_coefficient))  deallocate(m%prim_coefficient)
        if (allocated(m%prim_normalization)) deallocate(m%prim_normalization)
        if (allocated(m%ao_shell))          deallocate(m%ao_shell)
        if (allocated(m%ao_multiwfn_type))  deallocate(m%ao_multiwfn_type)
        if (allocated(m%ao_angular_type))   deallocate(m%ao_angular_type)
        if (allocated(m%ao_source_index))   deallocate(m%ao_source_index)
        if (allocated(m%ao_source_self_overlap)) deallocate(m%ao_source_self_overlap)
        if (allocated(m%ao_contraction_norm))    deallocate(m%ao_contraction_norm)
        if (allocated(m%ao_normalization_convention)) deallocate(m%ao_normalization_convention)
        if (allocated(m%orb_coefficients))  deallocate(m%orb_coefficients)
        if (allocated(m%orb_energies))      deallocate(m%orb_energies)
        if (allocated(m%orb_occupations))   deallocate(m%orb_occupations)
        if (allocated(m%orb_spin))          deallocate(m%orb_spin)
        call qe_mol_reset(m)
    end subroutine qe_mol_destroy

    subroutine qe_mol_reset(m)
        type(qe_mol_t), intent(inout) :: m
        m%ncenter       = 0
        m%nbasis        = 0
        m%nprims        = 0
        m%wfntype       = 0
        m%charge        = 0
        m%multiplicity  = 1
        m%nelectron     = 0
        m%nshell             = 0
        m%nmo_v1             = 0
        m%orb_coefficient_representation = 0
        m%orb_coefficient_layout = 0
        m%has_atoms      = .false.
        m%has_basis      = .false.
        m%has_density    = .false.
        m%has_overlap    = .false.
        m%has_metadata   = .false.
        m%has_shells     = .false.
        m%has_primitives = .false.
        m%has_ao_map     = .false.
        m%has_ao_normalization = .false.
        m%has_canonical_angular = .false.
        m%has_orbitals   = .false.
    end subroutine qe_mol_reset

end module qe_molecular_state
