# Design Document: TDMA Schedule Planner

## 1. Problem

Radios share one frequency and take turns in time slots. Two radios that can
hear each other, or that can both be heard by a third radio, must not
transmit in the same slot. Radios far enough apart may reuse a slot. The goal
is a short repeating frame (few slots) with no collisions.

## 2. Model

**Connectivity graph G.** One vertex per radio. An edge joins two radios when
their Euclidean distance is at most 500 m. The brief says "within 500 meters",
so the boundary is inclusive (a pair at exactly 500.0 m is linked; tested).
Coordinates may be 2-D or 3-D.

**Conflict graph C.** Two radios conflict if they are 1 hop apart in G
(direct interference) or 2 hops apart (hidden terminal: A and C both reach B,
so their frames collide at B even though A and C cannot hear each other).
C is the square of G (`G^2`), built explicitly in
`topology.build_conflict_graph`, which also records whether each conflict is
direct or hidden.

**Slot assignment = proper vertex colouring of C.** Colours are slot numbers.
Adjacent vertices in C get different slots, so the schedule is conflict-free
by construction, and any two radios more than two hops apart are free to
share a slot. That is the spatial reuse, and it falls out of the model rather
than being a separate step.

Minimising the number of colours is NP-hard, so the quality question is how
good a heuristic we can build, and how close we can show it is to optimal.

## 3. Algorithm

`coloring.optimise` runs a pipeline and keeps the best result from each
stage:

| Stage | What it does | Why |
|---|---|---|
| Lower bound | Maximum clique of C | Every radio in a clique conflicts with all the others, so the frame needs at least that many slots. Gives a target and a quality statement. |
| DSATUR | Colour the vertex that sees the most distinct neighbour colours next; ties by degree | Strong, fast constructive heuristic; exact on bipartite graphs |
| Largest-first, smallest-last | Greedy over two classic orderings | Cheap diversity; sometimes beats DSATUR on odd structures |
| Randomised DSATUR | 300 restarts with random tie-breaks | Escapes unlucky tie decisions |
| TabuCol | Local search: fix k = best - 1 colours, move conflicting vertices between colours with a tabu list, repeat until no conflicts or the iteration budget runs out | Can remove colours that greedy methods cannot |
| Exact search | DSATUR branch-and-bound, up to 60 nodes and a node budget | Either finds a better colouring or proves the current one optimal |

The search stops as soon as the colour count equals the clique lower bound,
at which point the result is provably optimal and the report says so. If the
bounds do not meet, the report prints the interval (`optimum lies between L
and U`) so the result is never over-claimed.

All randomness comes from a seeded generator (`--seed`), so a run is
reproducible.

## 4. Verification

`verify.py` re-checks every schedule using only coordinates and plain
Python. It does not share code with the graph builder or the colouring, so a
bug in the optimiser cannot hide itself. For every pair of nodes in the same
slot it tests: are they within range (direct conflict) or do they share a
neighbour within range (hidden terminal)? The CLI exits non-zero and prints
the offending pair if anything fails. The message
"Schedule verified conflict-free" is printed only after this check passes.

## 5. Design decisions

* **networkx** for graph construction, as required; the colouring routines
  work on plain adjacency sets for speed and so the algorithm is visible.
* **Distance-2 colouring rather than distance-1 plus fixes.** A distance-1
  colouring is the obvious first attempt and it fails: see section 7.
* **Natural sort of node names**, so `Node_2` precedes `Node_10` and the
  matrix columns are in the order the reader expects.
* **Strict input validation**: not JSON, empty, wrong arity, non-numeric,
  NaN/Infinity all fail with a clear message and exit code 2.
* **Isolated nodes** get slot 0 and share it with other far-away nodes, which
  is correct since nobody can be hurt by their transmissions.
* **JSON export** (`--json-out`) is the contract between Part 1 and the EMANE
  bridge, so Part 2 never re-implements scheduling logic.

## 6. Results

Three 16-node test topologies (`examples/`), 500 m range, seed 0:

| Topology | Links | Frame length | Clique lower bound | Result |
|---|---|---|---|---|
| `grid_16.json` (4x4, 300 m spacing, the layout implied by the brief's coordinate example) | 42 | 9 | 9 | optimal |
| `random_16.json` (random in 1200 m square) | 39 | 10 | 10 | optimal |
| `clusters_16.json` (two clusters 2.6 km apart plus one isolated node) | 47 | 8 | 8 | optimal |

Spatial reuse in the grid case: slot 0 carries four simultaneous
transmitters (Node_01, 04, 13, 16); five of the nine slots carry two or more.

Other checks: a 200-node random field is coloured in well under a second;
40 random topologies (2 to 30 nodes, three area sizes) all pass the
independent verifier; the final schedule is never worse than plain DSATUR
(tested).

## 7. Why the two-hop rule matters (`emane/slot_sim.py`)

The simulator replays each slot: a receiver decodes a frame only if exactly
one transmitter is audible to it. On the 4x4 grid (84 directed links):

| Schedule | Slots | Delivered | Collided |
|---|---|---|---|
| Distance-2 schedule (this project) | 9 | 84 | 0 |
| Plain distance-1 colouring | 4 | 20 | 64 |
| Random assignment, same slot count | 8 | 31 | 39 |

The distance-1 colouring is shorter but loses most traffic to hidden-terminal
collisions. The extra slots buy correctness.

## 8. Confirmation on EMANE

The same grid schedule was enforced by EMANE 1.5.3 (16 radios). Under 16
simultaneous flows it lost 0.8 % of packets; the plain distance-1 colouring
lost 43.1 %. Full account in `EMANE_INTEGRATION.md`.

## 9. Limitations and possible extensions

* The model is a unit-disk graph with a hard 500 m cut-off. Real RF has
  fading and capture effects; EMANE's pathloss modelling would handle that.
* One slot per node per frame means equal airtime for everyone. Per-node
  demand (several slots for busy nodes) would be a weighted-colouring
  extension.
* Static positions only. Mobility would call for incremental recolouring of
  the affected neighbourhood instead of replanning from scratch.
* The clique bound is not always tight on large sparse graphs; there the
  report prints an interval instead of claiming optimality.
