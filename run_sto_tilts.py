"""SrTiO3 at the experimental lattice: the three R-point tilt systems, fully refined."""
import json
from landau_agent.tools import Session
s = Session(); s.fc_cache = "results/SrTiO3_exp_force_constants.npy"
s.load_parent("results/SrTiO3_exp_lattice.cif", relax=False)
s.set_supercell([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
inst = s.find_instabilities()
r_label = next(m["label"] for m in inst["modes"] if m["name"].startswith("R+") and m["unstable"])
s.choose_order_parameters([r_label])
ph = s.enumerate_phases()
json.dump(ph, open("results/SrTiO3_exp_tilts_phases.json", "w"), indent=1, ensure_ascii=False)
ref = s.refine_phases(top=3)
json.dump(ref, open("results/SrTiO3_exp_tilts_refined.json", "w"), indent=1, ensure_ascii=False)
for p in ref["phases"]:
    print(p["space_group_seed"], p["order_parameter_directions"], "fixed", p["fixed_cell"]["energy_meV_per_fu"],
          "relaxed", p["relaxed_cell"]["energy_meV_per_fu"], p["relaxed_cell"]["space_group"], p["relaxed_cell"]["lattice_A"])
s.dump_log("results/SrTiO3_exp_tilts_log.json")
