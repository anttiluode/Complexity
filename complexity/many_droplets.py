"""Many droplets instead of one (HANDOFF next experiment). Float64, detector and write strength frozen.

Droplets differ in seeded bubble width r (LABELLED VARIANT of the box initializer: source uses r = N//6),
tension and grid N. For each droplet: droplet screen (steps 500-2500); if it passes, write +/-0.2 at the centre
at step 1000, wait 300 steps, check shape recovery (20 steps), probe 0.002 for 50 steps, E vs untouched twin,
remote-write control, and the retained breathing-amplitude difference (core lock-in at the twin's frequency
over the last 2 periods before the probe). Tests whether the retained amplitude predicts E across droplets.
"""
from __future__ import annotations

import json
import os
from multiprocessing import Pool

import numpy as np

from complexity.analysis import kick_profile, recovered, response_metrics, rms
from complexity.core import Config, State, kick, step
from complexity.droplet import droplet_mask, droplet_screen, equivalent_radius

AMP, PROBE, WAIT, HORIZON, WRITE_STEP = 0.2, 0.002, 300, 50, 1000


def init_bubble(cfg, r, seed=7):
    """Box initializer with bubble width r (VARIANT when r != N//6); zero velocity; 1e-4 noise."""
    n = cfg.n
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    c = n // 2
    phi = (2 * np.exp(-((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2) / (2 * r ** 2))).astype(cfg.dtype)
    eps = np.random.default_rng(seed).normal(0, 1e-4, phi.shape).astype(cfg.dtype)
    return State(phi + eps, phi + eps, 0, {})


def run(st, cfg, k):
    for _ in range(k):
        st = step(st, cfg)
    return st


def probe_R(st, cfg, prof):
    a, b = st.copy(), kick(st, cfg, prof, PROBE, "velocity")
    out = []
    for _ in range(HORIZON):
        a, b = step(a, cfg), step(b, cfg)
        out.append(b.phi - a.phi)
    return np.array(out)


def core_series(st, cfg, k, core):
    s = []
    for _ in range(k):
        st = step(st, cfg)
        s.append(float(st.phi[core].mean()))
    return st, np.array(s)


def lockin(series, omega, t0):
    t = t0 + np.arange(len(series))
    return 2 * np.mean((series - series.mean()) * np.exp(-1j * omega * t))


def one(spec):
    n, tension, r = spec["n"], spec["tension"], spec["r"]
    cfg = Config(n=n, tension=tension, boundary="nearest", dtype="float64")
    st = init_bubble(cfg, r)
    radii, base = {}, None
    while st.step_index < 2500:
        st = step(st, cfg)
        if st.step_index % 10 == 0:
            radii[st.step_index] = equivalent_radius(droplet_mask(st, cfg)[0])
        if st.step_index == WRITE_STEP:
            base = st.copy()
    scr = droplet_screen(radii)
    out = {**spec, "variant_initializer": r != n // 6, "screen": scr}
    if not scr["eligible"]:
        return out
    c = (n // 2,) * 3
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    core = ((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) <= 16
    prof = kick_profile(n, c)
    remote = (c[0], c[1], min(n - 5, c[2] + int(round(radii[WRITE_STEP] + 2))))
    prof_r = kick_profile(n, remote)
    arms = {"twin": base.copy(), "plus": kick(base, cfg, prof, AMP, "velocity"),
            "minus": kick(base, cfg, prof, -AMP, "velocity"), "remote": kick(base, cfg, prof_r, AMP, "velocity")}
    states, series, masks = {}, {}, {}
    for k, s0 in arms.items():
        s1, ser = core_series(s0, cfg, WAIT - 20, core)
        ms = []
        for _ in range(20):
            s1 = step(s1, cfg)
            ms.append(droplet_mask(s1, cfg)[0])
            ser = np.append(ser, float(s1.phi[core].mean()))
        states[k], series[k], masks[k] = s1, ser, ms
    tw = series["twin"] - series["twin"].mean()
    f = np.fft.rfftfreq(len(tw))
    omega = 2 * np.pi * f[np.argmax(np.abs(np.fft.rfft(tw * np.hanning(len(tw))))[1:]) + 1]
    win = int(round(2 * 2 * np.pi / omega))
    Rt = probe_R(states["twin"], cfg, prof)
    for k in ("plus", "minus", "remote"):
        m = response_metrics(probe_R(states[k], cfg, prof), Rt, 0.0)
        zt, zk = lockin(series["twin"][-win:], omega, 0), lockin(series[k][-win:], omega, 0)
        out[k] = {"E": m["E"], "D": m["D"], "recovered": all(recovered(a, b) for a, b in zip(masks[k], masks["twin"])),
                  "amp_twin": float(abs(zt)), "amp_arm": float(abs(zk)), "d_amp": float(abs(zk) - abs(zt)),
                  "d_phase": float(np.angle(zk / zt)), "state_rms_diff": rms(states[k].phi - states["twin"].phi)}
    out["omega_rad_per_step"] = float(omega)
    out["radius_at_write"] = radii[WRITE_STEP]
    return out


def main(out="results/many_droplets"):
    os.makedirs(out, exist_ok=True)
    specs = [{"n": 32, "tension": t, "r": r} for t in (3.0, 5.0, 8.0) for r in (4, 5, 6)]
    specs += [{"n": 40, "tension": 5.0, "r": 6}, {"n": 40, "tension": 5.0, "r": 7}]
    with Pool(2) as p:
        rows = p.map(one, specs)
    json.dump({"amp": AMP, "probe": PROBE, "wait": WAIT, "rows": rows}, open(os.path.join(out, "summary.json"), "w"), indent=1)
    ok = [r for r in rows if "plus" in r]
    print(f"{len(ok)}/{len(rows)} droplets pass the screen")
    for r in rows:
        if "plus" not in r:
            print(f"N={r['n']} t={r['tension']:g} r={r['r']}: screen fail ({r['screen']['reason']})")
            continue
        p, m, q = r["plus"], r["minus"], r["remote"]
        print(f"N={r['n']} t={r['tension']:g} r={r['r']} R={r['radius_at_write']:.1f} w={r['omega_rad_per_step']:.4f}: "
              f"E+={p['E']:.3f} E-={m['E']:.3f} Eremote={q['E']:.1e} rec={p['recovered']}/{m['recovered']} "
              f"dA+={p['d_amp']:+.4f} dA-={m['d_amp']:+.4f} (A_twin {p['amp_twin']:.4f})")
    if len(ok) >= 3:
        E = np.array([r[k]["E"] for r in ok for k in ("plus", "minus")])
        dA = np.array([abs(r[k]["d_amp"]) for r in ok for k in ("plus", "minus")])
        rho = float(np.corrcoef(dA, E)[0, 1])
        from scipy.stats import spearmanr
        print(f"across droplets and signs: corr(|dA|, E) Pearson {rho:.3f}, Spearman {spearmanr(dA, E).statistic:.3f}, n={len(E)}")


if __name__ == "__main__":
    main()
