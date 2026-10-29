"""The pre-specified droplet detector on a synthetic cold sphere in a hot background."""
import numpy as np

from complexity.core import Config, State
from complexity.droplet import droplet_mask, droplet_screen, equivalent_radius


def test_detector_finds_cold_sphere():
    n = 32
    rng = np.random.default_rng(0)
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    R = np.sqrt((X - 16) ** 2 + (Y - 16) ** 2 + (Z - 16) ** 2)
    phi = np.full((n, n, n), 2.2)
    v = np.where(R <= 8, 0.0, rng.normal(0, 2.0, (n, n, n)))     # hot outside, still inside
    cfg = Config(n=n, boundary="nearest")
    st = State(phi=phi, phi_prev=phi - cfg.dt * v, step_index=0, rng_state={})
    m, outer = droplet_mask(st, cfg)
    r = equivalent_radius(m)
    assert m[16, 16, 16] and 6.0 <= r <= 9.0 and outer > 0


def test_screen_window_and_fraction():
    ok = {s: 9.0 for s in range(500, 2501, 10)}
    assert droplet_screen(ok)["eligible"]
    bad = dict(ok)
    for s in list(bad)[:30]:
        bad[s] = 3.0
    assert not droplet_screen(bad)["eligible"]
