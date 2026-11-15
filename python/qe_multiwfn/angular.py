"""Canonical angular conventions and safe basis-phase transformations.

This module is deliberately independent of any input adapter.  It defines the
MDM angular contract, the known real-spherical conventions and the phase
transformations that may be applied at the import boundary.  It never calls
the native backend and it does not remove the Fortran f/g/h guard.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np

ANGULAR_REPRESENTATIONS = ("unknown", "cartesian", "spherical_real")
BASIS_ANGULAR_REPRESENTATIONS = ("unknown", "cartesian", "spherical_real", "mixed")
ANGULAR_STATES = ("unknown", "source", "canonical")
CANONICAL_CONVENTION_ID = "qe-mdm-real-spherical-1.0"
CANONICAL_CARTESIAN_ID = "qe-mdm-cartesian-1.0"
SUPPORTED_TRANSFORM_L = (0, 1, 2, 3)
CANONICAL_MAGNETIC_ORDER = {
    0: (0,),
    1: (0, 1, -1),
    2: (0, 1, -1, 2, -2),
    3: (0, 1, -1, 2, -2, 3, -3),
}
CANONICAL_CARTESIAN_ORDER = {
    0: ("s",),
    1: ("px", "py", "pz"),
    2: ("xx", "yy", "zz", "xy", "xz", "yz"),
    3: ("xxx", "yyy", "zzz", "xyy", "xxy", "xxz", "xzz", "yzz", "yyz", "xyz"),
}


class AngularError(ValueError):
    """Base class for angular-contract errors."""


class AngularConventionError(AngularError):
    """The supplied angular convention is incomplete or inconsistent."""


class AngularUnsupportedError(AngularError):
    """The angular representation/order is not supported in this phase."""


class AngularStateError(AngularError):
    """The object is in a state that forbids this operation."""


class AngularAlreadyCanonicalError(AngularStateError):
    """A canonical object was offered for a second transformation."""


class AngularDoubleTransformError(AngularStateError):
    """The same transform id was already recorded for this model."""


@dataclass(frozen=True)
class AngularConvention:
    """Angular convention for one shell / angular momentum.

    ``magnetic_order`` is the order of the real spherical components in the
    object.  ``phase_signs`` are the signs relative to the reference real
    spherical functions.  The canonical convention has all signs +1 and the
    order ``(0,+1,-1,+2,-2,...)``.
    """

    l: int
    representation: str = "unknown"
    magnetic_order: Tuple[int, ...] = ()
    phase_signs: Tuple[int, ...] = ()
    normalization: str = "unknown"
    cartesian_order: Tuple[str, ...] = ()
    convention_id: str = "unknown"
    source_program: str = ""
    source_version: str = ""
    source_format: str = ""
    state: str = "unknown"
    transform_id: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "l", int(self.l))
        object.__setattr__(self, "magnetic_order", tuple(int(x) for x in self.magnetic_order))
        object.__setattr__(self, "phase_signs", tuple(int(x) for x in self.phase_signs))
        object.__setattr__(self, "cartesian_order", tuple(str(x) for x in self.cartesian_order))
        if self.l < 0:
            raise AngularConventionError("angular l must be >= 0")
        if self.representation not in ANGULAR_REPRESENTATIONS:
            raise AngularConventionError(
                f"angular representation must be one of {ANGULAR_REPRESENTATIONS}"
            )
        if self.state not in ANGULAR_STATES:
            raise AngularConventionError(f"angular state must be one of {ANGULAR_STATES}")
        if self.representation in ("spherical_real", "unknown"):
            expected = 2 * self.l + 1
            if self.magnetic_order and len(self.magnetic_order) != expected:
                raise AngularConventionError(
                    f"magnetic_order length {len(self.magnetic_order)} != {expected}"
                )
            if self.phase_signs and len(self.phase_signs) != expected:
                raise AngularConventionError(
                    f"phase_signs length {len(self.phase_signs)} != {expected}"
                )
            if self.magnetic_order and set(self.magnetic_order) != set(
                CANONICAL_MAGNETIC_ORDER.get(self.l, ())
            ):
                # For l > 3 we do not claim a canonical set; only known l are
                # representable in this phase.
                if self.l in CANONICAL_MAGNETIC_ORDER:
                    raise AngularConventionError(
                        f"magnetic_order is not a permutation of the m set for l={self.l}"
                    )
            if any(s not in (-1, 1) for s in self.phase_signs):
                raise AngularConventionError("phase_signs must be +1 or -1")
        if self.representation == "cartesian":
            if self.cartesian_order and len(self.cartesian_order) != _cartesian_count(self.l):
                raise AngularConventionError("cartesian_order length mismatch")
        if self.l > max(SUPPORTED_TRANSFORM_L) and self.state == "canonical":
            raise AngularUnsupportedError(
                f"canonical angular metadata for l={self.l} is not supported"
            )

    def to_dict(self) -> dict:
        return {
            "l": self.l,
            "representation": self.representation,
            "magnetic_order": list(self.magnetic_order),
            "phase_signs": list(self.phase_signs),
            "normalization": self.normalization,
            "cartesian_order": list(self.cartesian_order),
            "convention_id": self.convention_id,
            "source_program": self.source_program,
            "source_version": self.source_version,
            "source_format": self.source_format,
            "state": self.state,
            "transform_id": self.transform_id,
        }


@dataclass(frozen=True)
class AngularBasisMetadata:
    """Global angular contract of a BasisSet."""

    representation: str = "unknown"
    magnetic_order_policy: str = "m0,+1,-1,+2,-2,..."
    phase_convention: str = "unknown"
    normalization: str = "unknown"
    convention_id: str = "unknown"
    state: str = "unknown"
    transform_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.representation not in BASIS_ANGULAR_REPRESENTATIONS:
            raise AngularConventionError("invalid basis angular representation")
        if self.state not in ANGULAR_STATES:
            raise AngularConventionError("invalid basis angular state")

    def to_dict(self) -> dict:
        return {
            "representation": self.representation,
            "magnetic_order_policy": self.magnetic_order_policy,
            "phase_convention": self.phase_convention,
            "normalization": self.normalization,
            "convention_id": self.convention_id,
            "state": self.state,
            "transform_id": self.transform_id,
        }


@dataclass(frozen=True)
class AngularObjectMetadata:
    """Angular state/provenance for a coefficient set or a matrix."""

    state: str = "unknown"
    convention_id: str = "unknown"
    source_convention_id: Optional[str] = None
    transform_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.state not in ANGULAR_STATES:
            raise AngularConventionError("invalid angular object state")

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "convention_id": self.convention_id,
            "source_convention_id": self.source_convention_id,
            "transform_id": self.transform_id,
        }


@dataclass(frozen=True)
class AngularTransformRecord:
    transform_id: str
    source_convention_id: str
    canonical_convention_id: str
    l: int
    shell_indices: Tuple[int, ...]
    phase_signs: Tuple[int, ...]
    applied_to: Tuple[str, ...]
    input_hashes: Dict[str, str]
    output_hashes: Dict[str, str]

    def to_dict(self) -> dict:
        return {
            "transform_id": self.transform_id,
            "source_convention_id": self.source_convention_id,
            "canonical_convention_id": self.canonical_convention_id,
            "l": self.l,
            "shell_indices": list(self.shell_indices),
            "phase_signs": list(self.phase_signs),
            "applied_to": list(self.applied_to),
            "input_hashes": dict(self.input_hashes),
            "output_hashes": dict(self.output_hashes),
        }


def _cartesian_count(l: int) -> int:
    return (l + 1) * (l + 2) // 2


def canonical_convention(l: int) -> AngularConvention:
    """Return the canonical real-spherical convention for ``l``."""
    l = int(l)
    if l not in SUPPORTED_TRANSFORM_L:
        raise AngularUnsupportedError(
            f"canonical real-spherical convention for l={l} is not supported in Phase 7B"
        )
    order = CANONICAL_MAGNETIC_ORDER[l]
    return AngularConvention(
        l=l,
        representation="spherical_real",
        magnetic_order=order,
        phase_signs=tuple(1 for _ in order),
        normalization="unit_spherical",
        cartesian_order=CANONICAL_CARTESIAN_ORDER[l],
        convention_id=CANONICAL_CONVENTION_ID,
        source_program="",
        source_version="",
        source_format="",
        state="canonical",
    )


def canonical_cartesian_convention(l: int) -> AngularConvention:
    """Return the canonical Cartesian convention for ``l`` (no phase change)."""
    l = int(l)
    if l not in SUPPORTED_TRANSFORM_L:
        raise AngularUnsupportedError(f"canonical Cartesian l={l} is not supported")
    return AngularConvention(
        l=l,
        representation="cartesian",
        magnetic_order=(),
        phase_signs=(),
        normalization="cartesian_normalized",
        cartesian_order=CANONICAL_CARTESIAN_ORDER[l],
        convention_id=CANONICAL_CARTESIAN_ID,
        state="canonical",
    )


def known_source_convention(l: int, program: str, version: str = "") -> AngularConvention:
    """Known source convention registry.

    Only the ORCA real-spherical convention investigated in Phase 7A is
    registered for f.  The s/p/d ORCA order/phase is the canonical one for
    the validated fixtures; the f phase is the Phase 7A result.  Unknown
    programs/versions fail closed.
    """
    l = int(l)
    p = str(program).strip().lower()
    if p != "orca" or l not in SUPPORTED_TRANSFORM_L:
        raise AngularConventionError(
            f"no registered source convention for program={program!r}, l={l}"
        )
    order = CANONICAL_MAGNETIC_ORDER[l]
    if l == 3:
        signs = (1, 1, 1, 1, 1, -1, -1)
        cid = "orca-6.1.1-real-f-phase-1"
    else:
        signs = tuple(1 for _ in order)
        cid = f"orca-{version or 'validated'}-real-l{l}-identity"
    return AngularConvention(
        l=l,
        representation="spherical_real",
        magnetic_order=order,
        phase_signs=signs,
        normalization="source_normalized",
        cartesian_order=CANONICAL_CARTESIAN_ORDER[l],
        convention_id=cid,
        source_program="ORCA",
        source_version=str(version),
        source_format="orca_json",
        state="source",
    )


def phase_matrix(
    l: int,
    source_phase_signs: Sequence[int],
    target_phase_signs: Optional[Sequence[int]] = None,
    *,
    source_order: Optional[Sequence[int]] = None,
    target_order: Optional[Sequence[int]] = None,
) -> np.ndarray:
    """Return the diagonal phase matrix source -> target.

    Only phase changes in the same magnetic order are supported in Phase 7B.
    A magnetic reordering requires an AO-map update and is rejected rather
    than silently permuting rows/columns.
    """
    l = int(l)
    if l not in SUPPORTED_TRANSFORM_L:
        raise AngularUnsupportedError(f"phase transform for l={l} is not supported")
    expected = 2 * l + 1
    ss = tuple(int(x) for x in source_phase_signs)
    if target_phase_signs is None:
        ts = tuple(1 for _ in range(expected))
    else:
        ts = tuple(int(x) for x in target_phase_signs)
    if len(ss) != expected or len(ts) != expected:
        raise AngularConventionError(
            f"phase_signs lengths must be {expected} for l={l}"
        )
    if any(x not in (-1, 1) for x in ss + ts):
        raise AngularConventionError("phase signs must be +1 or -1")
    so = tuple(CANONICAL_MAGNETIC_ORDER[l] if source_order is None else source_order)
    to = tuple(CANONICAL_MAGNETIC_ORDER[l] if target_order is None else target_order)
    if so != to:
        raise AngularUnsupportedError(
            "magnetic-order reordering is not implemented in Phase 7B; "
            "phase transform requires identical component order"
        )
    d = np.asarray(ss, dtype=np.float64) * np.asarray(ts, dtype=np.float64)
    return np.diag(d)


def apply_phase_to_coefficients(
    coefficients: np.ndarray,
    ao_indices: Sequence[int],
    phase: np.ndarray,
    *,
    layout: str,
) -> np.ndarray:
    """Apply a diagonal AO phase to a coefficient matrix (returns a copy)."""
    C = np.asarray(coefficients, dtype=np.float64)
    idx = np.asarray(tuple(int(i) for i in ao_indices), dtype=np.int64)
    D = np.asarray(phase, dtype=np.float64)
    if C.ndim != 2:
        raise AngularConventionError("coefficients must be 2-D")
    if D.ndim != 1 or D.size != idx.size:
        raise AngularConventionError("phase must be 1-D with len(ao_indices)")
    if np.any(np.abs(np.abs(D) - 1.0) > 0.0):
        raise AngularConventionError("phase entries must be exactly +/-1")
    if np.unique(idx).size != idx.size:
        raise AngularConventionError("ao_indices contain duplicates")
    if idx.size and (idx.min() < 0 or idx.max() >= (C.shape[0] if layout == "ao_orbital" else C.shape[1])):
        raise AngularConventionError("ao_indices out of range")
    out = np.array(C, copy=True, order="F")
    if layout == "ao_orbital":
        out[idx, :] *= D[:, None]
    elif layout == "orbital_ao":
        out[:, idx] *= D[None, :]
    else:
        raise AngularConventionError(f"unsupported coefficient layout {layout!r}")
    return out


def apply_phase_to_matrix(matrix: np.ndarray, ao_indices: Sequence[int],
                          phase: np.ndarray) -> np.ndarray:
    """Apply a diagonal AO phase to a square matrix: M' = D M D."""
    M = np.asarray(matrix, dtype=np.float64)
    idx = np.asarray(tuple(int(i) for i in ao_indices), dtype=np.int64)
    D = np.asarray(phase, dtype=np.float64)
    if M.ndim != 2 or M.shape[0] != M.shape[1]:
        raise AngularConventionError("matrix must be square")
    if D.ndim != 1 or D.size != idx.size:
        raise AngularConventionError("phase must be 1-D with len(ao_indices)")
    if np.any(np.abs(np.abs(D) - 1.0) > 0.0):
        raise AngularConventionError("phase entries must be exactly +/-1")
    if np.unique(idx).size != idx.size:
        raise AngularConventionError("ao_indices contain duplicates")
    if idx.size and (idx.min() < 0 or idx.max() >= M.shape[0]):
        raise AngularConventionError("ao_indices out of range")
    out = np.array(M, copy=True, order="F")
    block = out[np.ix_(idx, idx)]
    out[np.ix_(idx, idx)] = D[:, None] * block * D[None, :]
    return out


