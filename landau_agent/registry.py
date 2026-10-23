"""Materials drawn from a database under SELECTION_RULE.md, stored in materials/registry.json by
select_materials.py. Each entry carries what is needed to build the ideal aristotype (family, A, B,
lattice parameters) and the reference answer (lowest experimental polymorph in the database).
The builtin 13 hackathon materials are unaffected; registry entries only add to them."""
import json, os

PATH = os.path.join(os.path.dirname(__file__), "..", "materials", "registry.json")
SUPERCELL = {"ABO3": [[2, 0, 0], [0, 2, 0], [0, 0, 2]],            # R, M and X points of Pm-3m
             "A3B2O7": [[1, 1, 0], [-1, 1, 0], [0, 0, 1]]}        # X point of I4/mmm (conventional cell)


def load() -> dict:
    if not os.path.exists(PATH):
        return {}
    return json.load(open(PATH))


def builder(entry):
    from .structures import cubic_perovskite, ruddlesden_popper_n2
    if entry["family"] == "ABO3":
        return lambda: cubic_perovskite(entry["A"], entry["B"], a=entry["a"])
    if entry["family"] == "A3B2O7":
        return lambda: ruddlesden_popper_n2(entry["A"], entry["B"], "O", a=entry["a"], c=entry["c"])
    raise ValueError(entry["family"])


def supercell(entry):
    return SUPERCELL[entry["family"]]
