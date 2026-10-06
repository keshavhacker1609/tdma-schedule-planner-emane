#!/usr/bin/env python3
"""Write a baseline schedule JSON using a plain distance-1 colouring.

Same file format as `schedule_optimizer.py --json-out`, so it can be pushed
through the same bridge and EMANE run for a side-by-side comparison.

    python emane/make_baseline.py out.json baseline.json
"""
import json
import math
import sys

import networkx as nx

src, dst = sys.argv[1], sys.argv[2]
s = json.load(open(src, encoding="utf-8"))
pos, rng = s["positions"], s["radio_range_m"]
g = nx.Graph()
g.add_nodes_from(pos)
names = list(pos)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if math.dist(pos[a], pos[b]) <= rng:
            g.add_edge(a, b)
col = nx.greedy_color(g, strategy="largest_first")
s["node_to_slot"] = {n: col[n] for n in names}
s["frame_length"] = max(col.values()) + 1
s["slot_to_nodes"] = {str(k): [n for n in names if col[n] == k] for k in range(s["frame_length"])}
s["provably_optimal"] = False
json.dump(s, open(dst, "w"), indent=2)
print(f"baseline: {s['frame_length']} slots")
