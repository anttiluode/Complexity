"""Frozen, grouped held-out prediction of a droplet's changed probe response.

See docs/superpowers/plans/2026-10-29-compact-predictive-state.md.
No solver changes; features use only pre-probe histories. CPU, sequential,
streaming full-field norms, small sensor targets, resumable droplet receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import scipy

from complexity.analysis import iou, kick_profile, recovered
from complexity.core import Config, kick, step
from complexity.droplet import droplet_mask, equivalent_radius
from complexity.many_droplets import init_bubble

WAITS = (300, 600, 1000)
TRAIN_IDS = (0, 2, 4, 6, 8)
PROBE = 0.002
WRITE = 0.2
WINDOW = 192
HORIZON = 50
MODELS = ('context', 'shape_context', 'delta_state', 'absolute_state_context')


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('simulation budget exhausted')


def harmonic_state(series, omega):
    """LS coefficients of A*cos(omega*t+phase), t=0 at the last sample."""
    y = np.asarray(series, dtype=float)
    if y.ndim != 1 or len(y) < 4 or not np.isfinite(y).all():
        raise ValueError('finite 1D history of at least four samples required')
    t = np.arange(1-len(y), 1)
    design = np.column_stack([np.ones(len(y)), np.cos(omega*t), np.sin(omega*t)])
    mean, c, s = np.linalg.lstsq(design, y, rcond=None)[0]
    amp = float(np.hypot(c, s))
    residual = float(np.linalg.norm(y-design @ [mean, c, s]) / max(np.linalg.norm(y-y.mean()), 1e-12))
    return dict(mean=float(mean), cos=float(c), sin=float(s), amplitude=amp,
                phase=float(np.arctan2(-s, c)), phase_valid=bool(amp >= 1e-8), relative_residual=residual)


def grouped_split(ids, train_ids=TRAIN_IDS):
    mask = np.isin(ids, train_ids)
    if not mask.any() or mask.all():
        raise ValueError('both train and held-out groups required')
    return np.flatnonzero(mask), np.flatnonzero(~mask)


def ridge_predict(train_x, train_y, test_x):
    """Fixed quadratic ridge; every centering/scaling statistic uses training only."""
    train_x, test_x = np.asarray(train_x, float), np.asarray(test_x, float)
    center, scale = train_x.mean(0), train_x.std(0)
    scale = np.where(scale < 1e-12, 1., scale)
    a, b = (train_x-center)/scale, (test_x-center)/scale
    ii, jj = np.triu_indices(a.shape[1])
    a = np.column_stack([a, a[:, ii]*a[:, jj]])
    b = np.column_stack([b, b[:, ii]*b[:, jj]])
    center, scale = a.mean(0), a.std(0)
    scale = np.where(scale < 1e-12, 1., scale)
    a, b = (a-center)/scale, (b-center)/scale
    y = np.asarray(train_y, float)
    ym = y.mean(0)
    coef = np.linalg.solve(a.T @ a + np.eye(a.shape[1]), a.T @ (y-ym))
    return b @ coef + ym


def relative_error(prediction, target):
    denominator = np.linalg.norm(target)
    return float(np.linalg.norm(prediction-target)/denominator) if denominator > 1e-12 else None


def observe_pairs(states, cfg, profile, horizon, points, deadline):
    arms = {k: [s.copy(), kick(s, cfg, profile, PROBE, 'velocity')] for k, s in states.items()}
    names = [k for k in states if k != 'sham']
    sensors = tuple(np.array(points).T)
    targets = {k: [] for k in names}
    diff_sq = {k: 0. for k in names}
    sham_sq, count = 0., 0
    for _ in range(horizon):
        check_deadline(deadline)
        responses = {}
        for k, (a, b) in arms.items():
            a, b = step(a, cfg), step(b, cfg)
            arms[k] = [a, b]
            responses[k] = b.phi-a.phi
        ref = responses['sham']
        sham_sq += float(np.sum(ref*ref))
        count += ref.size
        for k in names:
            d = responses[k]-ref
            diff_sq[k] += float(np.sum(d*d))
            targets[k].append(d[sensors]/PROBE)
    denom = max(np.sqrt(sham_sq/count), 1e-12)
    return ({k: np.asarray(v) for k, v in targets.items()},
            {k: dict(D=float(np.sqrt(diff_sq[k]/count)), E=float(np.sqrt(diff_sq[k]/count)/denom)) for k in names})


def shape_state(mask, center):
    coords = np.argwhere(mask)
    if not len(coords):
        return [0.] * 7
    centroid = coords.mean(0)
    cov = (coords-centroid).T @ (coords-centroid)/len(coords)
    return [equivalent_radius(mask), *(centroid-center), *np.linalg.eigvalsh(cov)]


def specs():
    out = [dict(n=32, tension=t, r=r) for t in (3., 5., 8.) for r in (4, 5, 6)]
    out += [dict(n=40, tension=5., r=6), dict(n=40, tension=5., r=7)]
    return [dict(id=i, **s) for i, s in enumerate(out)]


def collect_droplet(spec, deadline):
    cfg = Config(n=spec['n'], tension=spec['tension'], boundary='nearest', dtype='float64', seed=7)
    st = init_bubble(cfg, spec['r'], seed=7)
    for _ in range(1000):
        check_deadline(deadline)
        st = step(st, cfg)
    center = np.array([cfg.n//2]*3)
    grid = np.indices(st.phi.shape)
    core = np.sum((grid-center[:, None, None, None])**2, axis=0) <= 16
    points = [tuple(center)]
    for axis in range(3):
        for offset in (-2, 2):
            point = center.copy(); point[axis] += offset
            points.append(tuple(point))
    profile = kick_profile(cfg.n, center)
    states = {'sham': st, 'plus': kick(st, cfg, profile, WRITE, 'velocity'),
              'minus': kick(st, cfg, profile, -WRITE, 'velocity')}
    series = {k: [] for k in states}
    mask_times = {w-j for w in WAITS for j in range(20)}
    rec_history = {k: [] for k in ('plus', 'minus')}
    rows = []
    for t in range(1, max(WAITS)+1):
        check_deadline(deadline)
        for k in states:
            states[k] = step(states[k], cfg)
            series[k].append(float(states[k].phi[core].mean()))
        if t in mask_times:
            masks = {k: droplet_mask(v, cfg)[0] for k, v in states.items()}
            for k in rec_history:
                rec_history[k].append(recovered(masks[k], masks['sham']))
        if t not in WAITS:
            continue
        hs = {k: harmonic_state(v[-WINDOW:], np.sqrt(2)*cfg.dt) for k, v in series.items()}
        shapes = {k: shape_state(m, center) for k, m in masks.items()}
        target, metrics = observe_pairs(states, cfg, profile, HORIZON, points, deadline)
        for k, sign in (('plus', 1), ('minus', -1)):
            row = dict(spec, wait=t, sign=sign, recovered=bool(all(rec_history[k][-20:])),
                       raw_iou=iou(masks[k], masks['sham']), sham_state=hs['sham'], written_state=hs[k],
                       sham_shape=shapes['sham'], written_shape=shapes[k], **metrics[k], target=target[k].tolist())
            rows.append(row)
    return rows


def features(row, model):
    context = [row['tension'], row['n'], row['r'], row['wait'], row['sign']]
    sham, written = row['sham_state'], row['written_state']
    if model == 'context':
        return context
    if model == 'shape_context':
        a, b = np.array(row['sham_shape']), np.array(row['written_shape'])
        return context + a.tolist() + (b-a).tolist()
    if model == 'delta_state':
        dphase = written['phase']-sham['phase']
        return [written['amplitude']-sham['amplitude'], np.sin(dphase), 1-np.cos(dphase), row['tension']]
    if model == 'absolute_state_context':
        return context + [sham['cos'], sham['sin'], written['cos']-sham['cos'], written['sin']-sham['sin']]
    raise ValueError(model)


def evaluate(rows, targets):
    expected = {(i, w, s) for i in range(11) for w in WAITS for s in (-1, 1)}
    keys = [(r['id'], r['wait'], r['sign']) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('complete, unique 11-droplet dataset required')
    if not all(r[k]['phase_valid'] for r in rows for k in ('sham_state', 'written_state')):
        raise ValueError('phase unidentifiable; do not score compact-state claim')
    ids = np.array([r['id'] for r in rows])
    tr, te = grouped_split(ids)
    y = np.asarray(targets).reshape(len(rows), -1)
    if not np.isfinite(y).all():
        raise ValueError('non-finite target')
    predictions = {'zero': np.zeros_like(y[te]), 'mean': np.tile(y[tr].mean(0), (len(te), 1))}
    counts = {}
    for name in MODELS:
        x = np.asarray([features(r, name) for r in rows])
        predictions[name] = ridge_predict(x[tr], y[tr], x[te])
        counts[name] = dict(raw=x.shape[1], quadratic=x.shape[1]+x.shape[1]*(x.shape[1]+1)//2)
    scores = {}
    for name, pred in predictions.items():
        by_group = {str(g): relative_error(pred[ids[te] == g], y[te][ids[te] == g]) for g in np.unique(ids[te])}
        rec = np.array([rows[i]['recovered'] for i in te])
        scores[name] = dict(relative_rmse=relative_error(pred, y[te]), by_droplet=by_group,
                           recovered_relative_rmse=relative_error(pred[rec], y[te][rec]),
                           grid32_relative_rmse=relative_error(pred[ids[te] < 9], y[te][ids[te] < 9]),
                           grid40_relative_rmse=relative_error(pred[ids[te] >= 9], y[te][ids[te] >= 9]))
    baselines = ('zero', 'mean', 'context', 'shape_context')
    best = min(scores[k]['relative_rmse'] for k in baselines)
    for name in ('delta_state', 'absolute_state_context'):
        score = scores[name]
        wins = sum(v <= 0.5 and v <= .75*min(scores[b]['by_droplet'][g] for b in baselines)
                   for g, v in score['by_droplet'].items())
        score['groups_passing'] = int(wins)
        score['screen_pass'] = bool(score['relative_rmse'] <= 0.5 and score['relative_rmse'] <= .75*best and wins >= 4)
    return dict(scores=scores, feature_counts=counts, train_ids=list(TRAIN_IDS),
                test_ids=sorted(set(ids[te].tolist())), train_rows=len(tr), test_rows=len(te),
                recovered_rows=sum(r['recovered'] for r in rows),
                max_harmonic_relative_residual=max(r[k]['relative_residual'] for r in rows for k in ('sham_state', 'written_state'))), predictions, te


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def read_receipt(path, protocol_hash):
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data['protocol_hash'] != protocol_hash:
        raise ValueError('protocol/code hash changed; use a new output directory')
    return data if data['status'] == 'complete' else None


def protocol():
    root = Path(__file__).resolve().parent.parent
    paths = ['complexity/'+n+'.py' for n in ('predictive', 'core', 'analysis', 'droplet', 'many_droplets')]
    paths += ['docs/superpowers/plans/2026-10-29-compact-predictive-state.md']
    source = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    value = dict(specs=specs(), waits=WAITS, train_ids=TRAIN_IDS, window=WINDOW, probe=PROBE,
                 write=WRITE, horizon=HORIZON, sources=source, numpy=np.__version__, scipy=scipy.__version__)
    value['hash'] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def campaign(out, max_seconds):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    proto = protocol()
    manifest_path = out/'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text())['hash'] != proto['hash']:
        raise ValueError('protocol/code hash changed; use a new output directory')
    atomic_json(manifest_path, proto)
    summary_path = out/'summary.json'
    prior_seconds = json.loads(summary_path.read_text()).get('simulation_seconds', 0.) if summary_path.exists() else 0.
    started = time.monotonic()
    deadline = started + max(0., max_seconds-prior_seconds)
    all_rows = []
    status = 'complete'
    for spec in specs():
        path = out/f"droplet_{spec['id']:02d}.json"
        data = read_receipt(path, proto['hash'])
        if data is None:
            tick = time.monotonic()
            try:
                rows = collect_droplet(spec, deadline)
            except TimeoutError:
                status = 'budget_stop'
                break
            data = dict(protocol_hash=proto['hash'], status='complete', spec=spec,
                        seconds=time.monotonic()-tick, rows=rows)
            atomic_json(path, data)
            print(f"droplet {spec['id']}: {data['seconds']:.1f}s; "
                  f"recovered {sum(r['recovered'] for r in rows)}/6", flush=True)
        all_rows.extend(data['rows'])
    summary = dict(status=status, protocol_hash=proto['hash'], completed_droplets=len(all_rows)//6,
                   simulation_seconds=prior_seconds+time.monotonic()-started,
                   python=platform.python_version(), machine=platform.machine())
    try:
        summary['implementation_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        summary['implementation_commit'] = 'unknown'
    atomic_json(summary_path, summary)
    if status == 'complete':
        targets = np.array([r['target'] for r in all_rows])
        assessment, predictions, test = evaluate(all_rows, targets)
        summary['assessment'] = assessment
        atomic_json(summary_path, summary)
        np.savez_compressed(out/'predictions.npz', target=targets[test], test_row_indices=test, **predictions)
        make_plot(out, assessment)
        print(json.dumps(assessment, indent=2), flush=True)
    return summary


def make_plot(out, assessment):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    scores = assessment['scores']
    fig, ax = plt.subplots(figsize=(9, 4))
    names = list(scores)
    ax.barh(names, [scores[n]['relative_rmse'] for n in names], color='#4363a3')
    ax.axvline(1, color='gray', linestyle='--', label='predict no change')
    ax.axvline(.5, color='#b04a4a', linestyle=':', label='absolute error gate')
    ax.set_xlabel('Held-out waveform relative RMSE (lower is better)')
    ax.set_title('Six held-out droplets; both signs and three waits')
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(Path(out)/'prediction_errors.png', dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='results/predictive')
    parser.add_argument('--max-seconds', type=float, default=600.)
    args = parser.parse_args()
    if not np.isfinite(args.max_seconds) or args.max_seconds <= 0:
        parser.error('--max-seconds must be positive and finite')
    campaign(args.out, args.max_seconds)
