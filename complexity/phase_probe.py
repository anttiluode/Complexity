"""Stage C phase analysis (spec: only if a repeatable oscillation with >= 3 cycles is measured).

Observable: mean phi over the pre-write droplet core (radius <= 4 cells around the centre), written
(+0.2 at the centre) vs untouched twin, float64, seed 201 state at step 1000. Reference frequency = peak of
the twin's spectrum. Lock-in in sliding windows of two periods gives amplitude and phase; phase difference
by circular_difference. Tests Astra's toy model: does amplitude recover while a phase offset remains?
"""
import json
import os

import numpy as np

from complexity.analysis import circular_difference, kick_profile
from complexity.core import kick, step
from complexity.stage_bc import CENTER, CFG, N, WRITE_STEP, noisy_initial, run_steps


def main(seed=201, amp=0.2, steps=1500, out="results/phase"):
    os.makedirs(out, exist_ok=True)
    base = run_steps(noisy_initial(seed), WRITE_STEP)
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    core = ((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2 + (Z - CENTER[2]) ** 2) <= 16
    prof = kick_profile(N, CENTER)
    sig = {}
    for name, st in (("twin", base.copy()), ("written", kick(base, CFG, prof, amp, "velocity")),
                     ("written_minus", kick(base, CFG, prof, -amp, "velocity"))):
        s = []
        for _ in range(steps):
            st = step(st, CFG)
            s.append(float(st.phi[core].mean()))
        sig[name] = np.array(s)
    tw = sig["twin"] - sig["twin"].mean()
    f = np.fft.rfftfreq(steps, d=1.0)
    k = np.argmax(np.abs(np.fft.rfft(tw * np.hanning(steps)))[1:]) + 1
    omega = 2 * np.pi * f[k]                      # rad per step
    period = 2 * np.pi / omega
    win = int(round(2 * period))
    t = np.arange(steps)
    rows = []
    for c in range(win, steps - win, max(1, win // 2)):
        sl = slice(c - win // 2, c + win // 2)
        ref = np.exp(-1j * omega * t[sl])
        z = {n: 2 * np.mean((v[sl] - v[sl].mean()) * ref) for n, v in sig.items()}
        rows.append({"step": int(c), "amp_twin": float(abs(z["twin"])), "amp_written": float(abs(z["written"])),
                     "amp_written_minus": float(abs(z["written_minus"])),
                     "dphase_plus": float(circular_difference(np.angle(z["written"]), np.angle(z["twin"]))),
                     "dphase_minus": float(circular_difference(np.angle(z["written_minus"]), np.angle(z["twin"]))),
                     "mean_shift_plus": float(sig["written"][sl].mean() - sig["twin"][sl].mean())})
    res = {"seed": seed, "amp": amp, "omega_rad_per_step": float(omega), "period_steps": float(period),
           "cycles_observed": float(steps / period), "window": win, "rows": rows,
           "rms_signal_diff_plus": float(np.sqrt(np.mean((sig["written"] - sig["twin"]) ** 2)))}
    json.dump(res, open(os.path.join(out, "phase.json"), "w"), indent=1)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 3.4))
    ax[0].plot(t[:300], sig["twin"][:300], label="twin"); ax[0].plot(t[:300], sig["written"][:300], label="written +0.2")
    ax[0].set_xlabel("steps after write"); ax[0].set_ylabel("mean phi, droplet core"); ax[0].legend(fontsize=7)
    s_ = [r["step"] for r in rows]
    ax[1].plot(s_, [r["amp_twin"] for r in rows], label="twin"); ax[1].plot(s_, [r["amp_written"] for r in rows], label="written +")
    ax[1].plot(s_, [r["amp_written_minus"] for r in rows], label="written -"); ax[1].set_ylabel("oscillation amplitude"); ax[1].legend(fontsize=7)
    ax[2].plot(s_, [r["dphase_plus"] for r in rows], label="+ write"); ax[2].plot(s_, [r["dphase_minus"] for r in rows], label="- write")
    ax[2].set_ylabel("phase vs twin (rad)"); ax[2].axhline(0, color="k", lw=0.5); ax[2].legend(fontsize=7)
    for a in ax[1:]:
        a.set_xlabel("steps after write")
    fig.tight_layout(); fig.savefig(os.path.join(out, "phase.png"), dpi=90); plt.close(fig)
    return res


if __name__ == "__main__":
    r = main()
    print(f"omega={r['omega_rad_per_step']:.4f} rad/step, period={r['period_steps']:.1f} steps, cycles={r['cycles_observed']:.1f}")
    for x in r["rows"][::6]:
        print(f"step {x['step']:5d} amp twin {x['amp_twin']:.4f} +{x['amp_written']:.4f} -{x['amp_written_minus']:.4f} "
              f"dphase + {x['dphase_plus']:+.4f} - {x['dphase_minus']:+.4f} mean shift {x['mean_shift_plus']:+.2e}")
