"""Build the protocol-comparison table (markdown) from results/benchmark_*.json. No hand-typed numbers."""
import glob, json, re, sys

KNOWN = {  # experimental ground state (space-group number) ; aliases that count as the same group
    "CaTiO3": ("Pnma", 62), "PbTiO3": ("P4mm", 99), "BaTiO3": ("R3m", 160), "LaAlO3": ("R-3c", 167),
    "SrTiO3": ("I4/mcm", 140), "Ca3Ti2O7": ("A2_1am", 36), "Sr3Zr2O7": ("A2_1am", 36), "Ca3Mn2O7": ("A2_1am", 36),
    "Ca3Sn2O7": ("A2_1am", 36), "Sr3Sn2O7": ("A2_1am", 36), "Sr3Hf2O7": ("A2_1am (DFT)", 36),
    "Sr3Ru2O7": ("Bbcb", 68), "Sr3Ti2O7": ("I4/mmm", 139),
}
ORDER = ["CaTiO3", "PbTiO3", "BaTiO3", "LaAlO3", "SrTiO3", "Ca3Ti2O7", "Sr3Zr2O7", "Ca3Mn2O7", "Ca3Sn2O7",
         "Sr3Sn2O7", "Sr3Hf2O7", "Sr3Ru2O7", "Sr3Ti2O7"]
PROTOCOLS = [("v1", "benchmark_{m}.json", "v1 (PBE)"), ("v2", "benchmark_v2_{m}.json", "v2 (PBE)"),
             ("v2r", "benchmark_v2_matpes_r2scan_0_{m}.json", "v2 (r2SCAN)"),
             ("v3", "benchmark_v3_matpes_r2scan_0_{m}.json", "v3 (r2SCAN)"),
             ("v4", "benchmark_v4_matpes_r2scan_0_{m}.json", "v4 (r2SCAN)"),
             ("v5", "benchmark_v5_matpes_r2scan_0_{m}.json", "v5 (r2SCAN)")]


def sgnum(label):
    m = re.search(r"\((\d+)\)", label or "")
    return int(m.group(1)) if m else None


def verdict(mat, d):
    """hit / unresolved(+contains) / miss, from the winner and the resolution verdict when present."""
    known_num = KNOWN[mat][1]
    w = d["winner"]
    if "no instability" in w.get("space_group", ""):
        return ("hit" if known_num == 139 else "miss"), "no instability"
    loose = w.get("space_group_tol_0_01") or w["space_group"]
    pol = d.get("winner_polished") or {}
    if pol.get("needed"):          # v3: winner converged to fmax 0.001 when its symmetry was tolerance-dependent
        loose = pol["space_group"]
        w = dict(w, energy_meV_per_fu=pol["energy_meV_per_fu"])
    res = (d.get("refined") or {}).get("resolution", {})
    key = (d.get("refined") or {}).get("ranked_by", "relaxed_cell")
    r = dict(res.get(key)) if res and res.get(key) else None
    if r:   # drop "competitors" that are the same relaxed phase as the winner (older logs kept them)
        r["within_1_meV_per_fu_of_lowest"] = [c for c in r["within_1_meV_per_fu_of_lowest"] if sgnum(c) != sgnum(loose)]
        if not r["within_1_meV_per_fu_of_lowest"]:
            r["verdict"] = "resolved"
    txt = f"{loose} ({w['energy_meV_per_fu']})"
    if sgnum(loose) == known_num:
        if r and r["verdict"] != "resolved":   # the tool itself declines to call a winner: not a hit
            return "unresolved", txt + "; known state lowest but within 1 meV/f.u. of " + ", ".join(r["within_1_meV_per_fu_of_lowest"])
        return "hit", txt
    if r and r["verdict"] != "resolved":
        close = r["within_1_meV_per_fu_of_lowest"]
        if any(sgnum(c) == known_num for c in close):
            return "unresolved", txt + "; known state within " + ", ".join(c for c in close if sgnum(c) == known_num)
        return "miss", txt + "; degenerate set lacks the known state"
    return "miss", txt


def main():
    rows, tally = [], {p[0]: [0, 0, 0] for p in PROTOCOLS}  # hit, unresolved, miss
    for mat in ORDER:
        cells = []
        for key, pat, _ in PROTOCOLS:
            f = glob.glob("results/" + pat.format(m=mat))
            if not f:
                cells.append("—")
                continue
            d = json.load(open(f[0]))
            v, txt = verdict(mat, d)
            mark = {"hit": "✅", "unresolved": "⚠️ unresolved", "miss": "❌"}[v]
            tally[key][0 if v == "hit" else 1 if v == "unresolved" else 2] += 1
            cells.append(f"{mark} {txt}")
        rows.append(f"| {mat} | {KNOWN[mat][0]} | " + " | ".join(cells) + " |")
    print("| Material | Known | " + " | ".join(p[2] for p in PROTOCOLS) + " |")
    print("|---|---|" + "---|" * len(PROTOCOLS))
    print("\n".join(rows))
    print("| **Tally (hit / unresolved / miss)** | | " + " | ".join(f"**{h} / {u} / {m}**" for h, u, m in tally.values()) + " |")


if __name__ == "__main__":
    main()
