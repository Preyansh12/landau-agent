"""Uniform post-pass for the v3 run (rule later built into refine_phases): if a winner's space group
differs between the 1e-3 and 1e-2 A tolerances, re-relax it from its seed to fmax = 0.001 eV/A and
record the converged space group as winner_polished. Applied to every v3 result file."""
import glob, json, sys, time
from landau_agent.tools import Session
from landau_agent import energy as E, softmodes as SM
from run_benchmark import SUPERCELLS
from ase.constraints import FixSymmetry
from ase.filters import FrechetCellFilter
from ase.optimize import BFGS

for f in sorted(glob.glob("results/benchmark_v3_matpes_r2scan_0_*.json")):
    d = json.load(open(f)); name = d["material"]; w = d["winner"]
    if "no instability" in w.get("space_group", "") or w["space_group"] == w.get("space_group_tol_0_01"):
        d["winner_polished"] = dict(needed=False); json.dump(d, open(f, "w"), indent=1, ensure_ascii=False, default=str)
        print(name, "no polish needed", flush=True); continue
    T = time.time()
    s = Session(); s.fc_cache = f"results/{name}_matpes_r2scan_0_force_constants.npy"
    s.load_parent(name); s.set_supercell(SUPERCELLS[name])
    modes = s.find_instabilities()["modes"]; picked, seen = [], set()
    for m in modes:
        if m["unstable"] and m["name"] not in seen:
            picked.append(m["label"]); seen.add(m["name"])
    s.choose_order_parameters(picked[:3]); s.enumerate_phases(max_phases=0, steps=1)
    at = s._seed_structs[w["seed"]].copy(); at.calc = E.get_calculator()
    at.set_constraint(FixSymmetry(at, symprec=1e-3))
    BFGS(FrechetCellFilter(at), logfile=None).run(fmax=0.001, steps=4000)
    at.set_constraint()
    e = (at.get_potential_energy() - s.model.E0) / s.model.n_fu * 1000
    d["winner_polished"] = dict(needed=True, fmax_eV_per_A=0.001, energy_meV_per_fu=round(float(e), 2),
                                space_group=SM.space_group(at, 1e-3), space_group_tol_0_01=SM.space_group(at, 1e-2),
                                lattice_A=[round(float(x), 4) for x in at.cell.cellpar()[:3]], runtime_s=round(time.time() - T))
    json.dump(d, open(f, "w"), indent=1, ensure_ascii=False, default=str)
    print(name, d["winner_polished"], flush=True)
