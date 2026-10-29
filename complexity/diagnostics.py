"""Passive diagnostics on the frozen atlas configurations (no dynamics or screen changes).

cold_core: the box initializer seeds a smooth bubble already near the + vacuum (phi = 2 vs
sqrt(5) = 2.24), while the background starts at phi = 0, the TOP of the double well. Falling
from the barrier releases V(0) - V(min) = pot_lin^2 / (4 pot_cub) = 1.25 per voxel; with
damping 1e-4 per step it stays as heat. This tracks, around the box centre, the radial profile
of the smoothed local kinetic energy e = v^2/2 and of phi, and the radius of the cold core.
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy.ndimage import gaussian_filter

from complexity.core import Config, initial_state, source_boundary, step


def radial_profile(field, center, r_max):
    n = field.shape[0]
    x = np.arange(n)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    R = np.sqrt((X - center) ** 2 + (Y - center) ** 2 + (Z - center) ** 2)
    edges = np.arange(0, r_max + 1)
    idx = np.digitize(R.ravel(), edges) - 1
    prof = np.array([field.ravel()[idx == i].mean() if np.any(idx == i) else np.nan for i in range(len(edges) - 1)])
    return prof


def cold_core(kind, tension, n=32, steps=4000, every=50, sigma=1.5, cold_frac=0.25):
    cfg = Config(n=n, tension=tension, boundary=source_boundary(kind))
    st = initial_state(cfg, kind)
    c = n // 2
    rows = []
    for _ in range(steps):
        st = step(st, cfg)
        if st.step_index % every == 0:
            v = (st.phi.astype(np.float64) - st.phi_prev) / cfg.dt
            mode = "wrap" if cfg.boundary == "wrap" else "nearest"
            e = gaussian_filter(0.5 * v * v, sigma, mode=mode)
            pe = radial_profile(e, c, c)
            pp = radial_profile(st.phi.astype(np.float64), c, c)
            outer = np.nanmedian(pe[c - 4:])
            cold = pe < cold_frac * outer
            r_cold = 0
            while r_cold < len(cold) and cold[r_cold]:
                r_cold += 1
            rows.append({"step": st.step_index, "r_cold": int(r_cold), "e_center": float(pe[0]),
                         "e_outer": float(outer), "phi_center": float(pp[0]),
                         "e_profile": pe.tolist(), "phi_profile": pp.tolist()})
    return {"kind": kind, "tension": tension, "n": n, "steps": steps, "sigma": sigma,
            "cold_frac": cold_frac, "rows": rows}


def plot_cold(results, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.6))
    for r in results:
        s = [x["step"] for x in r["rows"]]
        lab = f"{r['kind']} tension {r['tension']:g}"
        ax[0].plot(s, [x["r_cold"] for x in r["rows"]], label=lab)
        ax[1].plot(s, [x["e_center"] for x in r["rows"]], label=lab + " centre")
        ax[1].plot(s, [x["e_outer"] for x in r["rows"]], "--", label=lab + " outer")
    ax[0].set_ylabel("cold-core radius (cells)"); ax[0].set_xlabel("step"); ax[0].legend(fontsize=7)
    ax[1].set_yscale("log"); ax[1].set_ylabel("smoothed v^2/2"); ax[1].set_xlabel("step"); ax[1].legend(fontsize=6)
    for r in results:
        last = r["rows"][-1]
        ax[2].plot(last["phi_profile"], label=f"phi, tension {r['tension']:g}, step {last['step']}")
    ax[2].axhline(np.sqrt(5), color="k", lw=0.5); ax[2].set_xlabel("radius from centre"); ax[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def heating(kind="box", tensions=(0.0, 1.0, 5.0), n=32, steps=4000, every=250):
    """Mean kinetic energy v^2/2 and a lattice energy estimate over time. With tension 0 the rule is
    the ordinary phi^4 wave equation (variational, so energy only decays through damping). With tension
    > 0 the term c2(phi)*lap(phi) is not the variational derivative of any local energy."""
    out = []
    for t in tensions:
        cfg = Config(n=n, tension=t, boundary=source_boundary(kind))
        st = initial_state(cfg, kind)
        rows = []
        for _ in range(steps):
            st = step(st, cfg)
            if st.step_index % every == 0:
                p = st.phi.astype(np.float64)
                v = (p - st.phi_prev) / cfg.dt
                grad2 = sum((np.roll(p, -1, a) - p) ** 2 for a in range(3))
                V = -0.5 * cfg.pot_lin * p ** 2 + 0.25 * cfg.pot_cub * p ** 4 + cfg.pot_lin ** 2 / (4 * cfg.pot_cub)
                rows.append({"step": st.step_index, "kinetic": float(np.mean(0.5 * v * v)),
                             "phi4_energy": float(np.mean(0.5 * v * v + 0.5 * grad2 + V))})
        out.append({"tension": t, "rows": rows})
    return out


def variational_step(state, cfg):
    """EXPERIMENTAL VARIANT, not the source rule. Same ingredients, derived from the lattice energy
        E = sum_i v_i^2/2 + sum_links G_link (phi_j - phi_i)^2 / 2 + sum_i V(phi_i),
        G(phi) = 1/(1 + tension phi^2 + 1e-6), G_link = (G_i + G_j)/2, V = -pot_lin phi^2/2 + pot_cub phi^4/4,
    so amplitude still slows propagation, but force = -dE/dphi and leapfrog has no secular heating.
    Wrap boundary only (diagnostic)."""
    from complexity.core import State
    p = state.phi.astype(np.float64)
    G = 1.0 / (1.0 + cfg.tension * p ** 2 + 1e-6)
    dG = -2 * cfg.tension * p * G ** 2
    f = np.zeros_like(p)
    for a in range(3):
        for sh in (1, -1):
            q = np.roll(p, sh, a)
            Gq = np.roll(G, sh, a)
            d = q - p
            f += 0.5 * (G + Gq) * d - 0.25 * dG * d * d
    f += cfg.pot_lin * p - cfg.pot_cub * p ** 3
    vel = p - state.phi_prev
    new = p + (1 - cfg.damping * cfg.dt) * vel + cfg.dt ** 2 * f
    return State(phi=new, phi_prev=p, step_index=state.step_index + 1, rng_state=state.rng_state)


def lattice_energy(p, prev, cfg, variational):
    v = (p - prev) / cfg.dt
    G = 1.0 / (1.0 + cfg.tension * p ** 2 + 1e-6) if variational else np.ones_like(p)
    links = sum(0.5 * (G + np.roll(G, -1, a)) * (np.roll(p, -1, a) - p) ** 2 for a in range(3))
    V = -0.5 * cfg.pot_lin * p ** 2 + 0.25 * cfg.pot_cub * p ** 4 + cfg.pot_lin ** 2 / (4 * cfg.pot_cub)
    return float(np.mean(0.5 * v * v + 0.5 * links + V)), float(np.mean(0.5 * v * v))


def variant_check(tension=5.0, n=32, steps=4000, every=250):
    """Box initializer, periodic wrap so the variant and the source can be compared on one footing."""
    out = {}
    for name in ("source", "variational"):
        cfg = Config(n=n, tension=tension, boundary="wrap")
        st = initial_state(cfg, "box")
        rows = []
        for _ in range(steps):
            st = step(st, cfg) if name == "source" else variational_step(st, cfg)
            if st.step_index % every == 0:
                p = st.phi.astype(np.float64)
                E, K = lattice_energy(p, st.phi_prev.astype(np.float64), cfg, name == "variational")
                v = (p - st.phi_prev) / cfg.dt
                e = gaussian_filter(0.5 * v * v, 1.5, mode="wrap")
                pe = radial_profile(e, n // 2, n // 2)
                rows.append({"step": st.step_index, "energy": E, "kinetic": K,
                             "e_center": float(pe[0]), "e_outer": float(np.nanmedian(pe[n // 2 - 4:])),
                             "phi_center": float(radial_profile(p, n // 2, 2)[0])})
        out[name] = rows
    return out


def plot_summary(heat_path="results/diagnostics/heating.json", var_path="results/diagnostics/variant_check.json",
                 out="results/diagnostics/heating_variant.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    heat, var = json.load(open(heat_path)), json.load(open(var_path))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    for h in heat:
        ax[0].plot([r["step"] for r in h["rows"]], [r["kinetic"] for r in h["rows"]], label=f"source rule, tension {h['tension']:g}")
    ax[0].set_xlabel("step"); ax[0].set_ylabel("mean v^2/2 (box)"); ax[0].legend(fontsize=7)
    ax[0].set_title("best.py rule heats itself when tension > 0", fontsize=9)
    for name, rows in var.items():
        s = [r["step"] for r in rows]
        ax[1].plot(s, [r["e_center"] for r in rows], label=f"{name}: droplet centre")
        ax[1].plot(s, [r["e_outer"] for r in rows], "--", label=f"{name}: surroundings")
    ax[1].set_yscale("log"); ax[1].set_xlabel("step"); ax[1].set_ylabel("smoothed v^2/2")
    ax[1].set_title("cold droplet, tension 5 (wrap): finite lifetime in both rules", fontsize=9); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(out, dpi=90); plt.close(fig)


def plot_atlas_finals(atlas_dir="results/atlas", out="results/atlas/atlas_final_slices.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["box_t1_s0", "box_t5_s0", "sphere_t1_s0", "sphere_t5_s0", "torus_t1_s0", "torus_t5_s0"]
    fig, ax = plt.subplots(2, 6, figsize=(16, 5.6))
    for j, nm in enumerate(names):
        aux = np.load(os.path.join(atlas_dir, "checkpoints", f"{nm}_aux.npz"))
        for i, k in enumerate(("slice_midpoint", "slice_final")):
            ax[i, j].imshow(aux[k].T, origin="lower", cmap="RdBu_r", vmin=-2.6, vmax=2.6)
            ax[i, j].set_title(f"{nm} {'step 1000' if i == 0 else 'step 2000'}", fontsize=8)
            ax[i, j].set_xticks([]); ax[i, j].set_yticks([])
    fig.tight_layout(); fig.savefig(out, dpi=80); plt.close(fig)


if __name__ == "__main__":
    out = "results/diagnostics"
    os.makedirs(out, exist_ok=True)
    res = [cold_core("box", 1.0), cold_core("box", 5.0)]
    json.dump(res, open(os.path.join(out, "cold_core.json"), "w"))
    plot_cold(res, os.path.join(out, "cold_core.png"))
    for r in res:
        print(r["kind"], r["tension"], [(x["step"], x["r_cold"], round(x["e_center"], 3), round(x["e_outer"], 3),
                                         round(x["phi_center"], 2)) for x in r["rows"][::8]])
