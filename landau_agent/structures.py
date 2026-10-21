"""Parent structures for the validation cases (built from scratch, no database needed)."""
from __future__ import annotations

import numpy as np
from ase import Atoms


def cubic_perovskite(A: str, B: str, X: str = "O", a: float = 3.9) -> Atoms:
    """ABX3, Pm-3m, B at the origin."""
    return Atoms(
        symbols=[B, A, X, X, X],
        scaled_positions=[[0, 0, 0], [0.5, 0.5, 0.5],
                          [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5]],
        cell=np.eye(3) * a, pbc=True,
    )


def ruddlesden_popper_n2(A: str = "Ca", B: str = "Ti", X: str = "O",
                         a: float = 3.85, c: float = 19.5) -> Atoms:
    """A3B2X7, I4/mmm (n = 2 Ruddlesden-Popper), conventional tetragonal cell.

    Wyckoff positions as in Sr3Ti2O7 (Elcombe et al. type): A1 2b (0,0,1/2),
    A2 4e (0,0,z~0.318), B 4e (0,0,z~0.0975), X1 2a (0,0,0), X2 4e (0,0,z~0.195),
    X3 8g (0,1/2,z~0.0965). Body centring adds (1/2,1/2,1/2).
    """
    zB, zA2, zX2, zX3 = 0.0975, 0.3184, 0.1951, 0.0965
    half = np.array([0.5, 0.5, 0.5])
    base = []  # (symbol, frac) for one of the two body-centred halves
    base += [(B, [0, 0, zB]), (B, [0, 0, -zB])]
    base += [(A, [0, 0, 0.5])]
    base += [(A, [0, 0, zA2]), (A, [0, 0, -zA2])]
    base += [(X, [0, 0, 0]), (X, [0, 0, zX2]), (X, [0, 0, -zX2])]
    base += [(X, [0.5, 0, zX3]), (X, [0, 0.5, zX3]), (X, [0.5, 0, -zX3]), (X, [0, 0.5, -zX3])]
    syms, pos = [], []
    for s, p in base:
        for shift in (np.zeros(3), half):
            syms.append(s)
            pos.append((np.array(p, float) + shift) % 1.0)
    return Atoms(symbols=syms, scaled_positions=pos, cell=np.diag([a, a, c]), pbc=True)