def apply_phase_to_operator(matrix: np.ndarray, ao_indices: Sequence[int],
                            phase: np.ndarray) -> np.ndarray:
    """Operator matrices in the AO basis use the same M' = D M D rule."""
    return apply_phase_to_matrix(matrix, ao_indices, phase)


def _array_sha(a: np.ndarray) -> str:
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def _shell_ao_indices(model: Any, shell_index: int) -> Tuple[int, ...]:
    idx = []
    for ao in model.basis.aos:
        if ao.shell_index == shell_index:
            idx.append(ao.index - 1)
        elif ao.shell_index is None:
            raise AngularConventionError(
                "AO map lacks shell_index; cannot identify angular shells"
            )
    if not idx:
        raise AngularConventionError(f"shell {shell_index} has no AOs")
    return tuple(idx)


def _state_check(model: Any, source_ids: Iterable[str]) -> None:
    source_ids = set(source_ids)
    objs = []
    if getattr(model.basis, "angular", None) is not None:
        objs.append(("basis", model.basis.angular))
    for sh in model.basis.shells:
        if getattr(sh, "angular", None) is not None:
            objs.append((f"shell {sh.index}", sh.angular))
    if model.wavefunction is not None and getattr(model.wavefunction.orbitals, "angular", None) is not None:
        objs.append(("orbitals", model.wavefunction.orbitals.angular))
    for name in ("S", "P_total", "P_alpha", "P_beta"):
        rec = getattr(model.matrices, name)
        if rec is not None and getattr(rec, "angular", None) is not None:
            objs.append((name, rec.angular))
    for name, rec in model.matrices.extra.items():
        if getattr(rec, "angular", None) is not None:
            objs.append((f"extra:{name}", rec.angular))
    for label, obj in objs:
        state = getattr(obj, "state", None)
        if state == "canonical":
            raise AngularAlreadyCanonicalError(
                f"{label} is already in canonical angular state"
            )
        if state == "unknown":
            raise AngularStateError(
                f"{label} has unknown angular state; refusing to assume it"
            )
        cid = getattr(obj, "convention_id", None)
        if state == "source" and source_ids and cid not in source_ids:
            raise AngularStateError(
                f"{label} source convention {cid!r} does not match requested "
                f"source ids {sorted(source_ids)}"
            )


