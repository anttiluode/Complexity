"""Response metrics, masks, transfer weights and circular differences (Tasks 3-4)."""
from __future__ import annotations

import numpy as np
from scipy import ndimage

EPS = 1e-12


def rms(x) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def response_metrics(written: np.ndarray, sham: np.ndarray, replay_floor: float) -> dict:
    """Spec: D = RMS(R_written - R_sham); E = D / max(RMS(R_sham), 10 F, eps).
    Screening effect: D > max(10 F, eps) and E >= 0.05."""
    D = rms(np.asarray(written, np.float64) - np.asarray(sham, np.float64))
    denom = max(rms(sham), 10 * replay_floor, EPS)
    E = D / denom
    return {"D": D, "denominator": denom, "E": E, "replay_floor": replay_floor,
            "effect": bool(D > max(10 * replay_floor, EPS) and E >= 0.05)}


def iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.count_nonzero(a | b)
    return float(np.count_nonzero(a & b) / u) if u else 1.0


def aligned_iou(a: np.ndarray, b: np.ndarray, max_shift=3, wrap=False) -> float:
    """Best IoU over integer translations (reported only; never used for the recovery gate)."""
    best = 0.0
    for dx in range(-max_shift, max_shift + 1):
        for dy in range(-max_shift, max_shift + 1):
            for dz in range(-max_shift, max_shift + 1):
                if wrap:
                    s = np.roll(a, (dx, dy, dz), axis=(0, 1, 2))
                else:
                    s = ndimage.shift(a.astype(np.uint8), (dx, dy, dz), order=0, mode="constant").astype(bool)
                best = max(best, iou(s, b))
    return best


def recovered(mask_w, mask_ref, vol_tol=0.1, iou_min=0.9) -> bool:
    vw, vr = np.count_nonzero(mask_w), np.count_nonzero(mask_ref)
    if vr == 0:
        return False
    return iou(mask_w, mask_ref) >= iou_min and abs(vw - vr) / vr <= vol_tol


def kick_profile(n, center, sigma=2.0, radius=4.0, wrap=False) -> np.ndarray:
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    d2 = np.zeros((n, n, n))
    for A, c in zip((X, Y, Z), center):
        d = A - c
        if wrap:
            d = (d + n / 2) % n - n / 2
        d2 = d2 + d * d
    prof = np.exp(-d2 / (2 * sigma ** 2))
    prof[d2 > radius ** 2] = 0.0
    return (prof / prof.max()).astype(np.float32)


def transfer_weight(mask: np.ndarray, inner=2, outer=4) -> np.ndarray:
    """1 inside mask dilated by `inner`, 0 outside dilation by `outer`, linear ramp in distance between."""
    if not mask.any():
        return np.zeros(mask.shape, np.float32)
    dist = ndimage.distance_transform_edt(~mask)
    w = np.clip((outer - dist) / (outer - inner), 0.0, 1.0)
    return w.astype(np.float32)


def circular_difference(a, b):
    d = np.asarray(a, np.float64) - np.asarray(b, np.float64)
    return np.arctan2(np.sin(d), np.cos(d))
