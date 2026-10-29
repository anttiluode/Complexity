"""Stages B and C on the cold droplet (box, tension 5, nearest, N=32), detector pre-specified in droplet.py.

Stage B per spec: clone the selected state (step WRITE_STEP), velocity kick +/-0.02 (Gaussian sigma 2,
truncated r 4, unit peak) at the droplet centre, sham 0; waits 10/30/100 time units; recovery = droplet-mask
IoU >= 0.9 and |dV|/V <= 0.1 versus the unmodified twin for the 20 steps before the probe; probe +0.002 with
the same profile, 50-step horizon; R = traj(probe) - traj(no probe); D, E per analysis.response_metrics;
replay floor F from re-running the sham. Half-amplitude probe check.
EXTRA control (added because the gas is chaotic): REMOTE write, the same +0.02 kick placed in the hot gas
11 cells from the centre. A droplet memory must show up INSIDE the droplet more for the central write
than for the remote write.

Stage C on every wait that passes: velocity restoration and its reciprocal, interior transplant both
ways, exterior-only transplant, identity shams; then the same 100-step recovery wait and probe.
"""
from __future__ import annotations

import json
import os
import time
from multiprocessing import Pool

import numpy as np
from scipy import ndimage

from complexity.analysis import (aligned_iou, iou, kick_profile, recovered, response_metrics, rms,
                                 transfer_weight)
from complexity.core import Config, State, initial_state, kick, step
from complexity.droplet import droplet_mask, droplet_screen, equivalent_radius

