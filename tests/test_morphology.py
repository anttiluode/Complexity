"""Task 2: passive geometry, periodic seams, candidate screen."""
import numpy as np

from complexity.core import Config, State
from complexity.morphology import components, describe, select_candidate, ELIGIBLE_MIN


def _state(phi):
    return State(phi=phi.astype(np.float32), phi_prev=phi.astype(np.float32), step_index=0, rng_state={})


def test_empty_field_is_finite_and_empty():
    cfg = Config(n=10, boundary="wrap")
    d = describe(_state(np.zeros((10, 10, 10))), cfg, 0.5)
    assert d["n_components"] == 0 and d["largest_volume"] == 0
    assert all(np.isfinite(v) for v in d["cov_eigs"])
    assert np.isfinite(d["rms_phi"]) and np.isfinite(d["rms_v"])


def test_cuboid_volume_and_centroid():
    phi = np.zeros((12, 12, 12))
    phi[2:5, 3:7, 4:9] = 1.0            # 3 x 4 x 5 = 60 voxels
    d = describe(_state(phi), Config(n=12, boundary="nearest"), 0.5)
    assert d["n_components"] == 1 and d["largest_volume"] == 60
    np.testing.assert_allclose(d["centroid"], [3.0, 4.5, 6.0])
    assert not d["touches_boundary"]


def test_wrap_seam_joins_two_lobes():
    phi = np.zeros((12, 12, 12))
    phi[0:2, 5:7, 5:7] = 1.0
    phi[10:12, 5:7, 5:7] = 1.0          # same object across the x seam
    labels, n = components(phi > 0.5, wrap=True)
    assert n == 1
    d = describe(_state(phi), Config(n=12, boundary="wrap"), 0.5)
    assert d["largest_volume"] == 16 and d["crosses_seam"]
    # unwrapped centroid sits on the seam, not in the middle of the box
    assert min(abs(d["centroid"][0] - 11.5), abs(d["centroid"][0] + 0.5)) < 1e-6 or abs(d["centroid"][0] - 11.5) < 1e-6
    assert d["cov_eigs"][0] < 2.0       # compact, not spread across the box


def test_nearest_does_not_wrap():
    phi = np.zeros((12, 12, 12))
    phi[0:2, 5:7, 5:7] = 1.0
    phi[10:12, 5:7, 5:7] = 1.0
    _, n = components(phi > 0.5, wrap=False)
    assert n == 2


def _hist(vols, ok):
    return [{"tracked_volume": v, "track_ok": o} for v, o in zip(vols, ok)]


def test_selection_limits():
    n_dom = 32 ** 3
    base = dict(n_domain=n_dom)
    stable = [100.0] * 50
    # just inside: 90% tracked, CV <= 0.25
    ok90 = [True] * 45 + [False] * 5
    a = dict(base, name="a", order=0, history=_hist(stable, ok90))
    # just outside: 88% tracked
    ok88 = [True] * 44 + [False] * 6
    b = dict(base, name="b", order=1, history=_hist(stable, ok88))
    # CV above 0.25
    noisy = [100.0 * (1 + 0.3 * ((-1) ** i)) for i in range(50)]
    c = dict(base, name="c", order=2, history=_hist(noisy, [True] * 50))
    # too small
    small = dict(base, name="d", order=3, history=_hist([ELIGIBLE_MIN - 1.0] * 50, [True] * 50))
    # too large (> 25% of domain)
    big = dict(base, name="e", order=4, history=_hist([0.26 * n_dom] * 50, [True] * 50))
    sel = select_candidate([b, c, small, big, a])
    assert sel is not None and sel["name"] == "a"
    assert select_candidate([b, c, small, big]) is None
