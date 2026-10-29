# Field Structure and Encounter Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Execute sequentially in one session; Antti's credit constraint overrides per-task subagent/reviewer defaults.

**Goal:** Test whether a 3D field structure recovers its shape while retaining a causally testable change to a later encounter.

**Architecture:** Extract only the pinned best.py numerical core into a deterministic headless package. Build a bounded morphology atlas, then gate twin/probe experiments and state-transfer experiments on measured persistence. Detectors observe the solver and never modify it.

**Tech Stack:** Python 3.11+, NumPy, SciPy, Matplotlib, pytest; CPU.

**Spec:** ../specs/2026-10-29-field-structure-memory-design.md

## Global Constraints

All constraints and numerical definitions in the spec apply. In particular:
- One executing agent sequentially; no per-task subagents or repeated reviewer loops.
- First execution session ends after Tasks 1–2 and a written checkpoint.
- Pilot <=10 simulation minutes; first session <=60 simulation minutes total; default memory ceiling 2 GiB.
- One later continuation <=60 additional simulation minutes; further sweeps need a new user instruction.
- No GUI, GPU framework, neural network training, automatic parameter optimizer, or new nested-world machinery.
- Checkpoint phi AND phi_prev; preserve config, clock, RNG.
- Preserve failed runs; never silently clip.
- The repository currently contains documentation, not an implemented simulator. Commands below are acceptance targets to implement, not commands claimed to work today.

## Review Focus

1. Equal visible fields with unequal velocities must remain distinguishable: Task 1 state test.
2. Periodic seam components and empty masks must not produce false persistence or NaNs: Task 2 geometry tests.
3. Residual waves must not be mistaken for changed probe response: Task 3 linear-superposition test.
4. State blending and phase wrapping must not manufacture a causal story: Task 4 sham/wrap tests.
5. Budget interruptions and confirmation leakage must not silently become successful runs: Tasks 2 and 5 receipt tests.

## Files and ownership

- complexity/core.py: Config, State, exact update, initialization, kicks, serialization.
- complexity/morphology.py: passive masks, periodic components, descriptors, candidate gate.
- complexity/experiments.py: atlas, twin probes, and transfer campaigns.
- complexity/analysis.py: response differences, gates, circular diagnostics.
- complexity/cli.py: bounded commands, receipts, resumability, plotting.
- complexity/__init__.py and complexity/__main__.py: minimal package entry points.
- tests/test_core.py, test_morphology.py, test_experiments.py, test_analysis.py, test_receipts.py.
- configs/atlas.json: frozen six-configuration campaign; configs/selected.json created only after selection.
- requirements.txt, .gitignore, SOURCE_PROVENANCE.md, RESULTS.md, HANDOFF.md.
- results/<run_id>/: summary.json, metrics.csv, plots, selected .npz checkpoints.

No additional abstraction layers are needed. Functions below may use dataclasses; all arrays are NumPy ndarrays.

### Task 1: Faithful solver and complete state

**Interfaces:** Config(n:int, dt:float, damping:float, tension:float, pot_lin:float, pot_cub:float, boundary:str, dtype:str, seed:int); State(phi:ndarray, phi_prev:ndarray, step_index:int, rng_state:dict). Produce initial_state(config:Config, kind:str)->State; step(state:State, config:Config)->State; kick(state:State, config:Config, profile:ndarray, amplitude:float, channel:str)->State; save_state(path:str,state:State,config:Config)->None; load_state(path:str)->tuple[State,Config].

- [ ] Create tests/test_core.py: test_source_step_equivalence compares an independently transcribed pinned source core to step on fixed arrays for one step (float32 allclose rtol=1e-6, atol=1e-7), then 100 steps (rtol=1e-5, atol=1e-6). Test wrap and nearest separately.
- [ ] Add test_equal_shape_different_velocity: equal phi, phi_prev differing by 0.01 in one cell; assert next fields differ. test_checkpoint_continuation: 20 steps equals 10 + save/load + 10 bitwise under the same dtype/environment. test_kick_channels: velocity kick leaves phi unchanged and changes v by amplitude*profile; position kick preserves v.
- [ ] Run python -m pytest tests/test_core.py -q; confirm missing-module failure before implementation.
- [ ] Implement the spec's exact recurrence and source initializers; defaults remain float32. Input arrays must not alias clone outputs. Reject invalid shapes, dt<=0, unknown boundaries and non-finite states. Add minimal dependency and ignored-result files. SOURCE_PROVENANCE.md records source commit/blob and excluded GUI/agent code.
- [ ] Run core tests; additionally compare float64 short trajectories to float32 and report error without demanding bitwise cross-dtype equality.
- [ ] Commit the independently verified solver. No exploration until these tests pass.

