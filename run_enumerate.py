"""Direct phase enumeration (independent of the Landau fit) for one material."""
import json
import sys
import time

from landau_agent.tools import Session
from run_case import SUPERCELLS


def main(name: str, max_primary: int = 2, out_dir: str = "results"):
    T = time.time()
    s = Session()
    s.fc_cache = f"{out_dir}/{name}_force_constants.npy"
    s.load_parent(name)
    s.set_supercell(SUPERCELLS[name])
    inst = s.find_instabilities()
    picked, seen = [], set()
    for m in inst["modes"]:
        if m["unstable"] and m["name"] not in seen:
            picked.append(m["label"])
            seen.add(m["name"])
    s.choose_order_parameters(picked[:max_primary])
    res = s.enumerate_phases()
    print(json.dumps(res, indent=1, ensure_ascii=False), flush=True)
    json.dump(res, open(f"{out_dir}/{name}_phases.json", "w"), indent=1, ensure_ascii=False)
    print(f"Done in {time.time() - T:.0f}s")




def refine(name: str, top: int = 3, out_dir: str = "results", source=None, relax=True,
           supercell=None, tag=None):
    T = time.time()
    tag = tag or name
    s = Session()
    s.fc_cache = f"{out_dir}/{tag}_force_constants.npy"
    s.load_parent(source or name, relax=relax)
    s.set_supercell(supercell or SUPERCELLS[name])
    inst = s.find_instabilities()
    picked, seen = [], set()
    for m in inst["modes"]:
        if m["unstable"] and m["name"] not in seen:
            picked.append(m["label"])
            seen.add(m["name"])
    s.choose_order_parameters(picked[:2])
    ph = s.enumerate_phases()
    json.dump(ph, open(f"{out_dir}/{tag}_phases.json", "w"), indent=1, ensure_ascii=False)
    res = s.refine_phases(top=top, out_dir=f"{out_dir}" if tag == name else None)
    print(json.dumps(res, indent=1, ensure_ascii=False), flush=True)
    json.dump(res, open(f"{out_dir}/{tag}_refined.json", "w"), indent=1, ensure_ascii=False)
    s.dump_log(f"{out_dir}/{tag}_enumeration_log.json")
    print(f"Done in {time.time() - T:.0f}s")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "refine-exp":
        # experimental-lattice variant: python run_enumerate.py SrTiO3 refine-exp results/SrTiO3_exp_lattice.cif
        refine(sys.argv[1], source=sys.argv[3], relax=False, tag=f"{sys.argv[1]}_exp")
    elif len(sys.argv) > 2 and sys.argv[2] == "refine":
        refine(sys.argv[1])
    else:
        main(sys.argv[1])
