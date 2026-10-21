"""Exact symmetry analysis of a structural distortion.

Given a high-symmetry parent structure and a distorted child that lives on a
supercell of it, this module:

1. builds the action of the parent space group on the child supercell
   (a finite factor group G / T_super),
2. builds the displacement representation D(g) on the 3N atomic displacements,
3. splits displacement space into physically irreducible invariant subspaces
   (numerically, by diagonalising a group-averaged random symmetric matrix),
4. groups those subspaces into isotypic types (same characters = same irrep),
5. projects the actual distortion onto each type and, for every active irrep,
   builds an order-parameter basis from the orbit of the distortion so the
   representation matrices come out as clean signed permutations.

No language model is involved anywhere in here: every number is computed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np
import spglib
from ase import Atoms

TOL_POS = 1e-3          # fractional tolerance for site matching
TOL_EIG = 1e-6          # relative tolerance for eigenvalue degeneracy


# ----------------------------------------------------------------------------
# factor group on the supercell
# ----------------------------------------------------------------------------
@dataclass
class SupercellGroup:
    parent: Atoms
    P: np.ndarray                  # supercell matrix: child_cell = P @ parent_cell
    sites_frac: np.ndarray         # (N,3) supercell sites in PARENT fractional coords
    numbers: np.ndarray            # (N,)
    rotations: list = field(default_factory=list)      # parent-frac rotations
    translations: list = field(default_factory=list)   # parent-frac translations
    perms: list = field(default_factory=list)          # site permutation per op
    D: list = field(default_factory=list)              # 3N x 3N cartesian matrices
    rot_cart: list = field(default_factory=list)

    @property
    def order(self) -> int:
        return len(self.D)

    @property
    def dim(self) -> int:
        return 3 * len(self.numbers)

    @property
    def supercell(self) -> Atoms:
        cell = self.P @ self.parent.cell.array
        cart = self.sites_frac @ self.parent.cell.array
        return Atoms(numbers=self.numbers, positions=cart, cell=cell, pbc=True)


def _wrap(frac: np.ndarray) -> np.ndarray:
    w = frac - np.floor(frac + 1e-9)
    w[np.abs(w - 1.0) < 1e-9] = 0.0
    return w


def build_supercell_group(parent: Atoms, P, symprec: float = 1e-3) -> SupercellGroup:
    """Parent space group acting on the supercell defined by P (child = P @ parent)."""
    P = np.array(P, dtype=int)
    A = parent.cell.array
    Pinv = np.linalg.inv(P)

    # lattice points of the parent inside the supercell
    det = int(round(abs(np.linalg.det(P))))
    corners = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)]) @ P
    lo, hi = corners.min(0), corners.max(0)
    tvecs = []
    for i in range(lo[0], hi[0] + 1):
        for j in range(lo[1], hi[1] + 1):
            for k in range(lo[2], hi[2] + 1):
                s = np.array([i, j, k]) @ Pinv      # in supercell fractional coords
                if np.all(s > -1e-9) and np.all(s < 1 - 1e-9):
                    tvecs.append(np.array([i, j, k], dtype=float))
    assert len(tvecs) == det, f"found {len(tvecs)} lattice points, expected {det}"

    pfrac = parent.get_scaled_positions(wrap=True)
    sites = np.array([p + t for t in tvecs for p in pfrac])
    numbers = np.array([z for _ in tvecs for z in parent.numbers])
    N = len(sites)

    def to_super(frac_parent):
        return _wrap(frac_parent @ Pinv)

    sites_super = to_super(sites)

    sym = spglib.get_symmetry((A, pfrac, parent.numbers), symprec=symprec)
    rots, trans = sym["rotations"], sym["translations"]

    G = SupercellGroup(parent=parent, P=P, sites_frac=sites, numbers=numbers)
    Ainv_T = np.linalg.inv(A).T
    seen = set()
    for R, t in zip(rots, trans):
        # the supercell lattice must be invariant under R
        img = (P @ R.T) @ Pinv          # rows: images of supercell vectors, in supercell basis
        if not np.allclose(img, np.round(img), atol=1e-8):
            raise ValueError(
                "Supercell is not invariant under the parent point group; "
                "use a larger, symmetric supercell (e.g. 2x2x2 for cubic parents)."
            )
        Rc = A.T @ R @ Ainv_T           # cartesian rotation
        for tv in tvecs:
            new = sites @ R.T + t + tv
            new_s = to_super(new)
            perm = np.empty(N, dtype=int)
            for i, x in enumerate(new_s):
                d = sites_super - x
                d -= np.round(d)
                hit = np.where(np.all(np.abs(d) < TOL_POS, axis=1))[0]
                if len(hit) != 1 or numbers[hit[0]] != numbers[i]:
                    raise RuntimeError("site mapping failed; check symprec / structure")
                perm[i] = hit[0]
            key = tuple(perm) + tuple(np.round(R.ravel()).astype(int))
            if key in seen:
                continue
            seen.add(key)
            D = np.zeros((3 * N, 3 * N))
            for i, j in enumerate(perm):
                D[3 * j:3 * j + 3, 3 * i:3 * i + 3] = Rc
            G.rotations.append(R)
            G.translations.append(t + tv)
            G.perms.append(perm)
            G.D.append(D)
            G.rot_cart.append(Rc)
    return G


# ----------------------------------------------------------------------------
# irreducible decomposition
# ----------------------------------------------------------------------------
@dataclass
class IrrepType:
    label: str                      # e.g. "k=(1/2,1/2,1/2) d=3 #1"
    k_star: list                    # list of k vectors (parent reciprocal, fractional)
    dim: int                        # dimension of one physically irreducible copy
    multiplicity: int               # number of copies in displacement space
    basis: np.ndarray               # 3N x (dim*multiplicity) orthonormal basis (isotypic)
    characters: np.ndarray          # character over group ops
    amplitude: float = 0.0          # |projection of distortion|  (Å, whole supercell)


def _frac_str(x: float) -> str:
    f = Fraction(x).limit_denominator(12)
    return str(f) if f.denominator != 1 else str(f.numerator)


def _pure_translations(G: SupercellGroup):
    """Indices and vectors of all pure translations (identity rotation) in the factor group."""
    return [(n, t) for n, (R, t) in enumerate(zip(G.rotations, G.translations))
            if np.allclose(R, np.eye(3))]


def _centering_vectors(G: SupercellGroup):
    cached = getattr(G, "_cen_cache", None)
    if cached is not None:
        return cached
    ts = [t for _, t in _pure_translations(G)]
    cen = []
    for t in ts:
        f = t - np.round(t)
        if np.linalg.norm(f) > 1e-6 and not any(np.allclose(f, c) for c in cen):
            cen.append(f)
    G._cen_cache = cen
    return cen


def _equivalent_k(G: SupercellGroup, k1, k2) -> bool:
    """k1 ~ k2 modulo the parent reciprocal lattice (integers obeying the centring condition)."""
    d = np.array(k1, float) - np.array(k2, float)
    if not np.allclose(d, np.round(d), atol=1e-6):
        return False
    return all(abs(((np.dot(d, c)) + 1e-9) % 1.0) < 1e-6 for c in _centering_vectors(G))


def _k_of_subspace(G: SupercellGroup, V: np.ndarray) -> list:
    """k vectors from eigen-phases of ALL pure translations (incl. centring) on subspace V.

    Returned in the parent's (conventional) reciprocal coordinates, reduced to a canonical
    representative in [0, 1) x [0, 1) x [0, 2) so that e.g. Z = (0,0,1) is not confused with Γ.
    """
    pts = _pure_translations(G)
    tmat = np.array([t for _, t in pts])
    Ds = [V.T @ G.D[n] @ V for n, _ in pts]
    rng = np.random.default_rng(12345)
    wts = rng.normal(size=len(Ds)) + 1j * rng.normal(size=len(Ds))
    M = sum(c * T for c, T in zip(wts, Ds))
    _, U = np.linalg.eig(M)
    ks = []
    offs = np.array(list(np.ndindex(2, 2, 2)), float)
    for col in range(U.shape[1]):
        u = U[:, col]
        nrm = u.conj() @ u
        phases = np.array([(u.conj() @ T @ u) / nrm for T in Ds])
        base = _base_k(phases, pts, G.P)[0]
        # D(t) acting on a Bloch wave exp(i k.r) gives exp(-2 pi i k.t)
        cands = base[None, :] + offs                               # (8,3)
        pred = np.exp(-2j * np.pi * cands @ tmat.T)                # (8, n_t)
        err = np.abs(pred - phases[None, :]).sum(1)
        k = cands[int(np.argmin(err))] % 2.0
        ks.append(_canonical_k(G, k))
    return sorted(set(ks))


def _base_k(phases, pts, P=None):
    """k (mod 1) from the three primitive integer translations (matched modulo the supercell)."""
    Pinv = np.linalg.inv(P) if P is not None else np.eye(3)
    vals = []
    for e in np.eye(3):
        for ph, (_, t) in zip(phases, pts):
            d = (np.asarray(t) - e) @ Pinv
            if np.allclose(d, np.round(d), atol=1e-8):
                vals.append((-np.angle(ph) / (2 * np.pi)) % 1.0)
                break
        else:
            vals.append(0.0)
    k = np.array(vals)
    k[np.abs(k - 1) < 1e-6] = 0.0
    return [k]


def _canonical_k(G: SupercellGroup, k) -> tuple:
    best = None
    for n in np.ndindex(3, 3, 3):
        g = np.array(n, float) - 1
        kk = np.array(k) + g
        if not _equivalent_k(G, kk, k):
            continue
        key = (round(float(np.dot(kk, kk)), 6), tuple(-x for x in kk))
        if best is None or key < best[0]:
            best = (key, kk)
    kk = best[1]
    kk[np.abs(kk) < 1e-6] = 0.0
    return tuple(_frac_str(x) for x in kk)


def decompose(G: SupercellGroup, seed: int = 0) -> list[IrrepType]:
    """Split displacement space into isotypic components of physically irreducible reps."""
    rng = np.random.default_rng(seed)
    n = G.dim
    H = rng.normal(size=(n, n))
    H = H + H.T
    Hs = np.zeros((n, n))
    for D in G.D:
        Hs += D @ H @ D.T
    Hs /= G.order

    w, U = np.linalg.eigh(Hs)
    scale = max(1.0, np.abs(w).max())
    # group degenerate eigenvalues -> physically irreducible subspaces
    blocks, start = [], 0
    for i in range(1, n + 1):
        if i == n or abs(w[i] - w[start]) > TOL_EIG * scale:
            blocks.append(U[:, start:i])
            start = i

    # characters of each block -> isotypic types
    types: dict = {}
    for V in blocks:
        chi = np.array([np.trace(V.T @ D @ V) for D in G.D])
        key = tuple(np.round(chi, 4))
        types.setdefault(key, []).append(V)

    out = []
    for key, Vs in types.items():
        basis = np.hstack(Vs)
        d = Vs[0].shape[1]
        ks = _k_of_subspace(G, Vs[0])
        out.append(IrrepType(label="", k_star=ks, dim=d, multiplicity=len(Vs),
                             basis=basis, characters=np.array(key)))

    # deterministic labels: by k-star, then dim, then a counter
    out.sort(key=lambda t: (len(t.k_star), str(t.k_star), t.dim, -t.characters.sum()))
    counter: dict = {}
    for t in out:
        kname = "k=(" + ",".join(t.k_star[0]) + ")"
        if len(t.k_star) > 1:
            kname += f"*{len(t.k_star)}"
        c = counter.get((kname, t.dim), 0) + 1
        counter[(kname, t.dim)] = c
        t.label = f"{kname} d={t.dim} #{c}"
    assert sum(t.basis.shape[1] for t in out) == n
    return out


# ----------------------------------------------------------------------------
# distortion analysis
# ----------------------------------------------------------------------------
def displacement_vector(G: SupercellGroup, child: Atoms, origin_shift=(0, 0, 0)) -> np.ndarray:
    """3N cartesian displacement of the child relative to the undistorted supercell.

    The child must use the same lattice vectors (P @ parent cell) up to strain;
    strain is ignored here (positions compared in fractional coordinates).
    """
    Pinv = np.linalg.inv(G.P)
    ref_s = _wrap(G.sites_frac @ Pinv)
    ch_s = _wrap(child.get_scaled_positions(wrap=True) - np.asarray(origin_shift))
    A_sup = G.supercell.cell.array
    u = np.zeros((len(ref_s), 3))
    used = set()
    for i, x in enumerate(ref_s):
        d = ch_s - x
        d -= np.round(d)
        dist = np.linalg.norm(d @ A_sup, axis=1)
        mask = child.numbers == G.numbers[i]
        dist[~mask] = np.inf
        j = int(np.argmin(dist))
        if j in used:
            raise RuntimeError("ambiguous atom mapping between child and parent supercell")
        used.add(j)
        u[i] = d[j] @ A_sup
    u -= u.mean(0)                      # remove rigid translation
    return u.ravel()


@dataclass
class OrderParameter:
    irrep: IrrepType
    basis: np.ndarray        # 3N x d, orthonormal, built from the orbit of the distortion
    gammas: np.ndarray       # (|G|, d, d) representation matrices in that basis
    eta0: np.ndarray         # coordinates of the child distortion (first axis by construction)

    @property
    def dim(self) -> int:
        return self.basis.shape[1]


def _orbit_basis(G: SupercellGroup, p: np.ndarray, tol=1e-6) -> np.ndarray:
    """Gram-Schmidt over {D(g) p}: gives clean signed-permutation matrices for most cases."""
    vecs = []
    for D in G.D:
        v = D @ p
        for b in vecs:
            v = v - (b @ v) * b
        nv = np.linalg.norm(v)
        if nv > tol * np.linalg.norm(p):
            vecs.append(v / nv)
    return np.array(vecs).T


def clean_basis(G: SupercellGroup, B: np.ndarray, tol: float = 1e-6) -> np.ndarray:
    """Rotate an OP basis so a maximal commuting set of involutions is diagonal.

    Pure translations (arms of the k-star) are taken first, then point operations whose
    representation matrix squares to the identity (2-fold axes, mirrors, inversion).
    Their joint eigenbasis is unique up to signs when the set separates all components,
    which makes the representation matrices signed permutations (e.g. x, y, z for a
    cubic polar mode, or one component per arm for zone-boundary modes).
    """
    d = B.shape[1]
    if d == 1:
        return B
    gam = [B.T @ D @ B for D in G.D]
    trans_idx = [n for n, _ in _pure_translations(G)]
    order = trans_idx + [n for n in range(len(gam)) if n not in trans_idx]
    chosen = []
    for n in order:
        g = gam[n]
        if not np.allclose(g @ g, np.eye(d), atol=1e-8):
            continue
        if np.allclose(g, np.eye(d), atol=1e-8) or np.allclose(g, -np.eye(d), atol=1e-8):
            continue
        if all(np.allclose(g @ gam[m], gam[m] @ g, atol=1e-8) for m in chosen):
            chosen.append(n)
    if not chosen:
        return B
    rng = np.random.default_rng(11)
    M = sum(rng.normal() * 0.5 * (gam[n] + gam[n].T) for n in chosen)
    w, U = np.linalg.eigh(M)
    # inside degenerate clusters keep the orbit-derived vectors (projected)
    cols, start = [], 0
    for i in range(1, d + 1):
        if i == d or abs(w[i] - w[start]) > tol:
            Pc = U[:, start:i] @ U[:, start:i].T
            got = []
            for e in np.eye(d):
                v = Pc @ e
                for g in got:
                    v = v - (g @ v) * g
                if np.linalg.norm(v) > 1e-6:
                    got.append(v / np.linalg.norm(v))
                if len(got) == i - start:
                    break
            cols += got
            start = i
    V = np.array(cols).T
    # fix signs so the largest entry of each column is positive (deterministic output)
    for j in range(V.shape[1]):
        if V[np.argmax(np.abs(V[:, j])), j] < 0:
            V[:, j] *= -1
    return B @ V


def arm_adapted_basis(G: SupercellGroup, B: np.ndarray) -> np.ndarray:
    """Kept for compatibility: the full commuting-involution cleanup subsumes arm adaptation."""
    return clean_basis(G, B)


def _arm_adapted_basis_old(G: SupercellGroup, B: np.ndarray) -> np.ndarray:
    """Rotate an OP basis so each component lives on a single arm of the k-star.

    Pure translations act on commensurate zone-boundary modes with eigenvalues +-1, so they
    are real symmetric on the OP subspace and can be diagonalised together. Inside a block
    where all translations act the same (one arm, several components), the orbit-derived
    vectors are kept (projected), which preserves the clean signed-permutation form.
    """
    pts = _pure_translations(G)
    if B.shape[1] == 1 or not pts:
        return B
    Ts = [B.T @ G.D[n] @ B for n, _ in pts]
    if all(np.allclose(T, T[0, 0] * np.eye(len(T)), atol=1e-8) for T in Ts):
        return B                                # single arm: nothing to do
    rng = np.random.default_rng(7)
    M = sum(rng.normal() * 0.5 * (T + T.T) for T in Ts)
    w, U = np.linalg.eigh(M)
    cols, start = [], 0
    for i in range(1, len(w) + 1):
        if i == len(w) or abs(w[i] - w[start]) > 1e-6:
            Pc = U[:, start:i] @ U[:, start:i].T      # projector on this arm (orbit coords)
            got = []
            for e in np.eye(len(w)):
                v = Pc @ e
                for g in got:
                    v = v - (g @ v) * g
                if np.linalg.norm(v) > 1e-6:
                    got.append(v / np.linalg.norm(v))
                if len(got) == i - start:
                    break
            cols += got
            start = i
    V = np.array(cols).T
    return B @ V


def order_parameters(G: SupercellGroup, types: list[IrrepType], u: np.ndarray,
                     threshold: float = 1e-3) -> list[OrderParameter]:
    """Active irreps of a distortion u, each with an orbit-adapted order-parameter basis."""
    ops = []
    for t in types:
        proj = t.basis @ (t.basis.T @ u)
        t.amplitude = float(np.linalg.norm(proj))
        if t.amplitude < threshold:
            continue
        if np.allclose(t.characters, t.characters[0]) and t.dim == 1:
            # totally symmetric: secondary, never an order parameter on its own
            pass
        B = arm_adapted_basis(G, _orbit_basis(G, proj))
        gam = np.array([B.T @ D @ B for D in G.D])
        gam[np.abs(gam) < 1e-9] = 0.0
        ops.append(OrderParameter(irrep=t, basis=B, gammas=gam, eta0=B.T @ u))
    ops.sort(key=lambda o: -o.irrep.amplitude)
    return ops


# ----------------------------------------------------------------------------
# human-readable descriptors (computed, never guessed)
# ----------------------------------------------------------------------------
_KNAMES = {
    # simple cubic / primitive tetragonal-like reduced coordinates
    "P": {("0", "0", "0"): "Γ", ("1/2", "1/2", "1/2"): "R", ("0", "1/2", "1/2"): "M",
          ("1/2", "0", "1/2"): "M", ("1/2", "1/2", "0"): "M", ("0", "0", "1/2"): "X",
          ("0", "1/2", "0"): "X", ("1/2", "0", "0"): "X"},
    # body-centred tetragonal, CONVENTIONAL reduced coordinates
    "I": {("0", "0", "0"): "Γ", ("1/2", "1/2", "0"): "X", ("1/2", "1/2", "1"): "X",
          ("0", "0", "1"): "Z", ("1/2", "0", "1/2"): "N", ("0", "1/2", "1/2"): "N",
          ("1/2", "1/2", "1/2"): "P"},
}


def kpoint_name(G: SupercellGroup, k: tuple) -> str:
    ds = spglib.get_symmetry_dataset((G.parent.cell.array, G.parent.get_scaled_positions(),
                                      G.parent.numbers), symprec=1e-3)
    centring = ds.international[0]
    kf = np.array([float(Fraction(x)) for x in k])
    for name_k, name in _KNAMES.get(centring, {}).items():
        if _equivalent_k(G, kf, np.array([float(Fraction(x)) for x in name_k])):
            return name
    return "k=(" + ",".join(k) + ")"


def describe_irrep(G: SupercellGroup, t: IrrepType, u: np.ndarray | None = None) -> dict:
    """Parity, polarity, k-point name and which sublattices carry the distortion."""
    chi = t.characters
    d = t.dim
    # inversion through the parent origin only (parity is origin-dependent away from Gamma)
    inv_idx = [n for n, (R, tr) in enumerate(zip(G.rotations, G.translations))
               if np.allclose(R, -np.eye(3)) and np.allclose(tr, 0, atol=1e-8)]
    parity = "?"
    if inv_idx:
        vals = {round(chi[n] / d, 3) for n in inv_idx}
        if vals <= {1.0}:
            parity = "+"
        elif vals <= {-1.0}:
            parity = "-"
    # polar <=> irrep occurs in the vector representation (only possible at Gamma)
    chi_vec = np.array([np.trace(Rc) for Rc in G.rot_cart])
    polar = bool(t.k_star == [("0", "0", "0")] and abs(np.dot(chi, chi_vec) / G.order) > 1e-6)
    out = dict(label=t.label, k_point=kpoint_name(G, t.k_star[0]), parity=parity,
               dim=d, multiplicity=t.multiplicity, polar=polar,
               totally_symmetric=bool(np.allclose(chi, 1.0) and d == 1))
    out["name"] = f"{out['k_point']}{'' if parity == '?' else parity} (d={d})"
    if u is not None:
        proj = (t.basis @ (t.basis.T @ u)).reshape(-1, 3)
        from ase.data import chemical_symbols
        by = {}
        for z in sorted(set(G.numbers)):
            m = G.numbers == z
            by[chemical_symbols[z]] = round(float(np.linalg.norm(proj[m])), 4)
        out["amplitude_by_species_A"] = by
        out["amplitude_A"] = round(float(np.linalg.norm(proj)), 4)
    return out


def summarize(G: SupercellGroup, ops: list[OrderParameter], u: np.ndarray) -> list[dict]:
    rows = []
    for o in ops:
        row = describe_irrep(G, o.irrep, u)
        row["op_dim"] = o.dim
        row["direction"] = [round(float(x), 4) for x in o.eta0]
        rows.append(row)
    return rows
