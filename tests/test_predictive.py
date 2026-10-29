"""Protect measurement timing, held-out groups, and probe-subtraction semantics."""
import time

import numpy as np
import pytest

from complexity import predictive as p
from complexity.analysis import kick_profile
from complexity.core import Config, initial_state, kick, step


def test_harmonic_state_uses_probe_time_reference_without_fft_bin_bias():
    t = np.arange(-191, 1)
    out = p.harmonic_state(2.2 + 0.17 * np.cos(0.141421356 * t + 2.9), 0.141421356)
    assert out['amplitude'] == pytest.approx(0.17, abs=1e-12)
    assert out['phase'] == pytest.approx(2.9, abs=1e-12)
    assert out['relative_residual'] < 1e-11
    assert p.harmonic_state(np.ones(192), 0.1414)['phase_valid'] is False


def test_whole_droplets_stay_in_one_split():
    groups = np.repeat(np.arange(11), 6)
    train, test = p.grouped_split(groups, [0, 2, 4, 6, 8])
    assert len(train) == 30 and len(test) == 36
    assert set(groups[train]).isdisjoint(groups[test])
    with pytest.raises(ValueError):
        p.grouped_split(groups, list(range(11)))


def test_ridge_fits_known_relation_and_does_not_scale_on_test_values():
    x = np.linspace(-2, 2, 100)[:, None]
    y = np.column_stack([3*x[:, 0] + 2, -2*x[:, 0] + 1])
    ordinary = p.ridge_predict(x, y, np.array([[0.3]]))
    contaminated = p.ridge_predict(x, y, np.array([[0.3], [1e8]]))
    np.testing.assert_allclose(ordinary[0], [2.9, 0.4], atol=0.02)
    np.testing.assert_array_equal(ordinary[0], contaminated[0])


def test_relative_error_zero_baseline_and_exact_fit():
    y = np.array([[1., -2.], [3., 4.]])
    assert p.relative_error(np.zeros_like(y), y) == 1.0
    assert p.relative_error(y, y) == 0.0
    assert p.relative_error(y, np.zeros_like(y)) is None


def test_streaming_probe_equals_direct_response_difference():
    cfg = Config(n=8, dtype='float64')
    base = initial_state(cfg, 'box')
    profile = kick_profile(8, (4, 4, 4))
    states = {'sham': base, 'plus': kick(base, cfg, profile, 0.2, 'velocity')}
    points = [(4, 4, 4), (3, 4, 4)]
    target, metrics = p.observe_pairs(states, cfg, profile, 4, points, time.monotonic()+30)
    raw = {}
    for name, st in states.items():
        a, b = st.copy(), kick(st, cfg, profile, 0.002, 'velocity')
        series = []
        for _ in range(4):
            a, b = step(a, cfg), step(b, cfg)
            series.append(b.phi-a.phi)
        raw[name] = np.array(series)
    diff = raw['plus']-raw['sham']
    expected = np.stack([diff[:, x, y, z] for x, y, z in points], axis=1)/0.002
    np.testing.assert_allclose(target['plus'], expected, atol=1e-15)
    assert metrics['plus']['D'] == pytest.approx(np.sqrt(np.mean(diff**2)))


def test_deadline_stops_before_simulation():
    with pytest.raises(TimeoutError):
        p.check_deadline(time.monotonic()-1)


def test_resume_requires_exact_protocol_and_complete_droplet(tmp_path):
    import json
    path = tmp_path/'droplet.json'
    path.write_text(json.dumps({'protocol_hash': 'old', 'status': 'complete', 'rows': []}))
    with pytest.raises(ValueError, match='protocol'):
        p.read_receipt(path, 'new')
    path.write_text(json.dumps({'protocol_hash': 'new', 'status': 'budget_stop', 'rows': []}))
    assert p.read_receipt(path, 'new') is None


def test_evaluation_rejects_partial_dataset():
    with pytest.raises(ValueError, match='complete'):
        p.evaluate([], np.empty((0, 50, 7)))


def test_resume_charges_completed_receipts_when_summary_is_missing(tmp_path, monkeypatch):
    # A saved droplet can outlive the parent process and its absent summary.
    p.atomic_json(tmp_path/'droplet_00.json', dict(protocol_hash=p.protocol()['hash'],
                  status='complete', seconds=590., rows=[]))
    def stop_at_next_droplet(spec, deadline):
        raise TimeoutError('represent unavailable remaining simulation time')
    monkeypatch.setattr(p, 'collect_droplet', stop_at_next_droplet)
    result = p.campaign(tmp_path, 600.)
    assert result['status'] == 'budget_stop'
    assert 590. <= result['simulation_seconds'] < 591.


def test_interrupted_attempt_reserves_budget_before_starting(tmp_path, monkeypatch):
    # Replace expensive field evolution with interruption; exercise real disk bookkeeping.
    import json
    def interrupted(spec, deadline):
        raise KeyboardInterrupt
    monkeypatch.setattr(p, 'collect_droplet', interrupted)
    with pytest.raises(KeyboardInterrupt):
        p.campaign(tmp_path, 60.)
    receipt = json.loads((tmp_path/'summary.json').read_text())
    assert receipt['status'] == 'running'
    assert receipt['simulation_seconds'] == 60.
    # No surviving process can say how much of the interrupted allocation was spent.
    result = p.campaign(tmp_path, 60.)
    assert result['status'] == 'budget_stop'
    assert result['simulation_seconds'] >= 60.
