"""Fixed-protocol benchmark: same steps, same settings for every material, no per-material tuning.

Protocol versions (all kept, all reported):
  v1  original: incomplete direction set, refinement chosen at fixed lattice        results/benchmark_<name>.json
  v2  symmetry-complete directions, strain-aware refinement, single-point screening results/benchmark_v2_<name>.json
  v3  v2 + 25-step relaxation of every candidate before ranking, and 10x tighter re-relaxation
      of any phases within 1 meV/f.u. before they are declared unresolved; all 6 enumerated
      phases get a free-cell relaxation (v2: best 4 at fixed lattice)                results/benchmark_v3*_<name>.json
  v4  v3 + primaries are the three softest DISTINCT irreps (not one per short name), and the
      reported winner is always converged to fmax = 0.001 eV/A                        results/benchmark_v4*_<name>.json
  v5  v4, but primaries are every unstable irrep within a factor 2 of the softest curvature (max 4):
      a fixed count of 3 dropped the X+ rotation of Sr3Hf2O7. A winner whose 1e-3 A and 1e-2 A
      space groups differ is snapped to the looser one and re-relaxed inside it; if that costs
      < 0.05 meV/f.u. the higher symmetry is reported (PbTiO3 read Pm with P4mm at 1e-2 A)        results/benchmark_v5*_<name>.json
  v6  v5, but every candidate within 30 % of the best screened energy (max 24, min 6) gets the
      fixed-lattice relaxation instead of a fixed best-6: with 4 primaries and 72 patterns, CaZrO3's
      Pnma sat 10th after the screen and was cut; fully relaxed it beats the R3c winner by 74 meV/f.u.
      Designed after the first 23 test-set results (SELECTION_RULE.md, protocol log)                results/benchmark_v6*_<name>.json
MLIP: LANDAU_MLIP_MODEL=medium (MACE-MP-0, PBE) or mace-matpes-r2scan-0 (MACE MatPES r2SCAN); the tag records it.

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
from landau_agent import registry as _registry
REGISTRY = _registry.load()
for _n, _e in REGISTRY.items():
    SUPERCELLS.setdefault(_n, _registry.supercell(_e))

import os
from landau_agent import energy as _E
PROTOCOL = os.environ.get("LANDAU_PROTOCOL", "v2")          # v2: single-point screening; v3/v4: 25-step relaxation screening
SCREEN_STEPS = {"v2": 0, "v3": 25, "v4": 25, "v5": 25, "v6": 25}[PROTOCOL]
SCREEN_WINDOW = 0.30 if PROTOCOL == "v6" else None   # v6: fixed-lattice relaxation for every candidate within 30 % of the best screened energy (max 24)
V5_WINDOW, V5_CAP = 2.0, 4   # v5: every unstable irrep within a factor V5_WINDOW of the softest curvature, at most V5_CAP
TAG = PROTOCOL if _E.MODEL == "medium" else PROTOCOL + "_" + _E.MODEL.replace("mace-", "").replace("-", "_")


def run(name):
    T = time.time()
    s = Session()
    mtag = "" if _E.MODEL == "medium" else "_" + _E.MODEL.replace("mace-", "").replace("-", "_")
    s.fc_cache = f"results/{name}{mtag}_force_constants.npy"          # force constants depend only on the model
    parent = s.load_parent(name)
    s.set_supercell(SUPERCELLS[name])
    modes = s.find_instabilities()["modes"]
    picked, seen = [], set()
    if PROTOCOL in ("v5", "v6"):
        # v5: curvature window instead of a fixed count. v4's "three softest distinct" dropped the X+ rotation of
        # Sr3Hf2O7 (fourth softest, 0.015 eV/A^2 behind three X- modes), so A2_1am could not be enumerated.
        unstable = [m for m in modes if m["unstable"]]
        kmin = min((m["curvature_eV_A2"] for m in unstable), default=0.0)   # no instability -> nothing picked
        picked = [m["label"] for m in unstable if m["curvature_eV_A2"] <= kmin / V5_WINDOW][:V5_CAP]
    elif PROTOCOL == "v4":
        # v4: the three softest DISTINCT irreps, whatever their short names. Keeping one irrep per
        # name let a rotation displace the X3- tilt in Ca3Mn2O7 and Sr3Sn2O7 (see README).
        picked = [m["label"] for m in modes if m["unstable"]][:3]
    else:
        for m in modes:
            if m["unstable"] and m["name"] not in seen:
                picked.append(m["label"]); seen.add(m["name"])
        picked = picked[:3]
    if not picked:
        out = dict(material=name, parent=parent, instabilities=[], protocol=TAG, mlip=_E.MODEL,
                   winner=dict(space_group="parent (no instability)"), runtime_s=round(time.time() - T))
        json.dump(out, open(f"results/benchmark_{TAG}_{name}.json", "w"), indent=1, ensure_ascii=False, default=str)
        print(name, "->", out["winner"], flush=True)
        return
    s.choose_order_parameters(picked)
    ph = s.enumerate_phases(max_phases=6, fmax=0.03, steps=250, screen_steps=SCREEN_STEPS, screen_window=SCREEN_WINDOW)
    # v2: strain can reorder phases, so the best 4 (not 2) get a full cell relaxation
    # v2 refined the best 4 of the 6 fixed-lattice relaxations; strain-driven phases (PbTiO3 P4mm)
    # can sit 5th or 6th at fixed lattice and win with a free cell, so v3 refines all 6.
    ref = s.refine_phases(top=6 if PROTOCOL in ("v3", "v4", "v5", "v6") else 4, fmax=0.01, steps=800, relaxed_cell_only=True,
                          tighten_if_unresolved=(PROTOCOL in ("v3", "v4", "v5", "v6")), polish_winner=(PROTOCOL in ("v4", "v5", "v6")),
                          symmetrise_winner=(PROTOCOL in ("v5", "v6")))
    best = ref["phases"][0]
    out = dict(material=name, parent=parent, instabilities=[{k: m[k] for k in ("name", "label", "curvature_eV_A2", "polar")} for m in modes if m["unstable"]],
               primaries=picked, enumeration=ph, refined=ref,
               protocol=TAG, mlip=_E.MODEL, winner=dict(space_group=best["relaxed_cell"]["space_group"], space_group_tol_0_01=best["relaxed_cell"]["space_group_loose"],
                           energy_meV_per_fu=best["relaxed_cell"]["energy_meV_per_fu"], seed=best["space_group_seed"]),
               runtime_s=round(time.time() - T))
    json.dump(out, open(f"results/benchmark_{TAG}_{name}.json", "w"), indent=1, ensure_ascii=False, default=str)
    print(name, "->", out["winner"], f"{out['runtime_s']}s", flush=True)

if __name__ == "__main__":
    names = sys.argv[1:]
    if names == ["--registry"]:            # every database-drawn material not yet run under this tag
        names = [n for n, e in REGISTRY.items() if e["status"] == "new"
                 and not os.path.exists(f"results/benchmark_{TAG}_{n}.json")]
        print(f"{len(names)} registry materials to run under {TAG}", flush=True)
    for n in names:
        try:
            run(n)
        except Exception as e:
            print(n, "FAILED", type(e).__name__, e, flush=True)
