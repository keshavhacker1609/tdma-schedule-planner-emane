"""Radio topology: parsing node coordinates and building the graphs.

Two graphs are used throughout the project:

* the *connectivity graph* G: an edge joins two radios that are within
  radio range of each other (distance <= range, inclusive);
* the *conflict graph* C: an edge joins two radios that must not share a
  slot, i.e. radios that are 1 hop or 2 hops apart in G.
"""

import json
import math
import re
from itertools import combinations

import networkx as nx

DEFAULT_RANGE_M = 500.0


class TopologyError(ValueError):
    """Raised when the node input is malformed."""


def natural_key(name):
    """Sort key so that Node_2 comes before Node_10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def parse_nodes(text):
    """Parse the JSON node map: {"Node_01": [x, y], ...} -> {name: (x, y)}."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TopologyError(f"input is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or not raw:
        raise TopologyError("input must be a non-empty JSON object of name -> [x, y]")

    nodes = {}
    for name, pos in raw.items():
        if not isinstance(pos, (list, tuple)) or len(pos) not in (2, 3):
            raise TopologyError(f"{name}: expected [x, y] (or [x, y, z]), got {pos!r}")
        try:
            coords = tuple(float(v) for v in pos)
        except (TypeError, ValueError):
            raise TopologyError(f"{name}: coordinates must be numbers, got {pos!r}")
        if not all(math.isfinite(v) for v in coords):
            raise TopologyError(f"{name}: coordinates must be finite, got {pos!r}")
        nodes[str(name)] = coords
    return dict(sorted(nodes.items(), key=lambda kv: natural_key(kv[0])))


def distance(a, b):
    return math.dist(a, b)


def build_connectivity_graph(nodes, radio_range):
    """Radios are linked when they are within `radio_range` metres."""
    if radio_range <= 0:
        raise TopologyError("radio range must be positive")
    g = nx.Graph()
    g.add_nodes_from(nodes)
    for a, b in combinations(nodes, 2):
        d = distance(nodes[a], nodes[b])
        if d <= radio_range:
            g.add_edge(a, b, distance=d)
    return g


def build_conflict_graph(g):
    """Distance-2 conflict graph: connect every pair within two hops in G.

    Hop-1 pairs collide directly; hop-2 pairs collide at the shared
    neighbour (hidden terminal).  Anything further apart is free to reuse
    the slot.
    """
    c = nx.Graph()
    c.add_nodes_from(g)
    for u in g:
        one_hop = set(g[u])
        for v in one_hop:
            c.add_edge(u, v, kind="direct")
            for w in g[v]:
                if w != u and w not in one_hop and not c.has_edge(u, w):
                    c.add_edge(u, w, kind="hidden")
    return c
