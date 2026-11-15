"""
qe_multiwfn.normalization — explicit Gaussian normalization metadata.

The module resolves the 0.2.0 INCOMPLETE item: it computes and validates
normalization information for the canonical molecular model.

Conventions
-----------
- ``source_normalized``: the source S/C are already normalized. Verified by
  the source self-overlap (S_ii ~= 1). Used for spherical d/f from ORCA.
- ``cartesian_explicit``: standard Cartesian primitive normalization factors
  are stored per primitive; the contraction factor is stored per AO. The
  source self-overlap is verified to be 1.
- ``cartesian_source_scaled``: the source Cartesian AO has S_ii != 1 (for
  example PySCF Cartesian d). Primitive factors are stored and a per-AO
  factor 1/sqrt(S_ii) records how to normalize the source AO.
- ``cartesian_source_unnormalized``: the source coefficients behave as
  unnormalized primitives; the per-AO normalization factor is stored.
- ``unknown``: legacy 0.1.1 models or an adapter without sufficient data.

No original scientific routine is replaced. Normalization is metadata plus
validation; the density/overlap matrices supplied by the source are used
unchanged.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from .model_v1 import (
    AOFunction,
    BasisSet,
    MolecularSystemV1,
    NORMALIZATION_CONVENTIONS,
)

TOL_SELF = 1.0e-8
TOL_DIAG = 1.0e-6  # coefficient/print precision of source basis
TOL_FACTOR = 1.0e-10


def double_factorial(n: int) -> int:
    if n <= 0:
        return 1
    r = 1
    for k in range(n, 0, -2):
        r *= k
    return r


def component_powers(component: Optional[str], l: int) -> Tuple[int, int, int]:
    """Return (lx, ly, lz) for a component name such as ``s``, ``pz``, ``dxy``."""
    if l == 0:
        return (0, 0, 0)
    c = (component or "").lower().strip()
    if c and c[0] in "spdfgh":
        c = c[1:]
    if l == 1:
        return {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}.get(
            c, (0, 0, 0)
        )
    lx, ly, lz = c.count("x"), c.count("y"), c.count("z")
    if lx + ly + lz != l:
        raise ValueError(
            f"component {component!r} does not match angular momentum l={l}"
        )
    return (lx, ly, lz)


def cartesian_primitive_norm(alpha: float, powers: Tuple[int, int, int]) -> float:
    """Standard normalized Cartesian primitive Gaussian factor."""
    if alpha <= 0:
        raise ValueError("Gaussian exponent must be positive")
    lx, ly, lz = powers
    l = lx + ly + lz
    denom = math.sqrt(
        double_factorial(2 * lx - 1)
        * double_factorial(2 * ly - 1)
        * double_factorial(2 * lz - 1)
    )
    return (2.0 * alpha / math.pi) ** 0.75 * (4.0 * alpha) ** (l / 2.0) / denom


def _s1d(alpha: float, beta: float, power: int) -> float:
    """Same-center 1-D Gaussian overlap integral <x^L e^{-a x^2}|e^{-b x^2}>."""
    if power % 2:
        return 0.0
    p = alpha + beta
    return (
        double_factorial(power - 1)
        * math.sqrt(math.pi / p)
        / (2.0 * p) ** (power / 2.0)
    )


def contracted_self_overlap(
    exponents,
    coefficients,
    powers: Tuple[int, int, int],
    *,
    normalized_primitives: bool = True,
) -> float:
    """Self-overlap of a same-center contracted Cartesian shell component."""
    ex = np.asarray(exponents, dtype=np.float64)
    co = np.asarray(coefficients, dtype=np.float64)
    if ex.shape != co.shape or ex.size == 0:
        raise ValueError("invalid shell exponents/coefficients")
    lx, ly, lz = powers
    norm = np.ones_like(ex)
    if normalized_primitives:
        norm = np.array([cartesian_primitive_norm(a, powers) for a in ex])
    total = 0.0
    for i, a in enumerate(ex):
        for j, b in enumerate(ex):
            total += (
                co[i]
                * co[j]
                * norm[i]
                * norm[j]
                * _s1d(a, b, 2 * lx)
                * _s1d(a, b, 2 * ly)
                * _s1d(a, b, 2 * lz)
            )
    return float(total)


def analyze_ao_normalization(
    shell,
    ao: AOFunction,
    source_self_overlap: float,
) -> dict:
    """Analyze one AO and return the normalization metadata."""
    l = int(ao.l if ao.l is not None else ao.angular_type)
    if shell.spherical:
        if abs(source_self_overlap - 1.0) > TOL_SELF:
            return {
                "convention": "unknown",
                "primitive_norms": None,
                "contraction_normalization": None,
                "source_self_overlap": source_self_overlap,
                "detail": f"spherical source self-overlap {source_self_overlap:.6e} != 1",
            }
        return {
            "convention": "source_normalized",
            "primitive_norms": None,
            "contraction_normalization": 1.0,
            "source_self_overlap": source_self_overlap,
            "detail": "spherical source normalized (S_ii=1)",
        }

    powers = component_powers(ao.component, l)
    diag_norm = contracted_self_overlap(
        shell.exponents, shell.coefficients, powers, normalized_primitives=True
    )
    diag_un = contracted_self_overlap(
        shell.exponents, shell.coefficients, powers, normalized_primitives=False
    )
    norm = np.array(
        [cartesian_primitive_norm(a, powers) for a in np.asarray(shell.exponents)]
    )
    if abs(diag_norm - 1.0) <= TOL_DIAG:
        convention = (
            "cartesian_explicit"
            if abs(source_self_overlap - 1.0) <= TOL_SELF
            else "cartesian_source_scaled"
        )
        return {
            "convention": convention,
            "primitive_norms": norm,
            "contraction_normalization": 1.0 / math.sqrt(source_self_overlap)
            if source_self_overlap > 0 else None,
            "source_self_overlap": source_self_overlap,
            "detail": (
                f"normalized primitives; contraction self-overlap=1; "
                f"source S_ii={source_self_overlap:.6e}"
            ),
        }
    if abs(diag_un - source_self_overlap) <= TOL_DIAG:
        return {
            "convention": "cartesian_source_unnormalized",
            "primitive_norms": None,
            "contraction_normalization": 1.0 / math.sqrt(source_self_overlap)
            if source_self_overlap > 0 else None,
            "source_self_overlap": source_self_overlap,
            "detail": "source behaves as unnormalized primitives",
        }
    return {
        "convention": "unknown",
        "primitive_norms": None,
        "contraction_normalization": None,
        "source_self_overlap": source_self_overlap,
        "detail": (
            f"no recognized normalization convention: diag_norm={diag_norm:.6e}, "
            f"diag_un={diag_un:.6e}, S_ii={source_self_overlap:.6e}"
        ),
    }


def attach_normalization(model: MolecularSystemV1) -> MolecularSystemV1:
    """Compute and attach normalization metadata to a v1 model in place.

    The source S matrix is used only to validate the convention; S, P and C
    are never modified.
    """
    if model.matrices.S is None:
        raise ValueError("attach_normalization requires matrices.S")
    S = model.matrices.S.data
    if S.shape != (model.nbasis, model.nbasis):
        raise ValueError("S shape does not match nbasis")
    prim = model.basis.primitives
    if prim is not None and prim.normalization is None:
        prim.normalization = np.ones(prim.nprims, dtype=np.float64)

    conventions = set()
    for i, ao in enumerate(model.basis.aos):
        shell = None
        if ao.shell_index is not None and 0 < ao.shell_index <= len(model.basis.shells):
            shell = model.basis.shells[ao.shell_index - 1]
        if shell is None:
            ao.normalization_convention = "unknown"
            conventions.add("unknown")
            continue
        info = analyze_ao_normalization(shell, ao, float(S[i, i]))
        ao.normalization_convention = info["convention"]
        ao.contraction_normalization = info["contraction_normalization"]
        ao.source_self_overlap = info["source_self_overlap"]
        conventions.add(info["convention"])
        if prim is not None and info["primitive_norms"] is not None:
            mask = (
                (prim.shell_index == ao.shell_index)
                & (prim.type == ao.multiwfn_type)
            )
            if np.any(mask):
                prim.normalization[mask] = info["primitive_norms"]

    if len(conventions) == 1:
        model.basis.normalization_convention = next(iter(conventions))
    elif conventions:
        model.basis.normalization_convention = "mixed"
    else:
        model.basis.normalization_convention = "unknown"
    model.provenance.normalization_steps = list(
        model.provenance.normalization_steps
    ) + [f"normalization metadata: {model.basis.normalization_convention}"]
    return model


def normalization_report(model: MolecularSystemV1) -> dict:
    """PASS / FAIL / INCOMPLETE report for normalization metadata."""
    checks: Dict[str, dict] = {}
    if model.matrices.S is None:
        return {"status": "INCOMPLETE", "checks": {},
                "detail": "S missing"}
    S = model.matrices.S.data

    for i, ao in enumerate(model.basis.aos):
        name = f"ao{i+1}"
        if ao.normalization_convention is None or ao.source_self_overlap is None:
            checks[name] = {"passed": None, "detail": "normalization metadata missing"}
            continue
        err = abs(float(ao.source_self_overlap) - float(S[i, i]))
        if err > 1e-8:
            checks[name] = {
                "passed": False,
                "detail": f"source_self_overlap {ao.source_self_overlap:.6e} "
                          f"!= S_ii {S[i,i]:.6e}",
            }
            continue
        conv = ao.normalization_convention
        if conv == "source_normalized":
            ok = abs(ao.source_self_overlap - 1.0) <= 1e-8
            detail = f"S_ii={ao.source_self_overlap:.6e} (source-normalized)"
        elif conv in ("cartesian_explicit", "cartesian_source_scaled",
                      "cartesian_source_unnormalized"):
            ok = (ao.contraction_normalization is not None
                  and ao.contraction_normalization > 0)
            detail = f"{conv}; contraction={ao.contraction_normalization}"
            if conv in ("cartesian_explicit", "cartesian_source_scaled"):
                prim = model.basis.primitives
                if prim is None or prim.normalization is None:
                    ok = False
                    detail += "; primitive normalization missing"
                else:
                    mask = (
                        (prim.shell_index == ao.shell_index)
                        & (prim.type == ao.multiwfn_type)
                    )
                    if not np.any(mask) or not np.all(np.isfinite(prim.normalization[mask])):
                        ok = False
                        detail += "; primitive rows missing"
        else:
            ok = None
            detail = f"unknown convention {conv!r}"
        checks[name] = {"passed": ok, "detail": detail}

    states = [c["passed"] for c in checks.values()]
    if any(s is False for s in states):
        status = "FAIL"
    elif any(s is None for s in states):
        status = "INCOMPLETE"
    else:
        status = "PASS" if states else "INCOMPLETE"
    return {
        "status": status,
        "checks": checks,
        "basis_convention": model.basis.normalization_convention,
    }


__all__ = [
    "double_factorial",
    "component_powers",
    "cartesian_primitive_norm",
    "contracted_self_overlap",
    "analyze_ao_normalization",
    "attach_normalization",
    "normalization_report",
]
