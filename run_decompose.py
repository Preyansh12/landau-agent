"""Save irrep decompositions of result structures so every quoted amplitude is backed by a file."""
import json, sys
import spglib
from ase.io import read
from landau_agent.tools import Session
from run_case import SUPERCELLS

name, files = sys.argv[1], sys.argv[2:]
s = Session(); s.load_parent(name); s.set_supercell(SUPERCELLS[name])
out = {}
for f in files:
    at = read(f)
    sg = {str(tol): spglib.get_spacegroup((at.cell.array, at.get_scaled_positions(), at.numbers), symprec=tol)
          for tol in (1e-3, 1e-2)}
    r = s.analyze_child(f)
    out[f] = dict(space_group_by_tolerance_A=sg,
                  active_irreps=[x for x in r["active_irreps"] if x["amplitude_A"] > 0.001])
json.dump(out, open(f"results/{name}_decompositions.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
