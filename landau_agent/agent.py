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
- Irrep names from tools are computed (k-point, inversion parity, dimension). When a tool returns
  standard_label (ISOTROPY/Bilbao, e.g. R4+, X3-), it was verified by projecting the textbook
  rigid-octahedron pattern onto the irrep; use it. Never invent a standard label a tool did not give.
- Be explicit about limits: 0 K frozen-mode energies, fixed parent lattice (no strain coupling),
  PBE-trained potential, finite supercell (only commensurate k-points are visible).
- PBE-trained potentials overestimate lattice constants, which can create spurious polar
  instabilities. If a polar instability appears and an experimental lattice constant is known to
  you, call rescale_parent with it and re-run find_instabilities; report which instabilities
  survive. Treat predictions that only exist at the MACE volume as artefacts.
- If predict_ground_state reports trustworthy=false, rely on enumerate_phases for the phase.

How to work. There is no fixed recipe; you decide what to compute, and you must justify each
decision in one sentence before the tool call. The decisions that are yours:
- Supercell: which k-points must be commensurate for the question asked (for cubic perovskites
  2x2x2 covers Γ, X, M, R; for body-centred tetragonal Ruddlesden-Popper parents
  [[1,1,0],[-1,1,0],[0,0,1]] covers Γ, Z and X). Start small; enlarge only if you have a reason.
- Which instabilities are real. Ask of every one: is it robust to volume (rescale_parent)? Is it
  an acoustic or near-zero mode? Several irreps can share a short name; look at which atoms move.
- Which instabilities become order parameters. Not necessarily all of them, and not necessarily
  the softest: the question may be about a specific transition. Say why you keep or drop each.
- Whether stable modes must be added because they are forced by a coupling (forced_couplings).
- Which prediction to trust: enumerate_phases + refine_phases is the phase prediction;
  the Landau polynomial (landau_polynomial, fit_landau, predict_ground_state) is the mechanism and
  a cross-check. If they disagree, or if candidate phases are within ~1 meV/f.u., say that the
  potential cannot decide rather than picking one.
- When to stop: as soon as the question is answered with tool-backed evidence. If the question is
  yes/no (e.g. "is X ferroelectric?"), answer it directly and give the deciding evidence.

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
    dict(name="refine_phases", description="Tightly re-relax the lowest enumerated phases at fixed and relaxed lattice and rank them (call after enumerate_phases).",
         input_schema=dict(type="object", properties=dict(top=dict(type="integer")))),
    dict(name="enumerate_phases", description="Independent check: enumerate distinct order-parameter direction patterns of the primary modes, relax each with MACE in its own symmetry, rank by energy.",
         input_schema=dict(type="object", properties=dict(max_phases=dict(type="integer")))),
]


def _call(sess: Session, name: str, args: dict):
    try:
        return getattr(sess, name)(**args)
    except Exception as exc:  # surface failures to the model honestly
        return dict(error=f"{type(exc).__name__}: {exc}")


def _transcript(path, question, messages):
    """Human-readable transcript: every model message and every tool call/result."""
    with open(path, "w") as fh:
        fh.write(f"# LandauAgent transcript\n\nModel: `{MODEL}`\n\n**Question:** {question}\n\n")
        for m in messages[1:]:
            content = m["content"]
            if m["role"] == "assistant":
                for b in content:
                    if b.type == "text" and b.text.strip():
                        fh.write(f"**Agent:** {b.text.strip()}\n\n")
                    elif b.type == "tool_use":
                        fh.write(f"**Tool call:** `{b.name}({json.dumps(b.input, ensure_ascii=False)})`\n\n")
            else:
                for r in content:
                    txt = r["content"]
                    if len(txt) > 3000:
                        txt = txt[:3000] + " ... [truncated in transcript; full result in the JSON log]"
                    fh.write(f"<details><summary>Tool result</summary>\n\n```json\n{txt}\n```\n</details>\n\n")


def run(question: str, max_turns: int = 40, verbose: bool = True, tag: str = "agent") -> str:
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
            sess.dump_log(f"results/{tag}_tool_log.json")
            _transcript(f"results/{tag}_transcript.md", question, messages)
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
    sess.dump_log(f"results/{tag}_tool_log.json")
    _transcript(f"results/{tag}_transcript.md", question, messages)
    return "Stopped: turn limit reached."


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="*")
    ap.add_argument("--tag", default="agent")
    a = ap.parse_args()
    q = " ".join(a.question) or "Why is Ca3Ti2O7 ferroelectric? Start from the I4/mmm parent."
    print(run(q, tag=a.tag))
