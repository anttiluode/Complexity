"""Task 1: faithful solver and complete state."""
import numpy as np
import pytest
from scipy.ndimage import convolve

from complexity.core import Config, State, initial_state, step, kick, save_state, load_state


# ---- independent transcription of phi-world-theory/best.py MiniWoW.step (pinned 17e86f1, lines 452-465)
_SRC_KERN = np.zeros((3, 3, 3), np.float32)
_SRC_KERN[1, 1, 1] = -6
for _dx, _dy, _dz in [(1, 1, 0), (1, 1, 2), (1, 0, 1), (1, 2, 1), (0, 1, 1), (2, 1, 1)]:
    _SRC_KERN[_dx, _dy, _dz] = 1


def _source_step(phi, phi_o, dt, damp, tension, pot_lin, pot_cub, mode):
    lap = convolve(phi, _SRC_KERN, mode=mode)
    Vp = -pot_lin * phi + pot_cub * phi**3
    c2 = 1.0 / (1.0 + tension * phi**2 + 1e-6)
    acc = c2 * lap - Vp
    vel = phi - phi_o
    phi_o = phi.copy()
    phi = phi + (1 - damp * dt) * vel + dt**2 * acc
    return phi, phi_o


def _random_state(n, seed, boundary):
    rng = np.random.default_rng(seed)
    phi = (rng.standard_normal((n, n, n)) * 0.8).astype(np.float32)
    prev = (phi + rng.standard_normal((n, n, n)).astype(np.float32) * 0.01).astype(np.float32)
    cfg = Config(n=n, boundary=boundary)
    return State(phi=phi, phi_prev=prev, step_index=0, rng_state={}), cfg


@pytest.mark.parametrize("boundary", ["wrap", "nearest"])
def test_source_step_equivalence(boundary):
    st, cfg = _random_state(12, 3, boundary)
    sp, so = st.phi.copy(), st.phi_prev.copy()
    s1 = step(st, cfg)
    rp, ro = _source_step(sp, so, cfg.dt, cfg.damping, cfg.tension, cfg.pot_lin, cfg.pot_cub, boundary)
    np.testing.assert_allclose(s1.phi, rp, rtol=1e-6, atol=1e-7)
    np.testing.assert_allclose(s1.phi_prev, ro, rtol=1e-6, atol=1e-7)
    s = s1
    for _ in range(99):
        s = step(s, cfg)
        rp, ro = _source_step(rp, ro, cfg.dt, cfg.damping, cfg.tension, cfg.pot_lin, cfg.pot_cub, boundary)
    np.testing.assert_allclose(s.phi, rp, rtol=1e-5, atol=1e-6)
    assert s.step_index == 100


def test_initializer_matches_source_change_topology():
    # GUI path: MiniWoW(topology='none') then change_topology(kind): phi from init_field, phi_o = phi
    n = 18
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    c, r = n // 2, n // 6
    ref = np.zeros((n, n, n), np.float32)
    ref[:] = 2 * np.exp(-((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2) / (2 * r**2))
    st = initial_state(Config(n=n, boundary="nearest"), "box")
    np.testing.assert_array_equal(st.phi, ref)
    np.testing.assert_array_equal(st.phi_prev, st.phi)


def test_equal_shape_different_velocity():
    st, cfg = _random_state(10, 1, "wrap")
    other = State(phi=st.phi.copy(), phi_prev=st.phi_prev.copy(), step_index=0, rng_state={})
    other.phi_prev[3, 4, 5] += 0.01
    a, b = step(st, cfg), step(other, cfg)
    assert np.array_equal(st.phi, other.phi)
    assert not np.array_equal(a.phi, b.phi)


def test_checkpoint_continuation(tmp_path):
    cfg = Config(n=12, boundary="wrap", seed=4)
    s = initial_state(cfg, "torus")
    a = s
    for _ in range(20):
        a = step(a, cfg)
    b = s
    for _ in range(10):
        b = step(b, cfg)
    p = tmp_path / "ck.npz"
    save_state(str(p), b, cfg)
    b2, cfg2 = load_state(str(p))
    assert cfg2 == cfg and b2.step_index == 10
    for _ in range(10):
        b2 = step(b2, cfg2)
    assert np.array_equal(a.phi, b2.phi) and np.array_equal(a.phi_prev, b2.phi_prev)


def test_kick_channels():
    st, cfg = _random_state(10, 2, "nearest")
    prof = np.zeros_like(st.phi)
    prof[5, 5, 5] = 1.0
    v0 = (st.phi - st.phi_prev) / cfg.dt
    kv = kick(st, cfg, prof, 0.02, "velocity")
    assert np.array_equal(kv.phi, st.phi)
    np.testing.assert_allclose((kv.phi - kv.phi_prev) / cfg.dt - v0, 0.02 * prof, atol=1e-5)
    kp = kick(st, cfg, prof, 0.02, "position")
    np.testing.assert_allclose((kp.phi - kp.phi_prev) / cfg.dt, v0, atol=1e-5)
    np.testing.assert_allclose(kp.phi - st.phi, 0.02 * prof, atol=1e-7)
    # no aliasing: kicking must not modify the input state
    assert np.array_equal(st.phi, _random_state(10, 2, "nearest")[0].phi)


def test_rejects_invalid():
    with pytest.raises(ValueError):
        Config(n=8, dt=0.0)
    with pytest.raises(ValueError):
        Config(n=8, boundary="reflect")
    st, cfg = _random_state(8, 0, "wrap")
    st.phi[0, 0, 0] = np.nan
    with pytest.raises(FloatingPointError):
        step(st, cfg)
