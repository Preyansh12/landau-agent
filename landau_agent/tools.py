"""Tool layer: every physics step the agent can take, as a stateful session.

Each public method returns plain JSON-able dicts so the same tools serve
(a) the LLM agent through tool calls and (b) the scripted pipeline/CLI.
The language model chooses *what* to do; these functions do all the maths.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import numpy as np
from ase.io import read, write

from . import energy as E
from . import invariants as I
from . import softmodes as SM
from . import symmetry as S
from .structures import cubic_perovskite, ruddlesden_popper_n2

BUILTIN = {
    "SrTiO3": lambda: cubic_perovskite("Sr", "Ti", a=3.9),
    "BaTiO3": lambda: cubic_perovskite("Ba", "Ti", a=4.0),
    "PbTiO3": lambda: cubic_perovskite("Pb", "Ti", a=3.95),
    "CaTiO3": lambda: cubic_perovskite("Ca", "Ti", a=3.85),
    "Ca3Ti2O7": lambda: ruddlesden_popper_n2("Ca", "Ti", "O"),
    "LaAlO3": lambda: cubic_perovskite("La", "Al", a=3.8),
    "Sr3Zr2O7": lambda: ruddlesden_popper_n2("Sr", "Zr", "O", a=4.1, c=21.0),
    "Ca3Zr2O7": lambda: ruddlesden_popper_n2("Ca", "Zr", "O", a=4.0, c=20.4),
    "Sr3Ti2O7": lambda: ruddlesden_popper_n2("Sr", "Ti", "O", a=3.9, c=20.3),
}


@dataclass
class Session:
    parent: object = None
    G: object = None
    types: list = None
    H: np.ndarray = None
    curv: list = None
    child_u: np.ndarray = None
    ops: list = field(default_factory=list)
    op_names: list = field(default_factory=list)
    fit: object = None
    model: object = None
    prediction: dict = None
    log: list = field(default_factory=list)

    def _rec(self, tool, out):
        self.log.append(dict(tool=tool, t=time.strftime("%H:%M:%S"), result=out))
        return out

    # ------------------------------------------------------------------ setup
    def load_parent(self, source: str, relax: bool = True) -> dict:
        """Builtin name (SrTiO3, BaTiO3, PbTiO3, CaTiO3, Ca3Ti2O7, Sr3Ti2O7) or a CIF path."""
        at = BUILTIN[source]() if source in BUILTIN else read(source)
        if relax:
            at = E.relax_parent(at)
        self.parent = at
        sg = S.spglib.get_spacegroup((at.cell.array, at.get_scaled_positions(), at.numbers),
                                     symprec=1e-3)
        out = dict(formula=at.get_chemical_formula(), space_group=sg, n_atoms=len(at),
                   lattice_A=[round(x, 4) for x in at.cell.cellpar()], relaxed_with="MACE-MP-0 (medium, float64)")
        return self._rec("load_parent", out)

    def rescale_parent(self, target_a: float | None = None, factor: float | None = None) -> dict:
        """Uniformly rescale the parent lattice (e.g. to an experimental lattice constant) to test
        whether an instability is a volume artefact of the potential. Resets downstream state;
        call set_supercell again afterwards."""
        old = self.parent.cell.cellpar()[:3].copy()
        f = factor if factor else target_a / old[0]
        at = self.parent.copy()
        at.set_cell(at.cell.array * f, scale_atoms=True)
        self.parent = at
        self.G = self.types = self.H = self.curv = None
        self.ops, self.op_names, self.fit = [], [], None
        self.fc_cache = None
        return self._rec("rescale_parent", dict(old_lattice_A=[round(float(x), 4) for x in old],
                                                 new_lattice_A=[round(float(x), 4) for x in at.cell.cellpar()[:3]],
                                                 volume_change_percent=round((f ** 3 - 1) * 100, 2)))

    def set_supercell(self, matrix: list) -> dict:
        """Supercell matrix P (child_cell = P @ parent_cell). Must be invariant under the point group."""
        self.G = S.build_supercell_group(self.parent, np.array(matrix))
        self.types = S.decompose(self.G)
        self.H = self.curv = None
        self.ops, self.op_names, self.fit = [], [], None
        rows = [S.describe_irrep(self.G, t) for t in self.types]
        kpts = sorted({r["k_point"] for r in rows})
        out = dict(group_order=self.G.order, n_atoms=len(self.G.numbers), k_points=kpts,
                   irreps=[{k: r[k] for k in ("label", "name", "dim", "multiplicity", "polar")} for r in rows])
        return self._rec("set_supercell", out)

    # ------------------------------------------------------------ discovery
    def find_instabilities(self, threshold: float = -0.005) -> dict:
        """Harmonic curvature (eV/Å^2) of every irrep block; negative = unstable."""
        if self.H is None:
            cache = getattr(self, "fc_cache", None)
            import os
            if cache and os.path.exists(cache):
                self.H = np.load(cache)
            else:
                self.H = SM.force_constants(self.G)
                if cache:
                    np.save(cache, self.H)
        self.curv = SM.mode_curvatures(self.G, self.types, self.H)
        rows = []
        for r in self.curv:
            proj = r["eigvec"].reshape(-1, 3)
            from ase.data import chemical_symbols
            by = {chemical_symbols[z]: round(float(np.linalg.norm(proj[self.G.numbers == z])), 3)
                  for z in sorted(set(self.G.numbers))}
            rows.append(dict(label=r["label"], name=r["name"], curvature_eV_A2=r["curvature_eV_A2"],
                             polar=r["polar"], unstable=r["curvature_eV_A2"] < threshold,
                             eigvec_weight_by_species=by))
        return self._rec("find_instabilities", dict(modes=rows))

    def analyze_child(self, cif_path: str, origin_shift=(0, 0, 0)) -> dict:
        """Decompose an observed low-symmetry structure (on the current supercell) into irreps."""
        child = read(cif_path)
        u = S.displacement_vector(self.G, child, origin_shift)
        self.child_u = u
        ops = S.order_parameters(self.G, self.types, u)
        rows = S.summarize(self.G, ops, u)
        self._child_ops = ops
        return self._rec("analyze_child", dict(active_irreps=rows,
                                                total_distortion_A=round(float(np.linalg.norm(u)), 4)))

    # ------------------------------------------------------- order parameters
    def choose_order_parameters(self, labels: list, source: str = "instabilities",
                                amplitude: float = 0.3) -> dict:
        """Select irreps (by label) as order parameters, seeded from soft modes or the child."""
        self.ops, self.op_names = [], []
        for lab in labels:
            if source == "child":
                op = next(o for o in self._child_ops if o.irrep.label == lab)
            else:
                r = next(r for r in self.curv if r["label"] == lab)
                op = SM.op_from_vector(self.G, r["irrep_type"], r["eigvec"], amp=amplitude)
            self.ops.append(op)
            self.op_names.append(S.describe_irrep(self.G, op.irrep)["name"].split(" ")[0] + f"_{len(self.ops)}")
        self.fit = None
        return self._rec("choose_order_parameters",
                         dict(order_parameters=[dict(name=n, label=o.irrep.label, components=o.dim)
                                                for n, o in zip(self.op_names, self.ops)]))

    def forced_couplings(self, max_degree: int = 3) -> dict:
        """Stable modes that MUST appear once the chosen order parameters condense."""
        if self.curv is None:
            self.find_instabilities()
        chosen = {o.irrep.label for o in self.ops}
        cands = [r for r in self.curv if r["label"] not in chosen and not r["totally_symmetric"]]
        cops = [SM.op_from_vector(self.G, r["irrep_type"], r["eigvec"]) for r in cands]
        cn = [f"S{i}" for i in range(len(cands))]          # clean sympy names
        found = SM.forced_secondaries(self.ops, cops, self.op_names, cn, max_degree=max_degree)
        out = []
        for f in found:
            r = cands[int(f["irrep"][1:])]
            out.append(dict(label=r["label"], name=r["name"], polar=r["polar"],
                            curvature_eV_A2=r["curvature_eV_A2"],
                            coupling_terms=[t.replace(f["irrep"], "S") for t in f["coupling_terms"]]))
            f["irrep"] = r["label"]
        self._forced = found
        return self._rec("forced_couplings", dict(forced_secondary_modes=out))

    def add_secondary(self, label: str) -> dict:
        """Add a (forced) secondary mode to the order-parameter set before fitting."""
        r = next(r for r in self.curv if r["label"] == label)
        self._secondary_labels = getattr(self, "_secondary_labels", set()) | {label}
        self.ops.append(SM.op_from_vector(self.G, r["irrep_type"], r["eigvec"], amp=0.1))
        self.op_names.append(r["name"].split(" ")[0] + f"_{len(self.ops)}")
        self.fit = None
        return self._rec("add_secondary", dict(order_parameters=self.op_names))

    # --------------------------------------------------------------- Landau
    def landau_polynomial(self, max_degree: int = 4) -> dict:
        invs, syms, _ = I.invariants(self.ops, max_degree=max_degree, names=self.op_names)
        rows = [dict(degree=i.degree, term=str(i.expr), kind=i.kind(self.op_names)) for i in invs]
        single = I.landau_conditions(self.ops, self.op_names)
        return self._rec("landau_polynomial", dict(n_invariants=len(rows), invariants=rows,
                                                    landau_condition=single))

    def fit_landau(self, max_degree: int = 4, n_random: int = 80, scales=None,
                   single_degree: int = 6) -> dict:
        """Adaptive: 1D MACE well scans set the sampling range, then a least-squares fit.

        Single-mode terms go to `single_degree` (6 by default, needed for deep wells);
        couplings stay at `max_degree`.
        """
        self.model = E.FrozenModeModel(self.G, self.ops)
        wells = {}
        if scales is None:
            scales = []
            for k, (n, o) in enumerate(zip(self.op_names, self.ops)):
                a, e, curve = self.model.well_scan(k)
                wells[n] = dict(amp_at_min_A=a, E_min_meV_per_fu=e)
                scales.append(max(1.3 * a, 0.35))
            # forced (improper) secondaries can be driven far beyond their own shallow well by
            # the primaries: sample them out to a fraction of the largest primary amplitude
            unstable = {r["label"] for r in (self.curv or []) if r["curvature_eV_A2"] < -0.005}
            prim_scales = [sc for sc, o in zip(scales, self.ops) if o.irrep.label in unstable] or scales
            secondary = getattr(self, "_secondary_labels", set())
            for k, o in enumerate(self.ops):
                if o.irrep.label in secondary:
                    scales[k] = max(scales[k], 0.7 * max(prim_scales))
        self.fit = self.model.fit(max_degree, names=self.op_names, scale=np.array(scales),
                                  n_line=13, n_random=n_random, single_degree=single_degree)
        resid = self.fit.F(self.fit.eta_samples) * 1000 - self.fit.energies
        low = self.fit.energies < np.percentile(self.fit.energies, 50)
        self._fit_diag = dict(rmse_low_energy_half_meV=round(float(np.sqrt(np.mean(resid[low] ** 2))), 3),
                              energy_range_meV=[round(float(self.fit.energies.min()), 1),
                                                round(float(self.fit.energies.max()), 1)])
        return self._rec("fit_landau", dict(single_mode_wells=wells, sampling_scales_A=[round(x, 3) for x in scales],
                                            n_points=self.fit.n_points, rmse_meV_per_fu=round(self.fit.rmse_meV, 4),
                                            fit_diagnostics=self._fit_diag,
                                            units="meV per parent formula unit, order parameters in Å (whole supercell)",
                                            rmse_definition="RMSE over sampled configurations below the parent energy (weighted fit; far-uphill points down-weighted)",
                                            coefficients=self.fit.terms()))

    def predict_ground_state(self, relax_check: bool = True) -> dict:
        """Minimise the fitted Landau model, build the structure, verify with MACE."""
        x, F, at_edge = E.minimise(self.fit, scale=0.5, dims=[o.dim for o in self.ops])
        at = SM.build_structure(self.G, self.ops, x)
        sg_pred = SM.space_group(at, symprec=1e-3)
        e_direct = self.model.energy(x)
        mismatch = abs(F - e_direct)
        out = dict(order_parameter_values={}, landau_energy_meV_per_fu=round(F, 3),
                   mace_energy_at_prediction_meV_per_fu=round(e_direct, 3),
                   predicted_space_group=sg_pred,
                   reliability=dict(
                       minimum_on_sampling_boundary=at_edge,
                       landau_vs_mace_mismatch_meV_per_fu=round(mismatch, 3),
                       trustworthy=bool((not at_edge) and mismatch < max(2.0, 0.1 * abs(e_direct))),
                       note="if not trustworthy, use enumerate_phases for the phase and the "
                            "Landau polynomial only for the symmetry/coupling story"))
        s = 0
        for n, o in zip(self.op_names, self.ops):
            out["order_parameter_values"][n] = [round(float(v), 4) for v in x[s:s + o.dim]]
            s += o.dim
        if relax_check and not out["reliability"]["trustworthy"]:
            out["mace_relaxation"] = "skipped: Landau prediction flagged untrustworthy; use enumerate_phases"
            relax_check = False
        if relax_check:
            from ase.optimize import FIRE
            from ase.constraints import FixSymmetry
            at2 = at.copy()
            at2.calc = E.get_calculator()
            at2.set_constraint(FixSymmetry(at2, symprec=1e-3))
            FIRE(at2, logfile=None).run(fmax=5e-3, steps=600)
            at2.set_constraint()
            e_relax = (at2.get_potential_energy() - self.model.E0) / self.model.n_fu * 1000
            out["mace_relaxed_in_predicted_symmetry_meV_per_fu"] = round(float(e_relax), 3)
            out["relaxed_space_group"] = SM.space_group(at2, symprec=1e-3)
            out["relaxed_space_group_tol_0.01A"] = SM.space_group(at2, symprec=1e-2)
            out["polarization_nominal_charges_uC_cm2"] = self._nominal_polarization(at2)
            at2.calc = None
            self._pred_struct = at2
        self._pred_struct_unrelaxed = at
        self.prediction = out
        return self._rec("predict_ground_state", out)

    def _nominal_polarization(self, at) -> list:
        """P = sum_i q_i u_i / V with nominal oxidation states (no Born charges: an estimate)."""
        from pymatgen.core import Composition
        comp = Composition(self.parent.get_chemical_formula())
        guess = comp.oxi_state_guesses()[0]
        ref = self.G.supercell
        d = at.positions - ref.positions
        d -= d.mean(0)                                   # remove rigid shift
        q = np.array([guess[s] for s in at.get_chemical_symbols()])
        P = (q[:, None] * d).sum(0) / at.get_volume()   # e / Å^2
        return [round(float(x) * 1602.176634, 2) for x in P]

    def enumerate_phases(self, max_phases: int = 8, fmax: float = 0.03, steps: int = 250) -> dict:
        """Isotropy-subgroup style enumeration: every distinct OP-direction pattern of the
        PRIMARY order parameters, de-duplicated by space group, relaxed with MACE inside its
        own symmetry (all compatible secondary modes free to develop), ranked by energy."""
        from itertools import product
        from ase.constraints import FixSymmetry
        from ase.optimize import FIRE

        def directions(d):
            if d == 1:
                return [np.array([1.0])]
            out = [np.eye(d)[0]]
            if d >= 2:
                out += [np.eye(d)[1], (np.eye(d)[0] + np.eye(d)[1]) / np.sqrt(2),
                        (np.eye(d)[0] - np.eye(d)[1]) / np.sqrt(2)]
            if d >= 3:
                out += [np.ones(d) / np.sqrt(d)]
            return out

        if self.model is None:
            self.model = E.FrozenModeModel(self.G, self.ops)
        prim = [k for k, o in enumerate(self.ops) if self.curv is None or
                next((r for r in self.curv if r["label"] == o.irrep.label), {}).get("curvature_eV_A2", -1) < 0]
        amps = []
        for k in range(len(self.ops)):
            a, _, _ = self.model.well_scan(k) if k in prim else (0.0, 0, 0)
            amps.append(max(a, 0.2))
        options = [[None] + directions(self.ops[k].dim) if k in prim else [None] for k in range(len(self.ops))]
        seen, cands = set(), []
        for combo in product(*options):
            if all(c is None for c in combo):
                continue
            eta = np.concatenate([np.zeros(o.dim) if c is None else amps[k] * c
                                  for k, (o, c) in enumerate(zip(self.ops, combo))])
            at = SM.build_structure(self.G, self.ops, eta)
            sg = SM.space_group(at, symprec=1e-3)
            if sg in seen:
                continue
            seen.add(sg)
            desc = {self.op_names[k]: (None if c is None else [round(float(x), 3) for x in c])
                    for k, c in enumerate(combo)}
            cands.append((sg, desc, at))
        # screen: one MACE single point per distinct pattern at its seed amplitudes, then relax
        # only the most promising (scales to many order parameters / many patterns)
        calc0 = E.get_calculator()
        screened = []
        for sg, desc, at in cands:
            a0 = at.copy()
            a0.calc = calc0
            e0 = (a0.get_potential_energy() - self.model.E0) / self.model.n_fu * 1000
            screened.append((e0, sg, desc, at))
        screened.sort(key=lambda c: c[0])
        self._screen = [dict(space_group=sg, seed_energy_meV_per_fu=round(float(e), 1),
                             order_parameter_directions=d) for e, sg, d, _ in screened]
        cands = [(sg, desc, at) for _, sg, desc, at in screened]
        rows = []
        calc = E.get_calculator()
        for sg, desc, at in cands[:max_phases]:
            at = at.copy()
            at.calc = calc
            at.set_constraint(FixSymmetry(at, symprec=1e-3))
            FIRE(at, logfile=None).run(fmax=fmax, steps=steps)
            at.set_constraint()
            e = (at.get_potential_energy() - self.model.E0) / self.model.n_fu * 1000
            at.calc = None
            self._phase_structs = getattr(self, "_phase_structs", {})
            self._phase_structs[sg] = at.copy()
            rows.append(dict(space_group_seed=sg, space_group_relaxed=SM.space_group(at, 1e-3),
                             order_parameter_directions=desc, energy_meV_per_fu=round(float(e), 1),
                             polarization_nominal_uC_cm2=self._nominal_polarization(at)))
        rows.sort(key=lambda r: r["energy_meV_per_fu"])
        self._phases = rows
        return self._rec("enumerate_phases", dict(n_candidates=len(cands), n_relaxed=len(rows), screening=self._screen, phases=rows,
                                                   note="relaxed with MACE-MP-0 inside each seed symmetry; fixed parent lattice"))

    def refine_phases(self, top: int = 3, fmax: float = 0.005, steps: int = 1500,
                      relax_cell: bool = True, out_dir: str | None = None) -> dict:
        """Tight MACE relaxation of the lowest enumerated phases, fixed lattice and (optionally)
        full cell relaxation inside the same symmetry. Energies vs the relaxed parent."""
        from ase.constraints import FixSymmetry
        from ase.filters import FrechetCellFilter
        from ase.io import write as awrite
        from ase.optimize import BFGS, FIRE
        calc = E.get_calculator()
        rows = []
        for r in self._phases[:top]:
            sg = r["space_group_seed"]
            row = dict(space_group_seed=sg, order_parameter_directions=r["order_parameter_directions"])
            for mode in (["fixed_cell", "relaxed_cell"] if relax_cell else ["fixed_cell"]):
                at = self._phase_structs[sg].copy()
                at.calc = calc
                at.set_constraint(FixSymmetry(at, symprec=1e-3))
                if mode == "fixed_cell":
                    FIRE(at, logfile=None).run(fmax=fmax, steps=steps)
                else:
                    BFGS(FrechetCellFilter(at), logfile=None).run(fmax=fmax, steps=steps)
                at.set_constraint()
                e = (at.get_potential_energy() - self.model.E0) / self.model.n_fu * 1000
                row[mode] = dict(energy_meV_per_fu=round(float(e), 2),
                                 space_group=SM.space_group(at, 1e-3),
                                 space_group_loose=SM.space_group(at, 1e-2),
                                 lattice_A=[round(float(x), 4) for x in at.cell.cellpar()[:3]],
                                 polarization_nominal_uC_cm2=self._nominal_polarization(at) if mode == "fixed_cell" else None)
                if out_dir:
                    at.calc = None
                    awrite(f"{out_dir}/phase_{sg.split()[0].replace('/', '_')}_{mode}.cif", at)
            rows.append(row)
        key = "relaxed_cell" if relax_cell else "fixed_cell"
        rows.sort(key=lambda x: x[key]["energy_meV_per_fu"])
        return self._rec("refine_phases", dict(phases=rows, ranked_by=key))

    def save_prediction(self, path: str) -> dict:
        write(path, getattr(self, "_pred_struct", self._pred_struct_unrelaxed))
        return self._rec("save_prediction", dict(path=path))

    def dump_log(self, path: str):
        with open(path, "w") as fh:
            json.dump(self.log, fh, indent=1, default=str, ensure_ascii=False)
