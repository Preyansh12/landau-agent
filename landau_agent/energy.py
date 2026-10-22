"""Frozen-mode energies from a universal MLIP and Landau coefficient fitting."""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from . import invariants as I

warnings.filterwarnings("ignore")
_CALC = None


MODEL = __import__("os").environ.get("LANDAU_MLIP_MODEL", "medium")  # e.g. mace-matpes-r2scan-0


def get_calculator(model: str | None = None, device: str | None = None):
    """MACE foundation model in float64 (small energy wells need double precision).
    Default MACE-MP-0 medium (PBE); set LANDAU_MLIP_MODEL=mace-matpes-r2scan-0 for the r2SCAN model."""
    global _CALC
    model = model or MODEL
    if _CALC is None:
        import torch
        from mace.calculators import mace_mp
        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        _CALC = mace_mp(model=model, default_dtype="float64", device=dev)
    return _CALC


def relax_parent(parent, fmax: float = 1e-3, steps: int = 200):
    """Relax lattice (and free coordinates) of the parent while keeping its symmetry."""
    from ase.constraints import FixSymmetry
    from ase.filters import FrechetCellFilter
    from ase.optimize import BFGS
    at = parent.copy()
    at.calc = get_calculator()
    at.set_constraint(FixSymmetry(at, symprec=1e-3))
    BFGS(FrechetCellFilter(at), logfile=None).run(fmax=fmax, steps=steps)
    at.set_constraint()
    at.calc = None
    return at


@dataclass
class LandauFit:
    names: list
    invariants: list
    symbols: list
    owner: list
    coef: np.ndarray              # eV per parent formula unit, eta in Angstrom
    rmse_meV: float
    n_points: int
    n_fu: int
    eta_samples: np.ndarray
    energies: np.ndarray          # meV / f.u. relative to parent

    def F(self, eta) -> np.ndarray:
        return I.evaluate(self.invariants, eta) @ self.coef

    def terms(self, unit_scale: float = 1000.0):
        rows = []
        for inv, c in zip(self.invariants, self.coef):
            rows.append(dict(degree=inv.degree, coefficient_meV=round(float(c) * unit_scale, 4),
                             term=str(inv.expr), kind=inv.kind(self.names)))
        return rows


