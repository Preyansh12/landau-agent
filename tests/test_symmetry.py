"""Checks the symmetry core against textbook perovskite results."""
import numpy as np

from landau_agent import symmetry as S
from landau_agent import invariants as I
from landau_agent.structures import cubic_perovskite


def tilt_a0a0cm(G, delta=0.1):
    """a0a0c- octahedral rotation built by hand (pure R-point tilt)."""
    u = np.zeros((len(G.numbers), 3))
    a = G.parent.cell.array[0, 0]
    for i, (x, z) in enumerate(zip(G.sites_frac, G.numbers)):
        if z != 8:
            continue
        cell = np.floor(x + 1e-9).astype(int)
        f = x - cell
        s = (-1) ** int(cell.sum())
        if np.isclose(f[0], 0.5):          # O between Ti along x -> moves along y
            u[i, 1] = s * delta
        elif np.isclose(f[1], 0.5):        # O between Ti along y -> moves along -x
            u[i, 0] = -s * delta
    return u.ravel()


def child_from(G, u):
    sc = G.supercell
    sc.positions = sc.positions + u.reshape(-1, 3)
    return sc


def test_counts():
    G = S.build_supercell_group(cubic_perovskite("Sr", "Ti", a=3.9), np.eye(3) * 2)
    types = S.decompose(G)
    dims = {}
    for t in types:
        k = t.k_star[0]
        dims[(k, len(t.k_star))] = dims.get((k, len(t.k_star)), 0) + t.basis.shape[1]
    # 5 atoms x 3 = 15 per k point; stars of M and X have 3 arms
    assert dims[(("0", "0", "0"), 1)] == 15
    assert dims[(("1/2", "1/2", "1/2"), 1)] == 15
    assert sum(v for (k, n), v in dims.items() if n == 3) == 90


def test_tilt_is_single_R_irrep():
    G = S.build_supercell_group(cubic_perovskite("Sr", "Ti", a=3.9), np.eye(3) * 2)
    types = S.decompose(G)
    u = tilt_a0a0cm(G)
    child = child_from(G, u)
    u2 = S.displacement_vector(G, child)
    assert np.allclose(u, u2, atol=1e-8)
    ops = S.order_parameters(G, types, u2)
    assert len(ops) == 1
    op = ops[0]
    assert op.irrep.k_star == [("1/2", "1/2", "1/2")]
    assert op.dim == 3
    invs, syms, _ = I.invariants([op], max_degree=4, names=["R"])
    degs = sorted(i.degree for i in invs)
    # textbook R4+: one quadratic (a^2+b^2+c^2), no cubic, two quartics
    assert degs == [2, 4, 4], degs


def test_standard_labels_verified_by_patterns():
    import numpy as np
    from landau_agent.structures import cubic_perovskite, ruddlesden_popper_n2
    from landau_agent import symmetry as S, labels as L
    G = S.build_supercell_group(cubic_perovskite("Sr", "Ti", a=3.9), np.diag([2, 2, 2]))
    types = S.decompose(G)
    got = {v["standard"]: S.describe_irrep(G, next(t for t in types if t.label == k))["name"]
           for k, v in L.standard_labels(G, types, S.describe_irrep).items()}
    assert got == {"Γ4-": "Γ- (d=3)", "R4+": "R+ (d=3)", "M3+": "M+ (d=3)"}
    G = S.build_supercell_group(ruddlesden_popper_n2("Ca", "Ti", "O"), np.array([[1, 1, 0], [-1, 1, 0], [0, 0, 1]]))
    types = S.decompose(G)
    got = {v["standard"].split()[0]: S.describe_irrep(G, next(t for t in types if t.label == k))["name"]
           for k, v in L.standard_labels(G, types, S.describe_irrep).items()}
    assert got == {"Γ5-": "Γ- (d=2)", "Γ3-": "Γ- (d=1)", "X2+": "X+ (d=2)", "X3-": "X- (d=2)"}
