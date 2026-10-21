"""Standard (ISOTROPY/Bilbao) labels for the irreps LandauAgent computes, *verified geometrically*.

The engine labels irreps by what it computes (k-point, parity, dimension, index). Materials
scientists think in R4+, M3+, X2+, X3-, Gamma5-. Instead of trusting a hand-made lookup, we build
the textbook rigid-octahedron distortion pattern for each standard label (e.g. R4+ = out-of-phase
rotation of BO6 octahedra about one cubic axis, with the B site at the origin) directly in the
supercell, and project it onto every computed irrep. A label is attached only if one irrep
contains at least 90 % of the pattern. Polar Gamma irreps are unique in both parents, so their
labels follow from polarity and dimension alone.

Supported parents: Pm-3m perovskites with B at the origin (221) and n=2 Ruddlesden-Popper
I4/mmm with the bilayer centred at the origin (139), both as built by structures.py.
"""
from __future__ import annotations

import numpy as np
import spglib

from .symmetry import SupercellGroup


def _sg_number(G: SupercellGroup) -> int:
    at = G.parent
    return spglib.get_symmetry_dataset((at.cell.array, at.get_scaled_positions(), at.numbers),
                                       symprec=1e-3).number


def _octahedra(G: SupercellGroup):
    """B sites (cations with an anion octahedron) and, for each anion, its B neighbours."""
    sc = G.supercell
    cart, cell = sc.positions, sc.cell.array
    inv = np.linalg.inv(cell)
    anion = G.numbers == 8
    cations = np.where(~anion)[0]
    anions = np.where(anion)[0]

    def mic(d):
        f = d @ inv
        return (f - np.round(f)) @ cell

    dmin = {}
    for c in cations:
        d = np.linalg.norm(mic(cart[anions] - cart[c]), axis=1)
        dmin[c] = np.sort(d)[:6]
    shortest = min(v[0] for v in dmin.values())
    B = [c for c in cations if dmin[c][5] < 1.2 * shortest]   # six close anions = octahedron
    nbrs = {o: [] for o in anions}
    for b in B:
        for o in anions:
            r = mic(cart[o] - cart[b])
            if np.linalg.norm(r) < 1.2 * shortest:
                nbrs[o].append((b, r))
    return B, nbrs


def rotation_pattern(G: SupercellGroup, k, axis, layer_sign: bool = False) -> np.ndarray:
    """Rigid rotation of BO6 octahedra about `axis`; octahedron at R_B carries phase cos(2pi k.R_B).

    k is in parent fractional reciprocal coordinates. layer_sign=True multiplies by sign(z_B),
    which makes the two layers of an n=2 bilayer tilt in opposite senses, as corner sharing along
    c requires for a tilt about an in-plane axis.
    """
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    B, nbrs = _octahedra(G)
    u = np.zeros((len(G.numbers), 3))
    for o, lst in nbrs.items():
        for b, r in lst:
            s = np.cos(2 * np.pi * np.dot(k, G.sites_frac[b]))
            if layer_sign:
                z = G.sites_frac[b][2] - np.round(G.sites_frac[b][2] * 2) / 2  # height in its bilayer
                s *= np.sign(z) if abs(z) > 1e-6 else 0.0
            u[o] += s * np.cross(axis, r)
    for o, lst in nbrs.items():
        if lst:
            u[o] /= len(lst)
    return u.ravel()


# (standard label, k, axes to try, layer_sign, description)
PATTERNS = {
    221: [("R4+", (0.5, 0.5, 0.5), [(0, 0, 1)], False, "out-of-phase octahedral rotation (a0a0c-)"),
          ("M3+", (0.5, 0.5, 0.0), [(0, 0, 1)], False, "in-phase octahedral rotation (a0a0c+)")],
    139: [("X2+", (0.5, 0.5, 0.0), [(0, 0, 1)], False, "octahedral rotation about c"),
          # At k=(1/2,1/2,0) the tilts about [110] and [1-10] belong to two different irreps. X3- is
          # the one with the tilt axis along k: decomposing our MACE A2_1am structure (A2_1am is by
          # definition X2+ + X3- + Gamma5-, Benedek & Fennie 2011) puts its whole tilt there.
          ("X3-", (0.5, 0.5, 0.0), [(1, 1, 0)], True, "octahedral tilt about the in-plane axis along k")],
}
POLAR = {221: {3: "Γ4-"}, 139: {2: "Γ5-", 1: "Γ3- (A2u, polar along c)"}}


def standard_labels(G: SupercellGroup, types: list, describe) -> dict:
    """Map computed irrep label -> dict(standard, evidence). Unmatched irreps are left out."""
    sg = _sg_number(G)
    out = {}
    for t in types:
        info = describe(G, t)
        if info["polar"] and info["dim"] in POLAR.get(sg, {}) and t.multiplicity >= 1:
            out[t.label] = dict(standard=POLAR[sg][info["dim"]],
                                evidence="unique polar irrep of this dimension in the parent point group")
    for name, k, axes, layer, desc in PATTERNS.get(sg, []):
        best = None
        for ax in axes:
            v = rotation_pattern(G, np.array(k), ax, layer)
            nv = np.linalg.norm(v)
            if nv < 1e-9:
                continue
            for t in types:
                f = float(np.linalg.norm(t.basis.T @ v) / nv) ** 2
                if best is None or f > best[0]:
                    best = (f, t.label)
        if best and best[0] > 0.9:
            out.setdefault(best[1], dict(standard=name,
                                         evidence=f"contains {100 * best[0]:.1f}% of the rigid {desc} pattern"))
    return out