class FrozenModeModel:
    """E(eta) = MLIP energy of the parent supercell displaced by sum_k B_k eta_k."""

    def __init__(self, G, order_params):
        self.G = G
        self.ops = order_params
        self.B = np.hstack([o.basis for o in order_params])
        self.ref = G.supercell
        self.n_fu = int(round(abs(np.linalg.det(G.P))))
        self.calc = get_calculator()
        at = self.ref.copy()
        at.calc = self.calc
        self.E0 = at.get_potential_energy()

    def energy(self, eta: np.ndarray) -> float:
        """meV per parent formula unit relative to the undistorted parent."""
        at = self.ref.copy()
        at.positions = at.positions + (self.B @ eta).reshape(-1, 3)
        at.calc = self.calc
        return (at.get_potential_energy() - self.E0) / self.n_fu * 1000.0

    # ------------------------------------------------------------------
    def well_scan(self, k: int, step: float = 0.1, max_amp: float = 4.0):
        """1D scan along order parameter k's seed direction; returns (amp_min, E_min, curve)."""
        nvar = self.B.shape[1]
        s = sum(o.dim for o in self.ops[:k])
        d0 = self.ops[k].eta0 / (np.linalg.norm(self.ops[k].eta0) + 1e-12)
        curve, best, rising = [], (0.0, 0.0), 0
        a = step
        while a <= max_amp:
            v = np.zeros(nvar)
            v[s:s + self.ops[k].dim] = a * d0
            e = self.energy(v)
            curve.append((round(a, 3), round(e, 3)))
            if e < best[1]:
                best, rising = (a, e), 0
            else:
                rising += 1
                if rising >= 3:
                    break
            a += step
        return best[0], best[1], curve

    def sample(self, scale: np.ndarray, n_line: int = 9, n_random: int = 60, seed: int = 0):
        """Lines along each order parameter's own direction + random mixed points."""
        rng = np.random.default_rng(seed)
        dims = [o.dim for o in self.ops]
        nvar = sum(dims)
        pts = [np.zeros(nvar)]
        s = 0
        for k, o in enumerate(self.ops):
            d0 = o.eta0 / (np.linalg.norm(o.eta0) + 1e-12)
            for a in np.linspace(-1.4, 1.4, n_line):
                if abs(a) < 1e-9:
                    continue
                v = np.zeros(nvar)
                v[s:s + o.dim] = a * scale[k] * d0
                pts.append(v)
            s += o.dim
        for _ in range(n_random):
            v = np.zeros(nvar)
            s = 0
            for k, o in enumerate(self.ops):
                direction = rng.normal(size=o.dim)
                direction /= np.linalg.norm(direction)
                v[s:s + o.dim] = rng.uniform(0, 1.4) * scale[k] * direction
                s += o.dim
            pts.append(v)
        return np.array(pts)

    def fit(self, max_degree: int = 4, names=None, eta=None, scale=None, single_degree=None,
            **kw) -> LandauFit:
        names = names or [o.irrep.label for o in self.ops]
        if single_degree and single_degree > max_degree:
            invs, syms, owner = I.invariants_mixed(self.ops, single_degree, max_degree, names=names)
        else:
            invs, syms, owner = I.invariants(self.ops, max_degree=max_degree, names=names)
        # constant / linear invariants (totally symmetric OPs) are kept; constant dropped
        if scale is None:
            scale = np.array([max(np.linalg.norm(o.eta0), 0.05) for o in self.ops])
        if eta is None:
            eta = self.sample(scale, **kw)
        E = np.array([self.energy(e) for e in eta])
        X = I.evaluate(invs, eta)
        # weight the physically relevant region (near and below the parent) more strongly:
        # far-uphill configurations only need to be roughly right
        w = 1.0 / (1.0 + np.clip(E, 0, None) / 200.0)
        coef, *_ = np.linalg.lstsq(X * w[:, None], (E / 1000.0) * w, rcond=None)
        rmse = float(np.sqrt(np.mean(((X @ coef - E / 1000.0) * 1000.0)[E < 0] ** 2))) if np.any(E < 0) \
            else float(np.sqrt(np.mean((X @ coef - E / 1000.0) ** 2)) * 1000.0)
        return LandauFit(names=names, invariants=invs, symbols=syms, owner=owner, coef=coef,
                         rmse_meV=rmse, n_points=len(eta), n_fu=self.n_fu,
                         eta_samples=eta, energies=E)


def minimise(fit: LandauFit, scale: float, dims=None, n_starts: int = 40, seed: int = 0):
    """Global minimum of the fitted polynomial INSIDE the region the samples cover.

    Each order parameter is confined to the ball of radius = largest sampled norm for that
    order parameter, so the polynomial is never trusted where it was not fitted.
    """
    rng = np.random.default_rng(seed)
    nvar = fit.eta_samples.shape[1]
    dims = dims or [nvar]
    sl, s = [], 0
    for d in dims:
        sl.append(slice(s, s + d))
        s += d
    radii = np.array([np.linalg.norm(fit.eta_samples[:, z], axis=1).max() for z in sl])

    def to_eta(y):
        """Unconstrained y -> eta with |eta_k| < r_k for every order parameter (cannot escape)."""
        x = np.empty_like(y)
        for z, r in zip(sl, radii):
            n = np.linalg.norm(y[z])
            x[z] = 0.0 if n < 1e-12 else r * np.tanh(n) * y[z] / n
        return x

    best_x, best_f = None, np.inf
    for _ in range(n_starts):
        y0 = rng.normal(size=nvar) * 0.7
        res = minimize(lambda y: float(fit.F(to_eta(y))[0]) * 1000.0, y0, method="L-BFGS-B",
                       options=dict(maxiter=500))
        x = to_eta(res.x)
        f = float(fit.F(x)[0]) * 1000.0
        if np.isfinite(f) and f < best_f:
            best_x, best_f = x, f
    at_edge = bool(np.any([np.linalg.norm(best_x[z]) > 0.97 * r for z, r in zip(sl, radii)]))
    return best_x, best_f, at_edge
