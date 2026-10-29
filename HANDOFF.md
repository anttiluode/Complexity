# Handoff — 29 Oct 2026 (Codex/Astra continuation)

## Latest checkpoint

Claude's original campaign and 11-droplet follow-up are complete. The compact predictive-state follow-up
is now also complete. Do not rerun those campaigns. Read RESULTS.md, section "Compact predictive state
follow-up", and results/predictive/summary.json.

- Five droplets train, six entirely held out; two signs and three waits each.
- Delta amplitude/phase + tension fails to beat context (relative error 0.458 vs 0.402).
- Reference cosine/sine state plus their changes and context improves error to 0.218; frozen screen passes on 5/6 test droplets.
- All 66 cases recover the operational shape. A complete two-number state or autonomous reduced simulator is not established.
- Simulator cost 120.73 s within a 600-second cap. Inputs, sensor targets, hashes and predictions are retained.
- Models require pre-probe history and an untouched reference twin; no speed/storage advantage is claimed.

## Reproduce latest result

```bash
python -m pytest -q
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m complexity.predictive --out results/predictive_reproduction --max-seconds 600
```

Matching receipts are reused. Changed code/protocol/environment requires a new output directory.
The thread environment variables can be omitted on Windows; the Python command is portable.

## ONE next experiment (not run)

Vary write arrival time so the same kick reaches a different initial breathing phase. Hold out whole
write-time groups; freeze predictors before examining outcomes. Compare measured internal state against
time/sign/context controls. This probes transfer beyond the synchronized protocol used so far.

## Execution record and rulings

- Isolated branch/worktree from 39e1ee2; original numerical equations unchanged.
- Protocol and tested runner committed before simulation as b084d4b.
- Baseline: 25 tests passed. New tests first failed on the missing module; then eight focused tests and the full 33-test suite passed.
- Ruling: the user continuation authorizes this bounded follow-up; the earlier first-session stop no longer applies.
- Ruling: predict waveforms, include context/reference-state baselines. Cost: small regression fits, no extra field simulations. If the decoder is too restrictive, its failure does not reject compact-state models generally.
- Ruling: narrow unlimited-heating/no-energy-functional claims to finite observations. Existing measurements unchanged.
- Final fresh-context scientific/code review: no leakage or response-subtraction defects found; saved assessment independently reproduced.
- Important fix: interrupted runs no longer receive a fresh budget. Two regression tests failed before the fix and pass afterward; final suite 35/35 passed. Completed receipt time is charged and an in-flight attempt conservatively reserves the remaining allowance.
- Deferred minor: cached reruns update summary implementation_commit to current analysis HEAD. Original generating provenance remains in the archived manifest and b084d4b; separate generating/analysis commit fields are future polish.
- Deferred minor in frozen plan: its three-cycle wording is imprecise. At wait 300 the window begins 109 steps after writing (2.45 cycles); the 192-sample window itself spans 4.32 cycles. No timing or model changed after outcomes.
- Ruling: final review did not rerun the full simulation or test arbitrary fields; the claim remains restricted to the saved deterministic benchmark.
- The post-run budget fix changes the code hash. Archived receipts remain immutable: use a new output directory for fresh simulation, or evaluate saved targets without rerunning physics.
- Analysis replay matches exactly with the original one-thread BLAS setting; changing thread settings may change floating-point last digits.

## Previous campaign handoff (historical; next-step text superseded)

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

## Publication provenance

Shell git push could not authenticate, so publication uses the connected GitHub plugin. The locally committed
pre-experiment source tree b084d4b is preserved unchanged in published commit 50b08457286747abb4f59926349792b5fede98db.
The saved manifest identifies the exact measured file contents. Local and published commit IDs differ because
the connector creates new commit metadata; this does not change the measured source tree or data.
