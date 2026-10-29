"""Campaigns: morphology atlas (Task 2) with receipts, budget stops, resume and confirmation."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import time

import numpy as np

from complexity.core import Config, State, initial_state, source_boundary, step, save_state, load_state
from complexity.morphology import Tracker, describe, screen, select_candidate, thresholds

SLICE_KEYS = ("initial", "midpoint", "final")


def campaign_hash(camp: dict) -> str:
    return hashlib.sha256(json.dumps(camp, sort_keys=True).encode()).hexdigest()[:16]


def run_name(spec: dict, seed: int) -> str:
    return f"{spec['kind']}_t{spec['tension']:g}_s{seed}"


def _machine():
    import scipy
    return {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "platform": platform.platform(), "cpus": os.cpu_count()}


def _save_run_checkpoint(path, state, cfg, tracker, history, slices):
    save_state(path, state, cfg)
    extra = path.replace(".npz", "_aux.npz")
    np.savez_compressed(extra, tracker_prev=tracker.prev if tracker.prev is not None else np.zeros(0, bool),
                        tracker_started=np.array(tracker.started),
                        history=np.array(json.dumps(history)),
                        **{f"slice_{k}": v for k, v in slices.items()})


def _load_run_checkpoint(path, n):
    st, cfg = load_state(path)
    aux = np.load(path.replace(".npz", "_aux.npz"))
    tr = Tracker(n)
    prev = aux["tracker_prev"]
    tr.prev = prev if prev.size else None
    tr.started = bool(aux["tracker_started"])
    history = json.loads(str(aux["history"]))
    slices = {k[6:]: aux[k] for k in aux.files if k.startswith("slice_")}
    return st, cfg, tr, history, slices


def run_one(spec, camp, out_dir, deadline, record=None, seed=0, noise_std=0.0):
    """Advance one run toward camp['steps'], checking the deadline after every chunk."""
    n, steps = camp["n"], camp["steps"]
    every, chunk = camp.get("sample_every", 10), min(camp.get("chunk", 50), 50)
    name = run_name(spec, seed)
    ck_rel = f"checkpoints/{name}.npz"
    ck = os.path.join(out_dir, ck_rel)
    os.makedirs(os.path.dirname(ck), exist_ok=True)
    cfg = Config(n=n, tension=float(spec["tension"]), boundary=source_boundary(spec["kind"]), seed=seed)
    thr = thresholds(cfg.pot_lin, cfg.pot_cub)
    resumed_from = None
    if record and record.get("status") == "budget_stop" and os.path.exists(ck):
        st, cfg_l, tracker, history, slices = _load_run_checkpoint(ck, n)
        if cfg_l != cfg:
            raise ValueError("checkpoint config differs from campaign")
        resumed_from = st.step_index
    else:
        st = initial_state(cfg, spec["kind"])
        if noise_std > 0:
            rng = np.random.default_rng(seed)
            eps = rng.normal(0.0, noise_std, st.phi.shape).astype(st.phi.dtype)
            st = State(st.phi + eps, st.phi_prev + eps, 0, rng.bit_generator.state)   # same draw: velocity preserved
        tracker, history, slices = Tracker(n), [], {"initial": st.phi[:, :, n // 2].copy()}
    rec = {"name": name, "kind": spec["kind"], "tension": spec["tension"], "seed": seed,
           "noise_std": noise_std, "boundary": cfg.boundary, "config_hash": cfg.hash(),
           "checkpoint": ck_rel, "resumed_from": resumed_from}
    t_run = time.monotonic()
    try:
        while st.step_index < steps:
            for _ in range(min(chunk, steps - st.step_index)):
                st = step(st, cfg)
                if st.step_index % every == 0:
                    lab = {}
                    descs = [describe(st, cfg, t, labels_out=lab if i == 1 else None) for i, t in enumerate(thr)]
                    tr = tracker.update(lab["labels"], lab["volumes"])
                    history.append({"step": st.step_index, **tr,
                                    "levels": [{k: d[k] for k in ("n_components", "largest_volume",
                                                                  "positive_fraction", "touches_boundary")}
                                               for d in descs],
                                    "rms_phi": descs[0]["rms_phi"], "rms_v": descs[0]["rms_v"],
                                    "centroid": descs[1]["centroid"], "cov_eigs": descs[1]["cov_eigs"]})
                if st.step_index == steps // 2:
                    slices["midpoint"] = st.phi[:, :, n // 2].copy()
            if st.step_index < steps and time.monotonic() >= deadline:
                _save_run_checkpoint(ck, st, cfg, tracker, history, slices)
                rec.update(status="budget_stop", completed_steps=st.step_index,
                           seconds=time.monotonic() - t_run)
                return rec, history, slices
    except FloatingPointError as e:
        rec.update(status="failed", completed_steps=st.step_index, error=str(e),
                   seconds=time.monotonic() - t_run)
        return rec, history, slices
    slices["final"] = st.phi[:, :, n // 2].copy()
    _save_run_checkpoint(ck, st, cfg, tracker, history, slices)
    window = [h for h in history if h["step"] > steps - camp.get("screen_last", 500)]
    rec.update(status="completed", completed_steps=st.step_index, seconds=time.monotonic() - t_run,
               screen=screen(window, n ** 3))
    return rec, history, slices


def _write_metrics(path, history):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "track_ok", "event", "tracked_volume", "rms_phi", "rms_v"] +
                   [f"{k}_L{i}" for i in range(3) for k in ("n_components", "largest_volume", "positive_fraction")])
        for h in history:
            w.writerow([h["step"], h["track_ok"], h["event"], h["tracked_volume"], h["rms_phi"], h["rms_v"]] +
                       [lv[k] for lv in h["levels"] for k in ("n_components", "largest_volume", "positive_fraction")])


def plot_run(path, name, history, slices):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 5, figsize=(17, 3.3))
    for i, k in enumerate(SLICE_KEYS):
        if k in slices:
            im = ax[i].imshow(slices[k].T, origin="lower", cmap="RdBu_r", vmin=-2.6, vmax=2.6)
            ax[i].set_title(f"{name}: {k} (z = N/2)", fontsize=8)
            ax[i].set_xticks([]); ax[i].set_yticks([])
    fig.colorbar(im, ax=ax[2], fraction=0.046)
    s = [h["step"] for h in history]
    for L, style in zip(range(3), (":", "-", "--")):
        ax[3].plot(s, [h["levels"][L]["largest_volume"] for h in history], style, label=f"largest vol L{L}")
        ax[4].plot(s, [h["levels"][L]["n_components"] for h in history], style, label=f"components L{L}")
    ax[3].plot(s, [h["tracked_volume"] for h in history], "k", lw=0.6, label="tracked (L1)")
    for a in ax[3:]:
        a.set_xlabel("step"); a.legend(fontsize=6)
    ax[3].set_yscale("symlog")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def pilot(seconds_budget):
    """200 steps at N=24 (spec pilot) -> seconds per voxel-step, with describe() cost included."""
    cfg = Config(n=24, boundary="wrap")
    st = initial_state(cfg, "torus")
    t0 = time.monotonic()
    thr = thresholds()
    for i in range(200):
        st = step(st, cfg)
        if i % 10 == 0:
            for t in thr:
                describe(st, cfg, t)
    dt = time.monotonic() - t0
    return {"steps": 200, "n": 24, "seconds": dt, "sec_per_voxel_step": dt / (200 * 24 ** 3)}


def run_atlas(config_path: str, out_dir: str, max_seconds: float) -> dict:
    t_start = time.monotonic()
    deadline = t_start + max_seconds
    camp = json.load(open(config_path))
    h = campaign_hash(camp)
    os.makedirs(out_dir, exist_ok=True)
    sp = os.path.join(out_dir, "summary.json")
    prev = json.load(open(sp)) if os.path.exists(sp) else None
    if prev is not None and prev["campaign_hash"] != h:
        raise ValueError(f"{out_dir} holds results for campaign {prev['campaign_hash']}, not {h}; refusing to reuse")
    summary = prev or {"campaign_hash": h, "campaign": camp, "runs": [], "machine": _machine(),
                       "cumulative_seconds": 0.0}
    if camp.get("pilot", True) and "pilot" not in summary:
        p = pilot(max_seconds)
        est = p["sec_per_voxel_step"] * camp["n"] ** 3 * camp["steps"] * len(camp["runs"]) * 1.2
        summary["pilot"] = {**p, "estimated_atlas_seconds": est}
        if est > max_seconds:
            summary["status"] = "budget_estimate_exceeded"
            json.dump(summary, open(sp, "w"), indent=1)
            return summary
    records = {r["name"]: r for r in summary["runs"]}
    out_runs = []
    for order, spec in enumerate(camp["runs"]):
        name = run_name(spec, camp.get("seed", 0))
        r0 = records.get(name)
        if r0 and r0["status"] in ("completed", "failed"):
            out_runs.append(r0)
            continue
        rec, hist, slices = run_one(spec, camp, out_dir, deadline, r0, seed=camp.get("seed", 0))
        rec["order"] = order
        _write_metrics(os.path.join(out_dir, f"metrics_{name}.csv"), hist)
        if rec["status"] != "budget_stop":
            os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)
            plot_run(os.path.join(out_dir, "plots", f"{name}.png"), name, hist, slices)
            json.dump(hist, open(os.path.join(out_dir, f"history_{name}.json"), "w"))
        out_runs.append(rec)
        if rec["status"] == "budget_stop":
            break
    done = {r["name"] for r in out_runs}
    for order, spec in enumerate(camp["runs"]):
        nm = run_name(spec, camp.get("seed", 0))
        if nm not in done:
            out_runs.append(records.get(nm) or {"name": nm, "status": "not_run", "order": order})
    summary["runs"] = out_runs
    summary["cumulative_seconds"] = summary.get("cumulative_seconds", 0.0) + (time.monotonic() - t_start)
    statuses = [r["status"] for r in out_runs]
    summary["status"] = ("budget_stop" if "budget_stop" in statuses or "not_run" in statuses else "completed")
    summary["counts"] = {s: statuses.count(s) for s in set(statuses)}
    json.dump(summary, open(sp, "w"), indent=1)
    return summary


def atlas_candidates(out_dir, camp):
    rows = []
    for r in json.load(open(os.path.join(out_dir, "summary.json")))["runs"]:
        if r.get("status") != "completed":
            continue
        hist = json.load(open(os.path.join(out_dir, f"history_{r['name']}.json")))
        window = [x for x in hist if x["step"] > camp["steps"] - camp.get("screen_last", 500)]
        rows.append({"name": r["name"], "order": r["order"], "n_domain": camp["n"] ** 3, "history": window,
                     "kind": r["kind"], "tension": r["tension"]})
    return rows


def confirm(selected: dict, camp: dict, out_dir: str, max_seconds: float, seeds=(101, 102, 103)) -> dict:
    deadline = time.monotonic() + max_seconds
    spec = {"kind": selected["kind"], "tension": selected["tension"]}
    rows = []
    for s in seeds:
        rec, hist, slices = run_one(spec, camp, out_dir, deadline, None, seed=s, noise_std=1e-4)
        _write_metrics(os.path.join(out_dir, f"metrics_{rec['name']}.csv"), hist)
        if rec["status"] == "completed":
            os.makedirs(os.path.join(out_dir, "plots"), exist_ok=True)
            plot_run(os.path.join(out_dir, "plots", f"{rec['name']}.png"), rec["name"], hist, slices)
        rows.append(rec)
        if rec["status"] != "completed":
            break
    passed = len(rows) == len(seeds) and all(r["status"] == "completed" and r["screen"]["eligible"] for r in rows)
    status = "pass" if passed else ("budget_stop" if any(r["status"] == "budget_stop" for r in rows) else "fail")
    res = {"selected": spec, "seeds": list(seeds), "noise_std": 1e-4, "runs": rows, "status": status}
    json.dump(res, open(os.path.join(out_dir, "confirmation.json"), "w"), indent=1)
    return res
