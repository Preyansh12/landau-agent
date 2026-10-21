"""Parent-only analysis: harmonic instabilities, forced secondary modes, predicted phase."""
from __future__ import annotations

import numpy as np
import spglib

from . import invariants as I
from .energy import get_calculator
from .symmetry import (OrderParameter, SupercellGroup, _orbit_basis, arm_adapted_basis,
                       describe_irrep)


def force_constants(G: SupercellGroup, step: float = 0.01) -> np.ndarray:
    """Central-difference force constants of the parent supercell (eV/Å^2), symmetrised."""
    at = G.supercell
    calc = get_calculator()
    n = 3 * len(at)
    H = np.zeros((n, n))
    pos0 = at.positions.copy()
    for i in range(n):
        f = []
        for s in (+1, -1):
            at.positions = pos0.copy()
            at.positions[i // 3, i % 3] += s * step
            at.calc = calc
            f.append(at.get_forces().ravel())
        H[:, i] = -(f[0] - f[1]) / (2 * step)
    at.positions = pos0
    H = 0.5 * (H + H.T)
    # enforce the parent symmetry exactly (removes finite-difference noise)
    Hs = sum(D @ H @ D.T for D in G.D) / G.order
    return Hs


def mode_curvatures(G: SupercellGroup, types, H: np.ndarray):
    """Lowest curvature (eV/Å^2) and its eigenvector in every isotypic block."""
    out = []
    for t in types:
        Hb = t.basis.T @ H @ t.basis
        w, v = np.linalg.eigh(Hb)
        vec = t.basis @ v[:, 0]
        info = describe_irrep(G, t)
        info.update(curvature_eV_A2=round(float(w[0]), 4), eigvec=vec, irrep_type=t)
        out.append(info)
    out.sort(key=lambda r: r["curvature_eV_A2"])
    return out


def op_from_vector(G: SupercellGroup, t, vec: np.ndarray, amp: float = 0.1) -> OrderParameter:
    """Order parameter for one copy of irrep t, seeded by a mode shape."""
    p = vec / np.linalg.norm(vec)
    B = arm_adapted_basis(G, _orbit_basis(G, p))
    # seed direction: the single basis component carrying most of the soft mode
    c = B.T @ p
    i = int(np.argmax(np.abs(c)))
    eta0 = np.zeros(B.shape[1])
    eta0[i] = amp * np.sign(c[i])
    gam = np.array([B.T @ D @ B for D in G.D])
    gam[np.abs(gam) < 1e-9] = 0.0
    return OrderParameter(irrep=t, basis=B, gammas=gam, eta0=eta0)


def forced_secondaries(primaries: list[OrderParameter], candidates: list[OrderParameter],
                       names_p: list[str], names_c: list[str], max_degree: int = 3):
    """Secondary modes that appear LINEARLY in an invariant with the primaries.

    Such a term  c * Q_sec * f(Q_primary)  means the secondary mode is necessarily
    induced once the primaries condense (improper / triggered order).
    """
    found = []
    for cand, cname in zip(candidates, names_c):
        ops = primaries + [cand]
        invs, syms, owner = I.invariants(ops, max_degree=max_degree, names=names_p + [cname])
        k_c = len(primaries)
        hits = []
        for inv in invs:
            if k_c not in inv.irreps_involved or len(inv.irreps_involved) < 2:
                continue
            # linear in the candidate
            idx = inv.irreps_involved.index(k_c)
            deg_c = [sum(e[i] for i in range(len(e)) if owner[i] == k_c) for e in inv.terms]
            if all(d == 1 for d in deg_c):
                hits.append(str(inv.expr))
        if hits:
            found.append(dict(irrep=cname, coupling_terms=hits, op=cand))
    return found


def build_structure(G: SupercellGroup, ops: list[OrderParameter], eta: np.ndarray):
    at = G.supercell
    B = np.hstack([o.basis for o in ops])
    at.positions = at.positions + (B @ eta).reshape(-1, 3)
    return at


def space_group(at, symprec: float = 1e-3) -> str:
    return spglib.get_spacegroup((at.cell.array, at.get_scaled_positions(), at.numbers),
                                 symprec=symprec)
