"""Symmetry-allowed Landau free-energy polynomials, computed exactly.

Invariants are obtained with the Reynolds operator: every monomial in the
order-parameter coordinates is averaged over the group,

    R m(eta) = 1/|G| sum_g m(Gamma(g) eta),

and an independent basis of the resulting invariant polynomials is extracted
by exact rational row reduction. Coefficients are rationalised, so the output
is a readable polynomial (e.g.  a^2 + b^2 + c^2,  a*b*c, ...).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement
from math import prod

import numpy as np
import sympy as sp


@dataclass
class Invariant:
    degree: int
    terms: dict                     # exponent tuple -> sympy Rational
    irreps_involved: tuple          # indices of order parameters that appear
    orders: tuple                   # polynomial degree in each involved OP
    expr: sp.Expr = None

    def kind(self, names) -> str:
        parts = [f"{names[i]}^{o}" if o > 1 else names[i]
                 for i, o in zip(self.irreps_involved, self.orders)]
        n = len(self.irreps_involved)
        tag = {1: "single", 2: "bilinear-type coupling" if sum(self.orders) == 2 else "coupling",
               3: "trilinear coupling" if sum(self.orders) == 3 else "three-irrep coupling"}.get(n, f"{n}-irrep coupling")
        return f"{' * '.join(parts)}  [{tag}]"


def _monomials(nvar: int, deg: int):
    for combo in combinations_with_replacement(range(nvar), deg):
        e = [0] * nvar
        for i in combo:
            e[i] += 1
        yield tuple(e)


def _poly_mul(a: dict, b: dict) -> dict:
    out: dict = {}
    for ea, ca in a.items():
        for eb, cb in b.items():
            e = tuple(x + y for x, y in zip(ea, eb))
            out[e] = out.get(e, 0.0) + ca * cb
    return out


def _substitute(mono: tuple, gamma: np.ndarray) -> dict:
    """m(Gamma eta) expanded as a polynomial in eta."""
    nvar = len(mono)
    poly = {tuple([0] * nvar): 1.0}
    for i, p in enumerate(mono):
        if p == 0:
            continue
        lin = {}
        for j in range(nvar):
            c = gamma[i, j]
            if abs(c) > 1e-12:
                e = [0] * nvar
                e[j] = 1
                lin[tuple(e)] = c
        for _ in range(p):
            poly = _poly_mul(poly, lin)
    return poly


def block_gammas(order_params) -> np.ndarray:
    """Block-diagonal representation matrices for several order parameters."""
    n_ops = order_params[0].gammas.shape[0]
    dims = [o.dim for o in order_params]
    n = sum(dims)
    out = np.zeros((n_ops, n, n))
    s = 0
    for o in order_params:
        out[:, s:s + o.dim, s:s + o.dim] = o.gammas
        s += o.dim
    return out


def _rational(x: float, maxden: int = 1000) -> sp.Rational:
    return sp.Rational(x).limit_denominator(maxden)


def invariants_mixed(order_params, single_degree: int = 6, coupling_degree: int = 4, names=None):
    """Single-OP invariants up to single_degree; couplings only up to coupling_degree.

    The usual practical Landau expansion: each mode's own well needs 6th order when the
    distortion is large, while cross terms are kept at 3rd/4th order.
    """
    invs, syms, owner = invariants(order_params, max_degree=coupling_degree, names=names)
    if single_degree > coupling_degree:
        names = names or [f"Q{k}" for k in range(len(order_params))]
        dims = [o.dim for o in order_params]
        for k, o in enumerate(order_params):
            sub, _, _ = invariants([o], max_degree=single_degree, names=[names[k]])
            off = sum(dims[:k])
            nvar = sum(dims)
            for inv in sub:
                if inv.degree <= coupling_degree:
                    continue
                terms = {}
                for e, v in inv.terms.items():
                    full = [0] * nvar
                    full[off:off + o.dim] = e
                    terms[tuple(full)] = v
                expr = sum(v * prod(s ** p for s, p in zip(syms, e)) for e, v in terms.items())
                invs.append(Invariant(degree=inv.degree, terms=terms, irreps_involved=(k,),
                                      orders=(inv.degree,), expr=sp.expand(expr)))
    return invs, syms, owner


def invariants(order_params, max_degree: int = 4, names=None, sizes_only=False):
    """All independent invariant polynomials up to max_degree.

    Returns (invariants, symbols, owner) where owner[i] = index of the order
    parameter that variable i belongs to.
    """
    gam = block_gammas(order_params)
    dims = [o.dim for o in order_params]
    nvar = sum(dims)
    owner = [k for k, d in enumerate(dims) for _ in range(d)]
    if names is None:
        names = [f"Q{k}" for k in range(len(order_params))]
    symbols = []
    for k, d in enumerate(dims):
        base = names[k].replace("+", "p").replace("-", "m").replace(" ", "")
        symbols += sp.symbols(f"{base}_1:{d + 1}") if d > 1 else [sp.Symbol(f"{base}")]

    # drop duplicate group elements on the OP space (speeds things up a lot)
    uniq = {}
    for g in gam:
        uniq.setdefault(tuple(np.round(g, 8).ravel()), g)
    gam = np.array(list(uniq.values()))

    found: list[Invariant] = []
    for deg in range(1, max_degree + 1):
        monos = list(_monomials(nvar, deg))
        index = {m: i for i, m in enumerate(monos)}
        M = np.zeros((len(monos), len(monos)))
        for c, m in enumerate(monos):
            acc = np.zeros(len(monos))
            for g in gam:
                for e, v in _substitute(m, g).items():
                    acc[index[e]] += v
            M[:, c] = acc / len(gam)
        rank = np.linalg.matrix_rank(M, tol=1e-8)
        if rank == 0:
            continue
        # exact rational basis of the column space via rref of M^T
        Mq = sp.Matrix([[_rational(x) for x in row] for row in M.T])
        R, piv = Mq.rref()
        for r in range(len(piv)):
            row = R.row(r)
            terms = {monos[i]: row[i] for i in range(len(monos)) if row[i] != 0}
            # clear denominators for readability
            den = 1
            for v in terms.values():
                den = sp.ilcm(den, sp.fraction(v)[1])
            terms = {e: v * den for e, v in terms.items()}
            involved = sorted({owner[i] for e in terms for i, p in enumerate(e) if p})
            orders = tuple(sum(e[i] for i in range(nvar) if owner[i] == k)
                           for k in involved for e in [next(iter(terms))])
            expr = sum(v * prod(s ** p for s, p in zip(symbols, e)) for e, v in terms.items())
            found.append(Invariant(degree=deg, terms=terms, irreps_involved=tuple(involved),
                                   orders=orders, expr=sp.expand(expr)))
    return found, symbols, owner


def evaluate(invs, eta: np.ndarray) -> np.ndarray:
    """Design matrix: rows = samples (eta: n_samples x nvar), cols = invariants."""
    eta = np.atleast_2d(eta)
    X = np.zeros((eta.shape[0], len(invs)))
    for j, inv in enumerate(invs):
        col = np.zeros(eta.shape[0])
        for e, v in inv.terms.items():
            col += float(v) * np.prod(eta ** np.array(e), axis=1)
        X[:, j] = col
    return X


def landau_conditions(order_params, names, max_degree=4):
    """Quick symmetry verdicts for each single order parameter."""
    out = []
    for k, op in enumerate(order_params):
        invs, _, _ = invariants([op], max_degree=3, names=[names[k]])
        has_lin = any(i.degree == 1 for i in invs)
        has_cubic = any(i.degree == 3 for i in invs)
        out.append(dict(
            irrep=names[k],
            totally_symmetric=has_lin,
            third_order_invariant=has_cubic,
            landau_condition=("violated: a cubic invariant exists, so a continuous transition is "
                              "forbidden (first order)" if has_cubic else
                              "satisfied: no cubic invariant"),
        ))
    return out
