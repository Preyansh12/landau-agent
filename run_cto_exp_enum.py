"""Ca3Ti2O7 at the contracted lattice: only X- tilt and X+ rotation as order parameters.
If the polar phase still wins with large P, the polarisation is driven by the trilinear coupling."""
import json, numpy as np
from landau_agent.tools import Session
s = Session(); s.load_parent("Ca3Ti2O7")
a_c, c_c = 5.4234 / np.sqrt(2), 19.5207
at = s.parent.copy(); at.set_cell(np.diag([a_c, a_c, c_c]), scale_atoms=True); s.parent = at
s.fc_cache = "results/Ca3Ti2O7_exp_force_constants.npy"
s.set_supercell([[1, 1, 0], [-1, 1, 0], [0, 0, 1]])
modes = s.find_instabilities()["modes"]
xm = next(m["label"] for m in modes if m["name"].startswith("X-") and m["unstable"])
xp = next(m["label"] for m in modes if m["name"].startswith("X+") and m["unstable"])
s.choose_order_parameters([xm, xp])
fc = s.forced_couplings()
ph = s.enumerate_phases(max_phases=6)
ref = s.refine_phases(top=3, relax_cell=False)
out = dict(lattice_A=[round(a_c, 4), round(c_c, 4)], order_parameters=[xm, xp],
           forced=fc["forced_secondary_modes"], enumeration=ph, refined=ref)
json.dump(out, open("results/Ca3Ti2O7_contracted_enumeration.json", "w"), indent=1, ensure_ascii=False, default=str)
for p in ref["phases"]:
    print(p["space_group_seed"], p["order_parameter_directions"], p["fixed_cell"]["energy_meV_per_fu"],
          p["fixed_cell"]["space_group"], p["fixed_cell"]["space_group_loose"], p["fixed_cell"]["polarization_nominal_uC_cm2"])
