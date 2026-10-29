# Results ledger

Run by Claude (Opus 5.5), 29 Oct 2026, taking over from the plan Astra wrote for Sol.

**Part 1 (rows 1–7):** Tasks 1–2 as planned. The generic morphology gate failed (0/6); diagnostics found why.
**Part 2 (rows 8–14):** with Antti's go-ahead, the proposed droplet experiment. A cold-droplet detector was
fixed before any Stage B run, then Stage B, Stage C and the optional phase analysis were run. Deviations from
the spec are marked **[deviation]**.

### Headline (part 2)
A seeded cold droplet in the source rule recovers its shape after a kick but **keeps a changed internal
breathing amplitude**. That change alters its response to a later probe and is carried **by the droplet
interior alone**: the transplant tests are clean. It passes the spec's Stage B gate at write strength 0.2,
but **not at the spec's 0.02**, where the same effect is 10× smaller (E = 0.005). The three confirmation seeds
turn out to be the same deterministic droplet, but row 15 then repeats the test on 11 genuinely different
droplets (sizes, tensions, grids), and the effect holds in all of them.

Machine: cloud CPU, 2 cores, Python 3.13.18, NumPy 2.5.3, SciPy 1.18.1. Total simulation time
≈ 8 minutes (atlas 38.8 s; diagnostics ≈ 1.5 min; part 2 ≈ 6 min).

| # | Claim | Experiment | Controls | Observed evidence | Limits | Decision |
|---|---|---|---|---|---|---|
| 1 | `complexity.core.step` is the best.py rule | `tests/test_core.py` | independent transcription of source lines 452–465 | equal at rtol 1e-6 after 1 step and 1e-5 after 100 steps, wrap and nearest; initializer bit-identical to `init_field` + `change_topology` | float32, one machine | **pass** |
| 2 | Trajectories are precision-robust | float32 vs float64, box and torus, N=24 | same rule | max \|Δφ\| 1e-5 at 50 steps, 4e-5 to 4e-4 at 100, 0.04 to 0.07 at 200, **6.8 to 7.8 at 400** | — | **fails**: beyond ~200 steps, any particular shape is one sample of a roundoff-sensitive trajectory |
| 3 | A compact persistent structure exists in the 6-configuration atlas | `python -m complexity atlas` (N=32, 2000 steps, box/sphere/torus × tension 1/5) | spec screen at threshold 0.5·√5 over the final 500 steps | 0 of 6 eligible. Best: box, tension 5, track fraction 0.48 (needs ≥ 0.90), volume CV 0.46 (needs ≤ 0.25). Others: 0.00–0.16 tracked | one grid, one seed, seeded (not spontaneous) morphology | **fail** → memory branch stops |
| 4 | Why (3) fails | `results/atlas/*` histories | three thresholds | the positive phase fills 53–93% of the box and percolates: the largest component is 55–93% of the domain (screen cap 25%). What remains trackable are transient fragments of 16–140 voxels in a voxel-scale ± mosaic | — | **explained** (detector defeated by a percolating hot background) |
| 5 | The seeded box bubble persists inside that mosaic | `complexity/diagnostics.py: cold_core` | tension 1 vs 5 | **tension 5:** a cold core of radius 9 cells holds from step 450 to 3650; centre smoothed v²/2 is 0.003–0.05 against 1.2–2.8 outside (100–900× colder), φ ≈ 2.15 (the + vacuum). **Tension 1:** the core melts between steps 850 and 1250 | box only, one seed; not a gated result | **observed** (not screened) |
| 6 | The best.py rule conserves or dissipates the tested energy diagnostic | `diagnostics.heating`, `tests/test_diagnostics.py` | tension 0 (ordinary φ⁴ wave equation) | tension 0: energy 1.26 → 0.89 (damping). **Tension 1: kinetic 0.80 → 3.60; tension 5: 0.66 → 2.73**, still rising at step 4000. With damping 0 (test), kinetic grows over 1.5× in 1500 steps | lattice energy defined for the φ⁴ part; no long-time theorem or general energy-functional classification | **fails for this diagnostic**. The source rule differs from the tested variational variant. The finite runs establish increased kinetic proxy, not unbounded heating or impossibility of every alternative energy functional. |
| 7 | A conservative version of the same law stops the heating and keeps the droplet | `diagnostics.variant_check` (labelled VARIANT, wrap, tension 5) | source rule, same start | variant energy 1.19 → 0.89 (no heating; under 5% drift with damping 0, `tests/test_diagnostics.py`). But its droplet merges with the surroundings by ~3300 steps; the source droplet is still ~20× colder at 4000 and warming | exploratory variant, one run | **mixed**: heating removed, persistence not improved |

