"""Draw the paper benchmark set from the Materials Project under SELECTION_RULE.md.
Needs MP_API_KEY in the environment (free key from materialsproject.org). Writes results/selection.json
and prints the table; run it ONCE, commit the output, then run the benchmark."""
import json, os, sys, re
from collections import defaultdict
try:
    from mp_api.client import MPRester
except ImportError:
    sys.exit("pip install mp-api")

HULL_MEV, MAG_MUB, MAX_ATOMS_SUPERCELL = 30.0, 0.1, 160
BAD = set("He Ne Ar Kr Xe Rn Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Po At Fr Ra".split())
PRIOR = set("CaTiO3 PbTiO3 LaAlO3 BaTiO3 SrTiO3 Ca3Ti2O7 Sr3Zr2O7 Sr3Ru2O7 Sr3Ti2O7 Ca3Mn2O7 Ca3Sn2O7 Sr3Sn2O7 Sr3Hf2O7".split())
FAMILIES = {"ABO3": (r"^[A-Z][a-z]?[A-Z][a-z]?O3$", "Pm-3m", 40), "A3B2O7": (r"^[A-Z][a-z]?3[A-Z][a-z]?2O7$", "I4/mmm", 48)}

def main():
    key = os.environ.get("MP_API_KEY") or sys.exit("set MP_API_KEY")
    fields = ["material_id", "formula_pretty", "symmetry", "energy_above_hull", "theoretical",
              "total_magnetization", "nsites", "elements", "nelements"]
    rows = []
    with MPRester(key) as mpr:
        for fam, (pat, aristo, _) in FAMILIES.items():
            docs = mpr.materials.summary.search(formula=["*{}O3".format("*") if fam == "ABO3" else "*3*2O7"],
                                                 fields=fields)
            by_comp = defaultdict(list)
            for d in docs:
                if re.match(pat, d.formula_pretty) and d.nelements == 3:
                    by_comp[d.formula_pretty].append(d)
            for comp, ds in sorted(by_comp.items()):
                if set(e.symbol for e in ds[0].elements) & BAD:
                    continue
                exp = [d for d in ds if not d.theoretical]
                if not exp or not any(d.symmetry.symbol == aristo for d in ds):
                    continue
                exp.sort(key=lambda d: d.energy_above_hull)
                ref = exp[0]
                if ref.energy_above_hull * 1000 > HULL_MEV:
                    continue
                fu = ref.nsites // (5 if fam == "ABO3" else 12)
                if (ref.total_magnetization or 0) / max(fu, 1) >= MAG_MUB:
                    continue
                degenerate = [d.symmetry.symbol for d in exp if (d.energy_above_hull - ref.energy_above_hull) * 1000 < 1.0]
                rows.append(dict(family=fam, formula=comp, reference_sg=ref.symmetry.symbol, reference_id=ref.material_id,
                                 e_hull_meV_atom=round(ref.energy_above_hull * 1000, 1),
                                 degenerate_reference=sorted(set(degenerate)) if len(set(degenerate)) > 1 else None,
                                 experimental_polymorphs=sorted(set(d.symmetry.symbol for d in exp)),
                                 status="prior" if comp in PRIOR else "new"))
    os.makedirs("results", exist_ok=True)
    json.dump(rows, open("results/selection.json", "w"), indent=1)
    print(f"{'family':7} {'formula':10} {'reference':10} {'status':6} degenerate")
    for r in rows:
        print(f"{r['family']:7} {r['formula']:10} {r['reference_sg']:10} {r['status']:6} {r['degenerate_reference'] or ''}")
    print(len(rows), "compositions selected;", sum(r["status"] == "new" for r in rows), "new")

if __name__ == "__main__":
    main()
