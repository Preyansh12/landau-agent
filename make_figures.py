"""Phase-energy ladder from the MACE enumeration: the figure for README / social post."""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

POLAR = "#c0392b"
NONPOLAR = "#5d6d7e"


def ladder(ax, name: str):
    ph = json.load(open(f"results/{name}_phases.json"))["phases"]
    ref = {}
    try:
        for r in json.load(open(f"results/{name}_refined.json"))["phases"]:
            ref[r["space_group_seed"]] = r["fixed_cell"]["energy_meV_per_fu"]
    except FileNotFoundError:
        pass
    rows = []
    for p in ph:
        e = ref.get(p["space_group_seed"], p["energy_meV_per_fu"])
        polar = max(abs(x) for x in p["polarization_nominal_uC_cm2"]) > 0.5
        active = [k.split("_")[0] for k, v in p["order_parameter_directions"].items() if v is not None]
        rows.append((p["space_group_relaxed"].split(" ")[0], e, polar, " + ".join(active)))
    rows.sort(key=lambda r: r[1])
    for i, (sg, e, polar, act) in enumerate(rows):
        same = i > 0 and abs(e - rows[i - 1][1]) < 0.5      # relaxed into the phase above
        label = f"{sg}  ({act})" + (f"  ≡ {rows[i - 1][0]} after relaxation" if same else "")
        ax.barh(i, e, color=POLAR if polar else NONPOLAR, height=0.7, alpha=0.45 if same else 1.0)
        ax.text(e + abs(e) * 0.02, i, label, va="center", ha="left",
                color="white" if not same else "black", fontsize=8)
        ax.text(e - abs(e) * 0.01, i, f"{e:.0f}", va="center", ha="right", fontsize=7, color="0.3")
    lo = min(r[1] for r in rows)
    ax.set_xlim(lo * 1.1, max(5.0, max(r[1] for r in rows) * 1.1))
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.axvline(0, color="0.4", lw=0.8)
    ax.set_xlabel("MACE energy vs parent (meV / formula unit)")
    ax.set_title(f"{name}: phases from the symmetry-distinct order-parameter patterns", fontsize=10)


def main(names):
    fig, axes = plt.subplots(1, len(names), figsize=(6.2 * len(names), 4.2), squeeze=False)
    for ax, n in zip(axes[0], names):
        ladder(ax, n)
    handles = [plt.Rectangle((0, 0), 1, 1, color=POLAR), plt.Rectangle((0, 0), 1, 1, color=NONPOLAR)]
    fig.legend(handles, ["polar", "non-polar"], loc="lower center", ncol=2, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out = "results/phase_ladder_" + "_".join(names) + ".png"
    fig.savefig(out, dpi=170, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1:])