| 8 | The seeded droplet is a persistent structure under a pre-specified detector | `complexity/droplet.py` (smoothed v²/2 < 0.25 × outer-shell median, connected to the centre; equivalent radius ≥ 6 in ≥ 90% of samples, steps 500–2500), box, tension 5, nearest, N=32, seeds 101–103 with 1e-4 noise | — | **pass** in all 3 seeds, float32 and float64: 100% of samples ≥ 6, minimum radius 8.33–8.41 | **[deviation]** detector designed after seeing the atlas (fixed before Stage B); finite lifetime ~3000 steps | proceed |
| 9 | Stage B at the spec's write strength, float32 | `complexity/stage_bc.py` | sham, ±writes, replay floor, half-amplitude probe, **[deviation]** extra remote-write control in the gas | E ≈ 0.012–0.016 but the half-amplitude check disagrees by 120–180%: the response difference D ≈ 4e-7 is at float32 resolution of R (φ ≈ 2.2) | the replay floor F = 0 exactly (deterministic) and does not see the precision floor | **inconclusive (precision)** → float64 |
| 10 | Same, float64 | `CX_DTYPE=float64` | as above | linear (half-amplitude difference 0.00). Central write: **E = 0.004–0.005** at waits 10/30 time units, 0.010–0.011 at 100, identical for ±. Remote write: E ≤ 1e-9 although the gas is fully scrambled (state difference up to 1.8). Shape recovers (raw IoU ≥ 0.94) | — | **gate fail** (E < 0.05), but a clear local effect 10⁶× above the remote control |
| 11 | How the effect scales | exploratory write-strength scan, seed 101, float64 | remote write | at wait 100, E = 0.005 / 0.013 / 0.025 / 0.050 / 0.094 for strength 0.02 / 0.05 / 0.1 / 0.2 / 0.4 (**linear**); E **grows** with wait (strength 0.4: 0.094 → 0.199 → 0.251); remote ≤ 3e-8; shape always recovers | **[deviation]** amplitude chosen from this scan | freeze 0.2 (`configs/selected_droplet.json`) |
| 12 | Stage B gate at strength 0.2 | confirmation seeds 201–203, float64 | all spec controls + remote | **gate passes**: +write at wait 300 (E = 0.057) and 1000 (0.173); −write at 1000 (0.074–0.075); recovery ≥ 0.94 raw IoU; F = 0; linearity difference 0.001; remote ≤ 7e-9 | **seeds give identical numbers** (and equal the seed-101 scan): one deterministic droplet, not independent replications | **pass (one droplet)** |
| 13 | The retained change lives in the droplet | Stage C, every passing (sign, wait), 100-step post-transfer wait | identity shams (E = 0 exactly), same-parent transfer (0) | **interior written→sham reproduces the full effect** (0.108 at 300; 0.061–0.086 at 1000). **Interior sham→written and exterior-only give 0.000**, even when the exterior differs completely (mismatch 1.9–2.0). Channel: at wait 300 the effect sits in φ (written φ + sham v: 0.109; sham φ + written v: 0.008); at 1000 it is split (+: 0.032 / 0.065; −: 0.058 / 0.026), i.e. it rotates between position and velocity | the probe response stays inside the droplet over the horizon (D_outer = 0), so locality is partly built into the insulation | **localized causal carrier (this droplet, this probe)** |
| 14 | What the carrier is | `complexity/phase_probe.py`, mean φ over the core (r ≤ 4), seed 201, strength ±0.2, 1500 steps | untouched twin | breathing mode at ω = 0.1424 rad/step (≈ √V″(min) = √2 per time unit), 34 cycles. **Amplitude is retained**: + write 0.182 vs twin 0.133 (step 88), 0.106 vs 0.053 (step 1408); − write 0.086 → 0.035. **Phase drifts** (+: +0.07 → −0.26 rad; −: −0.16 → −0.76) because amplitude sets frequency in the anharmonic well | one seed; window lock-in | the change is **amplitude-like and persistent**; phase is its consequence, not the store |
| 15 | The effect holds across different droplets | `complexity/many_droplets.py`: bubble width r = 4–7 (**[deviation]** labelled initializer variant), tension 3/5/8, N = 32/40, float64, strength 0.2, wait 300 | twin, remote write just outside each droplet | **11/11 droplets pass the screen and recover shape.** E+ = 0.044–0.074, E− = 0.041–0.048; remote ≤ 1e-5. The droplet from row 12 reproduces exactly (0.057 / 0.041). E+ rises with tension (≈ 0.046 → 0.057 → 0.069 for tension 3/5/8). Retained breathing amplitude ΔA ≈ ±0.045 in every droplet | the frequency estimate is FFT-bin limited (all 0.1466); one wait | **robust across droplets.** ΔA is near-universal, so it does not explain the tension dependence of E (Spearman 0.71, n = 22): **compact predictive state not established** |

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

