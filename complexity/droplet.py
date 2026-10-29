"""Pre-specified cold-droplet detector (HANDOFF.md, fixed before any Stage B run).

droplet = face-connected region of smoothed (sigma 1.5) local kinetic energy v^2/2 below
cold_frac x the median energy of the outer shell (radius >= n/2 - 4 from the box centre),
containing the box centre. Passive: reads phi and phi_prev, writes nothing.
Screen: equivalent radius (3V / 4 pi)^(1/3) >= 6 cells in >= 90% of samples over steps 500-2500.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

SIGMA = 1.5
COLD_FRAC = 0.25
R_MIN = 6.0
WINDOW = (500, 2500)
TRACK_MIN = 0.90

_R_CACHE = {}


def _radius_grid(n):
    if n not in _R_CACHE:
        x = np.arange(n)
        X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
        c = n // 2
        _R_CACHE[n] = np.sqrt((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2)
    return _R_CACHE[n]


def energy(state, config):
    v = (state.phi.astype(np.float64) - state.phi_prev) / config.dt
    return ndimage.gaussian_filter(0.5 * v * v, SIGMA, mode=config.boundary)


def droplet_mask(state, config, cold_frac=COLD_FRAC):
    n = config.n
    e = energy(state, config)
    R = _radius_grid(n)
    outer = float(np.median(e[R >= n // 2 - 4]))
    cold = e < cold_frac * outer
    lab, _ = ndimage.label(cold)
    c = n // 2
    k = lab[c, c, c]
    return (lab == k) if k else np.zeros_like(cold), outer


def equivalent_radius(mask):
    return float((3 * np.count_nonzero(mask) / (4 * np.pi)) ** (1 / 3))


def droplet_screen(radii_by_step: dict) -> dict:
    vals = [r for s, r in radii_by_step.items() if WINDOW[0] <= s <= WINDOW[1]]
    if not vals:
        return {"eligible": False, "reason": "no samples in window"}
    frac = float(np.mean([r >= R_MIN for r in vals]))
    return {"eligible": frac >= TRACK_MIN, "fraction_r_ge_6": frac, "min_radius": float(min(vals)),
            "mean_radius": float(np.mean(vals)),
            "reason": "passes" if frac >= TRACK_MIN else f"radius >= {R_MIN} in only {frac:.2f} of samples"}