def canonicalize_model_angular(
    model: Any,
    *,
    source: Any,
    shell_signs: Optional[Mapping[int, Sequence[int]]] = None,
    transform_id: Optional[str] = None,
    strict: bool = True,
) -> Any:
    """Return a canonical MDM 1.2 copy with angular metadata.

    The operation is non-mutating and is rejected on an already canonical
    model.  It supports the known s/p/d/f real-spherical order and phase
    transforms.  It does not call the native backend and does not change the
    f/g/h guard.

    ``source`` may be an :class:`AngularConvention` (for one l) or a mapping
    ``{l: AngularConvention}``.  For l>=2, an explicit source convention is
    required unless the shell already carries a source-state convention.
    l=0/1 are identity.
    """
    # Lazy import avoids a module cycle at import time.
    from .model_v1 import (
        MolecularSystemV1, BasisSet, Shell, MatrixRecord, MatrixBundle,
        OrbitalSet, Wavefunction, SCHEMA_VERSION_1_2,
    )

    if not isinstance(model, MolecularSystemV1):
        raise TypeError("canonicalize_model_angular expects MolecularSystemV1")
    if model.schema_version not in ("1.1.0", "1.2.0"):
        raise AngularConventionError(f"unsupported schema version {model.schema_version!r}")
    if model.schema_version == "1.2.0":
        raise AngularAlreadyCanonicalError("model is already schema 1.2.0")

    if isinstance(source, AngularConvention):
        source_map: Dict[int, AngularConvention] = {int(source.l): source}
    elif isinstance(source, Mapping):
        source_map = {int(k): v for k, v in source.items()}
    else:
        raise TypeError("source must be AngularConvention or mapping l->AngularConvention")
    for l, conv in source_map.items():
        if not isinstance(conv, AngularConvention):
            raise TypeError("source mappings must contain AngularConvention values")
        if conv.l != l:
            raise AngularConventionError(
                f"source mapping key l={l} != convention.l={conv.l}"
            )

    # Determine the block phase for each shell.  Only spherical real shells
    # receive a phase; Cartesian shells are canonicalized without phase.
    ao_phase = np.ones(model.nbasis, dtype=np.float64)
    shell_conventions: Dict[int, AngularConvention] = {}
    transformed_shells = []
    transform_signs: Tuple[int, ...] = ()
    source_ids = []

    for sh in model.basis.shells:
        l = int(sh.l)
        if l > SUPPORTED_TRANSFORM_L[-1]:
            raise AngularUnsupportedError(
                f"shell {sh.index}: l={l} is not supported in Phase 7B"
            )
        if sh.angular is not None and sh.angular.state == "canonical":
            raise AngularAlreadyCanonicalError(
                f"shell {sh.index} is already canonical"
            )
        if sh.angular is not None and sh.angular.state == "unknown":
            raise AngularStateError(
                f"shell {sh.index} has unknown angular state"
            )
        conv = source_map.get(l)
        if conv is None:
            if sh.angular is not None and sh.angular.state == "source":
                conv = sh.angular
            elif l >= 2:
                raise AngularStateError(
                    f"shell {sh.index}: no explicit source convention for l={l}"
                )
            else:
                conv = canonical_convention(l)  # s/p identity baseline
                conv = replace(conv, state="source", convention_id="identity-s/p-1")
        if conv.state != "source":
            raise AngularStateError(
                f"shell {sh.index}: source convention must be in source state"
            )
        if conv.representation not in ("spherical_real", "cartesian"):
            raise AngularConventionError(
                f"shell {sh.index}: unsupported angular representation"
            )
        source_ids.append(conv.convention_id)
        ao_idx = _shell_ao_indices(model, sh.index)
        expected = 2 * l + 1
        if conv.representation == "spherical_real" and len(ao_idx) != expected:
            raise AngularConventionError(
                f"shell {sh.index}: {len(ao_idx)} spherical AOs, expected {expected}"
            )
        if conv.representation == "cartesian" and len(ao_idx) != _cartesian_count(l):
            raise AngularConventionError(
                f"shell {sh.index}: Cartesian AO count mismatch for l={l}"
            )
        if conv.representation == "spherical_real" and (
            l >= 2 or any(s != 1 for s in conv.phase_signs)
        ):
            if conv.magnetic_order != CANONICAL_MAGNETIC_ORDER[l]:
                raise AngularUnsupportedError(
                    f"shell {sh.index}: magnetic-order reordering is not implemented"
                )
            if conv.normalization not in ("source_normalized", "unit_spherical"):
                raise AngularStateError(
                    f"shell {sh.index}: phase transform requires normalized source"
                )
            signs = tuple(shell_signs.get(sh.index, conv.phase_signs)) if shell_signs else conv.phase_signs
            if len(signs) != expected:
                raise AngularConventionError(
                    f"shell {sh.index}: phase_signs length mismatch"
                )
            D = phase_matrix(l, signs, source_order=conv.magnetic_order,
                             target_order=CANONICAL_MAGNETIC_ORDER[l])
            ao_phase[np.asarray(ao_idx, dtype=int)] = np.diag(D)
            canonical_shell = replace(conv, phase_signs=tuple(1 for _ in signs),
                                      normalization="unit_spherical",
                                      state="canonical",
                                      convention_id=CANONICAL_CONVENTION_ID,
                                      transform_id=transform_id)
            transformed_shells.append(sh.index)
            transform_signs = tuple(signs)
        else:
            canonical_shell = replace(
                conv, state="canonical",
                normalization=("unit_spherical"
                               if conv.representation == "spherical_real"
                               else "cartesian_normalized"),
                convention_id=(CANONICAL_CONVENTION_ID
                               if conv.representation == "spherical_real"
                               else CANONICAL_CARTESIAN_ID),
                transform_id=transform_id,
            )
        shell_conventions[sh.index] = canonical_shell

    if not transformed_shells:
        # Nothing to phase-transform; still require an explicit source for
        # d/f shells above (already enforced).  The model can be marked 1.2.
        D = np.ones((model.nbasis, model.nbasis), dtype=np.float64)
        phase_applied = np.ones(model.nbasis, dtype=np.float64)
    else:
        D = np.diag(ao_phase)
        phase_applied = ao_phase

    # Idempotency / state checks before any mutation.
    _state_check(model, source_ids)
    tid = transform_id or "qe-angular-phase-" + _array_sha(phase_applied)
    if any(getattr(r, "transform_id", None) == tid
           for r in model.provenance.angular_transforms):
        raise AngularDoubleTransformError(f"transform id {tid!r} already recorded")

    # Input hashes for provenance.
    input_hashes = {"S": "", "C": "", "P_total": ""}
    if model.matrices.S is not None:
        input_hashes["S"] = _array_sha(model.matrices.S.data)
    if model.matrices.P_total is not None:
        input_hashes["P_total"] = _array_sha(model.matrices.P_total.data)
    if model.wavefunction is not None:
        input_hashes["C"] = _array_sha(model.wavefunction.orbitals.coefficients)

    # Coefficients.
    wavefunction = model.wavefunction
    if wavefunction is not None:
        orb = wavefunction.orbitals
        idx = np.array([i for i in range(model.nbasis) if phase_applied[i] != 1.0], dtype=int)
        # Apply to all AOs via the diagonal matrix to keep the operation simple.
        C2 = apply_phase_to_coefficients(
            orb.coefficients, np.arange(model.nbasis), phase_applied, layout=orb.coefficient_layout
        )
        new_orb = replace(
            orb,
            coefficients=np.ascontiguousarray(C2),
            angular=AngularObjectMetadata(
                state="canonical", convention_id=CANONICAL_CONVENTION_ID,
                transform_id=tid,
            ),
        )
        wavefunction = replace(wavefunction, orbitals=new_orb)

    # Matrices.
    def _matrix(rec):
        if rec is None:
            return None
        if rec.representation != "ao_current_basis":
            raise AngularUnsupportedError(
                f"matrix {rec.representation!r} is not AO-current-basis; "
                "phase transform is not defined here"
            )
        data = apply_phase_to_matrix(rec.data, np.arange(model.nbasis), phase_applied)
        return replace(
            rec, data=np.ascontiguousarray(data),
            derivation=(rec.derivation + " + angular_phase"),
            sha256="",
            angular=AngularObjectMetadata(
                state="canonical", convention_id=CANONICAL_CONVENTION_ID,
                transform_id=tid,
            ),
        )

    if model.matrices.P_total_prim is not None:
        raise AngularUnsupportedError(
            "P_total_prim is primitive-Cartesian; spherical phase transform "
            "is not defined in Phase 7B"
        )
    new_S = _matrix(model.matrices.S)
    new_P = _matrix(model.matrices.P_total)
    new_Pa = _matrix(model.matrices.P_alpha)
    new_Pb = _matrix(model.matrices.P_beta)
    new_extra = {}
    for name, rec in model.matrices.extra.items():
        if rec.representation != "ao_current_basis":
            if strict:
                raise AngularUnsupportedError(
                    f"extra matrix {name!r} is not ao_current_basis"
                )
            continue
        new_extra[name] = _matrix(rec)
    matrices = MatrixBundle(
        S=new_S, P_total=new_P, P_alpha=new_Pa, P_beta=new_Pb,
        P_total_prim=None, extra=new_extra,
    )

    # Shells / basis / provenance.
    new_shells = []
    for sh in model.basis.shells:
        conv = shell_conventions.get(sh.index)
        new_shells.append(replace(sh, angular=conv) if conv is not None else sh)
    basis_repr = "spherical_real"
    if any(sh.angular and sh.angular.representation == "cartesian" for sh in new_shells):
        basis_repr = "mixed" if any(sh.angular and sh.angular.representation == "spherical_real"
                                     for sh in new_shells) else "cartesian"
    basis = replace(
        model.basis, shells=new_shells,
        angular=AngularBasisMetadata(
            representation=basis_repr,
            magnetic_order_policy="m0,+1,-1,+2,-2,...",
            phase_convention="canonical-real-spherical",
            normalization="unit_spherical",
            convention_id=CANONICAL_CONVENTION_ID,
            state="canonical",
            transform_id=tid,
        ),
    )
    rec = AngularTransformRecord(
        transform_id=tid,
        source_convention_id=",".join(sorted(set(source_ids))),
        canonical_convention_id=CANONICAL_CONVENTION_ID,
        l=3 if 3 in source_map else (max(source_map) if source_map else -1),
        shell_indices=tuple(transformed_shells),
        phase_signs=tuple(transform_signs),
        applied_to=tuple(x for x in ("C", "S", "P", "operator")
                         if (x == "C" and wavefunction is not None)
                         or (x != "C" and (new_S is not None or new_P is not None))),
        input_hashes={k: v for k, v in input_hashes.items() if v},
        output_hashes={k: v for k, v in {
            "S": _array_sha(new_S.data) if new_S is not None else "",
            "P_total": _array_sha(new_P.data) if new_P is not None else "",
            "C": _array_sha(wavefunction.orbitals.coefficients) if wavefunction is not None else "",
        }.items() if v},
    )
    prov = replace(
        model.provenance,
        angular_transforms=list(model.provenance.angular_transforms) + [rec],
        normalization_steps=list(model.provenance.normalization_steps)
        + [f"angular phase transform {tid}: l={rec.l}"],
    )
    new_model = replace(
        model, provenance=prov, basis=basis, wavefunction=wavefunction,
        matrices=matrices, schema_version=SCHEMA_VERSION_1_2,
    )
    new_model.validate(strict=False)
    return new_model


