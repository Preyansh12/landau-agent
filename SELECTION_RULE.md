# Pre-registered material selection for the paper benchmark

Committed before any selected material is run. The rule, not the author, chooses the set.

**Source.** Materials Project (`mp-api`), all entries with `theoretical = False` (an ICSD/experimental
match exists), queried by `select_materials.py`.

**Families.**
1. ABO₃ oxides whose composition has a Pm-3m polymorph in MP (aristotype present), plus every other
   experimentally observed polymorph of the same composition.
2. A₃B₂O₇ oxides whose composition has an I4/mmm polymorph (n = 2 Ruddlesden–Popper aristotype).

**Inclusion.** For each composition: at least one experimental polymorph within 30 meV/atom of the hull;
total magnetization of the lowest experimental polymorph < 0.1 μB per formula unit (MACE is non-spin-polarised);
all elements present in the MatPES training set (Z ≤ 83, no noble gases, no actinides).

**Reference answer.** The space group of the lowest-energy *experimental* polymorph in MP is the "known"
ground state. This is a proxy for the low-temperature structure; where MP lists several experimental
polymorphs within 1 meV/atom the material is flagged `degenerate_reference` and is reported but scored
only if the predicted phase is one of them.

**Exclusions, fixed in advance.** Compositions with partial occupancy or more than 4 elements; compositions
where the aristotype supercell needed exceeds 160 atoms (cost). The 13 hackathon materials are kept and
marked `prior`; everything else is `new`.

**Protocol.** v4 (`run_v4_all.sh` style), `mace-matpes-r2scan-0`, no experimental lattice input. Scoring:
hit / unresolved / miss exactly as in `make_benchmark_table.py`. No material is removed after its run.

## Amendments made before any selected material was run (23 Oct 2026, evening)

- **Protocol frozen at v5** (`run_benchmark.py`, commit "v5: symmetrisation test"). v5 was developed on the 13 hackathon
  materials, which are therefore a *development set*; the database-drawn materials are the test set. Any later change to
  the protocol is a new version with its own column, never an edit to v5.
- **Two columns**: v5 with `mace-matpes-r2scan-0` (primary) and v5 with MACE-MP-0 `medium` (PBE baseline).
- **Reference when the lowest experimental polymorph is the aristotype itself** (`reference_is_aristotype`): the expected
  answer is "no instability", scored as a hit only if the pipeline finds none. This is a negative-control category, and
  it is also where a missing low-temperature ICSD entry would mislead the database reference.
- **Literature audit, after the run**: `literature_sg` is filled by hand from the literature *after* all results exist and is
  recorded separately. Two scores are reported, against the database reference and against the literature reference,
  with every disagreement between the two listed. The database reference is never edited.
- **Scoring**: the verdict function of `make_benchmark_table.py` as committed at the freeze; hit / unresolved / miss with the
  same 1 meV/f.u. window and the same alias rule as the hackathon table.
