"""Ca3Ti2O7: is the polar Γ- instability a volume artefact? Parent at the experimental pseudo-tetragonal lattice."""
import json, numpy as np
from landau_agent.tools import Session
s = Session(); s.load_parent("Ca3Ti2O7")                      # MACE-relaxed internal coordinates
a_exp, c_exp = 5.4234 / np.sqrt(2), 19.5207                     # experimental A21am cell (avg a,b) -> pseudo-tetragonal
at = s.parent.copy(); at.set_cell(np.diag([a_exp, a_exp, c_exp]), scale_atoms=True); s.parent = at
s.fc_cache = "results/Ca3Ti2O7_exp_force_constants.npy"
s.set_supercell([[1, 1, 0], [-1, 1, 0], [0, 0, 1]])
modes = s.find_instabilities()["modes"]
out = dict(lattice_A=[round(a_exp, 4), round(c_exp, 4)], modes=[{k: m[k] for k in ("name", "label", "curvature_eV_A2", "polar", "eigvec_weight_by_species")} for m in modes[:10]])
json.dump(out, open("results/Ca3Ti2O7_exp_instabilities.json", "w"), indent=1, ensure_ascii=False)
for m in out["modes"]: print(m["name"], m["label"], m["curvature_eV_A2"], "polar" if m["polar"] else "")
