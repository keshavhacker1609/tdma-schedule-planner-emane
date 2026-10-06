"""Slot assignment: heuristics for colouring the distance-2 conflict graph.

Minimum colouring is NP-hard, so the solver works in stages and keeps the
best result of each:

1. constructive greedy heuristics (DSATUR, largest-first, smallest-last);
2. randomised DSATUR restarts;
3. TabuCol local search that tries to remove one more colour at a time;
4. for small instances, an exact DSATUR branch-and-bound that either
   finds a better colouring or proves the current one optimal.

A clique lower bound is computed so the report can say how close the
result is to the optimum.
"""

import random
import time
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class ColoringResult:
    colors: dict                      # node -> slot index (0-based, compact)
    lower_bound: int
    optimal: bool
    trace: list = field(default_factory=list)   # (stage, colours) pairs

    @property
    def num_slots(self):
        return len(set(self.colors.values())) if self.colors else 0


# ---------------------------------------------------------------- helpers

def _adjacency(c):
    nodes = list(c.nodes)
    index = {n: i for i, n in enumerate(nodes)}
    adj = [set() for _ in nodes]
    for u, v in c.edges:
        adj[index[u]].add(index[v])
        adj[index[v]].add(index[u])
    return nodes, adj


def _count(colors):
    return len(set(colors))


def _greedy(adj, order):
    colors = [-1] * len(adj)
    for v in order:
        used = {colors[w] for w in adj[v] if colors[w] >= 0}
        k = 0
        while k in used:
            k += 1
        colors[v] = k
    return colors


def _dsatur(adj, rng=None):
    """DSATUR: always colour the vertex that sees the most distinct colours
    among its neighbours (ties: highest degree, then random if rng given)."""
    n = len(adj)
    colors = [-1] * n
    sat = [set() for _ in range(n)]
    uncolored = set(range(n))
    while uncolored:
        def key(v):
            tie = rng.random() if rng else 0.0
            return (len(sat[v]), len(adj[v]), tie)
        v = max(uncolored, key=key)
        k = 0
        while k in sat[v]:
            k += 1
        colors[v] = k
        uncolored.discard(v)
        for w in adj[v]:
            sat[w].add(k)
    return colors


def _smallest_last_order(adj):
    remaining = set(range(len(adj)))
    deg = {v: len(adj[v]) for v in remaining}
    out = []
    while remaining:
        v = min(remaining, key=lambda x: (deg[x], x))
        out.append(v)
        remaining.discard(v)
        for w in adj[v]:
            if w in remaining:
                deg[w] -= 1
    return out[::-1]


def _tabucol(adj, k, start, rng, max_iter):
    """Try to find a proper k-colouring (Hertz and de Werra, TabuCol)."""
    n = len(adj)
    col = [c if c < k else rng.randrange(k) for c in start]
    gamma = [[0] * k for _ in range(n)]
    for v in range(n):
        for w in adj[v]:
            gamma[v][col[w]] += 1
    conflicts = sum(gamma[v][col[v]] for v in range(n)) // 2
    if conflicts == 0:
        return col
    tabu = [[0] * k for _ in range(n)]
    best = conflicts
    for it in range(1, max_iter + 1):
        bad = [v for v in range(n) if gamma[v][col[v]] > 0]
        best_delta, moves = None, []
        for v in bad:
            cv = col[v]
            for c in range(k):
                if c == cv:
                    continue
                delta = gamma[v][c] - gamma[v][cv]
                if tabu[v][c] > it and conflicts + delta >= best:
                    continue
                if best_delta is None or delta < best_delta:
                    best_delta, moves = delta, [(v, c)]
                elif delta == best_delta:
                    moves.append((v, c))
        if not moves:
            continue
        v, c = rng.choice(moves)
        old = col[v]
        col[v] = c
        for w in adj[v]:
            gamma[w][old] -= 1
            gamma[w][c] += 1
        conflicts += best_delta
        tabu[v][old] = it + int(0.6 * len(bad)) + rng.randrange(10)
        best = min(best, conflicts)
        if conflicts == 0:
            return col
    return None


class _Abort(Exception):
    pass


def _exact(adj, upper, node_limit):
    """DSATUR branch and bound.  Looks for a colouring with fewer than
    `upper` colours.  Returns (colouring or None, search_completed)."""
    n = len(adj)
    colors = [-1] * n
    best = {"cols": None, "k": upper}
    visited = [0]

    def pick():
        choice, key = None, None
        for v in range(n):
            if colors[v] >= 0:
                continue
            s = len({colors[w] for w in adj[v] if colors[w] >= 0})
            kv = (s, len(adj[v]))
            if key is None or kv > key:
                choice, key = v, kv
        return choice

    def search(done, used):
        visited[0] += 1
        if visited[0] > node_limit:
            raise _Abort
        if done == n:
            best["cols"], best["k"] = colors[:], used
            return
        v = pick()
        forbidden = {colors[w] for w in adj[v] if colors[w] >= 0}
        for c in range(min(used + 1, best["k"] - 1)):
            if c in forbidden:
                continue
            colors[v] = c
            search(done + 1, max(used, c + 1))
            colors[v] = -1

    try:
        search(0, 0)
    except _Abort:
        return best["cols"], False
    return best["cols"], True


def _normalise(node_list, cols):
    """Renumber slots 0..k-1 in order of first appearance."""
    remap, out = {}, {}
    for node, col in zip(node_list, cols):
        remap.setdefault(col, len(remap))
        out[node] = remap[col]
    return out


def clique_lower_bound(c):
    if c.number_of_nodes() == 0:
        return 0
    return max(len(q) for q in nx.find_cliques(c))


# ---------------------------------------------------------------- driver

def optimise(c, seed=0, restarts=300, tabu_iters=20000, exact_nodes=500_000,
             exact_max_nodes=60, time_limit=20.0):
    """Colour conflict graph `c` with as few slots as the heuristics find."""
    rng = random.Random(seed)
    node_list, adj = _adjacency(c)
    n = len(node_list)
    if n == 0:
        return ColoringResult({}, 0, True, [])

    deadline = time.monotonic() + time_limit
    lower = clique_lower_bound(c)
    trace = []
    best, best_k = None, None

    def offer(stage, cols):
        nonlocal best, best_k
        k = _count(cols)
        if best is None or k < best_k:
            best, best_k = cols[:], k
        trace.append((stage, k))

    offer("DSATUR", _dsatur(adj))
    offer("largest-first", _greedy(adj, sorted(range(n), key=lambda v: -len(adj[v]))))
    offer("smallest-last", _greedy(adj, _smallest_last_order(adj)))

    if best_k > lower:
        for _ in range(restarts):
            if time.monotonic() > deadline:
                break
            cand = _dsatur(adj, rng)
            if _count(cand) < best_k:
                best, best_k = cand, _count(cand)
        trace.append((f"randomised DSATUR x{restarts}", best_k))

    while best_k > lower and time.monotonic() < deadline:
        found = _tabucol(adj, best_k - 1, best, rng, tabu_iters)
        if found is None:
            break
        best, best_k = found, _count(found)
        trace.append(("tabu search", best_k))

    optimal = best_k == lower
    if not optimal and n <= exact_max_nodes:
        better, finished = _exact(adj, best_k, exact_nodes)
        if better is not None:
            best, best_k = better, _count(better)
            trace.append(("exact branch-and-bound", best_k))
        optimal = finished
        if finished and better is None:
            trace.append(("exact branch-and-bound (proof)", best_k))
    if optimal:
        lower = best_k

    return ColoringResult(_normalise(node_list, best), lower, optimal, trace)
