# Out-of-sample predictions (committed before the literature check)

Protocol: `run_benchmark.py` v2, frozen at commit 8b75568, no per-material tuning, MACE-relaxed parent,
no volume correction. These five materials were not used while developing or fixing the pipeline.
The materials were chosen by us, and we knew some of the answers in general terms; what is
pre-registered is the pipeline output, which was not tuned to them.

| Material | MACE parent a, c (Å) | Leading instabilities (eV/Å²) | Predicted winner (strict / 0.01 Å) | ΔE vs I4/mmm (meV/f.u.) | Runner-up |
|---|---|---|---|---|---|
| Sr3Ti2O7 | see json | none below −0.005 | I4/mmm (no distortion) | 0 | — |
| Ca3Mn2O7 | 3.798, 19.353 | X⁻ −1.49, X⁻ −1.29, X⁺ −1.21, Γ⁻ −0.11 | Cm / Cmc2₁ | −678.4 | Pnma −662.8 |
| Ca3Sn2O7 | 4.071, 20.033 | X⁻ −2.75, X⁺ −2.70, X⁻ −2.53, Γ⁻ −1.71 | Cm / Cmc2₁ | −3099.1 | Cmc2₁ seed −3099.0, Aem2 −2683.4 |
| Sr3Sn2O7 | 4.122, 20.875 | X⁻ −1.17, X⁻ −1.00, X⁻ −0.94, X⁺ −0.92 | Cmc2₁ / Cmc2₁ | −556.7 | Pnma −550.2 |
| Sr3Hf2O7 | 4.132, 21.004 | X⁻ −1.17, X⁻ −0.90, X⁺ −0.81 | Cmc2₁ / Cmc2₁ | −453.1 | Pnma −441.2 |

Raw outputs: `results/benchmark_v2_<name>.json`, log `results/blind_log.txt`.
