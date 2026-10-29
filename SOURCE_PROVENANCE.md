# Source provenance

Numerical core extracted from [phi-world-theory/best.py](https://github.com/anttiluode/phi-world-theory/blob/17e86f10661414a46fe40ea9824e16dfb5be3fb9/best.py),
commit `17e86f10661414a46fe40ea9824e16dfb5be3fb9`, blob `630033583c9bc855c06110371a770d5d00acedf3` (verified with `git hash-object`).

## Kept, unchanged
* `MiniWoW.step` (lines 452–465): 6-point Laplacian via `scipy.ndimage.convolve`, `Vp = -pot_lin*phi + pot_cub*phi**3`,
  `c2 = 1/(1 + tension*phi**2 + 1e-6)`, `acc = c2*lap - Vp`, `phi_next = phi + (1 - damp*dt)*(phi - phi_o) + dt**2*acc`,
  in the same operation order, float32.
* Boundary rule: `wrap` for sphere/torus, `nearest` otherwise.
* `init_field` for box / sphere / torus (lines 205–232), followed by the GUI path `change_topology()`, which sets
  `phi_o = phi.copy()` (zero initial velocity). Note: the bare constructor leaves `phi_o = 0`, which would give a large
  initial velocity; the GUI never runs that way for these topologies.
* Defaults: dt=0.1, damping=0.001, tension=5, pot_lin=1, pot_cub=0.2.

## Excluded
GUI (tkinter, ursina), threading lock, energy tracking (`calculate_total_energy` is display only and does not feed back),
`detect_stable_patterns`, `FractalAgent`, nested `sub_sim` simulations and their coupling back into the parent
(`track_fractals` path, lines 467–474), colour-based agent merging. The source `save_state` stores only `phi` and
reloads with `phi_o = phi` (silently zeroing velocity); this package stores `phi` and `phi_prev`.

## Verified
`tests/test_core.py::test_source_step_equivalence` compares `complexity.core.step` to an independent transcription of
the source lines: 1 step at rtol 1e-6 / atol 1e-7 and 100 steps at rtol 1e-5 / atol 1e-6, wrap and nearest.
