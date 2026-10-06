"""Independent collision checker.

Deliberately does not reuse the graphs or the colouring code: it works
straight from the coordinates, so a bug in the optimiser cannot hide
itself here.
"""

import math
from itertools import combinations


def find_violations(nodes, slots, radio_range):
    """Return (a, b, reason) for every pair that breaks the schedule."""
    names = list(nodes)
    near = {a: {b for b in names if b != a and math.dist(nodes[a], nodes[b]) <= radio_range}
            for a in names}
    bad = []
    for a, b in combinations(names, 2):
        if slots[a] != slots[b]:
            continue
        if b in near[a]:
            bad.append((a, b, "direct link (1 hop)"))
        else:
            shared = near[a] & near[b]
            if shared:
                bad.append((a, b, f"hidden terminal at {sorted(shared)[0]} (2 hops)"))
    return bad


def reuse_pairs(slots):
    """Number of node pairs that legally share a slot (spatial reuse)."""
    return sum(1 for a, b in combinations(slots, 2) if slots[a] == slots[b])
