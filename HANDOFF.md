# Handoff — 29 Oct 2026 (Claude, Opus 5.5)

## State
* Task 1 (faithful solver, complete state): **done**. `complexity/core.py`, `tests/test_core.py`, `SOURCE_PROVENANCE.md`.
* Task 2 (morphology atlas, receipts, selection, confirmation): **done; gate failed** (0/6 eligible). `configs/selected.json`
  was not created and no confirmation seeds were run, because nothing qualified.
* Tasks 3–4: **not run** (entry gate is the morphology confirmation). Task 5 audit: performed by hand in `RESULTS.md`.
* Extra, outside the plan's tasks but within its rules (passive, labelled): `complexity/diagnostics.py` (cold-core radius,
  lattice heating, one labelled conservative variant), `tests/test_diagnostics.py`.

Tests: `python -m pytest -q` → 16 passed.

## Reproduce
```bash
pip install -r requirements.txt
python -m pytest -q
python -m complexity atlas --config configs/atlas.json --out results/atlas --max-seconds 3600   # ~40 s
python -m complexity.diagnostics                                                                  # cold core, ~20 s
python -c "from complexity.diagnostics import heating, variant_check; import json; \
json.dump(heating(), open('results/diagnostics/heating.json','w')); \
json.dump(variant_check(), open('results/diagnostics/variant_check.json','w'))"
```
Campaign hash `2e06d179abf13a59` (configs/atlas.json). Atlas simulation time 38.8 s; the pilot estimate was 39.6 s.

## Why the gate failed (short)
The positive phase percolates (55–93% of the box in one component). The screen's 25%-of-domain cap therefore removes the
only coherent object, the seeded bubble, together with the background it touches. What is left are transient fragments.
Underneath that: the rule heats itself whenever tension > 0 (RESULTS row 6), and trajectories are roundoff-sensitive
beyond ~200 steps (row 2).

## ONE proposed next experiment (needs Antti's go-ahead: it changes the screen, and the spec forbids doing that unasked)
**Kick the cold droplet within its lifetime, with the detector specified before running.**
Box initializer, tension 5, nearest boundary (the atlas configuration where the droplet lives longest), N=32.
* Detector, fixed in advance: droplet = connected region of smoothed (σ = 1.5) v²/2 below 0.25 × the median of the outer
  shell, containing the box centre. Screen: radius ≥ 6 cells in ≥ 90% of samples over steps 500–2500, in seeds 101–103
  (initial noise 1e-4, as in the spec).
* If it passes, run Stage B unchanged (velocity kicks ±0.02 at the droplet centre, sham, waits 10/30/100 time units,
  paired probe/no-probe twins, linear control), restricted to the droplet's lifetime window. Twins share identical
  float32 arithmetic, so roundoff sensitivity does not contaminate the paired differences.

Expected cost under 10 simulation minutes. If the droplet screen fails in any seed, stop: the deliverable is then
"no persistent object in this rule at N = 32, and the reason is self-heating plus percolation".

Next permitted command after approval: implement the droplet detector as a new screen in `complexity/morphology.py`
(with tests), add `configs/droplet.json`, then run Task 3 against it.
