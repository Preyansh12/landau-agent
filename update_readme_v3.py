"""Rewrite the README scorecard from the result files (protocol v3) and insert the failure analysis.
Run after the v3 benchmark and polish pass are complete. Idempotent."""
import json, glob, re, subprocess

readme = open("README.md").read()
table = subprocess.run(["python3", "make_benchmark_table.py"], capture_output=True, text=True, check=True).stdout.strip()

# ---- tally for v3 from the table's last line
m = re.search(r"\*\*(\d+) / (\d+) / (\d+)\*\* \|\s*$", table)
hits, unres, miss = map(int, m.groups())

summary = f"""**In one paragraph.** Give LandauAgent a high-symmetry crystal and it works out *why* the crystal distorts: which atomic motions are unstable, which ones symmetry forces to move together, and which low-symmetry structure results. For example, starting from nothing but the undistorted Ca₃Ti₂O₇ structure, it discovers that two non-polar octahedral motions, a tilt and a rotation, lower the energy together only by dragging a polarisation along with them, the mechanism that makes the material ferroelectric. **On 13 materials with known ground states, the current protocol gets {hits} right, declares {unres} unresolved (competing phases within 1 meV/f.u., the experimental phase always inside the degenerate set), and gets {miss} wrong. It never states a wrong answer with confidence: every disagreement is one the tool flags itself.**"""

scorecard = f"""## Scorecard

Every protocol version is kept and shown; the table is generated from the result files by `make_benchmark_table.py`. "Known" is the experimental ground state (Sr₃Hf₂O₇: DFT). Energies are meV/f.u. below the parent, relaxed cell. ⚠️ means the tool itself declined to name a winner because phases lie within 1 meV/f.u.; the text says whether the known phase is in that set.

{table}

- **v1 → v2** fixed two enumeration bugs (incomplete direction set; refinement chosen at fixed lattice).
- **v2 (PBE) → v2 (r2SCAN)** swaps MACE-MP-0 for the r2SCAN-trained `mace-matpes-r2scan-0`, with no experimental input. The false ferroelectric instabilities of SrTiO₃ and CaTiO₃ disappear; BaTiO₃ acquires the textbook R3m → Amm2 → tetragonal ladder.
- **v3** relaxes every candidate briefly before ranking (CaTiO₃'s Pnma had been discarded on an overshot seed), gives all enumerated phases a free-cell relaxation (PbTiO₃'s P4mm lives on its c/a strain), and converges near-degenerate phases and the winner ten times tighter before reporting. See [Where the failures came from](#where-the-failures-came-from-and-what-fixed-them).
- The BaTiO₃ and SrTiO₃ "unresolved" entries have the experimental phase lowest; we still count them as unresolved because the tool's own rule does, and we prefer a consistent rule to a flattering one.
- The v2 (PBE) column is the result we submitted first; the r2SCAN columns were run after reviewer feedback, with the code committed before each run.
- The 8 Ruddlesden–Popper compounds include 6 that were out of sample (inputs committed before the run), one that stays undistorted (Sr₃Ti₂O₇) and one whose ground state is not A2₁am (Sr₃Ru₂O₇). Ca₃Mn₂O₇ under r2SCAN is discussed below.

"""

failure = open("/tmp/claude-0/-home-claude/b10400be-8889-5114-a5b9-406b4f9f7989/scratchpad/failure_section.md").read().strip() + "\n\n"

# replace paragraph + scorecard section
start = readme.index("**In one paragraph.**")
end = readme.index("## The mechanism, found from the parent alone")
readme = readme[:start] + summary + "\n\n" + scorecard + readme[end:]
# insert / replace failure section before "## How the LLM is used"
if "## Where the failures came from" in readme:
    a = readme.index("## Where the failures came from"); b = readme.index("## How the LLM is used")
    readme = readme[:a] + failure + readme[b:]
else:
    b = readme.index("## How the LLM is used")
    readme = readme[:b] + failure + readme[b:]
open("README.md", "w").write(readme)
print("README updated:", hits, unres, miss)
