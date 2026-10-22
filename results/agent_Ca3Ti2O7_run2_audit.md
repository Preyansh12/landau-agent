# Audit of agent run 2 on "Why is Ca3Ti2O7 ferroelectric?" (GPT-OSS-120B via Groq free tier)

Complete run: 8 tool calls, a written answer. The question named the supercell; everything else was the model's choice. Transcript `agent_Ca3Ti2O7_run2_transcript.md`, tool log `agent_Ca3Ti2O7_run2_tool_log.json`.

## Checked against the result files
| Claim | Check |
|---|---|
| X3⁻ −1.648, X2⁺ −1.296 eV/Å² | ✅ (`Ca3Ti2O7_log.json`: −1.6484, −1.2955) |
| polar Γ5⁻ forced by the trilinear coupling | ✅ tool output |
| Landau fit RMSE 4.4 meV/f.u.; minimum Pmn2₁, Landau −596 vs MACE −590 | ✅ tool output (4th-order fit) |
| relaxation −865 meV/f.u., Cmc2₁ (A2₁am) at 0.01 Å | ✅ identical to the scripted run (−865.16) |
| P ≈ (−9.8, −9.8, 0) μC/cm², nominal charges | ✅ consistent with the scripted 14.6 |
| λ not quoted: "implicit in forced-coupling output" | ✅ honest rather than invented |

## Faults
- Describes the supercell as "2 × 2 × 1"; it used [[1,1,0],[−1,1,0],[0,0,1]] (48 atoms).
- "The X-point tilts remain unstable after any reasonable volume rescaling" is not backed by a tool call in this run (no `rescale_parent`); it is true from our other results, but the model did not establish it.
- Skipped `enumerate_phases` and `refine_phases`, which the system prompt names as the phase prediction, and relied on the Landau minimum plus one symmetry-constrained relaxation. The relaxation landed on the correct basin, so the answer is right, but by a weaker route than instructed.
- Writes the trilinear term with a single polar amplitude S; the tool gives it with two polar components (`X⁻₁X⁺₁(P₁−P₂) + X⁻₂X⁺₂(P₁+P₂)`), a simplification rather than an error.
