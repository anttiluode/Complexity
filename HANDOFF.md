# Handoff — 29 Oct 2026 (Claude, Opus 5.5)

## State
* Task 1 (solver): **done**. Task 2 (generic morphology atlas): **done, gate failed 0/6**, with the reason diagnosed.
* With Antti's go-ahead ("pre-approved to go the distance"): **droplet campaign done**, covering the pre-specified
  detector, Stage B, Stage C and phase analysis. Result in `RESULTS.md` rows 8–14 and "What the droplet shows".
* Task 5 audit: done by hand in `RESULTS.md` (deviations marked). 25 tests pass (`python -m pytest -q`).

## Reproduce (CPU, ~8 min total)
```bash
pip install -r requirements.txt
python -m pytest -q
python -m complexity atlas --config configs/atlas.json --out results/atlas --max-seconds 3600     # Task 2, ~40 s
python -m complexity.diagnostics                                                                    # cold core
CX_DTYPE=float64 python -m complexity.stage_bc                                                      # Stage B at spec strength 0.02
for A in 0.05 0.1 0.2 0.4; do CX_DTYPE=float64 CX_AMP=$A CX_SEEDS=101 CX_OUT=results/scan_amp/a$A python -m complexity.stage_bc; done
CX_DTYPE=float64 CX_AMP=0.2 CX_SEEDS=201,202,203 CX_OUT=results/droplet_confirm python -m complexity.stage_bc   # gate + Stage C
CX_DTYPE=float64 python -m complexity.phase_probe                                                   # breathing amplitude / phase
```

## Findings in one paragraph
best.py's rule heats itself and turns the box into a voxel-scale hot lattice gas. A seeded cold droplet survives
inside it for ~3000 steps, insulated by "amplitude slows propagation". Kick the droplet and its shape recovers, but
its **breathing amplitude stays changed**. A later probe responds differently (E up to 0.17 at strength 0.2;
0.005 at the spec's 0.02), and only the droplet interior carries that change: interior transplant reproduces it,
reverse and exterior transplants erase it, even when the surrounding gas differs completely.

## Caveats a reviewer should check first
1. Confirmation seeds 201–203 give bit-identical metrics: one deterministic droplet, not three replications.
2. The detector and write strength were chosen after looking (atlas, then the seed-101 scan). Both are frozen in files.
3. float32 cannot resolve the response differences at strength 0.02 (row 9); the conclusions use float64.
4. The probe's response never leaves the droplet within the horizon, so "local" partly restates "insulated".

## Done since: many droplets (RESULTS row 15)
11/11 different droplets keep the effect (E = 0.04–0.07). Reproduce: `python -m complexity.many_droplets` (~80 s).

## ONE most informative next experiment
**Compact predictive state.** The retained breathing amplitude is near-universal (ΔA ≈ ±0.045), yet E grows with
tension. Test whether a two-number state (ΔA, Δphase), plus the droplet's tension, predicts the probe response of a
written droplet *held out* from the fit: fit on half of the 11 droplets × 2 signs × 3 waits, predict the rest, and
compare against a shape-only predictor (which, since shape recovers, should predict no difference). Spec Stage-C
follow-up item; about 10 simulation minutes.
