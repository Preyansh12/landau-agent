"""Every tool the LLM can call must exist on Session with matching argument names."""
import inspect

from landau_agent.agent import TOOLS, _call
from landau_agent.tools import Session


def test_tools_match_session():
    for t in TOOLS:
        fn = getattr(Session, t["name"], None)
        assert fn is not None, t["name"]
        params = set(inspect.signature(fn).parameters) - {"self"}
        props = set(t["input_schema"].get("properties", {}))
        assert props <= params, (t["name"], props - params)
        for req in t["input_schema"].get("required", []):
            assert req in params


def test_errors_are_reported_not_raised():
    out = _call(Session(), "set_supercell", {"matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]})
    assert "error" in out          # no parent loaded yet -> honest error, no crash


def test_refine_resolution_flags_degenerate_phases():
    from landau_agent.tools import Session
    rows = [{"relaxed_cell": {"energy_meV_per_fu": e, "space_group_loose": sg}}
            for e, sg in ((-32.03, "I4/mcm"), (-31.77, "Imma"), (-20.0, "P4/mbm"))]
    r = Session._resolution(rows, ["relaxed_cell"])["relaxed_cell"]
    assert r["lowest"] == "I4/mcm" and r["verdict"].startswith("UNRESOLVED") and len(r["within_1_meV_per_fu_of_lowest"]) == 1
    rows[1]["relaxed_cell"]["energy_meV_per_fu"] = -25.0
    assert Session._resolution(rows, ["relaxed_cell"])["relaxed_cell"]["verdict"] == "resolved"
