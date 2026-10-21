# LandauAgent

**From a high-symmetry crystal to its Landau free energy, its instabilities and its low-symmetry phase, with an LLM that plans and explains but never does the group theory.**

Built for the Open Scientific Intelligence (OSI) Hackathon, 21–22 October 2026.

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
3. **Finds forced secondary modes.** A stable mode that appears *linearly* in an invariant with the primary order parameters must condense with them. This is how improper and hybrid-improper ferroelectricity is diagnosed.
4. **Generates the Landau polynomial exactly.** It applies the Reynolds operator to all monomials, row-reduces exactly in rational arithmetic, and checks the Landau condition (no cubic invariant).
5. **Fits the coefficients** to MACE frozen-mode energies (meV per formula unit).
6. **Predicts the ground state.** It minimises the fitted model, builds the structure, reports its space group (spglib), relaxes it with MACE in that symmetry as a check, and estimates the polarisation with nominal charges.

It can also take an *observed* low-symmetry structure and decompose it into irreps (`analyze_child`).

## Results

| Material | Parent | Found instabilities | Forced coupling | Predicted phase | Literature |
|---|---|---|---|---|---|
| SrTiO₃ | Pm-3m | R⁺ and M⁺ tilts; a polar Γ⁻ mode **only at the MACE (PBE-like) volume** | — | at the experimental lattice: **I4/mcm** (a⁰a⁰c⁻), selected by strain coupling (0.26 meV/f.u. below Imma, 0.41 below R-3c); at the MACE lattice: spurious polar Cc (−5.1 meV/f.u.) | I4/mcm below 105 K, paraelectric to 0 K; semilocal DFT overestimates the tilt (PBEsol 5.7°) |
| Ca₃Ti₂O₇ | I4/mmm | X⁻ tilt and X⁺ rotation (both O-dominated) | polar Γ⁻ via the trilinear invariant X⁻·X⁺·P | **Cmc2₁ = A2₁am**, −882 meV/f.u. (relaxed cell); X⁻ 1.75 Å, X⁺ 1.22 Å, Γ⁻ 0.85 Å; P ≈ 15 μC/cm² (nominal charges) | A2₁am via X2⁺ ⊕ X3⁻ ⊕ Γ5⁻, P ≈ 20 μC/cm² (Benedek & Fennie 2011) |

### Ca₃Ti₂O₇ in detail: hybrid improper ferroelectricity found from the parent alone

The only input is the I4/mmm parent. LandauAgent:

1. Finds the X-point octahedral tilt (X⁻) and rotation (X⁺) as the strongest MACE instabilities.
2. Shows that a polar Γ⁻ mode appears **linearly** in invariants with them. The invariants come out arm-resolved: `S_1·X⁻_1·X⁺_1 − S_2·X⁻_2·X⁺_2` and `S_1·X⁻_2·X⁺_2 + S_2·X⁻_1·X⁺_1`. This is the trilinear coupling of hybrid improper ferroelectricity.
3. Minimises the fitted Landau model (6th order in each mode, couplings to 4th). The minimum puts tilt and rotation on the same k-arm with an induced polarisation, and MACE relaxation in that symmetry gives Cmc2₁ (A2₁am).
4. Checks this independently by enumerating every distinct tilt/rotation pattern and relaxing each with MACE in its own symmetry (meV/f.u. vs I4/mmm):

| Phase | Fixed lattice | Relaxed lattice | Nominal P (μC/cm²) |
|---|---|---|---|
| Cmc2₁ (A2₁am) | −865.1 | −882.4 | 14.6 |
| Pmc2₁* | −865.0 | −882.4 | 14.2 |
| Pnma | −831.9 | −842.1 | 0 |
| Pmn2₁ | −720.1 | | 1.1 |
| P4₂/mnm (tilt only) | −632.2 | | 0 |
| Cmcm (tilt only) | −604.4 | | 0 |
| Cmce (rotation only) | −332.6 | | 0 |
| P4/mbm (rotation only) | −159.1 | | 0 |

\*Decomposing the relaxed Pmc2₁ structure shows its second-arm rotation has decayed to 0.0005 Å. It is A2₁am held at a lower imposed symmetry, not a separate phase.

The polar phase wins *because* tilt and rotation together drive the polarisation. Neither alone gets within 230 meV/f.u. of it.

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

At fixed cubic lattice the three tilt systems are degenerate to within 0.25 meV/f.u.; once the lattice can strain, the experimental tetragonal phase wins. The margins are small, comparable to the potential's precision, so this is consistency with experiment rather than a robust prediction.

The R⁺ invariants the engine derives (η², Σηᵢ⁴, Σηᵢ²ηⱼ², with no cubic term) are the textbook R4⁺ expansion. With the fitted coefficients, the single-axis tilt a⁰a⁰c⁻ (I4/mcm) wins because the cross-quartic coefficient is larger than twice the single quartic coefficient.

## How the LLM is used, and how it isn't

The agent (`landau_agent/agent.py`) is a tool-calling loop. The model picks the supercell, decides which instabilities to treat as order parameters, adds forced secondary modes, and writes the physical interpretation.

The system prompt forbids it from deriving irreps, invariants, couplings, energies or space groups itself. Those come only from tools. Irrep names are computed (k-point, inversion parity, dimension, polarity, which atoms move). The model may state a textbook correspondence only when that output makes it unambiguous.

## Install and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install torch mace-torch ase pymatgen spglib sympy scipy anthropic
python run_case.py SrTiO3            # scripted pipeline, no LLM needed
python run_case.py Ca3Ti2O7
export ANTHROPIC_API_KEY=...         # agent mode
python -m landau_agent.agent "Why is Ca3Ti2O7 ferroelectric? Start from the I4/mmm parent."
```

A GPU is optional. On two CPU cores, SrTiO₃ takes about 1 minute and Ca₃Ti₂O₇ about 15 minutes (force constants dominate).

## Limitations

- 0 K frozen-mode energies; no temperature, so no transition temperatures (yet).
- The parent lattice is fixed: strain coupling is not included.
- MACE-MP-0 is PBE-trained, so energy scales inherit PBE errors (e.g. overestimated tilts).
- Only k-points commensurate with the chosen supercell are visible.
- Polarisation uses nominal ionic charges, not Born effective charges, so it is an estimate.
- Irrep labels are computed descriptors (k-point, parity, dimension), not ISOTROPY's numbered labels.

## References

- N. A. Benedek and C. J. Fennie, *Hybrid improper ferroelectricity*, Phys. Rev. Lett. 106, 107204 (2011). [arXiv:1007.1003](https://arxiv.org/abs/1007.1003)
- I. Batatia et al., MACE-MP-0 foundation model (2023).
- H. T. Stokes, D. M. Hatch, H. M. Nelson, *Landau, Lifshitz, and weak Lifshitz conditions*, Phys. Rev. B 47, 9080 (1993).
- C. Capillas et al., *SYMMODES*, J. Appl. Cryst. 36, 953 (2003).
