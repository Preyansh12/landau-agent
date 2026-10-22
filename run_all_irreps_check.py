"""Check of the one-irrep-per-short-name rule: offer the three softest DISTINCT unstable irreps
(whatever their short names) as primaries, then enumerate/refine with the v3 settings."""
import json, sys, time
from landau_agent.tools import Session
from landau_agent import energy as E
from run_benchmark import SUPERCELLS
name = sys.argv[1]; T = time.time()
mtag = "" if E.MODEL == "medium" else "_" + E.MODEL.replace("mace-", "").replace("-", "_")
s = Session(); s.fc_cache = f"results/{name}{mtag}_force_constants.npy"
s.load_parent(name); s.set_supercell(SUPERCELLS[name])
modes = s.find_instabilities()["modes"]
picked = [m["label"] for m in modes if m["unstable"]][:3]
s.choose_order_parameters(picked)
ph = s.enumerate_phases(max_phases=6, fmax=0.03, steps=250, screen_steps=25)
ref = s.refine_phases(top=6, fmax=0.01, steps=800, relaxed_cell_only=True, tighten_if_unresolved=True)
out = dict(material=name, mlip=E.MODEL, primaries=[(m["label"], m["name"], m.get("standard_label"), m["curvature_eV_A2"]) for m in modes if m["label"] in picked],
           enumeration=ph, refined=ref, runtime_s=round(time.time() - T))
json.dump(out, open(f"results/all_irreps{mtag}_{name}.json", "w"), indent=1, default=str, ensure_ascii=False)
for p in ref["phases"]:
    print(name, p["space_group_seed"], p["relaxed_cell"]["energy_meV_per_fu"], p["relaxed_cell"]["space_group_loose"], flush=True)
print(name, "resolution", ref["resolution"], flush=True)
