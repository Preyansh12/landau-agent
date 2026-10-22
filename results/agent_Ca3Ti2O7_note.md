# Agent run on "Why is Ca3Ti2O7 ferroelectric?" (GPT-OSS-120B via Groq's free tier)

Outcome: a correct tool trajectory with no written answer. The model stopped at the turn cap (25) without a final message; GPT-OSS returns its reasoning in a separate field that the loop did not print, and the context budget needed for Groq's 8,000-token-per-minute limit (last 2 tool results kept) made it re-request results it had already seen.

What it decided and found (tool log `agent_Ca3Ti2O7_tool_log.json`):
- supercell 2x2x1 of the conventional cell (96 atoms), not the 48-atom cell suggested in the prompt;
- `rescale_parent(target_a=3.87)` on its own initiative, a -0.9 % volume change;
- order parameters chosen by standard label, `X3-` and `X2+` (the tilt and the rotation);
- `forced_couplings` returned the polar Γ5⁻ mode as forced by them (the hybrid-improper coupling);
- `fit_landau` RMSE 4.4 meV/f.u.; `enumerate_phases`: Pmc2₁ −883.3, Cmc2₁ −881.2 (the A2₁am basin), Pnma −844.8 meV/f.u.;
- two recoverable tool errors: it called `choose_order_parameters` before re-setting the supercell after rescaling, and `fit_landau` with no order parameters chosen.

Known loop limitations exposed by this run, fixed or to fix: print the `reasoning` field of models that use it; after `rescale_parent`, rebuild the supercell automatically; keep more, shorter tool results under a token budget.
