# Pre-registered material selection for the paper benchmark

The rule, not the author, chooses the set. It is committed before any selected material is run.

## Rule, version 2.1 (23 Oct 2026, 21:45 IST) — the one in force

Version 2 below, with two amendments made after inspecting its printed list and before any run:
- **Magnetism.** MP `ordering` ∈ {FM, AFM, FiM} excludes; "Unknown"/missing falls back to |total magnetization| < 0.1 μB/f.u.
  (Version 2 excluded everything ≠ "NM", which removed the titanates, whose entries carry "Unknown".)
- **Octahedral B.** Every B site of the reference polymorph must be six-coordinate by oxygen (pymatgen `CrystalNN`), and
  B is *defined* as the six-coordinate cation (A the other, and the larger). This is the defining feature of the
  perovskite and RP families (corner-sharing BO₆ octahedra) and removes the nitrates, borates, selenites, iodates and
  chain vanadates that the matcher alone admitted at rms 0.31–0.39. Calibration: CaTiO₃ Pnma, LiNbO₃, ilmenite FeTiO₃
  and our Ca₃Ti₂O₇ all have CN 6 (ilmenite is still removed by the pseudosymmetry test); calcite-type NaNO₃ has CN 3.
The version-2 list is kept in `materials/selection_v2_list.txt`.

## Rule, version 2 (23 Oct 2026, 21:30 IST)

**Source.** Materials Project (`mp-api`), summary documents for the anonymous formulas ABC₃ and A₂B₃C₇ containing
oxygen, queried by `select_materials.py`.

**Families.** ABO₃ (aristotype Pm-3m, 2×2×2 supercell) and A₃B₂O₇ (aristotype I4/mmm, √2×√2×1 supercell).
A is the larger cation by average ionic radius (ABO₃) or the 3-count cation (A₃B₂O₇); compositions are named A-first.

**Inclusion, in order.** For each composition:
1. no excluded element (noble gases, actinides, Po–Ra);
2. at least one polymorph with `theoretical = False`; the lowest-energy such polymorph is the **reference**;
3. reference within 30 meV/atom of the hull;
4. reference non-magnetic: MP `ordering == "NM"` (also catches antiferromagnets, which total magnetization misses);
5. **pseudosymmetry**: the reference polymorph matches the ideal aristotype built at the reference's volume under
   `StructureMatcher(ltol=0.3, stol=0.4, angle_tol=10, scale=True, attempt_supercell=True)`. This keeps distorted
   perovskites and excludes compositions whose ground state is not a distortion of the aristotype at all.

**Reference answer.** The space group of the reference polymorph. Experimental polymorphs within 1 meV/atom of it are
listed as `degenerate_reference`; a prediction of any of them counts. If the reference *is* the aristotype
(`reference_is_aristotype`), the expected answer is "no instability" (negative control).

**Protocol, frozen.** v5 as committed ("v5: symmetrisation test"), `mace-matpes-r2scan-0` (primary column) and
MACE-MP-0 `medium` (PBE baseline column). v5 was developed on the 13 hackathon materials, which are therefore the
development set; everything `status = new` is the test set. Any later change to the protocol is a new version with its
own column, never an edit to v5. No material is removed after its run.

**Scoring.** `make_benchmark_table.py --database`, as committed at the freeze: hit / unresolved / miss with the same
1 meV/f.u. window and alias rule as the hackathon table.

**Literature audit, after the run.** `literature_sg` is filled by hand from the literature after all results exist and is
recorded separately; two scores are reported (database reference, literature reference) with every disagreement listed.
The database reference is never edited.

## Calibration of the pseudosymmetry test (done before the run, on structures outside the database query)

| Structure | Type | rms (stol = 0.4) | Verdict |
|---|---|---|---|
| CaTiO₃ Pnma (experimental coordinates) | distorted perovskite | 0.154 | keep |
| Ca₃Ti₂O₇ A2₁am (our relaxed phase) | distorted RP | 0.149 | keep |
| LiNbO₃ R3c | LiNbO₃-type, large distortion | 0.259 | keep (borderline, by design) |
| FeTiO₃ R-3 | ilmenite | no match | exclude |
| BaNiO₃ P6₃/mmc | 2H hexagonal | no match | exclude |
| CaCO₃ R-3c | calcite | no match (matches only at stol ≥ 0.5) | exclude |
| MgSiO₃ Pbca | enstatite | no match | exclude |

## Rule, version 1 (23 Oct 2026, morning) — superseded, disclosed

Version 1 required a Pm-3m / I4/mmm *entry* to exist in MP and used total magnetization as the magnetism filter. Its
query was run once and the printed list (75 compositions, 70 new) was inspected; **no material was run under it**. The
list showed three defects, each fixed in version 2 for the stated reason:
- it admitted compositions whose ground state is not a perovskite derivative (chain silicates, ilmenites, hexagonal
  BaNiO₃, calcite-type GaBO₃) because a hypothetical cubic entry exists in MP → pseudosymmetry test;
- MP's formula ordering and some hypothetical entries inverted A and B (TiPbO₃ ≠ PbTiO₃ by name, PrGaO₃ with Ga on
  the A site) → A/B by ionic radius, lattice from the reference volume, no aristotype entry needed;
- antiferromagnets passed the total-magnetization filter (SrMnO₃, SrTcO₃, LaVO₃) → `ordering == "NM"`.
Version 1 also admitted only one A₃B₂O₇ composition, because few RP compounds have an I4/mmm entry in MP.
The version-1 list is kept in `materials/selection_v1_list.txt` for the record.

## Protocol log (changes after the test-set run began — each disclosed with its trigger)

- **v6 (24 Oct 2026, 02:40 IST), designed after the first 23 test-set results.** Trigger: CaZrO₃ (v5: R3c, −823 meV/f.u.;
  reference Pnma). Diagnosis from the result file: with four primaries and 72 candidate patterns, Pnma ranked 10th after
  the 25-step screen (−621) and the fixed best-6 cut removed it; relaxed on its own (`diag_target_phase.py CaZrO3 Pnma R3c`)
  Pnma reaches −896.8, **74 meV/f.u. below R3c**, so this is a pipeline cut, not the potential. v6 replaces the fixed count
  by a window: every candidate within 30 % of the best screened energy (at least 6, at most 24) gets the fixed-lattice
  relaxation; the free-cell refinement, tightening, polish and symmetrisation are unchanged from v5. v5 results stand as
  run; v6 is a separate column on both the development set and the test set. The 30 % figure was chosen so that CaZrO₃'s
  Pnma (14 % above the best) is inside it with margin; it was not tuned on any other material.
