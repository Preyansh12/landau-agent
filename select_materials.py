"""Draw the paper benchmark set from the Materials Project under SELECTION_RULE.md (rule version 2) and write
materials/registry.json (parent-building parameters + reference answer per composition) and
materials/selection_log.json (every excluded composition and why).
Needs MP_API_KEY in the environment (free key from materialsproject.org). Run ONCE, commit, then run the benchmark
(run_database.bat / run_database.sh). Never edit the registry after results exist."""
import json, os, sys
from collections import defaultdict
try:
    from mp_api.client import MPRester
    from pymatgen.core import Composition, Element
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.analysis.local_env import CrystalNN
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.io.ase import AseAtomsAdaptor
except ImportError:
    sys.exit("pip install mp-api pymatgen")
from landau_agent.structures import cubic_perovskite, ruddlesden_popper_n2

HULL_MEV = 30.0
MATCH = dict(ltol=0.3, stol=0.4, angle_tol=10)     # pseudosymmetry test; calibrated in SELECTION_RULE.md
MAGNETIC = {"FM", "AFM", "FiM"}                     # MP ordering values that mean magnetic; "Unknown"/None fall back to the moment
BAD = set("He Ne Ar Kr Xe Rn Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Po At Fr Ra".split())
PRIOR = set("CaTiO3 PbTiO3 LaAlO3 BaTiO3 SrTiO3 Ca3Ti2O7 Sr3Zr2O7 Sr3Ru2O7 Sr3Ti2O7 Ca3Mn2O7 Ca3Sn2O7 Sr3Sn2O7 Sr3Hf2O7".split())
# family: (MP anonymous formula, cation counts (A, B), O count, aristotype symbol)
FAMILIES = {"ABO3": ("ABC3", (1, 1), 3, "Pm-3m"), "A3B2O7": ("A2B3C7", (3, 2), 7, "I4/mmm")}
FIELDS = ["material_id", "formula_pretty", "symmetry", "energy_above_hull", "theoretical", "ordering",
          "total_magnetization", "nsites", "elements", "nelements", "volume"]


def radius(el):
    e = Element(el)
    return e.average_ionic_radius or e.atomic_radius or 1.0


def classify(formula, family):
    """Return (A, B) with A the larger cation, or None if the composition is not A_x B_y O_z of this family."""
    (na, nb), no, _ = FAMILIES[family][1], FAMILIES[family][2], None
    comp = Composition(formula).reduced_composition
    d = {el.symbol: int(round(n)) for el, n in comp.items()}
    if d.get("O") != no or len(d) != 3:
        return None
    cations = [el for el in d if el != "O"]
    if sorted(d[el] for el in cations) != sorted((na, nb)):
        return None
    if na == nb:                                      # ABO3: the larger cation is A
        A, B = sorted(cations, key=lambda el: -radius(el))
    else:                                             # A3B2O7: counts decide, radius is checked
        A = next(el for el in cations if d[el] == na); B = next(el for el in cations if d[el] == nb)
        if radius(A) < radius(B):
            return None
    return A, B


def octahedral_b(struct, A, B):
    """Perovskites are corner-sharing BO6 octahedra: every B site must be 6-coordinate by oxygen (CrystalNN).
    Returns (ok, list of B coordination numbers)."""
    cnn = CrystalNN()
    cns = []
    for i, site in enumerate(struct):
        if site.specie.symbol == B:
            nn = cnn.get_nn_info(struct, i)
            cns.append(sum(1 for n in nn if n["site"].specie.symbol == "O"))
    return bool(cns) and all(c == 6 for c in cns), sorted(set(cns))


def ideal(family, A, B, a, c):
    at = cubic_perovskite(A, B, a=a) if family == "ABO3" else ruddlesden_popper_n2(A, B, "O", a=a, c=c)
    return AseAtomsAdaptor.get_structure(at)


