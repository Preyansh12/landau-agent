# LandauAgent: from a crystal to its Landau theory, with an LLM that never does the group theory

## What we built

LandauAgent turns a high-symmetry crystal structure into a quantitative Landau theory of its structural phase transitions, then predicts and checks the low-symmetry phase.

It is a toolset with an agent on top:

- **Exact symmetry engine (no LLM, no lookup tables).** It builds the parent space group acting on a commensurate supercell and splits atomic displacements into physically irreducible representations. Each irrep is labelled by k-point (k-stars from translation eigenphases, including centring translations), inversion parity, dimension, polarity and which atoms move. Every order-parameter basis is rotated so that representation matrices are signed permutations. All symmetry-allowed Landau invariants then come from the Reynolds operator with exact rational row reduction, and the Landau condition (no cubic invariant) is checked automatically.
- **Energies from a universal MLIP (MACE-MP-0).** Exactly symmetrised force constants give the harmonic curvature of every irrep block, which finds the instabilities. Adaptive frozen-mode scans and a weighted least-squares fit give the Landau coefficients (6th order per mode, couplings to 4th).
- **Coupling discovery.** A stable mode that appears *linearly* in an invariant with the unstable modes is forced to condense with them. This is how the agent finds improper and hybrid-improper ferroelectricity without being told it exists.
- **Two independent phase predictions.**
  1. Minimise the fitted Landau model, confined to the sampled region, with a reliability flag when it disagrees with MACE.
  2. Enumerate every symmetry-distinct order-parameter direction pattern, relax each with MACE inside its own symmetry, at fixed and relaxed lattice, and rank by energy.
- **Volume check.** PBE-trained potentials overestimate lattice constants. The agent can rescale the parent to a known lattice constant and test whether an instability is real or a volume artefact.
- **Agent.** A tool-calling LLM picks supercells and order parameters, adds forced secondary modes, runs the checks and writes the physical explanation. Its system prompt forbids deriving irreps, invariants, couplings, energies or space groups itself; every number it quotes comes from a tool, and tool errors are passed back honestly.

## Results

**Ca₃Ti₂O₇ (hybrid improper ferroelectric), from the I4/mmm parent alone:**
- The strongest MACE instabilities are an X-point octahedral tilt (X⁻) and rotation (X⁺).
- The engine shows a polar Γ⁻ mode appears linearly in the arm-resolved trilinear invariants `S_1·X⁻_1·X⁺_1 − S_2·X⁻_2·X⁺_2` and `S_1·X⁻_2·X⁺_2 + S_2·X⁻_1·X⁺_1`. This is the Benedek–Fennie mechanism, found rather than assumed.
- The Landau minimum and the direct enumeration both give **Cmc2₁ = A2₁am**, the known ground state:
  - 865 meV/f.u. below I4/mmm at fixed lattice, 882 meV/f.u. with a relaxed lattice.
  - Mode amplitudes: X⁻ 1.75 Å, X⁺ 1.22 Å, Γ⁻ 0.85 Å.
  - Nominal-charge polarisation about 15 μC/cm², against about 20 μC/cm² from DFT with Born charges.
  - Tilt-only and rotation-only phases lie 230–700 meV/f.u. higher. The polar phase wins *because* of the coupling.

**SrTiO₃: catching a failure of the potential.**
- At its own (PBE-like, +1%) lattice, MACE finds a polar instability and predicts a ferroelectric ground state. That's wrong: SrTiO₃ stays paraelectric.
- At the experimental lattice constant the polar instability vanishes entirely, while the R⁺ and M⁺ oxygen tilts strengthen.
- The tilt-only analysis gives the textbook R4⁺ invariants. The three tilt systems (I4/mcm, Imma, R-3c) are degenerate to within 0.25 meV/f.u. at fixed cubic lattice. With the lattice relaxed, the experimental I4/mcm phase wins by 0.26 and 0.41 meV/f.u.; the margin is small, so we report this as consistency rather than a robust prediction.

## What we learned

- **Keep the LLM out of the algebra.** Group theory and invariant generation are exactly where language models are unreliable, and they are fully automatable. The useful job for the model is planning, choosing order parameters, cross-checking and explaining.
- **Exact symmetry plus universal MLIPs is a strong combination.** Soft modes, couplings and phase rankings that used to need days of hand analysis and DFT now take minutes on a CPU.
- **Fitted Landau polynomials are fragile for deep wells.** 4th order failed badly for Ca₃Ti₂O₇. 6th order, sampling sized by 1D scans, and a minimiser confined to the sampled region fixed it. We also added an automatic disagreement check against MACE and a fit-independent phase enumeration, which is what makes the predictions trustworthy.
- **Universal potentials carry their training functional's biases.** The SrTiO₃ volume artefact is invisible unless you look for it. Building that check into the agent's workflow was one of the most valuable outcomes.

## Limitations

- 0 K energies only; no transition temperatures yet.
- Strain enters only through the final relaxations, not the Landau fit.
- Only k-points commensurate with the supercell are visible.
- Polarisation uses nominal charges.
- Irrep labels are computed descriptors rather than ISOTROPY's numbered labels.
- MACE-MP-0 inherits PBE errors.
