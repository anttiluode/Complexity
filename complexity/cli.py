"""Bounded commands.

  python -m complexity atlas --config configs/atlas.json --out results/atlas --max-seconds 3600
"""
import argparse
import json
import os
import time

from complexity.experiments import atlas_candidates, confirm, run_atlas
from complexity.morphology import select_candidate


def cmd_atlas(a):
    t0 = time.monotonic()
    camp = json.load(open(a.config))
    s = run_atlas(a.config, a.out, a.max_seconds)
    print(f"atlas status: {s['status']}  counts: {s.get('counts')}  pilot: {s.get('pilot')}")
    for r in s["runs"]:
        print(f"  {r['name']:16s} {r['status']:12s} steps={r.get('completed_steps')}  screen={r.get('screen')}")
    if s["status"] != "completed":
        return
    sel = select_candidate(atlas_candidates(a.out, camp))
    if sel is None:
        print("no candidate passes the morphology screen; memory branch stops here")
        json.dump({"candidate": None}, open(os.path.join(a.out, "selection.json"), "w"), indent=1)
        return
    frozen = {"kind": sel["kind"], "tension": sel["tension"], "campaign": camp, "screen": sel["screen"]}
    os.makedirs("configs", exist_ok=True)
    json.dump(frozen, open("configs/selected.json", "w"), indent=1)
    print(f"selected {sel['name']} -> configs/selected.json  {sel['screen']}")
    remaining = a.max_seconds - (time.monotonic() - t0)
    res = confirm(frozen, camp, os.path.join(a.out, "confirmation"), remaining)
    print(f"confirmation: {res['status']}")
    for r in res["runs"]:
        print(f"  {r['name']:18s} {r['status']} {r.get('screen')}")


def main():
    p = argparse.ArgumentParser(prog="complexity")
    sub = p.add_subparsers(dest="cmd", required=True)
    at = sub.add_parser("atlas")
    at.add_argument("--config", default="configs/atlas.json")
    at.add_argument("--out", default="results/atlas")
    at.add_argument("--max-seconds", type=float, default=3600)
    at.set_defaults(fn=cmd_atlas)
    a = p.parse_args()
    a.fn(a)
