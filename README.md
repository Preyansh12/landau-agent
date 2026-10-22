# LandauAgent

**From a high-symmetry crystal to its symmetry-allowed couplings, its instabilities and its low-symmetry phase. An LLM plans and explains; exact group theory and a universal ML potential (MACE-MP-0) do all the computing.**

Built for the Open Scientific Intelligence (OSI) Hackathon, 21–22 October 2026. Built with Claude as a coding assistant.

**In one paragraph.** Give LandauAgent a high-symmetry crystal and it works out *why* the crystal distorts: which atomic motions are unstable, which ones symmetry forces to move together, and which low-symmetry structure results. For example, starting from nothing but the undistorted Ca₃Ti₂O₇ structure, it discovers that two non-polar octahedral motions, a tilt and a rotation, lower the energy together only by dragging a polarisation along with them, the mechanism that makes the material ferroelectric. **On 13 materials with known ground states, the current protocol gets 7 right, declares 3 unresolved (competing phases within 1 meV/f.u., the experimental phase always inside the degenerate set), and gets 3 wrong. Each of the 3 wrong answers traces to a pipeline rule, not to the symmetry analysis, and each has a verified fix that is not yet rerun as a full protocol.**

## Scorecard

Every protocol version is kept and shown; the table is generated from the result files by `make_benchmark_table.py`. "Known" is the experimental ground state (Sr₃Hf₂O₇: DFT). Energies are meV/f.u. below the parent, relaxed cell. ⚠️ means the tool itself declined to name a winner because phases lie within 1 meV/f.u.; the text says whether the known phase is in that set.

| Material | Known | v1 (PBE) | v2 (PBE) | v2 (r2SCAN) | v3 (r2SCAN) |
|---|---|---|---|---|---|
| CaTiO3 | Pnma | ❌ Ima2 (46) (-262.73) | ❌ R3c (161) (-274.39) | ❌ Imma (74) (-225.28) | ✅ Pnma (62) (-271.24) |
| PbTiO3 | P4mm | ❌ Amm2 (38) (-100.71) | ✅ P4mm (99) (-189.66) | ❌ Amm2 (38) (-56.25) | ❌ Pm (6) (-73.78) |
| BaTiO3 | R3m | ❌ Pc (7) (-46.07) | ❌ Aem2 (39) (-40.47) | ⚠️ unresolved R3m (160) (-6.78); known state lowest but within 1 meV/f.u. of Amm2 (38) (+0.91) | ⚠️ unresolved R3m (160) (-6.82); known state lowest but within 1 meV/f.u. of Amm2 (38) (+0.94), Amm2 (38) (+0.94) |
| LaAlO3 | R-3c | ❌ Imma (74) (-27.21) | ❌ Imma (74) (-27.21) | ⚠️ unresolved Imma (74) (-10.89); known state within R-3c (167) (+0.08) | ⚠️ unresolved Imma (74) (-10.94); known state within R-3c (167) (+0.10) |
| SrTiO3 | I4/mcm | — | ❌ R3c (161) (-5.19) | ⚠️ unresolved R-3c (167) (-0.26); known state within I4/mcm (140) (+0.01) | ⚠️ unresolved I4/mcm (140) (-0.3); known state lowest but within 1 meV/f.u. of R-3c (167) (+0.01), Imma (74) (+0.01) |
| Ca3Ti2O7 | A2_1am | — | ✅ Cmc2_1 (36) (-882.32) | ⚠️ unresolved Cmc2_1 (36) (-677.36); known state lowest but within 1 meV/f.u. of Pmn2_1 (31) (+0.42) | ✅ Cmc2_1 (36) (-677.39) |
| Sr3Zr2O7 | A2_1am | ✅ Cmc2_1 (36) (-807.52) | ✅ Cmc2_1 (36) (-807.52) | — | ✅ Cmc2_1 (36) (-615.9) |
| Ca3Mn2O7 | A2_1am | — | ✅ Cmc2_1 (36) (-678.37) | — | ❌ Ccce (68) (-286.21) |
| Ca3Sn2O7 | A2_1am | — | ✅ Cmc2_1 (36) (-3099.05) | — | ✅ Cmc2_1 (36) (-2799.74) |
| Sr3Sn2O7 | A2_1am | — | ✅ Cmc2_1 (36) (-556.71) | — | ❌ Ccce (68) (-266.65) |
| Sr3Hf2O7 | A2_1am (DFT) | — | ✅ Cmc2_1 (36) (-453.13) | — | ✅ Cmc2_1 (36) (-351.88) |
| Sr3Ru2O7 | Bbcb | — | ✅ Ccce (68) (-268.72) | ✅ Ccce (68) (-36.65) | ✅ Ccce (68) (-36.75) |
| Sr3Ti2O7 | I4/mmm | — | ✅ no instability | — | ✅ no instability |
| **Tally (hit / unresolved / miss)** | | **1 / 0 / 4** | **9 / 0 / 4** | **1 / 4 / 2** | **7 / 3 / 3** |

