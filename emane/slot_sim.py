#!/usr/bin/env python3
"""Slot-by-slot replay of a schedule, without EMANE.

This mirrors what the EMANE TDMA model enforces on the air: in each slot
only the scheduled nodes transmit, and a receiver decodes a frame only if
exactly one transmitter is audible to it (a second audible transmitter is
a collision).  Running it on the optimiser's schedule and on a naive
distance-1 colouring shows why the two-hop rule matters.

    python emane/slot_sim.py examples/grid_16.schedule.json
"""

import argparse
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import networkx as nx  # noqa: E402


def replay(pos, rng, node_to_slot):
    """Every node broadcasts once per frame in its slot.  Returns counters."""
    names = list(pos)
    audible = {n: {m for m in names if m != n and math.dist(pos[n], pos[m]) <= rng} for n in names}
    frame = max(node_to_slot.values()) + 1
    delivered = collided = 0
    for s in range(frame):
        tx = {n for n in names if node_to_slot[n] == s}
        for r in names:
            if r in tx:
                continue                       # half duplex
            heard = audible[r] & tx
            if len(heard) == 1:
                delivered += 1
            elif len(heard) > 1:
                collided += len(heard)
    return frame, delivered, collided


def random_assignment(pos, slots):
    r = random.Random(1)
    return {n: r.randrange(slots) for n in pos}


def naive_distance1_colouring(pos, rng):
    g = nx.Graph()
    g.add_nodes_from(pos)
    names = list(pos)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if math.dist(pos[a], pos[b]) <= rng:
                g.add_edge(a, b)
    return nx.greedy_color(g, strategy="largest_first")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("schedule")
    a = p.parse_args()
    sched = json.load(open(a.schedule, encoding="utf-8"))
    pos = {n: tuple(v) for n, v in sched["positions"].items()}
    rng = sched["radio_range_m"]

    # expected deliveries = every (transmitter, in-range receiver) pair
    links = sum(1 for n in pos for m in pos if n != m and math.dist(pos[n], pos[m]) <= rng)

    rows = [("distance-2 schedule (this project)", sched["node_to_slot"]),
            ("naive distance-1 colouring", naive_distance1_colouring(pos, rng)),
            ("random assignment, same slot count", random_assignment(pos, sched["frame_length"]))]
    print(f"{'schedule':38}{'slots':>6}{'delivered':>11}{'collided':>10}   (of {links} directed links)")
    for label, slots in rows:
        frame, ok, bad = replay(pos, rng, slots)
        print(f"{label:38}{frame:>6}{ok:>11}{bad:>10}")


if __name__ == "__main__":
    main()