### Task 2: Bounded morphology atlas and first handoff

**Consumes:** Task 1 state and step.
**Produces:** describe(state:State,config:Config,threshold:float)->dict; run_atlas(config_path:str,out_dir:str,max_seconds:float)->dict; select_candidate(rows:list[dict])->dict|None. A descriptor includes step/time, threshold, component count, largest volume, centroid, covariance eigenvalues, RMS values, and boundary flags.

- [ ] Write tests/test_morphology.py: empty field returns no component and finite zero-valued size metrics; a known cuboid has the expected volume and centroid; two lobes joined across a wrap boundary count as one component. A nearest-boundary case must not wrap. Test selection on synthetic descriptor histories immediately above/below the spec's screening limits.
- [ ] Write tests/test_receipts.py: a tiny runtime budget writes status budget_stop, completed steps and checkpoint; a resumed identical config continues rather than rerunning; a changed config hash refuses to reuse results.
- [ ] Run these tests and confirm expected failures.
- [ ] Implement passive observation with scipy.ndimage and seam unions for wrap components; unwrap component coordinates before centroid/covariance. Track the largest eligible component by overlap, handle splits/merges explicitly as track discontinuities. Implement the six fixed configs and sampling rules from the spec. Plot 2D slices and scalar histories; marching cubes is unnecessary.
- [ ] Implement CLI: python -m complexity atlas --config configs/atlas.json --out results/atlas --max-seconds 3600. It first performs the 200-step pilot, checks estimated runtime/memory, and stops with estimates if the fixed campaign cannot fit. Check budget between chunks <=50 steps and save on interruption. Default total limit includes pilot and confirmation, not 3600 seconds per run.
- [ ] Run tests, then the pilot and affordable fixed atlas. Select by morphology only, freeze configs/selected.json, and run the three specified nearby-condition confirmation seeds only if affordable.
- [ ] Write RESULTS.md and HANDOFF.md: exact commands, hashes, completed/remaining tasks, candidate or failure reason, cumulative runtime, next permitted command. Link compact plots. Commit summaries and selected small checkpoints; ignore bulk traces.
- [ ] STOP THIS EXECUTION SESSION. Do not automatically implement Tasks 3–5. This stop is the requested low-cost checkpoint, not a scientific conclusion.

### Task 3: Recovered shape and changed incremental response

**Entry gate:** User continues after Task 2; morphology confirmation passes. Otherwise finish the ledger and do not implement this stage; the documentation audit in Task 5 still applies without requiring unbuilt report tooling.
**Interfaces:** probe_response(state:State,config:Config,profile:ndarray,amplitude:float,horizon:int)->ndarray returns phi(probe)-phi(no_probe) at every step. run_twins(selected_path:str,out_dir:str,max_seconds:float)->dict. response_metrics(written:ndarray,sham:ndarray,replay_floor:float)->dict returns D,E,denominator and gate flags.