- **v1 → v2** fixed two enumeration bugs (incomplete direction set; refinement chosen at fixed lattice).
- **v2 (PBE) → v2 (r2SCAN)** swaps MACE-MP-0 for the r2SCAN-trained `mace-matpes-r2scan-0`, with no experimental input. The false ferroelectric instabilities of SrTiO₃ and CaTiO₃ disappear; BaTiO₃ acquires the textbook R3m → Amm2 → tetragonal ladder.
- **v3** relaxes every candidate briefly before ranking (CaTiO₃'s Pnma had been discarded on an overshot seed), gives all enumerated phases a free-cell relaxation (PbTiO₃'s P4mm lives on its c/a strain), and converges near-degenerate phases and the winner ten times tighter before reporting. See [Where the failures came from](#where-the-failures-came-from-and-what-fixed-them).
- The BaTiO₃ and SrTiO₃ "unresolved" entries have the experimental phase lowest; we still count them as unresolved because the tool's own rule does, and we prefer a consistent rule to a flattering one.
- The v2 (PBE) column is the result we submitted first; the r2SCAN columns were run after reviewer feedback, with the code committed before each run.
- The 8 Ruddlesden–Popper compounds include 6 that were out of sample (inputs committed before the run), one that stays undistorted (Sr₃Ti₂O₇) and one whose ground state is not A2₁am (Sr₃Ru₂O₇). The three v3 misses (PbTiO₃'s Pm label, Ca₃Mn₂O₇ and Sr₃Sn₂O₇) are traced below.

## The mechanism, found from the parent alone

For Ca₃Ti₂O₇ the symmetry engine derives, with no input but the I4/mmm structure, the trilinear invariant `X3⁻ · X2⁺ · Γ5⁻` (tilt × rotation × polarisation), the coupling behind hybrid improper ferroelectricity. To test it directly, we contract the lattice so that the polar mode has no instability of its own (curvature −0.006 eV/Å²) and use **only tilt and rotation as order parameters**. The polar mode is free to appear wherever symmetry allows it:

| Phase | Tilt / rotation pattern | Energy vs I4/mmm (meV/f.u.) | Nominal P (μC/cm²) |
|---|---|---|---|
| **A2₁am** | same k-arm (trilinear term on) | **−933.2** | **9.5** |
| Pnma | different k-arms (trilinear term zero) | −891.8 | 0 |
| tilt only | | −655.3 | 0 |
| rotation only | | −427.8 | 0 |

The ground state is polar purely because of the coupling the engine found. (`results/Ca3Ti2O7_contracted_enumeration.json`)

## The agent

A tool-calling LLM decides what to compute: the supercell, which instabilities are real, which become order parameters, which forced modes to add, and when the potential cannot decide. It is forbidden from doing any group theory or quoting any number a tool did not return. It works with Anthropic models or any OpenAI-compatible endpoint, such as Gemini.

In a live run on **"Is SrTiO₃ ferroelectric?"** (Gemini Flash, [console log](results/agent_SrTiO3_console_partial.md)), the model found the polar instability at the MACE volume. The question did not mention volume. The system prompt carries only the general rule that polar instabilities from a PBE-trained potential should be volume-checked; the model applied it, supplied the experimental lattice constant (3.905 Å) from its own knowledge, and called `rescale_parent` "to test whether the polar instability is an artefact of the PBE volume overestimation". It then re-checked the instabilities and chose R4⁺ as the real order parameter. That run stopped on a provider overload error after 11 tool calls. An independent second run ([log](results/agent_SrTiO3_run2_console_partial.md)) made the same decision, this time naming "the polar Γ4⁻ instability" with the verified standard label, before the free-tier daily quota ran out. A third run completed: the model rescaled the lattice, kept both tilts (R4⁺, M3⁺), ran the coupling check, enumeration, refinement and Landau fit, and answered "not ferroelectric, I4/mcm". Every number in its answer matches the tool outputs and the independent scripted runs. We also audited it for errors and found two: it named four secondary modes with standard labels no tool produced, and it called I4/mcm "confirmed" although the tilt systems are within 0.3 meV/f.u. ([audit](results/agent_SrTiO3_audit.md), [console log](results/agent_SrTiO3_console_complete.md)).

## The problem

Explaining a structural phase transition means answering three questions:
- Which modes condense?
- Which couplings does symmetry allow?
- Is the transition continuous?

The standard route is Landau theory, which in practice is expert hand-work with group-theory tables (ISOTROPY/ISODISTORT, Bilbao) followed by expensive DFT to put numbers on the coefficients.

Language models alone are unreliable at exactly this algebra. Universal machine-learned interatomic potentials (MLIPs), on the other hand, now make frozen-mode energy surfaces nearly free. LandauAgent joins the two: every number is computed, and the language model chooses what to compute and explains what it means.

## What it does

Given a parent structure, LandauAgent:

1. **Builds the parent space group on a supercell** and splits the 3N displacement space into physically irreducible representations. This is numerical but exact: commutant diagonalisation, characters, k-stars from translation eigenphases, and inversion parity.
2. **Finds instabilities.** It computes MACE-MP-0 force constants, symmetrises them exactly, projects them onto every irrep block, and flags negative curvature as an instability.
3. **Finds forced secondary modes.** A mode that appears *linearly* in an invariant with the primary order parameters must condense with them, whether or not it is unstable on its own. This is how improper and hybrid-improper ferroelectricity is diagnosed.
4. **Generates the Landau polynomial.** It applies the Reynolds operator to all monomials and row-reduces in rational arithmetic, and checks the Landau condition (no cubic invariant). The representation matrices are computed numerically and rationalised; in the cleaned order-parameter bases their entries are exactly 0 and ±1, so the invariants are exact.
5. **Fits the coefficients** to MACE frozen-mode energies (meV per formula unit).
6. **Predicts the ground state, by direct enumeration.** It enumerates every symmetry-distinct order-parameter direction pattern, screens them with one MACE energy each, relaxes the best inside their own symmetry (fixed and relaxed lattice), and ranks them by energy.
7. **Explains it with the Landau model.** The fitted polynomial says *why* the winner wins: which couplings lower its energy and which mode is driven by which. The polynomial's own minimum is also relaxed with MACE as a cross-check, but for deep, anharmonic wells it is a worse predictor than the enumeration, so we use it for the mechanism, not the verdict.

It can also take an *observed* low-symmetry structure and decompose it into irreps (`analyze_child`).

## Showcases

The two showcases in detail:

| Material | Parent | Found instabilities | Forced coupling | Predicted phase | Literature |
|---|---|---|---|---|---|
| SrTiO₃ | Pm-3m | R⁺ and M⁺ tilts; a polar Γ⁻ mode **only at the MACE (PBE-like) volume** | — | at the MACE lattice: spurious polar Cc (−5.1 meV/f.u.); at the experimental lattice the polar instability vanishes and the three tilt systems are within 0.25 meV/f.u. of each other (not resolvable) | I4/mcm below 105 K, paraelectric to 0 K; semilocal DFT overestimates the tilt (PBEsol 5.7°) |
| Ca₃Ti₂O₇ | I4/mmm | X⁻ tilt and X⁺ rotation (O-dominated); also a weaker polar Γ⁻ instability in MACE | polar Γ⁻ via the trilinear invariant X⁻·X⁺·P | **Cmc2₁ = A2₁am**: −865.1 meV/f.u. (fixed lattice), −882.4 (relaxed lattice); X⁻ 1.75 Å, X⁺ 1.22 Å, Γ⁻ 0.85 Å; P ≈ 15 μC/cm² (nominal charges, fixed lattice) | A2₁am via X2⁺ ⊕ X3⁻ ⊕ Γ5⁻, P ≈ 20 μC/cm² (Benedek & Fennie 2011) |

### Ca₃Ti₂O₇ in detail: hybrid improper ferroelectricity from the parent alone

The only input is the I4/mmm parent (`results/Ca3Ti2O7_run.txt`, `Ca3Ti2O7_log.json`).

1. **Instabilities.** The strongest MACE instabilities are X-point octahedral modes: an X⁻ tilt (−1.65 eV/Å², O with some Ca) and an X⁺ rotation (−1.30 eV/Å², O only). The scripted run takes the softest mode of each type. A second, pure-O X⁻ mode (−1.37) is not included; the agent can choose it.
2. **Coupling.** The engine finds a polar Γ⁻ mode that appears **linearly** in one trilinear invariant with them:
   `X⁻₁·X⁺₁·(P₁ − P₂) + X⁻₂·X⁺₂·(P₁ + P₂)`
   Each k-arm's tilt × rotation product drives one in-plane polarisation direction. This is the coupling behind hybrid improper ferroelectricity. *Caveat and volume test:* at the MACE lattice the polar mode is weakly unstable on its own (−0.48 eV/Å²). Contracting the parent by 1.2% in a and 0.3% in c (`results/Ca3Ti2O7_exp_instabilities.json`, about the size of MACE's PBE-like overestimate) makes it essentially neutral (−0.006 eV/Å²), while the tilt (−1.77) and rotation (−1.52) strengthen. As in SrTiO₃, the polar instability is mostly a volume artefact of the potential; at the smaller volume the polarisation must come from the trilinear coupling.

   **Direct test of the hybrid-improper mechanism** (`results/Ca3Ti2O7_contracted_enumeration.json`). At this contracted lattice we enumerate phases with **only the X⁻ tilt and X⁺ rotation** as order parameters. The polar mode is not an order parameter, but every relaxation lets it develop if symmetry allows (fixed lattice, meV/f.u. vs I4/mmm):

   | Phase | Tilt / rotation pattern | Energy | Nominal P (μC/cm²) |
   |---|---|---|---|
   | **A2₁am (Cmc2₁)** | same k-arm | **−933.2** | **9.5** |
   | Pnma | different k-arms | −891.8 | 0 |
   | P4₂/mnm, Cmcm (tilt only) | | −655.3, −640.9 | 0 |
   | Cmce (rotation only) | | −427.8 | 0 |

   The polar mode has essentially no drive of its own here (−0.006 eV/Å²), yet the ground state carries 9.5 μC/cm². When tilt and rotation sit on different arms the trilinear term vanishes; that phase (Pnma) is non-polar and loses by 41 meV/f.u. This is the textbook hybrid-improper mechanism, reproduced end to end.
3. **Landau prediction.** The fitted model has 6th order in each mode and couplings to 4th. Its RMSE is 14 meV/f.u. over all sampled configurations below the parent, but **31 meV/f.u. over the lowest-energy half of the samples**, the region that matters for the ground state (lowest sample −540 meV/f.u.; both numbers in `Ca3Ti2O7_log.json`). Its minimum is a Pmn2₁ point at −633 meV/f.u. (MACE gives −590 there). Relaxing that structure with MACE gives −865.16 meV/f.u.: Pmn2₁ at 0.001 Å tolerance, **Cmc2₁ (A2₁am) at 0.01 Å**, with residual second-arm tilt 0.009 Å (`Ca3Ti2O7_decompositions.json`). So the fitted polynomial gets into the right basin but does not pin the exact minimum; the deep, strongly anharmonic coupled wells need the MACE relaxation.
4. **Independent check: direct enumeration.** Every symmetry-distinct tilt/rotation pattern is relaxed with MACE inside its own symmetry (meV/f.u. vs I4/mmm; † = loose relaxation only):

| Phase | Fixed lattice | Relaxed lattice | Nominal P, fixed lattice (μC/cm²) |
|---|---|---|---|
| Cmc2₁ (A2₁am) | −865.1 | −882.4 | 14.6 |
| Pmc2₁* | −865.0 | −882.4 | 14.2 |
| Pnma | −831.9 | −842.1 | 0 |
| Pmn2₁ † | −720.1 | | 1.1 |
| P4₂/mnm (tilt only) † | −632.2 | | 0 |
| Cmcm (tilt only) † | −604.4 | | 0 |
| Cmce (rotation only) † | −332.6 | | 0 |
| P4/mbm (rotation only) † | −159.1 | | 0 |

\*The relaxed Pmc2₁ structure has the same mode amplitudes as A2₁am (X⁻ 1.74, X⁺ 1.22, Γ⁻ 0.85 Å). Only 0.0005 Å of second-arm rotation and 0.04 Å of a Z⁻ mode remain (`Ca3Ti2O7_decompositions.json`). It is A2₁am held at a lower imposed symmetry, not a separate phase.

At fixed lattice, the polar phase is more than 230 meV/f.u. below any tilt-only or rotation-only phase.

![Ca3Ti2O7 phase ladder](results/phase_ladder_Ca3Ti2O7.png)

### SrTiO₃: catching a known failure of the potential

At its own relaxed lattice (a = 3.943 Å, about 1% larger than experiment, as expected for a PBE-trained model), MACE-MP-0 finds three instabilities in cubic SrTiO₃: a polar Γ⁻ mode (−0.64 eV/Å²), the R⁺ octahedral tilt (−0.28) and a weak M⁺ tilt (−0.04). Enumeration then gives a polar ground state (Cc, close to R3c, −5.1 meV/f.u.) just below the experimental tetragonal phase I4/mcm (−3.5 meV/f.u.).

Real SrTiO₃ is not ferroelectric, so this prediction is wrong. LandauAgent can test why. Recomputing the instabilities at the **experimental** lattice constant (3.905 Å):

| Mode | Curvature at MACE lattice (eV/Å²) | Curvature at experimental lattice (eV/Å²) |
|---|---|---|
| Γ⁻ polar | −0.64 | **0.00** (only the acoustic translation remains) |
| R⁺ tilt (O only) | −0.28 | −0.42 |
| M⁺ tilt (O only) | −0.04 | −0.15 |

The ferroelectric instability is a volume artefact of the potential, while the tilts are robust. At the experimental lattice the tilt-only enumeration gives (meV/f.u. vs cubic):

| Tilt system | Fixed cubic lattice | Relaxed lattice |
|---|---|---|
| **I4/mcm (a⁰a⁰c⁻)** | −6.95 | **−32.03** |
| Imma (a⁰b⁻b⁻) | −6.99 | −31.77 |
| R-3c (a⁻a⁻a⁻) | −6.76 | −31.62 |

At the fixed experimental lattice the three tilt systems lie within 0.25 meV/f.u. of each other, below what we would trust MACE to resolve. In the "relaxed lattice" column the cell is free, so it expands back towards the MACE volume (a ≈ 3.93–3.95 Å). Most of the extra ~25 meV/f.u. is that volume relaxation, not tilt–strain coupling. I4/mcm comes out lowest there (Pmmn relaxes to the same energy), but the margins are a few tenths of a meV/f.u. **The honest conclusion: MACE reproduces the tilt instability and its R4⁺ symmetry, but cannot decide between the tilt systems of SrTiO₃.**

The R⁺ invariants the engine derives (η², Σηᵢ⁴, Σηᵢ²ηⱼ², no cubic term) are the textbook R4⁺ expansion. In the Landau fit at the MACE lattice (`results/SrTiO3_log.json`), the cross-quartic coefficient (48.28 meV/f.u. per Å⁴) is only marginally larger than twice the single quartic (2 × 23.65), which at quartic order is the condition that favours a single-axis tilt. The fit also has small 6th-order terms. This marginality is the same near-degeneracy seen in the enumeration.

## Benchmark (protocol v2, PBE potential): seven materials with known ground states

The same automated protocol on every material (`run_benchmark.py`): the MACE-relaxed parent, up to three distinct unstable irreps as primaries, symmetry-complete enumeration, then the four lowest candidates re-relaxed with a free cell (fmax 0.01 eV/Å). The winner is the lowest relaxed-cell energy. Space groups are reported at the strict tolerance and at 0.01 Å. **No volume correction is applied here**, so this is what the potential gives without the agent's volume check.

v1 is our first protocol. Its misses exposed two bugs in the pipeline, both fixed in v2: the enumeration directions were not symmetry-complete (Pnma could never be generated), and candidates were picked for refinement by fixed-lattice energy (strain-favoured phases such as P4mm were never refined). v1 results are kept in `results/benchmark_*.json`, v2 in `results/benchmark_v2_*.json`.

| Material | Known ground state | v1 winner | v2 winner (strict / 0.01 Å) | v2 energy (meV/f.u.) | v2 verdict |
|---|---|---|---|---|---|
| Ca₃Ti₂O₇ | A2₁am (Cmc2₁) | Cmc2₁ | Cm / **Cmc2₁** | −882.3 | **hit** |
| Sr₃Zr₂O₇ | A2₁am (Cmc2₁) | Cmc2₁ | Pm / **Cmc2₁** | −807.5 | **hit** |
| PbTiO₃ | P4mm | Amm2 | P4bm / **P4mm** | −189.7 | **hit** (v1 miss) |
| LaAlO₃ | R-3c | Imma | Imma | −27.21 (R-3c −26.92) | near miss, 0.3 meV/f.u. |
| BaTiO₃ | R3m | Pc | Aem2 | −40.47 (I4cm −40.36, P4bm −40.14) | miss |
| CaTiO₃ | Pnma | Ima2 | R3c | −274.4 (Imma −262.2, R-3c −246.7) | miss |
| SrTiO₃ | I4/mcm | Cc | R3c | −5.19 | miss (fixed by volume check, see above) |

**3 hits and 1 near miss out of 7**, up from 2 in v1. In the two strict-tolerance labels (Cm, Pm) the residual distortion beyond Cmc2₁ is below 0.01 Å.

What the misses say:
- **CaTiO₃ and SrTiO₃ are polar artefacts of the PBE-like volume.** At the MACE lattice both have a strong polar Γ⁻ instability (−1.35 and −0.64 eV/Å²), and the polar phase wins. For SrTiO₃ we showed that the instability disappears at the experimental lattice. This is exactly the failure the agent's `rescale_parent` check is there to catch; the benchmark deliberately runs without it.
- **BaTiO₃** has three nearly degenerate polar or antipolar instabilities in MACE (Γ⁻ −4.83, X⁻ −4.48, M⁻ −4.41 eV/Å²), and the top three phases lie within 0.3 meV/f.u. The potential gives no usable ranking.
- **LaAlO₃** has the right instability (R⁺ dominates), and R-3c is among the four refined candidates, but Imma is 0.3 meV/f.u. lower. Like the SrTiO₃ tilt systems, this is below MACE's resolution.

The pattern is useful in its own right: where the physics is driven by large, strongly coupled oxygen-octahedron modes (the layered hybrid-improper compounds, PbTiO₃'s large polar distortion), the pipeline gets the ground state. Where the answer depends on sub-meV differences or on the equilibrium volume, it fails, and the tool output (near-degenerate energies, a polar mode that is volume-sensitive) shows that it is in that regime.

## Out-of-sample test (protocol v2, PBE potential): six compounds the pipeline never saw

After the benchmark, we froze the protocol (commit `766821e`). We ran it on five n=2 Ruddlesden–Popper compounds that were never used while developing or fixing the pipeline. The predictions were committed (`results/out_of_sample_predictions.md`, commit `10bcd67`) **before** we checked them against the literature. We chose the materials ourselves, and we knew the general picture for some of them. What is pre-registered is the pipeline output, which was not tuned to them.

| Material | Predicted (strict / 0.01 Å) | ΔE vs I4/mmm (meV/f.u.) | Runner-up | Literature | Verdict |
|---|---|---|---|---|---|
| Sr₃Ti₂O₇ | **I4/mmm**, no instability below −0.005 eV/Å² | 0 | — | I4/mmm, undistorted | **hit** (negative control) |
| Ca₃Mn₂O₇ | Cm / **Cmc2₁** | −678.4 | Pnma −662.8 | polar A2₁am ground state, then Acaa and I4/mmm on heating (arXiv:1803.03957) | **hit** |
| Ca₃Sn₂O₇ | Cm / **Cmc2₁** | −3099 † (parent far from stable; not a transition energy) | Aem2 −2683 | polar; T_C of (Sr,Ca)₃Sn₂O₇ rises to about 800 K with Ca content (Yoshida et al. 2018) | **hit** |
| Sr₃Sn₂O₇ | **Cmc2₁** | −556.7 | Pnma −550.2 | A2₁am ground state, T_C ≈ 410 K, Pnab above (Yoshida et al. 2018; Acta Cryst. B 2025) | **hit** |
| Sr₃Hf₂O₇ | **Cmc2₁** | −453.1 | Pnma −441.2 | Cmc2₁ ground state from PBEsol DFT; no experimental structure found (Pressure-induced phase transformations of Sr₃Hf₂O₇, 2023) | agrees with DFT |
| Sr₃Ru₂O₇ (added after review, inputs committed in `ebf1862` before the run) | Aea2 / **Ccce** | −268.7 | Ccce seed −268.7, P-4b2 −257.6, Cmce −246.6 | Bbcb (No. 68 = Ccce): RuO₆ rotations of about 7–8°, no tilt (arXiv:1003.5221 reports rotation only; Bbcb is the usual orthorhombic assignment) | **hit** ‡ |

Cmc2₁ is the standard setting of A2₁am.

Notes:
- **Ca₃Sn₂O₇:** the −3.1 eV/f.u. is measured from an I4/mmm parent that is far from stable for this composition (small Ca on a large Sn–O framework). Its leading curvatures are about twice those of the other compounds. The phase is the prediction; that energy is not a physical transition energy.
- **Ca₃Mn₂O₇:** MACE is used without spin, so magnetism is ignored.
- **Close runner-ups:** in all four polar compounds the runner-up is the non-polar Pnma, 6–16 meV/f.u. higher. That fits the real phase diagrams, where non-polar orthorhombic phases (Acaa, Pnab) follow the polar phase on heating.

Sr₃Ru₂O₇ answers the obvious objection that the pipeline simply returns A2₁am for every n=2 compound with a tilt and a rotation. Its two rotation instabilities (same sense −0.85 eV/Å², opposite sense −0.90 eV/Å², identified by pattern projection) compete, and the pipeline picks the opposite-sense rotation, Ccce = Bbcb, the observed space group. The same-sense rotation phase Cmce (No. 64) is 22 meV/f.u. higher.

*Robustness check (not part of the frozen protocol).* The protocol keeps one irrep per short name, so the X3⁻ tilt (−0.84 eV/Å²) was not offered as an order parameter. Rerun with both rotations **and** the tilt (`run_sro_tilt_check.py`, `results/Sr3Ru2O7_with_tilt.json`, relaxed cell):

| Phase | Energy (meV/f.u.) |
|---|---|
| **Ccce (= Bbcb), rotation only** | **−268.68** |
| P2₁/c | −268.35 |
| Pmn2₁ seed → A2₁am (Cmc2₁ at 0.01 Å) | −253.91 |
| Cmce, same-sense rotation | −246.58 |

The hybrid-improper A2₁am state is available and loses by 15 meV/f.u., so the pipeline's answer is not built in. P2₁/c, a lower-symmetry phase, is only 0.33 meV/f.u. above Ccce, below what we trust MACE to resolve.

Under protocol v2 with the PBE-trained potential this gave 9 of 13 right, all 8 Ruddlesden–Popper compounds among them, with all four failures cubic perovskites. The [Scorecard](#scorecard) at the top shows how that changed once the failures were traced and the protocol and potential were revised.

## Where the failures came from, and what fixed them

Four of the five cubic perovskites were wrong under protocol v2. Rather than report them as "MACE's fault" we traced each one. Every change below was committed before the run that tested it, and every protocol version's results are kept.

**1. The potential's volume (SrTiO₃, BaTiO₃, LaAlO₃, partly CaTiO₃).** MACE-MP-0 is trained on PBE data and inherits PBE's 1–2 % overestimate of lattice constants, which is known to create or exaggerate polar instabilities in titanates; universal MLIPs trained on near-equilibrium data also systematically soften the energy surface (Deng et al., npj Comput. Mater. 2025). We swapped in `mace-matpes-r2scan-0`, trained on r2SCAN data with off-equilibrium sampling (MatPES, Kaplan et al. 2025). No experimental input is used. Its cubic lattice constants come out at 3.900 Å for SrTiO₃ (experiment 3.905; MACE-MP-0 gives 3.943).
- SrTiO₃: the false ferroelectric instability disappears; only the R4⁺ tilt remains.
- BaTiO₃: wrong → **R3m**, then Amm2 (+0.9 meV/f.u.), then tetragonal: the experimental phase sequence, with the R–O gap DFT also gives.
- LaAlO₃: R-3c moves to within 0.08 meV/f.u. of the winner.

**2. Our screening (CaTiO₃).** The enumeration scored every candidate with one energy evaluation at its seed amplitude. A seed that superposes two modes at their individual well amplitudes (Pnma = R4⁺ tilt + M3⁺ rotation) overshoots: Pnma's seed scored −112 meV/f.u. and was discarded, while fully relaxed it is −271 meV/f.u., **46 meV/f.u. below** the Imma phase that won. The correct answer was generated and thrown away. v3 relaxes every candidate for 25 symmetry-constrained steps before ranking.

**3. Our refinement cut and convergence (PbTiO₃ under r2SCAN).** Only the best 4 of 6 fixed-lattice candidates got a free-cell relaxation. PbTiO₃'s tetragonal phase lives on its c/a strain: P4mm is 6th at the cubic lattice and the best phase once the cell is free (−73.8 vs −56.3 meV/f.u. for the phase that had won). v3 refines all enumerated candidates with a free cell. The v3 run then reports PbTiO₃ as **Pm**, which is P4mm with a residual tilt that the 800-step cap had not relaxed away (same c/a ≈ 1.11, energy within 0.06 meV/f.u.); continuing that relaxation to fmax = 0.001 eV/Å gives P4mm at every tolerance, −73.84 meV/f.u. (`results/diag_pto_polish.log`). The v3 table keeps the Pm label as run and counts it as a miss; "always converge the reported winner to fmax = 0.001" is the third v4 change.

**4. Real degeneracy (SrTiO₃ tilt system, LaAlO₃).** Where phases lie within a few tenths of a meV/f.u., `refine_phases` now re-relaxes just those phases ten times tighter and, if they stay degenerate, returns an explicit **UNRESOLVED** verdict instead of a winner. For SrTiO₃ the three tilt systems stay within 0.01 meV/f.u. at fmax = 0.005 eV/Å; this is below the resolution of DFT itself at this energy scale, so "unresolved" is the correct answer.

**5. Our order-parameter selection (Ca₃Mn₂O₇ and Sr₃Sn₂O₇ under r2SCAN).** The benchmark protocol keeps one unstable irrep per short name ("X⁻", "X⁺"). Under the r2SCAN model the opposite-sense rotation (X⁻, −1.19 eV/Å²) edges out the X3⁻ tilt (−1.17) for the X⁻ slot, so the tilt was never offered and the hybrid-improper A2₁am phase was never enumerated; the pipeline returned Ccce, which is this material's *intermediate* paraelectric phase (Acaa, stable above 310 K). Offering the three softest distinct irreps instead (`run_all_irreps_check.py`, `results/all_irreps_matpes_r2scan_0_Ca3Mn2O7.json`) gives **A2₁am at −335.6 meV/f.u., 49 meV/f.u. below Ccce**, clearly resolved. The same check on Sr₃Ru₂O₇ (PBE model) left Ccce the winner with A2₁am 15 meV/f.u. higher, so selecting by distinct irrep fixes Ca₃Mn₂O₇ without breaking the one compound that really is rotation-only. Sr₃Sn₂O₇ shows the same pattern under r2SCAN (rotation −0.97 vs tilt −0.89 eV/Å²); with the three softest distinct irreps it gives A2₁am at −312.7 meV/f.u., resolved (`results/all_irreps_matpes_r2scan_0_Sr3Sn2O7.json`). This is a protocol v4 change we have identified but not rerun across all materials before the deadline; the v3 table reports both as misses.

**v4 preview.** The three v3 misses, each rerun with only the identified fix applied (files cited above):

| Material | v3 as run | with the identified fix | Known |
|---|---|---|---|
| PbTiO₃ | Pm, −73.78 | **P4mm**, −73.84 (winner converged to fmax 0.001) | P4mm ✅ |
| Ca₃Mn₂O₇ | Ccce, −286.2 | **A2₁am**, −335.6, resolved (distinct-irrep selection) | A2₁am ✅ |
| Sr₃Sn₂O₇ | Ccce, −266.7 | **A2₁am**, −312.7, resolved (distinct-irrep selection) | A2₁am ✅ |

These are not counted in the scorecard, because they were not run as one uniform protocol over all 13 materials.

The honest summary: every disagreement we traced was either our pipeline (screening, refinement cut, winner convergence, order-parameter selection) or the potential's PBE volume, each fixed or identified with a verified rerun, or a sub-meV degeneracy that the tool now declares rather than guesses. None was a failure of the symmetry analysis. Three wrong answers remain in the protocol as run; each has a verified fix listed above.

## How the LLM is used, and how it isn't

The agent (`landau_agent/agent.py`) is a tool-calling loop. The model picks the supercell, decides which instabilities to treat as order parameters, adds forced secondary modes, and writes the physical interpretation.

The system prompt forbids it from deriving irreps, invariants, couplings, energies or space groups itself. Those come only from tools. Irrep names are computed (k-point, inversion parity, dimension, polarity, which atoms move). The model may state a textbook correspondence only when that output makes it unambiguous.

## Computed labels vs standard (ISOTROPY/Bilbao) labels

LandauAgent labels irreps by what it computes: k-point, inversion parity (about the parent origin), dimension and an index, plus polarity and which atoms move. The index (`#n`) depends on numerical ordering and can change with the lattice constant, so on its own it is not a usable name.

Standard labels are attached **by the code, and verified**, not looked up (`landau_agent/labels.py`). For each standard label the code builds the textbook rigid-octahedron pattern directly in the supercell (for example R4⁺: BO₆ octahedra rotating about one cubic axis, out of phase between neighbours, B at the origin). It then projects that pattern onto every computed irrep. The label is attached only to an irrep that contains more than 90% of the pattern; in practice the match is 100.0%, and every other irrep gets 0%. Polar Γ irreps are unique for their dimension in both parent point groups, so their labels follow from polarity and dimension. Tools return the result as `standard_label`, and the agent may use only labels a tool returned. Tested in `tests/test_symmetry.py`.

| Parent (origin) | Computed | Verified standard label | Pattern |
|---|---|---|---|
| Pm-3m (B at origin) | Γ⁻ (d=3), polar | Γ4⁻ | polar B against O |
| | R⁺ (d=3) | R4⁺ | out-of-phase octahedral rotation (a⁰a⁰c⁻) |
| | M⁺ (d=3) | M3⁺ | in-phase octahedral rotation (a⁰a⁰c⁺) |
| I4/mmm, n=2 RP (bilayer at origin) | X⁺ (d=2) | X2⁺ | octahedral rotation about c |
| | X⁻ (d=2) | X3⁻ | octahedral tilt about the in-plane axis along k, the two layers of a bilayer in opposite sense |
| | Γ⁻ (d=2), polar | Γ5⁻ | in-plane polarisation |
| | Γ⁻ (d=1), polar | Γ3⁻ (A2u) | polarisation along c |

At X = (½,½,0) the tilts about [110] and [1̄10] fall into **two different irreps**. Geometry alone does not say which one ISOTROPY calls X3⁻. We fixed it with one external fact: A2₁am is X2⁺ ⊕ X3⁻ ⊕ Γ5⁻ (Benedek & Fennie 2011). Decomposing our relaxed A2₁am Ca₃Ti₂O₇ puts the whole tilt (1.75 Å) in the irrep whose tilt axis lies along k. Other unstable irreps with the same short name (for example the second X⁻ instability of Ca₃Ti₂O₇) get no standard label; we have not mapped them.

## Provenance of the results

All benchmark and showcase numbers come from the **scripted pipeline** (`run_case.py`, `run_enumerate.py`, `run_sto_tilts.py`, `run_decompose.py`, `run_benchmark.py`), which calls exactly the same tools the agent uses. This keeps the numbers reproducible without an API key and independent of the LLM. Live agent runs (see [The agent](#the-agent)) use the same tools, and their transcripts are kept in `results/`. The tool layer is tested against the agent's tool schema (`tests/test_agent_tools.py`). Raw outputs, logs and structures are in `results/`.

## Related work and what is new here

Each ingredient exists on its own; the combination, as far as our literature search found (SciSpace and web search, October 2026), does not.
- **Group theory for phase transitions:** ISOTROPY (INVARIANTS, COPL), the Bilbao server, and spgrep (on-the-fly space-group irreps) are mature. Our symmetry engine is a re-implementation, not a new method.
- **Landau models fitted to data:** recent work learns Landau potentials by regression over *predefined* invariants for PbTiO₃ (arXiv:2507.23369), or fits a neural network, without symmetry invariants, to universal-MLIP energies for HfO₂ (arXiv:2512.16207). Neither generates the invariants or finds couplings automatically.
- **Universal MLIPs and instabilities:** VibroML (arXiv:2604.27685) repairs dynamical instabilities with foundation MLIPs using a genetic algorithm, without irreps or Landau theory.
- **LLM agents for atomistic simulation:** El Agente Sólido (Quantum ESPRESSO, phonons, MLIPs), AtomisticSkills, Catalyst-Agent and an agentic LAMMPS workflow (arXiv:2607.22596) orchestrate simulations, but none performs symmetry-mode or Landau analysis of phase transitions. The closest in spirit is PTagent (arXiv:2610.21118), an LLM agent for building finite-temperature models of *cosmological* phase transitions, where the LLM likewise organises and the tools compute.

**What we did not find elsewhere:** a tool-using agent that goes from a parent crystal alone to (i) exact symmetry-allowed invariants, (ii) automatic discovery of forced (improper or hybrid-improper) couplings, (iii) universal-MLIP energetics for a symmetry-complete set of candidate phases, and (iv) an explicit check for artefacts of the potential's volume. We also found no prior pre-registered test of such a pipeline on materials it was not developed on. Absence of evidence is not proof: very recent preprints may be missing from the indexes.

## Install and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install torch mace-torch ase pymatgen spglib sympy scipy anthropic
python run_case.py SrTiO3            # scripted pipeline, no LLM needed
python run_case.py Ca3Ti2O7
export ANTHROPIC_API_KEY=...         # agent mode (Anthropic, default)
python -m landau_agent.agent "Why is Ca3Ti2O7 ferroelectric? Start from the I4/mmm parent."

# or any OpenAI-compatible endpoint, e.g. the free Gemini tier
pip install openai
export LANDAU_AGENT_PROVIDER=gemini GEMINI_API_KEY=... LANDAU_AGENT_MODEL=<Gemini model id>
./run_agent_demo.sh                  # SrTiO3 + Ca3Ti2O7, writes results/agent_*_transcript.md
```

The agent loop is backend-neutral: the same tools, system prompt and transcript writer serve both providers (`tests/test_agent_loop.py` checks both paths with fake clients). Everything except the LLM calls runs on a CPU.

A GPU is optional. On two CPU cores each scripted case takes about 5–10 minutes, and the phase enumeration with tight refinement 10–40 minutes. Force constants are cached in `results/`.

## Limitations

- 0 K frozen-mode energies; no temperature, so no transition temperatures (yet).
- The Landau fit uses the fixed parent lattice: strain coupling is not in the polynomial. Strain enters only through the final MACE cell relaxations, which also move towards the MACE equilibrium volume.
- MACE-MP-0 is PBE-trained, so energy scales inherit PBE errors (e.g. overestimated tilts).
- Only k-points commensurate with the chosen supercell are visible.
- Polarisation uses nominal ionic charges, not Born effective charges, so it is an estimate.
- Standard (ISOTROPY) labels are attached and verified only for the irreps in the table above; other irreps keep computed descriptors.
- Phase enumeration uses all {−1,0,1} direction patterns for order parameters of dimension ≤ 3 (symmetry-complete there), but only axes and pairs above that. It is not a full isotropy-subgroup enumeration.
- The Reynolds averaging is over dense monomials, so several 3-dimensional order parameters at 6th order become slow.

## References

- N. A. Benedek and C. J. Fennie, *Hybrid improper ferroelectricity*, Phys. Rev. Lett. 106, 107204 (2011). [arXiv:1007.1003](https://arxiv.org/abs/1007.1003)
- I. Batatia et al., MACE-MP-0 foundation model (2023).
- H. T. Stokes, D. M. Hatch, H. M. Nelson, *Landau, Lifshitz, and weak Lifshitz conditions*, Phys. Rev. B 47, 9080 (1993).
- C. Capillas et al., *SYMMODES*, J. Appl. Cryst. 36, 953 (2003).
- S. Yoshida et al., *Hybrid improper ferroelectricity in (Sr,Ca)₃Sn₂O₇ and beyond*, J. Am. Chem. Soc. 140, 15690 (2018). [record](https://research-portal.st-andrews.ac.uk/en/publications/hybrid-improper-ferroelectricity-in-srcasub3subsnsub2subosub7sub-/)
- *Revealing pressure-driven structural transitions in the hybrid improper ferroelectric Sr₃Sn₂O₇*, Acta Cryst. B 81 (2025). [link](https://journals.iucr.org/b/issues/2025/03/00/yh5041/)
- *Soft tilt and rotational modes in the hybrid improper ferroelectric Ca₃Mn₂O₇*. [arXiv:1803.03957](https://arxiv.org/abs/1803.03957)
- spgrep: on-the-fly generator of space-group irreps, [JOSS](https://joss.theoj.org/papers/10.21105/joss.05269)
- D. M. Hatch and H. T. Stokes, *INVARIANTS*, J. Appl. Cryst. (2003), doi:10.1107/S0021889803005946.
- *Pressure-induced phase transformations of quasi-2D Sr₃Hf₂O₇*, J. Phys. Chem. C (2023). [arXiv:2306.04624](https://arxiv.org/abs/2306.04624)