## What the droplet shows (part 2)

The question of the campaign was: *can a field structure recover its shape while retaining a change that
affects its next encounter?* For one seeded droplet in best.py's rule, **yes**. Its shape mask returns to the
twin's (IoU ≥ 0.94), its breathing amplitude stays changed, and a later probe at its centre responds
differently by 5–17% (strength 0.2). Only the droplet's own interior carries this. The chaotic gas around
it, even when completely different, contributes nothing measurable, because propagation through the hot,
large-amplitude gas is slow (the same insulation as row 5).

The mechanism is the opposite of the toy model in the design (amplitude heals, phase remembers). Here the
breathing amplitude is the memory, because damping is 1e-4 per step and the gas radiates slowly. The phase
drifts because amplitude sets frequency.

Spec categories reached in the original campaign: morphology only ✓, persistent field structure ✓ (finite lifetime, pre-specified
detector), retained history ✓, changed incremental response ✓ (at strength 0.2, not 0.02), localized causal
carrier ✓. Compact predictive state was not tested in that campaign; the follow-up below now evaluates a limited predictive descriptor.

## Not claimed

Positions other than the box centre, and droplets that were not seeded (row 15 covers sizes, tensions and
grids). Spontaneous structure (the droplet is seeded). Indefinite persistence (it melts in
~3000 steps as the rule heats the lattice). Anything about the multichannel crystal_kingdom model, the rain
meshes, or best.py's nested sub-simulations (excluded by design). Any claim at the spec's write strength
0.02 beyond "a linear local effect of E ≈ 0.5%, below the screen".

## Compact predictive state follow-up

Codex/Astra, 29 Oct 2026, continuing 39e1ee2. Protocol and runner were committed as **b084d4b before the new
simulation**; settings, split, features, models and criteria were frozen in
[the continuation plan](docs/superpowers/plans/2026-10-29-compact-predictive-state.md).
The droplet family was already selected for showing effects: this is a new grouped prediction test, not a
blind sample of arbitrary fields. The old campaigns were not rerun.

**Target:** signed (written probe response minus sham probe response) at seven fixed local sensors over
50 steps, divided by probe amplitude. Each probe response subtracts its own matched no-probe trajectory.
Features use only the 192 samples before probing; future response samples never enter them. Full-field D/E
is recorded, but predicting scalar E alone is not the endpoint.

