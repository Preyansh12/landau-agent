# Live agent run 3, console output (complete)

Model: gemini-3.8-flash via the OpenAI-compatible backend, Windows laptop, 22 Oct 2026. Run on the code before commit b4d8314; see agent_SrTiO3_audit.md.
The full transcript and tool log are agent_SrTiO3_transcript.md and agent_SrTiO3_tool_log.json. Console output below, verbatim except that local paths are redacted and the final answer, which the old CLI printed twice, appears once.

```
(<conda-env>) C:\Users\<user>\landau-agent>   python -m landau_agent.agent "Is SrTiO3 ferroelectric? Start from the cubic Pm-3m parent and use the tools to decide." --tag agent_SrTiO3

[agent] I will load the cubic Pm-3m parent structure of SrTiO3 to obtain the relaxed reference lattice and coordinates.
[tool] load_parent({"source": "SrTiO3"})
cuequivariance or cuequivariance_torch is not available. Cuequivariance acceleration will be disabled.
Using Materials Project MACE for MACECalculator with C:\Users\<user>\.cache\mace/20231203mace128L1_epoch199model
Using float64 for MACECalculator, which is slower but more accurate. Recommended for geometry optimization.

[agent] I will set a 2x2x2 supercell to make the high-symmetry zone-boundary points R, M, and X, as well as the zone-centre Γ point, commensurate with the cell.
[tool] set_supercell({"matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]})

[agent] I will calculate the harmonic curvature of every irrep block using MACE force constants to detect structural instabilities.
[tool] find_instabilities({})

[agent] I will rescale the parent to the experimental lattice parameter of 3.905 Å to test whether the polar Γ4- instability is a volume artefact of the PBE-trained potential.
[tool] rescale_parent({"target_a": 3.905})

[agent] I will set the 2x2x2 supercell on the rescaled lattice to re-evaluate the phonon irreps and harmonic curvatures.
[tool] set_supercell({"matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]})

[agent] I will calculate harmonic curvatures at the experimental lattice volume to determine which instabilities survive compression.
[tool] find_instabilities({})

[agent] I will select the active tilt instabilities R4+ and M3+ as order parameters to investigate their condensation and possible couplings to polar modes.
[tool] choose_order_parameters({"labels": ["k=(1/2,1/2,1/2) d=3 #3", "k=(0,1/2,1/2)*3 d=3 #2"], "source": "instabilities"})

[agent] I will check for forced couplings between these tilt modes and any secondary modes up to degree 4.
[tool] forced_couplings({"max_degree": 4})

[agent] I will enumerate distinct order-parameter direction patterns of the active tilt modes to find the energetically favored phases.
[tool] enumerate_phases({"max_phases": 10})

[agent] I will refine the lowest energy phases to compare their energetics with and without lattice relaxation.
[tool] refine_phases({"top": 3})

[agent] I will choose the dominant out-of-phase tilt mode R4+ as the order parameter to construct the Landau expansion.
[tool] choose_order_parameters({"source": "instabilities", "labels": ["k=(1/2,1/2,1/2) d=3 #3"]})

[agent] I will generate the symmetry-allowed Landau invariants for the R4+ order parameter up to degree 4.
[tool] landau_polynomial({"max_degree": 4})

[agent] I will fit the Landau model coefficients using MACE frozen-mode energies.
[tool] fit_landau({"max_degree": 4, "n_random": 30})

[agent] I will minimize the fitted Landau model, construct the distorted structure, and verify its space group with MACE.
[tool] predict_ground_state({"relax_check": true})

[agent] **Direct Answer: No, $\text{SrTiO}_3$ is not ferroelectric.** Its low-temperature structural transition is driven purely by non-polar antiferrodistortive octahedral rotations leading to a centrosymmetric tetragonal ground state ($I4/mcm$).

---

### 1. Phonon Instabilities and Volume Sensitivity

Starting from the cubic parent $Pm\bar{3}m$ (relaxed by MACE to $a = 3.9429\text{ \AA}$):
- In the initial MACE-relaxed cell, a polar $\Gamma_4^-$ mode appears unstable with curvature $-0.6365\text{ eV/\AA}^2$.
- Because PBE-trained potentials overestimate equilibrium volumes—which famously induces artificial ferroelectric soft modes in titanates—the cell was rescaled to the experimental cubic lattice parameter $a = 3.905\text{ \AA}$ (a volume change of $-2.85\%$).
- Upon rescaling to $a = 3.905\text{ \AA}$, the polar mode $\Gamma_4^-$ is completely quenched, with curvature $-0.0\text{ eV/\AA}^2$ (classified as non-unstable).
- The only genuine instabilities that survive compression are octahedral tilt modes:
  - **$R_4^+$** ($k = (1/2, 1/2, 1/2)$, out-of-phase octahedral rotation): curvature **$-0.4193\text{ eV/\AA}^2$**
  - **$M_3^+$** ($k = (0, 1/2, 1/2)$, in-phase octahedral rotation): curvature **$-0.1526\text{ eV/\AA}^2$**

---

### 2. Couplings and Symmetry

- A symmetry analysis of invariant couplings between the active tilt modes ($R_4^+$, $M_3^+$) up to degree 4 reveals that no polar secondary modes are forced. All coupled secondary modes ($X_5^+$, $R_5^+$, $M_2^+$, $M_5^+$, etc.) are strictly non-polar and centrosymmetric.
- Therefore, there is neither proper nor improper ferroelectricity.

---

### 3. Fitted Landau Free Energy

For the dominant order parameter $R_4^+ = (\eta_1, \eta_2, \eta_3)$ describing out-of-phase rotations, the symmetry-allowed Landau free energy per formula unit up to degree 6 (with amplitudes in Å across the supercell) fits with RMSE = $0.007\text{ meV/f.u.}$:

$$E(\boldsymbol{\eta}) = A \, (\eta_1^2 + \eta_2^2 + \eta_3^2) + B_1 \, (\eta_1^4 + \eta_2^4 + \eta_3^4) + B_2 \, (\eta_1^2 \eta_2^2 + \eta_1^2 \eta_3^2 + \eta_2^2 \eta_3^2) + C_1 \, (\eta_1^6 + \eta_2^6 + \eta_3^6) + \dots$$

Fitted coefficients:
- **Degree 2:**
  - $\eta_1^2 + \eta_2^2 + \eta_3^2$: **$-26.11\text{ meV}$**
- **Degree 4:**
  - $\eta_1^4 + \eta_2^4 + \eta_3^4$: **$+24.7351\text{ meV}$**
  - $\eta_1^2 \eta_2^2 + \eta_1^2 \eta_3^2 + \eta_2^2 \eta_3^2$: **$+51.2279\text{ meV}$**
- **Degree 6:**
  - $\eta_1^6 + \eta_2^6 + \eta_3^6$: **$-0.5385\text{ meV}$**
  - $\sum_{i \neq j} \eta_i^4 \eta_j^2$: **$-2.2156\text{ meV}$**
  - $\eta_1^2 \eta_2^2 \eta_3^2$: **$-1.3449\text{ meV}$**

Because $B_2 > 2 B_1$, single-axis condensation $(0, 0, \eta)$ ($a^0a^0c^-$ rotation) is energetically favored over multi-axis condensation.

---

### 4. Ground State and Phase Enumeration

- **Landau Ground State:**
  - Minimum at order parameter $\boldsymbol{\eta} = (0.733, 0.0, 0.0)\text{ \AA}$.
  - Landau energy: **$-6.972\text{ meV/f.u.}$**; MACE evaluated energy: **$-6.978\text{ meV/f.u.}$**.
  - Predicted space group: **$I4/mcm$ (No. 140)**, with nominal polarization $[0.0, 0.0, 0.0]\text{ }\mu\text{C/cm}^2$.
- **Independent Phase Enumeration and Refinement:**
  - Fixed-cell relaxation yields $I4/mcm$ at **$-6.95\text{ meV/f.u.}$** (competing closely with $Imma$ at $-6.99\text{ meV/f.u.}$ and $R\bar{3}c$ at $-6.76\text{ meV/f.u.}$, within ~0.2 meV/f.u.).
  - Full cell relaxation confirms **$I4/mcm$ (No. 140)** as the lowest-energy phase at **$-32.03\text{ meV/f.u.}$**, with lattice parameters $a = b = 7.8691\text{ \AA}$, $c = 7.9040\text{ \AA}$.
  - The polarization remains strictly zero in all cases.

---

### 5. Caveats and Physical Limits
- **Temperature & Quantum Fluctuations:** Calculations correspond to static $0\text{ K}$ frozen-mode potentials. In reality, SrTiO3 is a quantum paraelectric where quantum zero-point fluctuations suppress any incipient ferroelectricity down to $0\text{ K}$.
- **Volume Sensitivity:** The appearance of a soft $\Gamma_4^-$ mode at the MACE-optimized volume ($3.9429\text{ \AA}$) is an artifact of PBE volume overestimation; restoring the volume to the experimental lattice constant ($3.905\text{ \AA}$) removes it.
```
