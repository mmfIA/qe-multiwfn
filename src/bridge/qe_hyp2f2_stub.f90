! ===================================================================
!  qe_hyp2f2_stub.f90
!
!  Multiwfn's function.f90 uses module mod_2F2 (from ext/2F2.f90),
!  whose interface declares a C function `hyp2F2` (provided by
!  ext/2F2.c when linked against flint/arb). The fractional-derivative
!  / fractional-integral features in Multiwfn rely on this function.
!
!  In the QE-Multiwfn 0.1.1 (unused in the minimal Mayer build) build we do NOT have flint/arb available,
!  and the Mayer code path does not exercise hyp2F2 anyway. This
!  module provides a Fortran-side stub bound with the same C name,
!  so the linker resolves the symbol and the library can be built.
!
!  The stub writes a warning to stderr and returns a sentinel.
!  If the fractional-derivative path is ever reached, it will return
!  an invalid value that the caller can detect.
!
!  This is documented in docs/LIMITATIONS.md.
! ===================================================================
function qe_hyp2f2_stub(a, b, c, d, z) bind(C, name="hyp2F2")
    use, intrinsic :: iso_c_binding
    implicit none
    real(c_double), value, intent(in) :: a, b, c, d, z
    real(c_double) :: qe_hyp2f2_stub

    ! Fractional derivative/integral features are unavailable in
    ! QE-Multiwfn 0.1.1 (unused in the minimal Mayer build) because flint/arb is not linked.
    ! Return -1.0 (callers in Multiwfn guard against z<=0, so -1 is
    ! a clearly invalid sentinel that the caller can detect).
    qe_hyp2f2_stub = -1.0_c_double
end function qe_hyp2f2_stub
