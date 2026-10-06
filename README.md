# TDMA Schedule Planner and EMANE Integration

Centralised slot planner for a TDMA radio network. Given static node
coordinates it builds the radio-connectivity graph (500 m range), colours the
distance-2 conflict graph to get a collision-free slot per radio, reuses slots
spatially, and exports the result as an EMANE TDMA schedule.

* **Part 1 (mandatory)** - Python optimiser and CLI: `tdma_planner/`
* **Part 2 (bonus)** - EMANE bridge, profiles and run scripts: `emane/`
* **Documentation** - `docs/TDMA_Planner_Report.pdf` (full report with the
  day-wise work log), `docs/DESIGN.md`, `docs/EMANE_INTEGRATION.md`
* **Presentation** - `docs/TDMA_Planner_Presentation.pptx`

## Quick start

```bash
pip install -r requirements.txt

# JSON string argument, as in the brief
python schedule_optimizer.py --nodes '{"Node_01":[0.0,0.0],"Node_02":[300.0,0.0],"Node_03":[600.0,0.0]}'

# or from a file / stdin
python schedule_optimizer.py --nodes-file examples/grid_16.json
cat examples/grid_16.json | python schedule_optimizer.py

# also save the schedule for the EMANE bridge
python schedule_optimizer.py --nodes-file examples/grid_16.json --json-out out.json
```

On Windows PowerShell, quoting inline JSON is awkward; use `--nodes-file`.

Options: `--range` (default 500), `--seed`, `--restarts`, `--time-limit`,
`--json-out`. Exit codes: `0` success, `1` verification found a collision
(should never happen), `2` bad input.

### Sample run (16 nodes, 4x4 grid, 300 m spacing)

```
Total Nodes Processed   : 16
Configured Radio Range  : 500.0 meters
Radio Links (1-hop)     : 42
Optimized Frame Length  : 9 unique timeslots (Lower is better)
Lower Bound             : 9 (frame length is provably optimal)
...
 Slot 00    |  1 |  0 |  0 |  1 |  0 |  0 |  0 |  0 |  0 |  0 |  0 |  0 |  1 |  0 |  0 |  1
```

The full report (node-to-slot list, slot-to-nodes view, boolean matrix) is
printed for every run; see `docs/DESIGN.md` for complete output.

## Part 2

```bash
python emane/bridge.py out.json --out emane/build     # schedule -> EMANE XML
python emane/slot_sim.py out.json                     # slot-level replay, no EMANE needed
sh emane/run_in_docker.sh examples/grid_16.json       # full pipeline in a container
```

`slot_sim.py` replays the schedule slot by slot without EMANE. The Docker run
was executed on EMANE 1.5.3: all 120 node pairs behave as the 500 m topology
dictates, and under 16 simultaneous flows this schedule loses 0.8 % of packets
against 43.1 % for a naive distance-1 colouring. Use `SLOT_US=10000` on a
laptop (1 ms slots need realtime scheduling); details and the problems found
on the first run are in `docs/EMANE_INTEGRATION.md`.

## Tests

```bash
python -m pytest -q
```

29 tests: input validation, direct and hidden-terminal conflicts, the 500 m
boundary, spatial reuse, 40 randomised topologies checked by an independent
collision verifier, determinism, CLI behaviour, and the bridge output.

## Layout

```
schedule_optimizer.py        CLI launcher
tdma_planner/
  topology.py                parsing, connectivity graph, distance-2 conflict graph
  coloring.py                heuristics, tabu search, exact branch-and-bound
  verify.py                  independent collision checker (coordinates only)
  report.py                  text report and JSON export
  cli.py
emane/
  bridge.py                  schedule JSON -> EMANE XML / EEL
  slot_sim.py                slot-level enforcement replay
  Dockerfile, run_in_docker.sh, container_run.sh, check_schedule.sh
  build/                     sample generated output for the 4x4 grid
examples/                    sample inputs and schedules
docs/tools/                  scripts that rebuild the figures, report PDF and slide deck
tests/
docs/
```
