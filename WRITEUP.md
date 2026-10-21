# LandauAgent: from a crystal to its Landau theory, with an LLM that never does the group theory

## What we built

LandauAgent turns a high-symmetry crystal structure into a quantitative Landau theory of its structural phase transitions, then predicts and checks the low-symmetry phase.

It is a toolset with an agent on top:

- **Symmetry engine (no LLM, no lookup tables).** It builds the parent space group acting on a commensurate supercell and splits atomic displacements into physically irreducible representations. Each irrep is labelled by k-point (k-stars from translation eigenphases, including centring translations), inversion parity, dimension, polarity and which atoms move. Every order-parameter basis is rotated until its representation matrices are signed permutations. Symmetry-allowed Landau invariants then come from the Reynolds operator with rational row reduction, and the Landau condition (no cubic invariant) is checked automatically.
- **Energies from a universal MLIP (MACE-MP-0).** Symmetrised force constants give the harmonic curvature of every irrep block, which finds the instabilities. Adaptive frozen-mode scans and a weighted least-squares fit give the Landau coefficients (6th order per mode, couplings to 4th).
- **Coupling discovery.** A mode that appears *linearly* in an invariant with the unstable modes must condense with them. This is the signature of improper and hybrid-improper ferroelectricity, and the engine finds it from symmetry alone.
- **Two independent phase predictions.**
  1. Minimise the fitted Landau model, confined to the sampled region and checked against MACE, then relax the result with MACE.
  2. Enumerate every symmetry-distinct order-parameter direction pattern, relax each with MACE inside its own symmetry, and rank by energy.
- **Volume check.** PBE-trained potentials overestimate lattice constants. A tool rescales the parent to a known lattice constant to test whether an instability is real or a volume artefact.
- **Agent.** A tool-calling LLM picks supercells and order parameters, adds forced secondary modes, runs the checks and writes the physical explanation. Its system prompt forbids deriving irreps, invariants, couplings, energies or space groups itself; every number must come from a tool, and tool errors are passed back to it.

The benchmark and showcase numbers below come from a scripted pipeline that calls the same tools as the agent, so they are reproducible without an API key. In a live run on "Is SrTiO₃ ferroelectric?" (Gemini Flash), the model applied the volume-check rule on its own initiative for this question. It supplied the experimental lattice constant from its own knowledge, called `rescale_parent`, saw the polar instability vanish, and chose the R4⁺ tilt as the real order parameter (`results/agent_SrTiO3_console_partial.md`).

## Results

**Ca₃Ti₂O₇ (hybrid improper ferroelectric), from the I4/mmm parent alone.**
- **Instabilities.** The strongest MACE instabilities are an X-point octahedral tilt (X⁻, −1.65 eV/Å²) and rotation (X⁺, −1.30 eV/Å²).
- **Coupling.** The engine finds that a polar Γ⁻ mode appears linearly in one trilinear invariant: `X⁻₁·X⁺₁·(P₁ − P₂) + X⁻₂·X⁺₂·(P₁ + P₂)`. Each k-arm's tilt × rotation product drives an in-plane polarisation, the coupling behind hybrid improper ferroelectricity, derived rather than assumed. At the MACE lattice the polar mode is also weakly unstable on its own (−0.48 eV/Å²), but contracting the parent by about 1% (the size of MACE's PBE-like overestimate) makes it essentially neutral (−0.006). At that volume, with **only tilt and rotation as order parameters**, the A2₁am ground state still develops 9.5 μC/cm² (nominal charges) and beats the non-polar Pnma, where the trilinear term vanishes, by 41 meV/f.u.: the polarisation is driven purely by the coupling.
- **Direct enumeration.** It gives **Cmc2₁ = A2₁am**, the known ground state:
  - 865 meV/f.u. below I4/mmm at fixed lattice, 882 meV/f.u. with a relaxed lattice.
  - Mode amplitudes: X⁻ 1.75 Å, X⁺ 1.22 Å, Γ⁻ 0.85 Å.
  - Nominal-charge polarisation about 15 μC/cm², against about 20 μC/cm² from DFT with Born charges.
  - Every tilt-only or rotation-only phase is more than 230 meV/f.u. higher.
- **Landau model.** Its minimum (a Pmn2₁ point) lies in the same basin. Relaxing it with MACE converges to the A2₁am energy (−865.16 meV/f.u., Cmc2₁ at 0.01 Å tolerance). The polynomial explains the mechanism, but by itself it does not pin the exact minimum of these deep, anharmonic coupled wells.

