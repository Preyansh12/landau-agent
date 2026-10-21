"""Fixed-protocol benchmark: same steps, same settings for every material, no per-material tuning.

Protocol: MACE-relax the parent -> instabilities -> up to 3 most unstable distinct irreps as
primaries -> screen all symmetry-distinct patterns with one MACE energy each -> relax the best 6
in their own symmetry (fixed lattice) -> tighten the best 2 with full cell relaxation -> winner.
"""
import json, sys, time
from landau_agent.tools import Session
from run_case import SUPERCELLS

SUPERCELLS.update({"SrTiO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]], "LaAlO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
                   "Sr3Zr2O7": [[1, 1, 0], [-1, 1, 0], [0, 0, 1]],
                   "Ca3Zr2O7": [[1, 1, 0], [-1, 1, 0], [0, 0, 1]]})
for _n in ("Sr3Ti2O7", "Ca3Mn2O7", "Ca3Sn2O7", "Sr3Sn2O7", "Sr3Hf2O7", "Sr3Ru2O7"):
    SUPERCELLS[_n] = [[1, 1, 0], [-1, 1, 0], [0, 0, 1]]

def run(name):
    T = time.time()
    s = Session(); s.fc_cache = f"results/{name}_force_constants.npy"
    parent = s.load_parent(name)
    s.set_supercell(SUPERCELLS[name])
    modes = s.find_instabilities()["modes"]
    picked, seen = [], set()
    for m in modes:
        if m["unstable"] and m["name"] not in seen:
            picked.append(m["label"]); seen.add(m["name"])
    picked = picked[:3]
    if not picked:
        out = dict(material=name, parent=parent, instabilities=[], protocol="v2",
                   winner=dict(space_group="parent (no instability)"), runtime_s=round(time.time() - T))
        json.dump(out, open(f"results/benchmark_v2_{name}.json", "w"), indent=1, ensure_ascii=False, default=str)
        print(name, "->", out["winner"], flush=True)
        return
    s.choose_order_parameters(picked)
    ph = s.enumerate_phases(max_phases=6, fmax=0.03, steps=250)
    # v2: strain can reorder phases, so the best 4 (not 2) get a full cell relaxation
    ref = s.refine_phases(top=4, fmax=0.01, steps=800, relaxed_cell_only=True)
    best = ref["phases"][0]
    out = dict(material=name, parent=parent, instabilities=[{k: m[k] for k in ("name", "label", "curvature_eV_A2", "polar")} for m in modes if m["unstable"]],
               primaries=picked, enumeration=ph, refined=ref,
               protocol="v2", winner=dict(space_group=best["relaxed_cell"]["space_group"], space_group_tol_0_01=best["relaxed_cell"]["space_group_loose"],
                           energy_meV_per_fu=best["relaxed_cell"]["energy_meV_per_fu"], seed=best["space_group_seed"]),
               runtime_s=round(time.time() - T))
    json.dump(out, open(f"results/benchmark_v2_{name}.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(name, "->", out["winner"], f"{out['runtime_s']}s", flush=True)

if __name__ == "__main__":
    for n in sys.argv[1:]:
        try:
            run(n)
        except Exception as e:
            print(n, "FAILED", type(e).__name__, e, flush=True)
