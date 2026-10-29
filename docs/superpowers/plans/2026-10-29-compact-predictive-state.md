# Compact Predictive State — bounded continuation

> Execute with superpowers:executing-plans, sequentially. User authorized continuation on 2026-10-29. This follows HANDOFF.md at commit 39e1ee2; do not rerun the completed campaign.

## Question and limits

Can a small internal description predict the **time-dependent change in probe response** of a held-out droplet? Predicting a scalar effect magnitude alone is insufficient. This does not establish a complete reduced simulator, learning, or spontaneous objects.

Use the existing 11 (grid, tension, width) settings in many_droplets.py and seed 7, float64. Keep the source rule, center write at step 1000, +/-0.2 velocity writes, 0.002 probe, and 50-step probe horizon. Extend to waits 300, 600, 1000 **steps** (not physical time units). These waits allow at least three breathing cycles before each feature window. Existing results are exploratory evidence for choosing this question, not a blind discovery dataset.

## Frozen protocol (before generating new outcomes)

- Droplet IDs 0..8: tensions 3,5,8 outer loop, widths 4,5,6 inner loop, N=32. IDs 9,10: N=40, tension 5, widths 6,7.
- Train IDs [0,2,4,6,8]; test IDs [1,3,5,7,9,10]. All signs/waits of a droplet stay together. Test N=32 interpolation and N=40 size generalization separately.
- Three arms: sham, plus, minus. Evolve shared histories; take features strictly before probing. Do not use target trajectories or response magnitudes in the features.
- Target: signed difference R_written-R_sham at seven fixed sensors (center and +/-2 cells along each axis), 50 steps, divided by probe amplitude. R is probed minus unprobed evolution. Also accumulate full-field RMS D/E for comparison with past work without retaining full 4D arrays.
- Fit each arm's last 192 pre-probe core-mean samples to intercept + cos(omega*t) + sin(omega*t), omega=sqrt(2)*dt fixed in advance. Time zero is the probe instant. Report fit residuals; do not assume harmonic purity. Convert coefficients to A and phase. If amplitude <1e-8, record phase invalid rather than dividing by zero.
- Shape descriptors use the cold mask: equivalent radius, centroid offsets and covariance eigenvalues. Supply written-minus-sham changes plus sham descriptors. Cold-mask shape uses velocity as well as phi, so it is an operational morphology baseline, not a pure photograph. Report 20-step raw recovery; evaluate all rows first, recovered-only second without selecting the split by outcomes.
- Models: zero; training target mean; context-only (tension, n, width, wait, write sign); shape+context; compact delta state (delta A, sin(delta phase), 1-cos(delta phase), tension); absolute state+context (sham cosine/sine coefficients and coefficient changes, plus context). The last model checks the missing phase-reference problem explicitly.
- Each learned model uses fixed quadratic features (linear terms and upper-triangle products), training-only standardization and ridge alpha=1 with unpenalized intercept. No hyperparameter search. Report feature counts. The two-number delta state is represented circularly, not as a discontinuous raw angle.
- Metrics: aggregate relative RMSE ||prediction-target||/||target|| and each held-out droplet's error; constant-zero is 1. Also scalar E prediction is not the primary endpoint.
- Proposed screening gate: relative RMSE <=0.5 and >=25% lower error than the best zero/mean/context/shape baseline, in >=4/6 held-out droplets as well as aggregate. Label the compact-delta and richer absolute-state outcomes separately. Small deterministic benchmark, not a significance test or universal sufficiency claim.
- Budget: 600 seconds of simulator execution, <=2 GiB working memory, no GPU or extra sweep. Sequential droplets, deadline checks during stepping, per-droplet atomic receipts, resume by exact protocol/code hash. Partial datasets cannot pass the gate. Save small sensor arrays/features so analysis can be rerun without simulation.

## Files, interfaces and task checklist

New complexity/predictive.py owns harmonic_state(series,omega), grouped_split(ids,train_ids), ridge_predict(train_x,train_y,test_x), collect_droplet(spec,deadline), evaluate(rows,targets), and CLI. Reuse core.step/kick, many_droplets.init_bubble, analysis.kick_profile/recovered, droplet.droplet_mask. Do not change equations or the old experiments.

- [ ] Test first: known noninteger-period sinusoid recovers amplitude/phase at probe time; entire-droplet split and unknown test values cannot affect training standardization; known affine response generalizes; zero baseline gives relative error 1; probe collector equals direct full-array reference on a tiny grid; deadline and resume reject incomplete/mismatched runs.
- [ ] Run failing tests, implement minimal utilities/collector, pass focused tests and full suite.
- [ ] Commit protocol and tested runner before campaign; run 600-second bounded campaign, save per-droplet inputs/outcomes and analysis. No decisions based on held-out results alter models or split.
- [ ] Inspect compact and richer state vs baselines; make one summary figure, update RESULTS.md/HANDOFF.md/README.md with exact scope and limits. Fix stale README claim that no simulator exists. Narrow unlimited-heating and no-energy-functional claims: finite experiments do not establish either theorem.
- [ ] Final scientific/code review, targeted fixes if needed, full suite, commit and publish continuation with reproduction command. No next campaign automatically.

## Rulings and progress

- Ruling: new user request authorizes the handoff's compact-state follow-up; the earlier first-session stop no longer applies. New 600-second budget limits this continuation.
- Ruling: add baseline absolute phase and context controls; delta phase alone lacks a reference and successful E prediction alone would be too weak. Cost: a few extra regression fits, no extra field simulations.
- Ruling: the new isolated worktree preserves main while executing; documentation/results are published only after verification.
- Baseline: pending. Implementation: pending. Simulation: not run.