def validate_1_2_angular(model: Any) -> None:
    """Validate that a 1.2 model is fully canonical and self-consistent."""
    if model.schema_version != "1.2.0":
        return
    b = model.basis
    if b.angular is None or b.angular.state != "canonical":
        raise AngularStateError("schema 1.2 requires canonical basis.angular")
    for sh in b.shells:
        if sh.angular is None or sh.angular.state != "canonical":
            raise AngularStateError(
                f"schema 1.2 shell {sh.index} lacks canonical angular metadata"
            )
        if sh.l > 3:
            raise AngularUnsupportedError("schema 1.2 f is limited to l<=3 in Phase 7B")
        if sh.angular.l != sh.l:
            raise AngularConventionError("shell angular l mismatch")
        if sh.angular.representation == "cartesian":
            if sh.angular.cartesian_order != CANONICAL_CARTESIAN_ORDER[sh.l]:
                raise AngularConventionError("shell Cartesian order is not canonical")
        elif sh.angular.magnetic_order != CANONICAL_MAGNETIC_ORDER[sh.l]:
            raise AngularConventionError("shell angular order is not canonical")
    if model.wavefunction is not None:
        if model.wavefunction.orbitals.angular is None:
            raise AngularStateError("schema 1.2 orbitals lack angular metadata")
        if model.wavefunction.orbitals.angular.state != "canonical":
            raise AngularStateError("schema 1.2 orbitals are not canonical")
    for name in ("S", "P_total", "P_alpha", "P_beta"):
        rec = getattr(model.matrices, name)
        if rec is not None:
            if rec.angular is None or rec.angular.state != "canonical":
                raise AngularStateError(f"schema 1.2 {name} lacks canonical angular metadata")


__all__ = [
    "ANGULAR_REPRESENTATIONS",
    "ANGULAR_STATES",
    "CANONICAL_CONVENTION_ID",
    "CANONICAL_CARTESIAN_ID",
    "CANONICAL_MAGNETIC_ORDER",
    "CANONICAL_CARTESIAN_ORDER",
    "AngularError",
    "AngularConventionError",
    "AngularUnsupportedError",
    "AngularStateError",
    "AngularAlreadyCanonicalError",
    "AngularDoubleTransformError",
    "AngularConvention",
    "AngularBasisMetadata",
    "AngularObjectMetadata",
    "AngularTransformRecord",
    "canonical_convention",
    "canonical_cartesian_convention",
    "known_source_convention",
    "phase_matrix",
    "apply_phase_to_coefficients",
    "apply_phase_to_matrix",
    "apply_phase_to_operator",
    "canonicalize_model_angular",
    "validate_1_2_angular",
]
