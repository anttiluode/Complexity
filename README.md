# Complexity

Can a field structure recover its shape while retaining a change that affects its next encounter?

This repository begins with a research plan. No simulator or experimental results are implemented here yet. Complex geometry is a valid research outcome; memory, causal control and useful computation require separate evidence.

## Start here

- [Research design and scientific gates](docs/superpowers/specs/2026-10-29-field-structure-memory-design.md)
- [Superpowers execution plan for Sol](docs/superpowers/plans/2026-10-29-field-structure-memory.md)

The recommended route is a small, headless 3D extraction of the numerical core of phi-world-theory/best.py. The first session builds a faithful solver and a bounded morphology atlas, then stops with a checkpoint. Later stages test recovery, changed probe response and state transfer only if earlier gates pass.

## Handoff (for Sol or anyone continuing)

Tasks 1–2 are done and the morphology gate failed (see Current status below). Do **not** rerun them.
Continue from [HANDOFF.md](HANDOFF.md): it holds the reproduction commands and the one proposed next experiment,
which needs Antti's explicit go-ahead because it introduces a new, pre-specified detector.

## Research ladder

1. Generate and describe geometry.
2. Establish persistence under the actual field dynamics.
3. Show recovery after a controlled encounter.
4. Test whether incremental response to a later probe changed.
5. Test which retained state carries that change.

A low-dimensional predictive object model and interactions between such objects are follow-up work, not assumed achievements.

## Current status (29 Oct 2026)

Tasks 1–2 done by Claude; **the morphology gate failed (0/6)**, so the memory stages were not started.
Read [RESULTS.md](RESULTS.md) for the ledger and [HANDOFF.md](HANDOFF.md) for the one proposed next step.

* The solver reproduces best.py's rule exactly (tested against a line-by-line transcription).
* The voxel "crystal" mosaic is a hot lattice gas. φ = 0 is the top of the double well, each falling voxel
  releases 1.25 units that the 1e-4 damping never removes, and with tension > 0 **the rule heats itself
  without limit** (mean kinetic energy 0.66 → 2.73 over 4000 steps at tension 5; flat at tension 0).
* The one coherent object is the seeded bubble: a **cold droplet** (radius 9, 100–900× colder than its
  surroundings) that survives about 3000 steps at tension 5 and melts within about 1000 at tension 1. It is
  insulated by "amplitude slows propagation" itself, but it has a finite lifetime.
* Trajectories are roundoff-sensitive beyond ~200 steps (float32 vs float64 diverge to O(1) by 400).

![atlas](results/atlas/atlas_final_slices.png)
![heating and droplet](results/diagnostics/heating_variant.png)
