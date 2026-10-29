"""Tasks 3-4 analysis checks, the linear-superposition control and the analytic positive control."""
import numpy as np

from complexity.analysis import (aligned_iou, circular_difference, iou, kick_profile, recovered,
                                 response_metrics, transfer_weight)


def test_response_metrics():
    a = np.random.default_rng(0).normal(size=(5, 4, 4, 4))
    m = response_metrics(a, a, 0.0)
    assert m["D"] == 0.0 and not m["effect"]
    z = response_metrics(np.zeros(10), np.zeros(10), 0.0)
    assert np.isfinite(z["E"]) and z["denominator"] == 1e-12
    sham = np.ones(100)
    written = sham + 0.1
    m = response_metrics(written, sham, 0.0)
    assert abs(m["D"] - 0.1) < 1e-12 and abs(m["E"] - 0.1) < 1e-12 and m["effect"]


def test_raw_vs_aligned_iou_on_translated_cuboid():
    a = np.zeros((16, 16, 16), bool)
    a[4:9, 4:9, 4:9] = True
    b = np.roll(a, 2, axis=0)
    assert iou(a, b) < 0.9 and not recovered(b, a)
    assert aligned_iou(b, a, max_shift=3) == 1.0


def test_transfer_weight_extremes():
    m = np.zeros((12, 12, 12), bool)
    assert transfer_weight(m).max() == 0
    m[4:8, 4:8, 4:8] = True
    w = transfer_weight(m)
    assert w[m].min() == 1.0 and w[0, 0, 0] == 0.0 and 0 < w[4, 4, 1] < 1


def test_circular_difference_wraps():
    assert abs(abs(float(circular_difference(np.pi - 0.01, -np.pi + 0.01))) - 0.02) < 1e-12


def test_kick_profile_unit_peak_truncated():
    p = kick_profile(16, (8, 8, 8))
    assert p.max() == 1.0 and p[8, 8, 13] == 0.0 and p[8, 8, 11] > 0


def test_linear_control_response_is_history_independent():
    """Fixed linear recurrence: incremental probe response must not depend on history."""
    rng = np.random.default_rng(1)
    n = 10

    def lin_step(p, q):
        lap = sum(np.roll(p, s, a) for a in range(3) for s in (1, -1)) - 6 * p
        return p + (1 - 1e-4) * (p - q) + 0.01 * (lap - 0.1 * p), p

    def traj(p, q, steps=40):
        out = []
        for _ in range(steps):
            p, q = lin_step(p, q)
            out.append(p.copy())
        return np.array(out)

    probe = np.zeros((n, n, n)); probe[5, 5, 5] = 1e-3
    hists = [(rng.normal(size=(n,) * 3), rng.normal(size=(n,) * 3)) for _ in range(2)]
    R = []
    raws = []
    for p, q in hists:
        base = traj(p, q)
        kicked = traj(p, q - 0.1 * probe)
        R.append(kicked - base)
        raws.append(base)
    assert np.allclose(R[0], R[1], atol=1e-10)
    assert not np.allclose(raws[0], raws[1])


def test_positive_control_oscillator():
    """da/dt = -a, dtheta/dt = 1 + a, a0 = 0.1: amplitude recovers, phase lead -> 0.1 (1 - e^-t)."""
    a, th, th_ref, dt = 0.1, 0.0, 0.0, 1e-4
    for _ in range(int(10 / dt)):
        k1a, k1t = -a, 1 + a
        k2a, k2t = -(a + 0.5 * dt * k1a), 1 + (a + 0.5 * dt * k1a)
        k3a, k3t = -(a + 0.5 * dt * k2a), 1 + (a + 0.5 * dt * k2a)
        k4a, k4t = -(a + dt * k3a), 1 + (a + dt * k3a)
        a += dt * (k1a + 2 * k2a + 2 * k3a + k4a) / 6
        th += dt * (k1t + 2 * k2t + 2 * k3t + k4t) / 6
        th_ref += dt
    assert abs(a) < 1e-5
    assert abs((th - th_ref) - 0.1 * (1 - np.exp(-10))) < 1e-4
