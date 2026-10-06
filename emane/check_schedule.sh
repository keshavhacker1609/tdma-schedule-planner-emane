#!/bin/sh
# Ping every ordered pair of in-range nodes and report what got through.
# In-range pairs should answer; out-of-range pairs must not (pathloss events).
OUT=${1:-emane/build}
python3 - "$OUT" <<'PY'
import json, math, subprocess, sys
out = sys.argv[1]
s = json.load(open(f"{out}/schedule.json"))
nems = json.load(open(f"{out}/nems.json"))
pos, rng = s["positions"], s["radio_range_m"]
from concurrent.futures import ThreadPoolExecutor

pairs = [(a, b) for a in pos for b in pos if a < b]


def probe(pair):
    a, b = pair
    r = subprocess.run(["ip", "netns", "exec", f"nem{nems[a]['nem_id']}", "ping", "-c", "3", "-W", "2",
                        nems[b]["ip"]], capture_output=True)
    return pair, r.returncode == 0


ok = bad = 0
with ThreadPoolExecutor(max_workers=16) as pool:
    for (a, b), got in pool.map(probe, pairs):
        expect = math.dist(pos[a], pos[b]) <= rng
        if got == expect:
            ok += 1
        else:
            bad += 1
            print(f"MISMATCH {a}->{b}: expected {'reply' if expect else 'no reply'}")
print(f"{ok} pairs behaved as scheduled, {bad} mismatches")
sys.exit(1 if bad else 0)
PY
