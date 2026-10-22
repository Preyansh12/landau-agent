# Audit of the live agent run on "Is SrTiO₃ ferroelectric?"

Run: gemini-3.8-flash through the OpenAI-compatible backend, 22 Oct 2026. Complete run, 13 tool calls. Transcript: `agent_SrTiO3_transcript.md`; tool outputs: `agent_SrTiO3_tool_log.json`.
We checked the agent's final answer against the tool outputs and against independent scripted runs already in `results/`.

## What the model decided
1. It saw the polar Γ4⁻ instability at the MACE volume (−0.6365 eV/Å²).
2. The question does not mention volume. The model applied the system prompt's general volume-check rule, supplied the experimental lattice constant (3.905 Å) from its own knowledge, and called `rescale_parent`.
3. It kept **both** surviving tilts (R4⁺ and M3⁺) for the coupling check and the enumeration, then reduced to R4⁺ alone for the Landau fit.
4. It answered the question directly: not ferroelectric, with I4/mcm as the tilt ground state.

## Numbers checked
| Agent's claim | Source | Check |
|---|---|---|
| MACE parent a = 3.9429 Å; Γ4⁻ −0.6365 eV/Å² | tool log; `benchmark_v2_SrTiO3.json` | ✅ |
| Volume change −2.85 % | (3.905/3.9429)³ − 1 = −2.86 % | ✅ |
| At 3.905 Å: Γ4⁻ ≈ 0; R4⁺ −0.4193; M3⁺ −0.1526 eV/Å² | `SrTiO3_exp_tilts_log.json` (independent scripted run) | ✅ identical |
| Fixed cell: I4/mcm −6.95, Imma −6.99, R-3c −6.76 meV/f.u. | `SrTiO3_exp_enumeration_log.json` | ✅ identical |
| Relaxed cell: I4/mcm −32.03 meV/f.u. | same | ✅ |
| B₂ = 51.23 > 2B₁ = 49.47, favouring a single-axis tilt | tool log | ✅ arithmetic correct |

## Problems in the answer
- **Invented standard labels.** It names the secondary modes X5⁺, R5⁺, M2⁺ and M5⁺. The code attaches verified labels only to Γ4⁻, R4⁺ and M3⁺ for this parent, so these four labels did not come from a tool. That breaks the system prompt's rule against inventing labels. The underlying claim, that no forced secondary mode is polar, does come from the tool.
- **Overstated certainty about the tilt system.** It says the full relaxation "confirms" I4/mcm. The tool numbers put I4/mcm, Imma and R-3c within about 0.3 meV/f.u., and at fixed cell Imma is actually lowest. The system prompt asks the model to say the potential cannot decide in that case, and it did not. Its yes/no answer (not ferroelectric) is unaffected.
- The statement that SrTiO₃ is a quantum paraelectric is correct general knowledge, but it is not a tool result.
