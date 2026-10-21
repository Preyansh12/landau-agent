"""LLM orchestrator. The model plans and interprets; every number comes from a tool.

Usage:
    export ANTHROPIC_API_KEY=...
    python -m landau_agent.agent "Why is Ca3Ti2O7 ferroelectric?"
"""
from __future__ import annotations

import json
import os
import sys

from .tools import BUILTIN, Session

MODEL = os.environ.get("LANDAU_AGENT_MODEL", "claude-sonnet-5-5")

SYSTEM = f"""You are LandauAgent, a computational solid-state physicist that explains and predicts
structural phase transitions by combining exact group theory with machine-learned interatomic
potentials (MACE-MP-0).

Hard rules:
- NEVER derive irreps, invariants, couplings, space groups or energies yourself. Call the tools;
  they compute everything exactly. If a tool fails, say so; do not fill the gap with guesses.
- Quote numbers exactly as tools return them, with units (meV per formula unit, Å, eV/Å^2).
- Irrep names from tools are computed (k-point, inversion parity, dimension). You may say which
  textbook label they *correspond to* only if the tool output (k-point, parity, polarity, which
  atoms move) makes the correspondence unambiguous, and say it is a correspondence.
- Be explicit about limits: 0 K frozen-mode energies, fixed parent lattice (no strain coupling),
  PBE-trained potential, finite supercell (only commensurate k-points are visible).
- PBE-trained potentials overestimate lattice constants, which can create spurious polar
  instabilities. If a polar instability appears and an experimental lattice constant is known to
  you, call rescale_parent with it and re-run find_instabilities; report which instabilities
  survive. Treat predictions that only exist at the MACE volume as artefacts.
- If predict_ground_state reports trustworthy=false, rely on enumerate_phases for the phase.

Typical workflow:
1. load_parent  2. set_supercell (pick a matrix whose commensurate k-points contain the
   instabilities you care about; for cubic perovskites 2x2x2 covers Γ, X, M, R; for body-centred
   tetragonal Ruddlesden-Popper parents [[1,1,0],[-1,1,0],[0,0,1]] covers Γ and X)
3. find_instabilities  4. choose_order_parameters (unstable irreps)  5. forced_couplings
6. add_secondary for each forced mode (especially polar ones)  7. landau_polynomial
8. fit_landau  9. predict_ground_state  10. enumerate_phases (independent check of the
   predicted phase; if the two disagree, say so and trust the direct MACE ranking for the
   phase while using the Landau model for the mechanism)  11. answer the question.

Final answer: a short physical explanation (which modes, which couplings, why), the fitted Landau
free energy with coefficients, the predicted phase and its MACE check, and the caveats.
Builtin parents: {", ".join(BUILTIN)}."""

TOOLS = [
    dict(name="load_parent", description="Load and MACE-relax the high-symmetry parent (builtin name or CIF path).",
         input_schema=dict(type="object", properties=dict(source=dict(type="string")), required=["source"])),
    dict(name="rescale_parent", description="Rescale the parent lattice to target_a (Å) or by factor, to test whether an instability is a volume artefact of the PBE-trained potential. Then call set_supercell and find_instabilities again.",
         input_schema=dict(type="object", properties=dict(target_a=dict(type="number"), factor=dict(type="number")))),
    dict(name="set_supercell", description="Set the supercell matrix P (child_cell = P @ parent_cell); returns all irreps of the displacement representation.",
         input_schema=dict(type="object", properties=dict(matrix=dict(type="array", items=dict(type="array", items=dict(type="integer")))), required=["matrix"])),
    dict(name="find_instabilities", description="Harmonic curvature of every irrep block from MACE force constants. Negative = unstable.",
         input_schema=dict(type="object", properties=dict(threshold=dict(type="number")))),
    dict(name="analyze_child", description="Decompose an observed distorted structure (CIF on the current supercell) into irreps.",
         input_schema=dict(type="object", properties=dict(cif_path=dict(type="string")), required=["cif_path"])),
    dict(name="choose_order_parameters", description="Select irreps by label as primary order parameters. source='instabilities' or 'child'.",
         input_schema=dict(type="object", properties=dict(labels=dict(type="array", items=dict(type="string")), source=dict(type="string")), required=["labels"])),
    dict(name="forced_couplings", description="Find stable modes that appear linearly in invariants with the chosen order parameters (improper/triggered modes).",
         input_schema=dict(type="object", properties=dict(max_degree=dict(type="integer")))),
    dict(name="add_secondary", description="Add a forced secondary mode (by label) to the order-parameter set.",
         input_schema=dict(type="object", properties=dict(label=dict(type="string")), required=["label"])),
    dict(name="landau_polynomial", description="Exact symmetry-allowed invariants of the chosen order parameters up to max_degree, plus Landau-condition checks.",
         input_schema=dict(type="object", properties=dict(max_degree=dict(type="integer")))),
    dict(name="fit_landau", description="Fit invariant coefficients to MACE frozen-mode energies.",
         input_schema=dict(type="object", properties=dict(max_degree=dict(type="integer"), n_random=dict(type="integer")))),
    dict(name="predict_ground_state", description="Minimise the fitted Landau model, build the structure, verify with MACE and report its space group.",
         input_schema=dict(type="object", properties=dict(relax_check=dict(type="boolean")))),
    dict(name="enumerate_phases", description="Independent check: enumerate distinct order-parameter direction patterns of the primary modes, relax each with MACE in its own symmetry, rank by energy.",
         input_schema=dict(type="object", properties=dict(max_phases=dict(type="integer")))),
]


def _call(sess: Session, name: str, args: dict):
    try:
        return getattr(sess, name)(**args)
    except Exception as exc:  # surface failures to the model honestly
        return dict(error=f"{type(exc).__name__}: {exc}")


def run(question: str, max_turns: int = 30, verbose: bool = True) -> str:
    import anthropic
    client = anthropic.Anthropic()
    sess = Session()
    messages = [dict(role="user", content=question)]
    for _ in range(max_turns):
        resp = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM,
                                      tools=TOOLS, messages=messages)
        messages.append(dict(role="assistant", content=resp.content))
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            sess.dump_log("agent_log.json")
            return text
        results = []
        for block in resp.content:
            if block.type == "text" and verbose:
                print(f"\n[agent] {block.text}", flush=True)
            if block.type == "tool_use":
                if verbose:
                    print(f"[tool] {block.name}({json.dumps(block.input)})", flush=True)
                out = _call(sess, block.name, block.input)
                results.append(dict(type="tool_result", tool_use_id=block.id,
                                    content=json.dumps(out, default=str)[:20000]))
        messages.append(dict(role="user", content=results))
    sess.dump_log("agent_log.json")
    return "Stopped: turn limit reached."


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Why is Ca3Ti2O7 ferroelectric? Start from the I4/mmm parent."
    print(run(q))
