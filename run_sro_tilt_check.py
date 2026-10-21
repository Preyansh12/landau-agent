"""Robustness check for Sr3Ru2O7: add the X3- tilt, which the frozen protocol's one-irrep-per-name rule left out."""
import json
from landau_agent.tools import Session
s = Session(); s.fc_cache = "results/Sr3Ru2O7_force_constants.npy"
s.load_parent("Sr3Ru2O7"); s.set_supercell([[1, 1, 0], [-1, 1, 0], [0, 0, 1]])
modes = {m["label"]: m for m in s.find_instabilities()["modes"]}
rot_opp, rot_same = "k=(1/2,-1/2,0)*2 d=2 #8", "k=(1/2,-1/2,0)*2 d=2 #6"
tilt = next(l for l, m in modes.items() if m.get("standard_label") == "X3-")
s.choose_order_parameters([rot_opp, rot_same, tilt])
ph = s.enumerate_phases(max_phases=6, fmax=0.03, steps=250)
ref = s.refine_phases(top=4, fmax=0.01, steps=800, relaxed_cell_only=True)
json.dump(dict(primaries=[rot_opp, rot_same, tilt], enumeration=ph, refined=ref),
          open("results/Sr3Ru2O7_with_tilt.json", "w"), indent=1, default=str, ensure_ascii=False)
for p in ref["phases"]:
    print(p["space_group_seed"], p["relaxed_cell"]["energy_meV_per_fu"], p["relaxed_cell"]["space_group_loose"], flush=True)
