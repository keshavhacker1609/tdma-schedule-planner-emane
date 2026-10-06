# Part 2: EMANE Integration

## Status

Part 2 was run end to end on **EMANE 1.5.3** (Ubuntu 22.04 container, 16
radios, one `emane` process per radio in its own network namespace).

| Check | Result |
|---|---|
| EMANE loads the generated MAC, PHY, NEM, platform, transport and event-service profiles | Yes, after the fixes listed in section 5 |
| TDMA schedule delivered with `emaneevent-tdmaschedule` | Yes; NEM 1 reports 535 valid transmit slots and its neighbour table lists exactly NEMs 2, 5, 6, the three radios within 500 m |
| Pings between all 120 node pairs follow the 500 m topology (reply in range, none out of range), 10 ms slots | 120 / 120 |
| Same check with the spec's 1 ms slots on a laptop container | 92 / 120 (see section 6) |
| 16 simultaneous flows under load, this project's 9-slot schedule | mean loss 0.8 %, worst flow 4 % |
| Same load, naive distance-1 colouring (4 slots) | mean loss 43.1 %, worst flow 78 % |

The last two rows are the headline result: on the real emulator the
distance-2 schedule delivers almost everything, and the shorter naive schedule
loses nearly half the traffic to hidden-terminal collisions. Numbers vary a
little run to run because the containers do not use realtime scheduling.

## 1. Approach

```
node coordinates (JSON)
    -> schedule_optimizer.py  (Part 1)        -> schedule.json
    -> emane/bridge.py                         -> tdmaschedule.xml, profiles, scenario.eel
    -> EMANE (one emane process per radio)     -> frames delivered per schedule
```

The bridge is the only coupling between the parts. It reads `schedule.json`
and never recomputes anything. Before writing it re-checks the distance-2
rule and refuses to export a colliding schedule.

## 2. Schedule mapping

EMANE's TDMA model takes a schedule event: a frame of numbered slots, with
each slot saying which NEMs transmit and which receive.

* **Slot duration**: 1 ms (`slotduration="1000"`, microseconds), as the brief
  specifies. One frame, `frames="1"`, `slots=<frame length>`, so a 9-slot
  plan repeats every 9 ms.
* **Frequency**: one frequency for the whole network (`2.4G`), because
  separation is by time, not frequency. Multi-frequency would be an
  extension: use one `<multiframe>` per channel.
* **Transmit**: node with colour `s` gets `<slot index="s" nodes="..."><tx/>`.
  All nodes sharing colour `s` are in the same `nodes` list, which is the
  spatial reuse.
* **Receive**: in every other slot a node gets `<rx/>`, so it can decode
  whatever neighbours send. A node never transmits and receives in the same
  slot.
* **NEM ids**: the number in `Node_NN` (Node_07 is NEM 7), else 1..N.

The file is loaded with `emaneevent-tdmaschedule tdmaschedule.xml -i <iface>`,
which sends each NEM only its own slot assignments.

## 3. Reproducing the radio range

The schedule only guarantees no collisions if EMANE's radios hear each other
the way the planner assumed. The bridge writes `scenario.eel`, a list of
pathloss events: 80 dB for pairs within range, 250 dB (unreachable) beyond it.
The PHY runs in `precomputed` propagation mode, so EMANE uses exactly those
values. This makes the 500 m disk model exact instead of approximating it
with free-space RF numbers.

## 4. Running it

Everything runs in one privileged container; each radio gets its own network
namespace, so no multi-machine setup is needed.

```bash
sh emane/run_in_docker.sh examples/grid_16.json            # 1 ms slots
SLOT_US=10000 sh emane/run_in_docker.sh examples/grid_16.json   # reliable on a laptop
BASELINE=1 SLOT_US=10000 sh emane/run_in_docker.sh examples/grid_16.json   # naive colouring, for comparison
```

`container_run.sh` does: plan -> bridge -> create a bridge network and one
namespace per NEM -> start one `emane` per namespace -> start the event
service (pathloss) -> send the TDMA schedule -> `check_schedule.sh`.

`check_schedule.sh` pings every node pair. In-range pairs should answer;
out-of-range pairs should not. It checks the radio topology and basic TDMA
delivery. It does not by itself prove slot timing; for that, compare MAC
statistics via `emanesh` and the per-NEM logs in `emane/build/logs`.

## 5. Problems found on the first real run (all fixed)

Writing the profiles from documentation was not enough; EMANE rejected the
first attempt. Each failure and its fix:

1. The PHY profile requires a `subid` parameter (`ConfigurationException:
   Required item not present: subid`). Added to `phy.xml`.
2. EEL timestamps do not accept `-Inf`; changed to `0.0` so the pathloss
   events apply at start.
3. `emane` uses `--pidfile`; `-p` is the realtime priority.
4. The event service resolves `scenario.eel` relative to its working
   directory, so it is started from the build directory.
5. The Docker image lacked `python3-networkx`, which the planner needs.
6. The PCR curve path and the TDMA model library name
   (`tdmaeventschedulerradiomodel`) were confirmed against the installed
   package, as were the EEL loader names for pathloss.

## 6. Slot length in the emulation

The brief specifies 1 ms slots and `bridge.py` uses that by default. On a
laptop, sixteen non-realtime EMANE processes in one container cannot hit every
1 ms slot boundary: NEM 1 counted 8 missed receive slots, and 28 of 120 pair
checks failed. At 10 ms (`SLOT_US=10000`) all 120 pass, because the schedule
logic is identical and only the timing margin grows. For a faithful 1 ms run
use realtime scheduling (`emane -r`) on a host with spare cores.

## 6b. Fallback without EMANE

`slot_sim.py` models the same rule EMANE enforces (one audible transmitter
per receiver per slot) and shows zero collisions for the generated schedule,
against heavy loss for naive ones. It is not a substitute for the real
emulator; it shows that the schedule semantics being handed to EMANE are the
right ones.

## 7. Generated files (`emane/build/`)

| File | Purpose |
|---|---|
| `tdmaschedule.xml` | TDMA schedule event |
| `scenario.eel` | pathloss events for the 500 m range |
| `tdmamac.xml`, `phy.xml` | model profiles shared by all NEMs |
| `nemN.xml`, `transportN.xml`, `platformN.xml` | per-radio configuration; transport gives `10.100.0.N` |
| `eventservice.xml`, `eelgenerator.xml` | event service driving the EEL file |
| `nems.json` | node -> NEM id, IP and slot |
