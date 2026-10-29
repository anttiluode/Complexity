"""Regression checks for the two diagnostic claims in RESULTS.md (fast, n=16)."""
import numpy as np

from complexity.core import Config, initial_state, step
from complexity.diagnostics import lattice_energy, variational_step


def _run(fn, cfg, steps):
    st = initial_state(cfg, "box")
    for _ in range(80):              # let the unstable background fall into the wells first
        st = fn(st, cfg)
    e0 = lattice_energy(st.phi.astype(np.float64), st.phi_prev.astype(np.float64), cfg, fn is variational_step)
    for _ in range(steps):
        st = fn(st, cfg)
    e1 = lattice_energy(st.phi.astype(np.float64), st.phi_prev.astype(np.float64), cfg, fn is variational_step)
    return e0, e1


def test_source_rule_heats_the_lattice():
    cfg = Config(n=16, tension=5.0, boundary="wrap", damping=0.0)
    (_, k0), (_, k1) = _run(step, cfg, 1500)
    assert k1 > 1.5 * k0


def test_variational_variant_conserves_energy():
    cfg = Config(n=16, tension=5.0, boundary="wrap", damping=0.0)
    (e0, _), (e1, _) = _run(variational_step, cfg, 1500)
    assert abs(e1 - e0) < 0.05 * abs(e0)
