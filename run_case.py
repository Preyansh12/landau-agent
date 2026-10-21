"""Scripted (LLM-free) end-to-end run of the LandauAgent tools on one material.

    python run_case.py SrTiO3      # 2x2x2, expect R-point tilt -> I4/mcm
    python run_case.py Ca3Ti2O7    # sqrt2 x sqrt2 x 1, expect X tilts + trilinear polar mode
"""
import json
import sys
import time

from landau_agent.tools import Session

SUPERCELLS = {
    "SrTiO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
    "BaTiO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
    "PbTiO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
    "CaTiO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
    "Ca3Ti2O7": [[1, 1, 0], [-1, 1, 0], [0, 0, 1]],
    "Sr3Ti2O7": [[1, 1, 0], [-1, 1, 0], [0, 0, 1]],
}


def main(name: str, max_primary: int = 2, out_dir: str = "results"):
    import os
    os.makedirs(out_dir, exist_ok=True)
    T = time.time()
    s = Session()
    s.fc_cache = f"{out_dir}/{name}_force_constants.npy"

    def show(step, res):
        print(f"\n=== {step}  [{time.time() - T:.0f}s]", flush=True)
        print(json.dumps(res, indent=1, ensure_ascii=False, default=str)[:3000], flush=True)

    show("load_parent", s.load_parent(name))
    sc = s.set_supercell(SUPERCELLS[name])
    show("set_supercell", {k: v for k, v in sc.items() if k != "irreps"})
    inst = s.find_instabilities()
    unstable = [m for m in inst["modes"] if m["unstable"]]
    show("instabilities", unstable)
    # one representative per k-point name/parity (avoid duplicate copies), softest first
    picked, seen = [], set()
    for m in unstable:
        if m["name"] not in seen:
            picked.append(m["label"])
            seen.add(m["name"])
    picked = picked[:max_primary]
    show("choose_order_parameters", s.choose_order_parameters(picked))
    forced = s.forced_couplings()
    show("forced_couplings", forced)
    for f in forced["forced_secondary_modes"]:
        if f["polar"]:
            s.add_secondary(f["label"])
    show("landau_polynomial", s.landau_polynomial(4))
    show("fit_landau", s.fit_landau(4, n_random=160))
    show("predict_ground_state", s.predict_ground_state())
    s.save_prediction(f"{out_dir}/{name}_predicted.cif")
    s.dump_log(f"{out_dir}/{name}_log.json")
    print(f"\nDone in {time.time() - T:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], max_primary=int(sys.argv[2]) if len(sys.argv) > 2 else 2)