11 configurations × two signs × waits 300/600/1000 **steps** = 66 cases. Five entire configurations (30 cases)
train; six entire configurations (36 cases) are held out, including both N=40 settings. All 66 recover the
operational shape; minimum final raw IoU 0.929. Full-field E ranges 0.041–0.187, so not every row meets the
original E>=0.05 effect gate.

All learned models use quadratic ridge, alpha=1, training-only scaling. Context is tension, grid size,
seeded width, wait and write sign. Internal coordinates come from fixed-frequency least-squares fits to
the core mean, with the probe instant as phase reference.

| Predictor | Raw features / quadratic terms | Held-out relative waveform RMSE | N=32 | N=40 |
|---|---:|---:|---:|---:|
| Predict no change | — | 1.000 | 1.000 | 1.000 |
| Training mean | — | 0.932 | 0.935 | 0.929 |
| Context only | 5 / 20 | **0.402** | 0.401 | 0.404 |
| Shape + context | 19 / 209 | 1.173 | 1.263 | 1.016 |
| Delta amplitude, circular delta phase, tension | 4 / 14 | 0.458 | 0.452 | 0.468 |
| Reference cosine/sine state + changes + context | 9 / 54 | **0.218** | 0.234 | 0.191 |

Relative RMSE is ||prediction-target||/||target||, not classification accuracy. Circular delta phase uses
sin(delta) and 1-cos(delta). The richer model uses four internal coordinates: sham cosine/sine coefficients
and their written-minus-sham changes. These plus context are **not a two-scalar complete state**.

The delta-only proposal **fails** to outperform context. The richer descriptor **passes the frozen screen**:
aggregate error <=0.5, >=25% below the best baseline, and both requirements on >=4 held-out configurations.
It passes on five of six. ID 1 (N=32, tension 3, width 5) fails with error 0.555. Aggregate improvement over
context is 45.8% in relative RMSE.

**Interpretation and limits:** internal dynamics add transferable predictive information for this local probe.
Several coordinates were added together, so this does not isolate absolute phase as the unique cause of
improvement. Failure of the delta-only decoder does not prove that no better decoder exists. The shape model
has many features relative to 30 training rows; its failure does not prove shape has zero information. The
cold mask also uses velocity, so it is not a purely visual measurement.

These are deterministic centered seeded droplets, one initialization seed, fixed write time/strength/probe,
three waits, and no uncertainty interval across independent campaigns. Fixed frequency sqrt(2)*dt gives a
maximum harmonic-fit relative residual of 0.220. Features require history and an untouched twin. There is no
autonomous reduced simulator, demonstrated storage/speed advantage, or complete-state sufficiency result.

**Cost:** 120.73 simulator seconds, float64, Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0; 11/11 completed,
no failed or budget-stopped configurations. Per-droplet features and sensor targets, hashes, split and predictions
are saved under results/predictive. Reproduce with:

```bash
python -m pytest -q
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m complexity.predictive --out results/predictive_reproduction --max-seconds 600
```

Matching completed receipts are reused; changed protocol/code/environment requires a fresh output directory.
The manifest records the implementation used, independently of later documentation commits.

**Next test, not run:** vary write arrival time and hold out whole write-time groups. Keep the predictors
frozen and compare measured state against time/sign/context controls. This tests generalization beyond the
present synchronized write schedule.

**Audit correction:** row 6 and README now describe finite-time heating of the measured diagnostic. Finite
observations and one variational comparison do not prove unlimited heating or exclude all energy functionals.

Final review found no scientific-path defect. An interrupted-run budget bug was fixed after the campaign; two regression tests failed before the fix and now pass. Archived measurement code/hash remains b084d4b. Analysis reproduced exactly with the same one-thread BLAS setting after the fix. Final suite: **35 tests passed**. The frozen plan's timing wording is qualified in HANDOFF.md: the feature window spans more than three cycles, but starts only 2.45 cycles after the earliest write.