**SrTiO₃: catching a failure of the potential.**
- At its own (PBE-like, +1%) lattice, MACE finds a polar instability and predicts a ferroelectric ground state. That's wrong: SrTiO₃ stays paraelectric.
- At the experimental lattice constant the polar instability vanishes entirely, while the R⁺ and M⁺ oxygen tilts strengthen (R⁺ −0.28 → −0.42 eV/Å²).
- The engine derives the textbook R4⁺ invariants. However, the three tilt systems (I4/mcm, Imma, R-3c) lie within 0.25 meV/f.u. of each other at the experimental lattice. MACE reproduces the tilt instability but cannot resolve which tilt system wins.

**Benchmark: seven perovskite-family materials with known ground states**, same automated protocol, no volume correction.
- **Hits (3):** Ca₃Ti₂O₇ and Sr₃Zr₂O₇ (A2₁am), PbTiO₃ (P4mm, at 0.01 Å tolerance).
- **Near miss (1):** LaAlO₃: Imma beats the correct R-3c by 0.3 meV/f.u., below MACE's resolution.
- **Misses (3):** CaTiO₃ and SrTiO₃ go polar (R3c) because of the PBE-like volume, the artefact the agent's volume check exists for. BaTiO₃ has three phases within 0.3 meV/f.u., so the potential gives no ranking.
- Our first protocol scored 2/7. Its misses exposed two pipeline bugs (non-exhaustive direction set; refinement picked at fixed lattice), which we fixed before rerunning. Both versions are in the repository.

**Out-of-sample test: six Ruddlesden–Popper compounds the pipeline never saw**, with inputs committed to git before each run (the first five also before any literature check).
- Sr₃Ti₂O₇: no instability, stays I4/mmm (negative control, correct).
- Ca₃Mn₂O₇, Ca₃Sn₂O₇, Sr₃Sn₂O₇: polar A2₁am, matching experiment.
- Sr₃Hf₂O₇ (no experimental structure that we found): A2₁am, matching a published PBEsol DFT study.
- In each polar case the non-polar Pnma is the runner-up, 6–16 meV/f.u. higher, consistent with the non-polar orthorhombic phases these materials pass through on heating.
- Sr₃Ru₂O₇, chosen because its ground state is not A2₁am (Bbcb, rotation only): the pipeline predicts Ccce (= Bbcb, the same space group No. 68), a pure opposite-sense rotation. With the tilt also offered as an order parameter, A2₁am is 15 meV/f.u. higher, so the answer is not built into the method.
- Overall: 9 of 13 materials right, including all 8 n=2 Ruddlesden–Popper compounds. All four failures are cubic perovskites.

## What we learned

- **Keep the LLM out of the algebra.** Group theory and invariant generation are exactly where language models are unreliable, and they are fully automatable. The useful job for the model is planning, choosing order parameters, cross-checking and explaining.
- **Symmetry engine plus universal MLIP is a strong combination.** Soft modes, couplings and phase rankings that used to need days of hand analysis and DFT now take minutes on a laptop-class CPU.
- **Fitted Landau polynomials are fragile for deep wells.**
  - 4th order failed badly for Ca₃Ti₂O₇.
  - 6th order, sampling sized by 1D scans, and a minimiser confined to the sampled region made the fit usable, but it still did not land exactly on the minimum.
  - Forced secondary modes have to be sampled far beyond their own shallow wells, because the primaries drive them there.
  - The fit-independent enumeration and the MACE cross-checks are what make the phase predictions trustworthy.
- **Universal potentials carry their training functional's biases.** The SrTiO₃ ferroelectric artefact is invisible unless you look for it, so the volume check is now part of the agent's instructions.
- **Benchmarks find bugs that showcases hide.** Two of the first benchmark's misses were our own enumeration and refinement errors, not the potential's. The remaining misses fall into two recognisable regimes, volume-sensitive polar modes and sub-meV degeneracies, both visible in the tool output.
- **Check the write-up as hard as the code.** An independent audit of our own write-up against the raw result files caught several overstatements, now corrected. Every number here is backed by a file in `results/`.

## Limitations

- 0 K energies only; no transition temperatures yet.
- Strain enters only through the final relaxations, not the Landau fit.
- Only k-points commensurate with the supercell are visible.
- Polarisation uses nominal charges.
- Standard ISOTROPY labels (Γ4⁻, R4⁺, M3⁺, X2⁺, X3⁻, Γ5⁻) are attached by the code and verified by projecting rigid-octahedron patterns, but only for the two parent families here.
- Phase enumeration is symmetry-complete only for order parameters of dimension ≤ 3.
- MACE-MP-0 inherits PBE errors.
- Benchmark numbers come from the scripted pipeline; live agent transcripts are fewer and one run was cut short by a provider overload error.
