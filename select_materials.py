"""Draw the paper benchmark set from the Materials Project under SELECTION_RULE.md and write
materials/registry.json (parent-building parameters + reference answer per composition).
Needs MP_API_KEY in the environment (free key from materialsproject.org). Run ONCE, commit the registry,
then run the benchmark (run_database.bat / run_database.sh). Never edit the registry after results exist."""
import json, os, sys, re
from collections import defaultdict
try:
    from mp_api.client import MPRester
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
except ImportError:
    sys.exit("pip install mp-api pymatgen")

HULL_MEV, MAG_MUB = 30.0, 0.1
BAD = set("He Ne Ar Kr Xe Rn Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Po At Fr Ra".split())
PRIOR = set("CaTiO3 PbTiO3 LaAlO3 BaTiO3 SrTiO3 Ca3Ti2O7 Sr3Zr2O7 Sr3Ru2O7 Sr3Ti2O7 Ca3Mn2O7 Ca3Sn2O7 Sr3Sn2O7 Sr3Hf2O7".split())
# family: (regex on the pretty formula, aristotype space group, MP anonymous formula, atoms per formula unit)
FAMILIES = {"ABO3": (r"^[A-Z][a-z]?[A-Z][a-z]?O3$", "Pm-3m", "ABC3", 5),
            "A3B2O7": (r"^[A-Z][a-z]?3[A-Z][a-z]?2O7$", "I4/mmm", "A2B3C7", 12)}
FIELDS = ["material_id", "formula_pretty", "symmetry", "energy_above_hull", "theoretical",
          "total_magnetization", "nsites", "elements", "nelements"]


def a_and_b(struct, a_inplane):
    """Which cation is octahedral (B)? The one with 6 oxygens within 0.56 a. The other is A."""
    counts = defaultdict(list)
    for i, site in enumerate(struct):
        if site.specie.symbol == "O":
            continue
        n_o = sum(1 for nb in struct.get_neighbors(site, 0.56 * a_inplane) if nb.specie.symbol == "O")
        counts[site.specie.symbol].append(n_o)
    cations = sorted(counts, key=lambda el: -max(counts[el]))
    if len(cations) != 2 or max(counts[cations[0]]) < 6:
        return None, None
    return cations[1], cations[0]           # A, B


def main():
    key = os.environ.get("MP_API_KEY") or sys.exit("set MP_API_KEY")
    registry, log = {}, []
    with MPRester(key) as mpr:
        for fam, (pat, aristo, anon, n_per_fu) in FAMILIES.items():
            docs = mpr.materials.summary.search(formula=anon, elements=["O"], fields=FIELDS)
            by_comp = defaultdict(list)
            for d in docs:
                if re.match(pat, d.formula_pretty) and d.nelements == 3:
                    by_comp[d.formula_pretty].append(d)
            for comp, ds in sorted(by_comp.items()):
                if set(e.symbol for e in ds[0].elements) & BAD:
                    log.append((comp, "excluded element")); continue
                exp = [d for d in ds if not d.theoretical]
                aristos = [d for d in ds if d.symmetry.symbol == aristo]
                if not exp:
                    log.append((comp, "no experimental polymorph")); continue
                if not aristos:
                    log.append((comp, "no aristotype polymorph")); continue
                exp.sort(key=lambda d: d.energy_above_hull)
                ref = exp[0]
                if ref.energy_above_hull * 1000 > HULL_MEV:
                    log.append((comp, f"{ref.energy_above_hull*1000:.0f} meV/atom above hull")); continue
                fu = max(ref.nsites // n_per_fu, 1)
                if abs(ref.total_magnetization or 0) / fu >= MAG_MUB:
                    log.append((comp, "magnetic")); continue
                # aristotype lattice from the database structure; A/B assignment from coordination
                ar = min(aristos, key=lambda d: d.energy_above_hull)
                st = SpacegroupAnalyzer(mpr.get_structure_by_material_id(ar.material_id)).get_conventional_standard_structure()
                a, c = float(st.lattice.a), float(st.lattice.c)
                A, B = a_and_b(st, a)
                if A is None:
                    log.append((comp, "could not assign A/B sites")); continue
                deg = sorted({d.symmetry.symbol for d in exp if (d.energy_above_hull - ref.energy_above_hull) * 1000 < 1.0})
                registry[comp] = dict(
                    family=fam, A=A, B=B, a=round(a, 4), c=round(c, 4) if fam == "A3B2O7" else None,
                    aristotype_id=str(ar.material_id),
                    reference_sg=ref.symmetry.symbol, reference_sg_number=int(ref.symmetry.number),
                    reference_id=str(ref.material_id), e_hull_meV_atom=round(ref.energy_above_hull * 1000, 1),
                    degenerate_reference=deg if len(deg) > 1 else None,
                    reference_is_aristotype=(ref.symmetry.symbol == aristo),
                    experimental_polymorphs=sorted({d.symmetry.symbol for d in exp}),
                    literature_sg=None,                       # filled AFTER the run, from the literature; see SELECTION_RULE.md
                    status="prior" if comp in PRIOR else "new")
    os.makedirs("materials", exist_ok=True)
    json.dump(registry, open("materials/registry.json", "w"), indent=1)
    json.dump(log, open("materials/selection_log.json", "w"), indent=1)
    print(f"{'family':7} {'formula':10} {'A':3}{'B':3} {'a':7} {'reference':12} {'status':6} notes")
    for n, r in registry.items():
        notes = ("aristotype " if r["reference_is_aristotype"] else "") + (f"degenerate {r['degenerate_reference']}" if r["degenerate_reference"] else "")
        print(f"{r['family']:7} {n:10} {r['A']:3}{r['B']:3} {r['a']:7.3f} {r['reference_sg']:12} {r['status']:6} {notes}")
    print(len(registry), "compositions;", sum(r["status"] == "new" for r in registry.values()), "new;",
          len(log), "excluded (materials/selection_log.json)")


if __name__ == "__main__":
    main()
