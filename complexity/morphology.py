"""Passive observation: masks, periodic components, descriptors, tracking, candidate screen.

Nothing here writes to the field. Thresholds are observation settings only.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

ELIGIBLE_MIN = 16          # voxels
ELIGIBLE_MAX_FRAC = 0.25   # of the domain
CV_MAX = 0.25
TRACK_MIN = 0.90


def thresholds(pot_lin=1.0, pot_cub=0.2):
    v = float(np.sqrt(pot_lin / pot_cub))
    return [0.25 * v, 0.5 * v, 0.75 * v]


def components(mask: np.ndarray, wrap: bool):
    """Face-connected components; with wrap, components touching opposite faces are joined."""
    labels, n = ndimage.label(mask)
    if not wrap or n == 0:
        return labels, n
    parent = np.arange(n + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for axis in range(3):
        first = np.take(labels, 0, axis=axis)
        last = np.take(labels, -1, axis=axis)
        both = (first > 0) & (last > 0)
        for a, b in set(zip(first[both].tolist(), last[both].tolist())):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(n + 1)])
    uniq = np.unique(roots[1:])
    remap = np.zeros(n + 1, dtype=np.int64)
    for new, r in enumerate(uniq, start=1):
        remap[roots == r] = new
    remap[0] = 0
    return remap[labels], len(uniq)


def _geometry(coords: np.ndarray, n: int, wrap: bool):
    """Centroid and covariance eigenvalues; periodic coordinates are unwrapped about a circular mean."""
    if coords.shape[0] == 0:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    x = coords.astype(np.float64)
    if wrap:
        ang = 2 * np.pi * x / n
        c = np.angle(np.exp(1j * ang).mean(0)) * n / (2 * np.pi)
        d = (x - c + n / 2) % n - n / 2
        centroid = (c + d.mean(0)) % n
    else:
        d = x - x.mean(0)
        centroid = x.mean(0)
    cov = np.cov(d.T, bias=True) if x.shape[0] > 1 else np.zeros((3, 3))
    eig = np.sort(np.linalg.eigvalsh(np.atleast_2d(cov)))[::-1]
    return centroid.tolist(), eig.tolist()


def describe(state, config, threshold: float, labels_out: dict | None = None) -> dict:
    n = config.n
    wrap = config.boundary == "wrap"
    mask = state.phi > threshold
    labels, k = components(mask, wrap)
    vols = np.bincount(labels.ravel(), minlength=k + 1)[1:] if k else np.zeros(0, int)
    v = (state.phi.astype(np.float64) - state.phi_prev) / config.dt
    out = {"step": int(state.step_index), "time": float(state.step_index * config.dt),
           "threshold": float(threshold), "n_components": int(k),
           "largest_volume": int(vols.max()) if k else 0,
           "positive_fraction": float(mask.mean()),
           "rms_phi": float(np.sqrt(np.mean(state.phi.astype(np.float64) ** 2))),
           "rms_v": float(np.sqrt(np.mean(v ** 2)))}
    if k:
        big = int(np.argmax(vols)) + 1
        coords = np.argwhere(labels == big)
        out["centroid"], out["cov_eigs"] = _geometry(coords, n, wrap)
        out["touches_boundary"] = bool((coords == 0).any() or (coords == n - 1).any())
        out["crosses_seam"] = bool(wrap and out["touches_boundary"])
    else:
        out["centroid"], out["cov_eigs"] = None, [0.0, 0.0, 0.0]
        out["touches_boundary"] = out["crosses_seam"] = False
    if labels_out is not None:
        labels_out["labels"], labels_out["volumes"] = labels, vols
    return out


class Tracker:
    """Follow the eligible component that overlaps the previously tracked mask most.
    A sample is track_ok if an eligible component exists and (after the first) overlaps the previous one."""

    def __init__(self, n):
        self.n_dom = n ** 3
        self.prev = None
        self.started = False

    def update(self, labels, vols):
        elig = [i + 1 for i, v in enumerate(vols) if ELIGIBLE_MIN <= v <= ELIGIBLE_MAX_FRAC * self.n_dom]
        if not elig:
            self.prev = None
            return {"tracked_volume": 0.0, "track_ok": False, "event": "none"}
        if self.prev is not None:
            ov = {i: int(np.count_nonzero((labels == i) & self.prev)) for i in elig}
            best = max(ov, key=ov.get)
            if ov[best] > 0:
                n_hit = sum(1 for i in elig if ov[i] > 0)
                self.prev = labels == best
                return {"tracked_volume": float(vols[best - 1]), "track_ok": True,
                        "event": "split" if n_hit > 1 else "continue"}
            event = "lost"
        else:
            event = "restart" if self.started else "start"
        self.started = True
        best = max(elig, key=lambda i: vols[i - 1])
        self.prev = labels == best
        # only the very first sighting counts as tracked; "lost"/"restart" are discontinuities
        return {"tracked_volume": float(vols[best - 1]), "track_ok": event == "start", "event": event}


def screen(history, n_domain):
    """Spec screen over the supplied (final-window) history."""
    if not history:
        return {"eligible": False, "reason": "no samples"}
    ok = np.array([h["track_ok"] for h in history])
    vol = np.array([h["tracked_volume"] for h in history], float)
    frac = float(ok.mean())
    tv = vol[ok]
    if tv.size == 0:
        return {"eligible": False, "track_fraction": 0.0, "reason": "never tracked"}
    cv = float(tv.std() / tv.mean()) if tv.mean() > 0 else float("inf")
    in_range = bool((tv >= ELIGIBLE_MIN).all() and (tv <= ELIGIBLE_MAX_FRAC * n_domain).all())
    reasons = []
    if frac < TRACK_MIN:
        reasons.append(f"track fraction {frac:.2f} < {TRACK_MIN}")
    if cv > CV_MAX:
        reasons.append(f"volume CV {cv:.3f} > {CV_MAX}")
    if not in_range:
        reasons.append("tracked volume outside [16, 25% domain]")
    return {"eligible": not reasons, "track_fraction": frac, "volume_cv": cv,
            "mean_volume": float(tv.mean()), "reason": "; ".join(reasons) or "passes"}


def select_candidate(rows):
    """rows: dicts with name, order, n_domain, history. Morphology only: eligible, then smallest CV, then order."""
    scored = []
    for r in rows:
        s = screen(r["history"], r["n_domain"])
        if s["eligible"]:
            scored.append((s["volume_cv"], r["order"], r, s))
    if not scored:
        return None
    scored.sort(key=lambda t: (t[0], t[1]))
    best = dict(scored[0][2])
    best["screen"] = scored[0][3]
    return best
