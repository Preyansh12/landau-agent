"""Diagnostic: fully relax a named candidate phase (by seed space group) for a material, bypassing screening."""
import json, sys, os
import numpy as np
from landau_agent.tools import Session
from landau_agent import energy as E, softmodes as SM
from run_benchmark import SUPERCELLS, TAG
from ase.constraints import FixSymmetry
from ase.filters import FrechetCellFilter
from ase.optimize import BFGS, FIRE

name, targets = sys.argv[1], sys.argv[2:]
from landau_agent import energy as _E
mtag = "" if _E.MODEL == "medium" else "_" + _E.MODEL.replace("mace-", "").replace("-", "_")
s = Session(); s.fc_cache = f"results/{name}{mtag}_force_constants.npy"
s.load_parent(name); s.set_supercell(SUPERCELLS[name])
modes = s.find_instabilities()["modes"]
picked, seen = [], set()
for m in modes:
    if m["unstable"] and m["name"] not in seen:
        picked.append(m["label"]); seen.add(m["name"])
s.choose_order_parameters(picked[:3])
# rebuild candidates exactly as enumerate_phases does, but relax only the targets
s.enumerate_phases(max_phases=0, fmax=0.03, steps=1)
calc = E.get_calculator()
out = {}
for row in s._screen:
    sg = row["space_group"]
    if not any(sg.startswith(t) for t in targets):
        continue
    at = s._seed_structs.get(sg)
    if at is None:
        continue
    res = dict(seed_energy=row["seed_energy_meV_per_fu"], directions=row["order_parameter_directions"])
    for mode in ("fixed_cell", "relaxed_cell"):
        a = at.copy(); a.calc = calc; a.set_constraint(FixSymmetry(a, symprec=1e-3))
        if mode == "fixed_cell":
            FIRE(a, logfile=None).run(fmax=0.01, steps=1500)
        else:
            BFGS(FrechetCellFilter(a), logfile=None).run(fmax=0.01, steps=1500)
        a.set_constraint()
        e = (a.get_potential_energy() - s.model.E0) / s.model.n_fu * 1000
        res[mode] = dict(energy_meV_per_fu=round(float(e), 2), space_group=SM.space_group(a, 1e-3),
                         space_group_loose=SM.space_group(a, 1e-2), lattice_A=[round(float(x), 4) for x in a.cell.cellpar()[:3]])
    out[sg] = res
    print(sg, json.dumps(res), flush=True)
json.dump(out, open(f"results/diag_{TAG}_{name}_{'_'.join(t.replace('/', '') for t in targets)}.json", "w"), indent=1, default=str)
