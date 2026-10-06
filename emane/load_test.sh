#!/bin/sh
# Every node pings its nearest in-range neighbour at the same time (50 probes, 100 ms apart)
# and the loss is averaged.  A collision-free schedule should lose (almost) nothing.
OUT=${1:-emane/build}
python3 - "$OUT" <<'PY'
import json, math, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

out = sys.argv[1]
s = json.load(open(f"{out}/schedule.json"))
nems = json.load(open(f"{out}/nems.json"))
pos, rng = s["positions"], s["radio_range_m"]


def nearest(a):
    cand = [(math.dist(pos[a], pos[b]), b) for b in pos if b != a and math.dist(pos[a], pos[b]) <= rng]
    return min(cand)[1] if cand else None


def ping(args, count, gap):
    a, b = args
    r = subprocess.run(["ip", "netns", "exec", f"nem{nems[a]['nem_id']}", "ping", "-c", str(count),
                        "-i", str(gap), "-W", "1", nems[b]["ip"]], capture_output=True, text=True)
    m = re.search(r"(\d+(?:\.\d+)?)% packet loss", r.stdout)
    return float(m.group(1)) if m else 100.0


pairs = [(a, nearest(a)) for a in pos if nearest(a)]
with ThreadPoolExecutor(max_workers=len(pairs)) as pool:
    list(pool.map(lambda p: ping(p, 3, 0.5), pairs))                 # warm ARP caches
    loss = list(pool.map(lambda p: ping(p, 50, 0.1), pairs))
print(f"frame length {s['frame_length']} slots, {len(pairs)} simultaneous flows, "
      f"mean loss {sum(loss) / len(loss):.1f}%, worst flow {max(loss):.0f}%")
PY