def main():
    key = os.environ.get("MP_API_KEY") or sys.exit("set MP_API_KEY")
    registry, log = {}, []
    matcher = StructureMatcher(primitive_cell=True, scale=True, attempt_supercell=True, **MATCH)
    with MPRester(key) as mpr:
        for fam, (anon, counts, n_o, aristo) in FAMILIES.items():
            n_per_fu = sum(counts) + n_o
            docs = mpr.materials.summary.search(formula=anon, elements=["O"], fields=FIELDS)
            by_comp = defaultdict(list)
            for d in docs:
                if d.nelements != 3:
                    continue
                ab = classify(d.formula_pretty, fam)
                if ab is None:
                    continue
                name = f"{ab[0]}{ab[1]}O3" if fam == "ABO3" else f"{ab[0]}3{ab[1]}2O7"
                by_comp[name].append((ab, d))
            for name, items in sorted(by_comp.items()):
                (A, B), _ = items[0]
                ds = [d for _, d in items]
                if {A, B} & BAD:
                    log.append((name, "excluded element")); continue
                exp = sorted([d for d in ds if not d.theoretical], key=lambda d: d.energy_above_hull)
                if not exp:
                    log.append((name, "no experimental polymorph")); continue
                ref = exp[0]
                if ref.energy_above_hull * 1000 > HULL_MEV:
                    log.append((name, f"{ref.energy_above_hull * 1000:.0f} meV/atom above hull")); continue
                fu = max(ref.nsites // n_per_fu, 1)
                ordering = str(ref.ordering or "Unknown").replace("Ordering.", "")
                if ordering in MAGNETIC or (ordering not in ("NM",) and abs(ref.total_magnetization or 0) / fu >= 0.1):
                    log.append((name, f"magnetic ({ordering}, {ref.total_magnetization})")); continue
                ref_struct = mpr.get_structure_by_material_id(ref.material_id)
                # B must be the six-coordinate cation; A the other one (and the larger, as a sanity check)
                okB, cnB = octahedral_b(ref_struct, A, B)
                if not okB:
                    okA, cnA = octahedral_b(ref_struct, B, A)
                    if okA and radius(B) >= radius(A):
                        A, B = B, A
                        name = f"{A}{B}O3" if fam == "ABO3" else f"{A}3{B}2O7"
                    else:
                        log.append((name, f"B site not octahedral (CN {cnB})")); continue
                # aristotype lattice from the reference polymorph's volume (no aristotype entry needed)
                v_fu = ref.volume / fu
                if fam == "ABO3":
                    a, c = v_fu ** (1 / 3), None
                else:
                    st = SpacegroupAnalyzer(ref_struct).get_conventional_standard_structure()
                    c = max(st.lattice.abc)
                    if not 17.0 < c < 25.0:
                        log.append((name, f"cannot infer RP c axis ({c:.1f} A)")); continue
                    a = (2 * v_fu / c) ** 0.5
                # pseudosymmetry: the reference polymorph must be a small distortion of the ideal aristotype
                rms = matcher.get_rms_dist(ref_struct, ideal(fam, A, B, a, c))
                if rms is None:
                    log.append((name, f"reference polymorph {ref.symmetry.symbol} not pseudosymmetric to {aristo}")); continue
                deg = sorted({d.symmetry.symbol for d in exp if (d.energy_above_hull - ref.energy_above_hull) * 1000 < 1.0})
                registry[name] = dict(
                    family=fam, A=A, B=B, a=round(float(a), 4), c=round(float(c), 4) if c else None,
                    reference_sg=ref.symmetry.symbol, reference_sg_number=int(ref.symmetry.number),
                    reference_id=str(ref.material_id), e_hull_meV_atom=round(ref.energy_above_hull * 1000, 1),
                    pseudosymmetry_rms=round(float(rms[0]), 3),
                    degenerate_reference=deg if len(deg) > 1 else None,
                    reference_is_aristotype=(ref.symmetry.symbol == aristo),
                    experimental_polymorphs=sorted({d.symmetry.symbol for d in exp}),
                    literature_sg=None,                 # filled AFTER the run, from the literature; see SELECTION_RULE.md
                    status="prior" if name in PRIOR else "new")
    os.makedirs("materials", exist_ok=True)
    json.dump(registry, open("materials/registry.json", "w"), indent=1)
    json.dump(log, open("materials/selection_log.json", "w"), indent=1)
    print(f"{'family':7} {'formula':10} {'A':3}{'B':3} {'a':7} {'c':7} {'reference':12} {'rms':6} {'status':6} notes")
    for n, r in registry.items():
        notes = ("aristotype " if r["reference_is_aristotype"] else "") + (f"degenerate {r['degenerate_reference']}" if r["degenerate_reference"] else "")
        print(f"{r['family']:7} {n:10} {r['A']:3}{r['B']:3} {r['a']:7.3f} {(r['c'] or 0):7.2f} {r['reference_sg']:12} {r['pseudosymmetry_rms']:6.3f} {r['status']:6} {notes}")
    reasons = defaultdict(int)
    for _, why in log:
        reasons["above hull" if "above hull" in why else why.split(" (")[0].split(" not ")[0][:40]] += 1
    print(len(registry), "compositions;", sum(r["status"] == "new" for r in registry.values()), "new;", len(log), "excluded:",
          dict(reasons))
    print("prior materials not selected:", {n: w for n, w in log if n in PRIOR} or "none")


if __name__ == "__main__":
    main()