N = 32
DTYPE = os.environ.get("CX_DTYPE", "float32")
CFG = Config(n=N, tension=5.0, boundary="nearest", dtype=DTYPE)
WRITE_STEP = 1000
WAITS = (100, 300, 1000)          # 10, 30, 100 time units
HORIZON = 50
AMP_WRITE = float(os.environ.get("CX_AMP", "0.02"))
AMP_PROBE = 0.002
CENTER = (N // 2, N // 2, N // 2)
REMOTE = (N // 2, N // 2, N // 2 + 11)
SEEDS = tuple(int(x) for x in os.environ.get("CX_SEEDS", "101,102,103").split(","))
C_WAIT = 100


def noisy_initial(seed):
    st = initial_state(Config(n=N, tension=5.0, boundary="nearest", seed=seed, dtype=DTYPE), "box")
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, 1e-4, st.phi.shape).astype(st.phi.dtype)
    return State(st.phi + eps, st.phi_prev + eps, 0, rng.bit_generator.state)


def run_steps(st, k):
    for _ in range(k):
        st = step(st, CFG)
    return st


def screen_seed(seed, out_dir):
    st = noisy_initial(seed)
    radii, saved = {}, None
    while st.step_index < 2500:
        st = step(st, CFG)
        if st.step_index % 10 == 0:
            radii[st.step_index] = equivalent_radius(droplet_mask(st, CFG)[0])
        if st.step_index == WRITE_STEP:
            saved = st.copy()
    return droplet_screen(radii), radii, saved


def probe_R(st, prof, amp):
    """Return R (HORIZON, N, N, N) float32: trajectory with probe minus without."""
    a, b = st.copy(), kick(st, CFG, prof, amp, "velocity")
    out = np.empty((HORIZON,) + st.phi.shape, st.phi.dtype)
    for i in range(HORIZON):
        a, b = step(a, CFG), step(b, CFG)
        out[i] = b.phi - a.phi
    return out


def region_metrics(Rw, Rs, F, local, outer):
    m = response_metrics(Rw, Rs, F)
    m["D_local"] = rms((Rw - Rs)[:, local]) if local.any() else 0.0
    m["D_outer"] = rms((Rw - Rs)[:, outer]) if outer.any() else 0.0
    m["sham_local"] = rms(Rs[:, local]) if local.any() else 0.0
    m["E_local"] = m["D_local"] / max(m["sham_local"], 1e-12)
    return m


def evolve_with_masks(st, waits, need_masks_for):
    """Advance to each wait; return states at waits and droplet masks for the 20 steps before each."""
    states, masks = {}, {}
    want = {w - k for w in need_masks_for for k in range(20)}
    t = 0
    for w in waits:
        while t < w:
            st = step(st, CFG); t += 1
            if t in want:
                masks[t] = droplet_mask(st, CFG)[0]
        states[w] = st.copy()
    return states, masks


def stage_b_seed(seed, out_dir):
    t0 = time.monotonic()
    scr, radii, base = screen_seed(seed, out_dir)
    res = {"seed": seed, "screen": scr, "radii": radii}
    if not scr["eligible"]:
        res["stage_b"] = "not_run (droplet screen failed)"
        return res
    pre_mask, _ = droplet_mask(base, CFG)
    local = pre_mask
    outer = ~ndimage.binary_dilation(pre_mask, iterations=4)
    prof_c = kick_profile(N, CENTER)
    prof_r = kick_profile(N, REMOTE)
    arms = {"sham": base.copy(),
            "plus": kick(base, CFG, prof_c, +AMP_WRITE, "velocity"),
            "minus": kick(base, CFG, prof_c, -AMP_WRITE, "velocity"),
            "remote_plus": kick(base, CFG, prof_r, +AMP_WRITE, "velocity")}
    st_at, masks = {}, {}
    for name, st in arms.items():
        st_at[name], masks[name] = evolve_with_masks(st, WAITS, WAITS)
    # replay floor: the sham re-run from the identical checkpoint
    replay, _ = evolve_with_masks(base.copy(), WAITS, ())
    rows = []
    sham_R = {}
    for w in WAITS:
        Rs_full = probe_R(st_at["sham"][w], prof_c, AMP_PROBE)
        Rs_half = probe_R(st_at["sham"][w], prof_c, AMP_PROBE / 2)
        F = rms(probe_R(replay[w], prof_c, AMP_PROBE) - Rs_full)
        sham_R[w] = Rs_full
        for name in ("plus", "minus", "remote_plus"):
            rec_ok = all(recovered(masks[name][w - k], masks["sham"][w - k]) for k in range(20))
            last_w, last_s = masks[name][w - 1], masks["sham"][w - 1]
            Rw_full = probe_R(st_at[name][w], prof_c, AMP_PROBE)
            Rw_half = probe_R(st_at[name][w], prof_c, AMP_PROBE / 2)
            m = region_metrics(Rw_full, Rs_full, F, local, outer)
            eff_full = (Rw_full - Rs_full) / AMP_PROBE
            eff_half = (Rw_half - Rs_half) / (AMP_PROBE / 2)
            lin = rms(eff_full - eff_half) / max(rms(eff_full), 1e-12)
            rows.append({"seed": seed, "arm": name, "wait_steps": w, "recovered": rec_ok,
                         "raw_iou": iou(last_w, last_s), "aligned_iou": aligned_iou(last_w, last_s, 2),
                         "vol_written": int(last_w.sum()), "vol_sham": int(last_s.sum()),
                         "state_rms_diff": rms(st_at[name][w].phi - st_at["sham"][w].phi),
                         "linearity_rel_diff": lin,
                         "label": "finite-amplitude interaction" if lin > 0.2 else "local response derivative",
                         **m})
    res["stage_b_rows"] = rows
    # ---- Stage C on every (central arm, wait) that passes in this seed
    c_rows = []
    w_mask = transfer_weight(pre_mask)
    for w in WAITS:
        for name in ("plus", "minus"):
            r = next(x for x in rows if x["arm"] == name and x["wait_steps"] == w)
            if not (r["recovered"] and r["effect"]):
                continue
            W, S = st_at[name][w], st_at["sham"][w]
            c_rows += stage_c(seed, name, w, W, S, w_mask, prof_c, local, outer)
    res["stage_c_rows"] = c_rows
    res["seconds"] = time.monotonic() - t0
    return res


def _vel(st):
    return (st.phi.astype(np.float64) - st.phi_prev) / CFG.dt


def _compose(phi, v):
    phi = phi.astype(DTYPE)
    return State(phi, (phi - CFG.dt * v).astype(DTYPE), 0, {})


def stage_c(seed, arm, wait, W, S, w, prof, local, outer):
    vW, vS = _vel(W), _vel(S)
    pW, pS = W.phi.astype(np.float64), S.phi.astype(np.float64)
    variants = {
        "identity_sham": _compose(pS, vS),
        "identity_written": _compose(pW, vW),
        "written_phi+sham_velocity": _compose(pW, vS),
        "sham_phi+written_velocity": _compose(pS, vW),
        "interior_written_into_sham": _compose(w * pW + (1 - w) * pS, w * vW + (1 - w) * vS),
        "interior_sham_into_written": _compose(w * pS + (1 - w) * pW, w * vS + (1 - w) * vW),
        "exterior_written_into_sham": _compose((1 - w) * pW + w * pS, (1 - w) * vW + w * vS),
        "same_parent_sham_transfer": _compose(w * pS + (1 - w) * pS, w * vS + (1 - w) * vS),
    }
    ref = run_steps(variants["identity_sham"], C_WAIT)
    Rref = probe_R(ref, prof, AMP_PROBE)
    out = []
    for name, st in variants.items():
        mismatch = rms(st.phi - S.phi)
        after = run_steps(st, C_WAIT)
        R = probe_R(after, prof, AMP_PROBE)
        m = region_metrics(R, Rref, 0.0, local, outer)
        after_mask = droplet_mask(after, CFG)[0]
        ref_mask = droplet_mask(ref, CFG)[0]
        out.append({"seed": seed, "arm": arm, "wait_steps": wait, "variant": name,
                    "immediate_phi_rms_vs_sham": mismatch, "shape_iou_vs_sham": iou(after_mask, ref_mask), **m})
    return out


def main(out_dir=None):
    out_dir = out_dir or os.environ.get("CX_OUT") or ("results/droplet" if DTYPE == "float32" else f"results/droplet_{DTYPE}")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.monotonic()
    with Pool(min(2, len(SEEDS))) as pool:
        results = pool.starmap(stage_b_seed, [(s, out_dir) for s in SEEDS])
    summary = {"dtype": DTYPE, "config": CFG.to_dict(), "write_step": WRITE_STEP, "waits_steps": WAITS, "horizon": HORIZON,
               "amp_write": AMP_WRITE, "amp_probe": AMP_PROBE, "center": CENTER, "remote": REMOTE,
               "seeds": SEEDS, "seconds": time.monotonic() - t0}
    screens = {r["seed"]: r["screen"] for r in results}
    summary["droplet_screen"] = screens
    summary["droplet_screen_pass"] = all(s["eligible"] for s in screens.values())
    rows = [x for r in results for x in r.get("stage_b_rows", [])]
    gate = {}
    for arm in ("plus", "minus", "remote_plus"):
        for w in WAITS:
            sel = [x for x in rows if x["arm"] == arm and x["wait_steps"] == w]
            gate[f"{arm}@{w}"] = bool(len(sel) == len(SEEDS) and all(x["recovered"] and x["effect"] for x in sel))
    summary["stage_b_gate"] = gate
    summary["stage_b_rows"] = rows
    summary["stage_c_rows"] = [x for r in results for x in r.get("stage_c_rows", [])]
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=1)
    json.dump({r["seed"]: r["radii"] for r in results}, open(os.path.join(out_dir, "radii.json"), "w"))
    return summary


if __name__ == "__main__":
    s = main()
    print("droplet screen:", s["droplet_screen"])
    for r in s["stage_b_rows"]:
        print(f"seed {r['seed']} {r['arm']:12s} wait {r['wait_steps']:5d} rec={r['recovered']} rawIoU={r['raw_iou']:.2f} "
              f"D={r['D']:.2e} E={r['E']:.3f} D_loc={r['D_local']:.2e} E_loc={r['E_local']:.3f} "
              f"D_out={r['D_outer']:.2e} state_diff={r['state_rms_diff']:.2e} lin={r['linearity_rel_diff']:.2f} eff={r['effect']}")
    print("gate:", s["stage_b_gate"])
    for r in s["stage_c_rows"]:
        print(f"C seed {r['seed']} {r['arm']}@{r['wait_steps']} {r['variant']:28s} E={r['E']:.3f} E_loc={r['E_local']:.3f} "
              f"mismatch={r['immediate_phi_rms_vs_sham']:.2e} shapeIoU={r['shape_iou_vs_sham']:.2f}")
    print("seconds", round(s["seconds"], 1))
