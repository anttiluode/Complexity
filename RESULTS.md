# Results ledger

Run by Claude (Opus 5.5), 29 Oct 2026, taking over from the plan Astra wrote for Sol. Tasks 1–2 of
`docs/superpowers/plans/2026-10-29-field-structure-memory.md` are complete. The morphology gate did
**not** pass, so by the plan's own rule the memory branch (Tasks 3–4) was not started. Two passive
diagnostics were added to explain *why* the gate failed. They change neither the dynamics nor the screen.

Machine: cloud CPU, 2 cores, Python 3.13.18, NumPy 2.5.3, SciPy 1.18.1. Total simulation time
≈ 2.5 minutes (atlas 38.8 s; diagnostics ≈ 1.5 min), against a 60-minute budget.

| # | Claim | Experiment | Controls | Observed evidence | Limits | Decision |
|---|---|---|---|---|---|---|
| 1 | `complexity.core.step` is the best.py rule | `tests/test_core.py` | independent transcription of source lines 452–465 | equal at rtol 1e-6 after 1 step and 1e-5 after 100 steps, wrap and nearest; initializer bit-identical to `init_field` + `change_topology` | float32, one machine | **pass** |
| 2 | Trajectories are precision-robust | float32 vs float64, box and torus, N=24 | same rule | max \|Δφ\| 1e-5 at 50 steps, 4e-5 to 4e-4 at 100, 0.04 to 0.07 at 200, **6.8 to 7.8 at 400** | — | **fails**: beyond ~200 steps, any particular shape is one sample of a roundoff-sensitive trajectory |
| 3 | A compact persistent structure exists in the 6-configuration atlas | `python -m complexity atlas` (N=32, 2000 steps, box/sphere/torus × tension 1/5) | spec screen at threshold 0.5·√5 over the final 500 steps | 0 of 6 eligible. Best: box, tension 5, track fraction 0.48 (needs ≥ 0.90), volume CV 0.46 (needs ≤ 0.25). Others: 0.00–0.16 tracked | one grid, one seed, seeded (not spontaneous) morphology | **fail** → memory branch stops |
| 4 | Why (3) fails | `results/atlas/*` histories | three thresholds | the positive phase fills 53–93% of the box and percolates: the largest component is 55–93% of the domain (screen cap 25%). What remains trackable are transient fragments of 16–140 voxels in a voxel-scale ± mosaic | — | **explained** (detector defeated by a percolating hot background) |
| 5 | The seeded box bubble persists inside that mosaic | `complexity/diagnostics.py: cold_core` | tension 1 vs 5 | **tension 5:** a cold core of radius 9 cells holds from step 450 to 3650; centre smoothed v²/2 is 0.003–0.05 against 1.2–2.8 outside (100–900× colder), φ ≈ 2.15 (the + vacuum). **Tension 1:** the core melts between steps 850 and 1250 | box only, one seed; not a gated result | **observed** (not screened) |
| 6 | The best.py rule conserves or dissipates energy | `diagnostics.heating`, `tests/test_diagnostics.py` | tension 0 (ordinary φ⁴ wave equation) | tension 0: energy 1.26 → 0.89 (damping). **Tension 1: kinetic 0.80 → 3.60; tension 5: 0.66 → 2.73**, still rising at step 4000. With damping 0 (test), kinetic grows over 1.5× in 1500 steps | lattice energy defined for the φ⁴ part | **fails**: c²(φ)∇²φ = ∇·(c²∇φ) − ∇c²·∇φ is not the variation of any energy, so the rule pumps energy into the lattice |
| 7 | A conservative version of the same law stops the heating and keeps the droplet | `diagnostics.variant_check` (labelled VARIANT, wrap, tension 5) | source rule, same start | variant energy 1.19 → 0.89 (no heating; under 5% drift with damping 0, `tests/test_diagnostics.py`). But its droplet merges with the surroundings by ~3300 steps; the source droplet is still ~20× colder at 4000 and warming | exploratory variant, one run | **mixed**: heating removed, persistence not improved |

## What the "crystals" are, in this rule

The background starts at φ = 0, which is the **top** of the double well V = −φ²/2 + 0.05φ⁴
(minima at ±√5 ≈ ±2.24). Every voxel that falls releases V(0) − V(min) = 1.25. Damping is 1e-4 per
step, so that energy stays. With tension 5, propagation inside the wells is slow
(c² ≈ 1/(1 + 5·5) ≈ 0.04), so neighbouring voxels barely talk. The lattice behaves like an array of
almost independent anharmonic oscillators sitting near their barrier, hopping between wells: the
voxel-scale ± mosaic in `results/atlas/atlas_final_slices.png`. On top of that the rule heats itself
(row 6).

The one coherent object is the seeded bubble, which started already near the + vacuum and so never
received the released heat. It survives as a **cold droplet in a hot lattice gas**, insulated because
hot (large-amplitude) surroundings propagate slowly, which is exactly the "amplitude slows propagation"
law. That is persistence by slow heat transport, with a finite lifetime. It is not a self-maintaining
structure.

## Not claimed

No memory, recovery or changed-response result: Tasks 3–4 did not run. No spontaneous structure (all
morphology here is seeded). Nothing about the multichannel crystal_kingdom model, the rain meshes, or
best.py's nested sub-simulations (excluded by design).