- [ ] In tests/test_experiments.py create a fixed linear recurrence control with two different histories. Assert incremental probe responses match within float64 atol=1e-10 over a short stable horizon; assert raw unprobed histories differ. This catches confusing residual history with altered response.
- [ ] In tests/test_analysis.py test D=0 for identical arrays; zero denominator yields a finite result using the specified floor; a constructed D=0.1 and sham RMS=1 yields E=0.1. Test raw/aligned mask comparison on a translated cuboid; alignment must not satisfy the raw recovery gate.
- [ ] Add positive-control oscillator check at t=10: a=0.1*exp(-10), phase offset=0.1*(1-exp(-10)); recovered amplitude <1e-5 and phase within 1e-4 of 0.1. Use numerical integration and the analytic solution as independent checks.
- [ ] Run failing tests; implement twin cloning, velocity kicks, fixed waits, 20-step recovery criterion, no-probe subtraction, both write signs and half-amplitude probe check exactly as the spec defines. Preserve both local and outer-region diagnostic traces.
- [ ] Run python -m pytest tests/test_experiments.py tests/test_analysis.py -q.
- [ ] Run python -m complexity twins --selected configs/selected.json --out results/twins --max-seconds 2400. The later-session cumulative cap remains 3600 seconds. If insufficient remaining budget for the fixed confirmation, stop with partial/inconclusive status instead of reducing seed counts.
- [ ] Update ledger with every condition, controls and absolute response sizes; commit. Proceed only if the prespecified recovered-response gate passes. Otherwise skip Task 4, complete Task 5 for the scope actually run, and stop.

### Task 4: Causal state transfer

**Consumes:** successful Task 3 condition and saved parent states.
**Produces:** transfer_state(target:State,donor:State,config:Config,weight:ndarray,channel:str)->State, where channel is velocity or both; run_transfers(twin_run_dir:str,out_dir:str,max_seconds:float)->dict.

- [ ] Write tests: all-zero weight returns target unchanged; all-one both-channel transfer equals donor fields; all-one velocity transfer retains target phi and adopts donor velocity; same-parent transfer does not launch a wave beyond roundoff. circular_difference(pi-0.01,-pi+0.01) has magnitude 0.02.
- [ ] Run failing tests; implement global velocity restoration/reciprocal transfer, then fixed-mask interior/exterior transfer with the specified smooth weights. Use the pre-write mask, identical wait and probe in every arm; never choose the mask by the resulting memory score.
- [ ] Implement circular_difference(a:ndarray,b:ndarray)->ndarray in analysis.py. Add phase estimation only if at least three cycles are available; otherwise retain velocity-channel results and mark phase unidentifiable. Phase estimation is optional analysis, not a condition for finishing.
- [ ] Run the tests; run python -m complexity transfer --from results/twins --out results/transfer --max-seconds 1200, further limited by the later-session remaining budget.
- [ ] Compare identity shams, both transfer directions, exterior controls, immediate mismatch and post-transfer recovery. Interpret global velocity attribution separately from local-state attribution; transplant artifacts mean inconclusive, not causal proof.
- [ ] Commit compact receipts and update the claim ladder in RESULTS.md.

### Task 5: Evidence audit and final handoff

**Files:** RESULTS.md, HANDOFF.md, README.md, tests/test_receipts.py; no new simulation features.
**Interface:** validate_receipt(receipt:dict)->list[str], returning named validation errors; aggregate_reports(run_dirs:list[str])->dict.

- [ ] Add tests for missing previous-state metadata, missing controls, attempted/completed/failed count mismatch, and budget_stop being mislabeled pass. Run failures, implement the minimal validators, rerun.
- [ ] Run python -m pytest -q once for the completed scope. If the report CLI is built, run python -m complexity report --runs results --out RESULTS.md; otherwise perform the same audit directly without expanding a stopped campaign. The report must distinguish not_run, invalid, budget_stop, fail and pass.
- [ ] Check every public claim against a receipt; identify threshold sensitivity, source-rule deviations, boundary recurrence and any numerical instability. A finite periodic/reflecting box can retain remote waves: no object-local claim without transfer evidence.
- [ ] Write a short final handoff: what exists, what was measured, what failed, cumulative cost, reproduction command, and ONE most informative next experiment. Do not launch a compact-state model, neural benchmark, UI, or new parameter sweep.
- [ ] Commit and report the exact commit plus links. Tests passing establishes implementation checks, not success of the scientific hypothesis.

## Self-review and execution status

Planning checks completed: source recurrence and defaults verified; all five review risks assigned tests; interfaces and gates aligned with the spec. No implementation or experiment results claimed. The first deliverable is Tasks 1–2, even if no persistent candidate appears.

The planner has selected a sequential workflow to respect the credit limit. Sol should read the spec and plan once, keep HANDOFF.md current, and resume from the last verified checkpoint instead of repeating discovery or expanding the scope.
