"""Task 2: budget stops, resume, and config-hash protection."""
import json

import pytest

from complexity.experiments import run_atlas


def _cfg(tmp_path, steps=120, n=10):
    p = tmp_path / "atlas.json"
    p.write_text(json.dumps({"n": n, "steps": steps, "sample_every": 10, "screen_last": 60,
                             "chunk": 10, "pilot": False,
                             "runs": [{"kind": "box", "tension": 1.0}]}))
    return str(p)


def test_budget_stop_then_resume(tmp_path):
    cfg = _cfg(tmp_path)
    out = tmp_path / "out"
    s1 = run_atlas(cfg, str(out), max_seconds=0.0)
    r1 = s1["runs"][0]
    assert s1["status"] == "budget_stop" and r1["status"] == "budget_stop"
    assert 0 < r1["completed_steps"] < 120
    assert (out / r1["checkpoint"]).exists()
    s2 = run_atlas(cfg, str(out), max_seconds=600.0)
    r2 = s2["runs"][0]
    assert r2["status"] == "completed" and r2["completed_steps"] == 120
    assert r2["resumed_from"] == r1["completed_steps"]       # continued, not rerun


def test_changed_config_refuses_reuse(tmp_path):
    out = tmp_path / "out"
    run_atlas(_cfg(tmp_path), str(out), max_seconds=0.0)
    with pytest.raises(ValueError):
        run_atlas(_cfg(tmp_path, steps=130), str(out), max_seconds=600.0)
