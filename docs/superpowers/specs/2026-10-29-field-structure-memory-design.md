# Complexity: structure, retained state, and changed encounters

Date: 2026-10-29. Status: proposed research design; no experiments have been run in this repository.

## Intent

Investigate whether a nonlinear field can support a recognizable structure that survives an encounter, retains a writable internal change, and consequently responds differently to a later encounter. Discovering and explaining interesting geometry is a valid result independently of computational performance.

This is a bounded research program, not a promise of artificial life, a new physical law, or an AI advantage. The numerical thresholds below are proposed engineering screening criteria, not universal physical constants or statistical significance levels.

## Starting evidence and provenance

Complexity contained only LICENSE at commit fd6e94550f521b9c66718591040ea45126074baf.

Primary source: [phi-world-theory/best.py](https://github.com/anttiluode/phi-world-theory/blob/17e86f10661414a46fe40ea9824e16dfb5be3fb9/best.py), blob 630033583c9bc855c06110371a770d5d00acedf3. MiniWoW.step is the starting numerical rule. Preserve its core update with track_fractals disabled. Its default parameters are dt=0.1, damping=0.001, tension=5, pot_lin=1, pot_cub=0.2. The original uses float32, a six-neighbor lattice Laplacian, and wrap boundaries for sphere/torus, nearest otherwise. The topology labels also select initial conditions: they are not different spatial manifolds.

The source's detector, color-based agent merging, nested simulations, and coupling back into the parent are additional machinery. They are excluded from the initial field-only experiment. Its displayed energy is not an established conserved physical energy. Its save_state omits the previous field; do not reuse that incomplete checkpoint format.

The user supplied crystal_kingdom(1).py in the conversation. Code inspection found multiple driven scalar channels, a rendered surface of their mean, and explicit copies of meshes subjected to programmed gravity. Those falling meshes do not retain internal field dynamics or remove their source from the field. That file is not presently in this repo and is not needed for the first campaign. Do not invent a download URL or silently replace best.py with that model.

Related mechanisms, not results transferable to this model:
- [Kompressori](https://github.com/anttiluode/Kompressori): finite-horizon changes to probe responses; a compact update need not describe the full state.
- [VMN](https://github.com/anttiluode/VMN) and [VMNClaude](https://github.com/anttiluode/VMNClaude): amplitude recovery, retained relative phase, and read disturbance.
- [ComputationalChainsInPumpedGPUfield](https://github.com/anttiluode/ComputationalChainsInPumpedGPUfield): explicit monomers interacting with a field. Claude's newly reported phase-memory results were not independently rerun here.
- [Oscillons in a scalar field](https://doi.org/10.1103/PhysRevD.107.076023): useful prior art, not identification of our patterns as oscillons.

## Approaches and recommendation

1. Headless scalar best.py core: cheapest faithful test of the field-only question. Recommended first.
2. Multichannel crystal model: closer to the rain imagery, but more parameters, explicit driving, and greater hidden-state ambiguity. Deferred until its exact source and a reason to expand are available.
3. Add oscillator monomers immediately: gives controllable state, but assumes the objecthood we want to investigate. Defer; use a simple oscillator only as a diagnostic positive control.

These choices are the planner's recommendations, not additional preferences attributed to Antti. Preserve 3D in the first experiment; use small grids rather than substituting a 2D model.

## Global constraints

- Python 3.11 or newer; CPU first; dependencies limited to NumPy, SciPy, Matplotlib, and pytest.
- No GUI, GPU framework, neural network training, automatic parameter optimizer, or new nested-world machinery in the first campaign.
- Use one executing agent sequentially; do not launch per-task subagents or repeated reviewer loops.
- First execution session ends after Tasks 1–2 and a written checkpoint.
- Simulation budget: pilot at most 10 wall-clock minutes; all first-session experiments combined at most 60 wall-clock minutes; default memory ceiling 2 GiB.
- One later continuation may use at most 60 additional simulation minutes. Further sweeps require a new user instruction.
- Time budgets concern simulation runtime, not a claim about model-credit consumption.
- Preserve the exact field rule for fidelity mode; label every altered initialization, forcing, boundary, or equation as an experimental variant.
- No clipping or silent replacement of non-finite values. Failed runs remain in the ledger.
- Save both current and previous fields, configuration, step index, and random-generator state.
- Separate exploratory candidate selection from confirmation; freeze configuration before using confirmation seeds.
- Report negative or inconclusive results within the tested settings; never conclude that the entire architecture cannot compute.

## Core state and rule

State consists of phi, phi_prev, step_index, and RNG state; config records all constants, boundary mode, dtype, and seed.

With lattice spacing 1:
L(phi) = sum of six adjacent cells - 6 phi
a = L(phi)/(1 + tension phi^2 + 1e-6) + pot_lin phi - pot_cub phi^3
phi_next = phi + (1 - damping dt)(phi - phi_prev) + dt^2 a

Return a fresh state with previous field equal to the old current field. Shape, motion, and hidden state are distinct: equal phi with unequal phi_prev generally produces unequal futures.

Define velocity proxy v=(phi-phi_prev)/dt. For a velocity kick delta_v, keep phi fixed and set phi_prev <- phi_prev-dt*delta_v. A position kick keeping v fixed adds the same delta_phi to both arrays. The original GUI poke changes phi alone and therefore also changes this proxy; do not confuse the interventions.

## Stage A: faithful dynamics and a small morphology atlas

Run a deterministic source-equivalence test before exploration. Reproduce the pinned MiniWoW core and initializers without importing the GUI. Record provenance and the exact changes made by extraction.

Pilot grid N=24, dt=0.1; 200 steps for timing, with an extrapolated cost before larger runs. Exploration uses box, sphere, torus initializers crossed with tension in {1,5}: six configurations, defaults otherwise, 2000 steps each, descriptors every 10 steps. Preserve each initializer's source boundary mode. Save initial, midpoint, and final slices plus one selected full checkpoint per run. Seed=0; no random perturbation in the initial deterministic atlas.

Candidate descriptors: positive excursion above a threshold, connected-component count, largest-component voxel count, centroid, covariance eigenvalues, and field/velocity RMS. Use thresholds {0.25,0.5,0.75}*sqrt(pot_lin/pot_cub). Thresholds are observation settings, never fed into dynamics. Report boundary contacts and connected components split across periodic seams; seam-aware labeling is required before claiming a compact periodic object.

Screen over the final 500 steps: an eligible candidate has a tracked component of at least 16 voxels and at most 25% of the domain, volume coefficient of variation <=0.25, and an identifiable track in >=90% of samples. No promotion to a nested simulation. Record transient and extended structures even when they fail this screen. Qualify seeded morphology as seeded, not spontaneous nucleation.

Select at most one configuration, using persistence/compactness before any memory score. Tie-break by smaller volume coefficient of variation, then fixed configuration order. Confirm with seeds 101,102,103, adding Gaussian initial-position noise of standard deviation 1e-4 to both fields so initial velocity is preserved. Require the screen in all three to proceed. These are nearby-condition checks, not three wholly independent physical worlds.

If no candidate qualifies, stop the memory branch. Deliver the morphology atlas, exact failed criteria, and one proposed next experiment. Do not automatically search more parameters. An interesting shape atlas is still a successful deliverable.

## Stage B: disturbance, recovery, and future response

Use the frozen candidate. For each confirmation seed, clone its selected state. Write a localized velocity kick centered at the largest-component centroid, Gaussian sigma=2 lattice cells, truncated at radius 4 and normalized to unit peak. Use minimum-image distances for wrap boundaries; truncate at the domain edge for nearest boundaries. Write amplitudes are {-0.02,+0.02} in field-velocity units; include sham amplitude 0. No parameter changes during trials.

Wait physical durations {10,30,100}, converted to step counts. Always compare to an unmodified twin at the same physical time. Shape recovery means component-mask IoU >=0.9 and relative component-volume difference <=0.1 for 20 consecutive steps, at the middle threshold. Evaluate the other two thresholds as sensitivity checks. Report both raw and integer-translation-aligned IoU; only raw IoU qualifies for the initial gate, to avoid hiding displacement. A failure may be deformation or movement rather than erasure; label it.

For each history and wait, create probe and no-probe clones. Probe is a +0.002 velocity kick with the same spatial profile, 50-step observation horizon. R_H = trajectory(H+probe) - trajectory(H without probe). This paired subtraction separates changed susceptibility from a surviving unprobed waveform. Use the full phi trajectories for the primary RMS comparison, plus local and outer-region traces for diagnosis.

Define D = RMS(R_written-R_sham). Let F be RMS difference in the same observable from replaying an identical sham checkpoint, and use epsilon=1e-12 to guard zero. Define E=D/max(RMS(R_sham),10F,epsilon). A screening effect requires D>max(10F,epsilon) and E>=0.05. Report absolute D and denominator, not just a ratio. It must occur for the same write sign and wait in all three confirmation seeds, after the shape criterion passes. This is a reproducibility screen, not a p-value.

Repeat the selected condition at half probe amplitude: if the two finite-difference responses divided by probe amplitude disagree by >20% RMS relative to the full-amplitude estimate, label the result finite-amplitude interaction rather than a local response derivative. Keep the result; do not misname it.

Controls:
1. Sham, duplicate-state replay, both write signs, and no-probe trajectories.
2. A matched fixed linear field update with amplitude-independent propagation coefficient frozen at phi=0, pot_cub=0, same boundaries and damping. Superposition predicts history-independent incremental response; it need not reproduce morphology. Restrict its horizon if unstable and report that.
3. Analytic positive-control oscillator: da/dt=-k a; dtheta/dt=omega+alpha a. Use k=1, alpha=1, omega=1, a0=0.1. Confirm amplitude recovery and relative phase approaching 0.1 radians. This validates analysis only; never count it as field evidence.

No reliable recovered-state response difference: stop and report. A visible lingering wave alone is not the target result.

## Stage C: locate the retained change

Do not assume phase exists. Begin with one exact, interpretable channel intervention: keep the written current field and replace its previous field to restore the sham velocity proxy; perform the reciprocal velocity transfer into the sham current field. Include identity-copy shams. This tests whether velocity/history carried by the two-step state matters; it does not by itself identify a local oscillator or phase.

Then test locality with a fixed smooth spatial weight: 1 inside the pre-write component dilated by 2 cells, 0 outside dilation by 4, linear ramp by distance between. Transplant both phi and velocity inside that weight, reconstructing phi_prev. Test both directions and an exterior-only transfer, plus same-parent sham transfers. Blending changes the state and can launch waves; measure the immediate mismatch and allow the same prespecified recovery wait before probing. Treat artifacts or loss of shape as inconclusive. If exterior-only transfer reproduces the effect, do not call it object-local memory.

Only if a repeatable oscillation is measured, estimate phase relative to the untouched twin. Use circular differences atan2(sin(delta),cos(delta)); report the oscillation observable and reference. Require at least three observed cycles; otherwise report phase as unidentifiable. Do not force a sinusoid fit onto irregular traces.

Success is a repeatable change to later response that survives shape recovery and follows a controlled state intervention. Compact coding and learning remain separate claims.

## Stopping and reporting

Maintain RESULTS.md as a ledger, with rows: claim, experiment, controls, observed evidence, limits, decision. State all counts attempted/completed/failed. Save compact JSON/CSV summaries and selected compressed checkpoints; ignore bulk traces. Include config hashes, implementation commit, library versions, wall time and machine summary. Budget exhaustion produces status "budget_stop", never a fabricated failure/pass.

Final categories: morphology only; persistent field structure; retained history; changed incremental response; localized causal carrier; compact predictive state. Each requires its own evidence. None alone establishes adaptation, evolution, useful AI, fractality, or a new physical law.

After Stage C, a separately authorized follow-up could compare shape-only versus shape+velocity/phase predictors on held-out encounters, then test two-object interactions. Do not launch that work in this campaign.
