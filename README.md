# Complexity

Can a field structure recover its shape while retaining a change that affects its next encounter?

This repository begins with a research plan. No simulator or experimental results are implemented here yet. Complex geometry is a valid research outcome; memory, causal control and useful computation require separate evidence.

## Start here

- [Research design and scientific gates](docs/superpowers/specs/2026-10-29-field-structure-memory-design.md)
- [Superpowers execution plan for Sol](docs/superpowers/plans/2026-10-29-field-structure-memory.md)

The recommended route is a small, headless 3D extraction of the numerical core of phi-world-theory/best.py. The first session builds a faithful solver and a bounded morphology atlas, then stops with a checkpoint. Later stages test recovery, changed probe response and state transfer only if earlier gates pass.

## Handoff (for Sol or anyone continuing)

Tasks 1–5 and the droplet campaign are done (see Current status below). Do **not** rerun them.
Continue from [HANDOFF.md](HANDOFF.md): it holds the reproduction commands, the caveats to check first, and the one
most informative next experiment (many droplets instead of one).

## Research ladder

1. Generate and describe geometry.
2. Establish persistence under the actual field dynamics.
3. Show recovery after a controlled encounter.
4. Test whether incremental response to a later probe changed.
5. Test which retained state carries that change.

A low-dimensional predictive object model and interactions between such objects are follow-up work, not assumed achievements.

## Current status (29 Oct 2026)

**Yes, for seeded droplets (11/11 tested).** A seeded cold droplet in best.py's rule recovers its shape after a kick but keeps a
changed internal breathing amplitude. That makes a later probe respond differently, and only the droplet's
interior carries the change. Full ledger: [RESULTS.md](RESULTS.md). Next step: [HANDOFF.md](HANDOFF.md).

* The solver reproduces best.py's rule exactly (tested against a line-by-line transcription).
* The voxel "crystal" mosaic is a hot lattice gas, and **the rule heats itself without limit** whenever tension > 0
  (kinetic energy 0.66 → 2.73 over 4000 steps at tension 5; flat at tension 0). The generic atlas screen found no
  compact object (0/6), because the positive phase percolates.
* The seeded bubble survives as a **cold droplet** (radius ~9, 100–900× colder) for ~3000 steps at tension 5,
  insulated by "amplitude slows propagation".
* Kick it (float64, write strength 0.2): shape recovers (IoU ≥ 0.94), and a later probe responds 5.7–17% differently;
  the same kick in the gas changes the droplet's response by ≤ 1e-8. Transplanting the droplet interior carries the
  whole effect; transplanting everything else carries none. The retained variable is the **breathing amplitude**
  (ω ≈ √2), whose anharmonic frequency shift makes the phase drift.
* Across 11 different droplets (sizes, tensions 3/5/8, grids 32/40) every one recovers its shape and keeps the
  effect (E = 0.04–0.07); the retained breathing amplitude is nearly universal (ΔA ≈ ±0.045).
* Caveats: at the spec's write strength 0.02 the effect is only 0.5%; the detector and strength were chosen after
  exploration and frozen before confirmation; droplets are seeded, finite-lifetime, and centred.

![atlas](results/atlas/atlas_final_slices.png)
![heating and droplet](results/diagnostics/heating_variant.png)
![breathing memory](results/phase/phase.png)
