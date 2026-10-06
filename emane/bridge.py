#!/usr/bin/env python3
"""Integration bridge: Part 1 schedule (JSON) -> EMANE TDMA configuration.

Reads the file written by `schedule_optimizer.py --json-out` and produces
everything an EMANE run needs:

    tdmaschedule.xml      schedule event file for `emaneevent-tdmaschedule`
    scenario.eel          pathloss events that reproduce the radio range
    tdmamac.xml           TDMA MAC model profile
    phy.xml / nemN.xml / transportN.xml / platformN.xml
    eventservice.xml, eelgenerator.xml

Standard library only, so it runs inside the container without extra
packages.
"""

import argparse
import json
import math
import os
import re
import sys
from xml.sax.saxutils import quoteattr

HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'


def nem_ids(names):
    """NEM id per node: the number in Node_NN when every name has one, else 1..N."""
    nums = [re.search(r"(\d+)$", n) for n in names]
    if all(nums):
        ids = [int(m.group(1)) for m in nums]
        if len(set(ids)) == len(ids) and min(ids) >= 1:
            return dict(zip(names, ids))
    return {n: i + 1 for i, n in enumerate(names)}


def schedule_xml(sched, ids, a):
    """TDMA schedule: one frame of N one-millisecond slots.

    Every node transmits in its own slot (the optimiser guarantees nobody
    within two hops shares it).  In all other slots a node listens, so
    EMANE can receive on that frequency.
    """
    frame_len = sched["frame_length"]
    node_slot = sched["node_to_slot"]
    lines = [HEADER.rstrip(), "<emane-tdma-schedule>",
             f'  <structure frames="1" slots="{frame_len}" slotoverhead="{a.slot_overhead_us}" '
             f'slotduration="{a.slot_us}" bandwidth="{a.bandwidth}"/>',
             f'  <multiframe frequency="{a.frequency}" power="{a.power}" class="0" datarate="{a.datarate}">',
             '    <frame index="0">']
    for s in range(frame_len):
        tx = [ids[n] for n, v in node_slot.items() if v == s]
        rx = [ids[n] for n, v in node_slot.items() if v != s]
        if tx:
            lines += [f'      <slot index="{s}" nodes="{",".join(map(str, sorted(tx)))}">', "        <tx/>", "      </slot>"]
        if rx:
            lines += [f'      <slot index="{s}" nodes="{",".join(map(str, sorted(rx)))}">', "        <rx/>", "      </slot>"]
    lines += ["    </frame>", "  </multiframe>", "</emane-tdma-schedule>", ""]
    return "\n".join(lines)


def eel(sched, ids, a):
    """Pathloss events: in range -> a low loss, out of range -> unreachable."""
    pos = sched["positions"]
    names = list(pos)
    rng = sched["radio_range_m"]
    out = ["# symmetric pathloss derived from node positions"]
    for n in names:
        parts = []
        for m in names:
            if m == n:
                continue
            loss = a.loss_in_range if math.dist(pos[n], pos[m]) <= rng else a.loss_out_of_range
            parts.append(f"nem:{ids[m]},{loss:.1f}")
        out.append(f"0.0 nem:{ids[n]} pathloss " + " ".join(parts))
    return "\n".join(out) + "\n"


def mac_xml(a):
    params = {
        "pcrcurveuri": a.pcr_curve,
        "fragmentcheckthreshold": "2",
        "fragmenttimeoutthreshold": "5",
        "neighbormetricdeletetime": "60.0",
        "neighbormetricupdateinterval": "1.0",
        "queue.aggregationenable": "on",
        "queue.aggregationslotthreshold": "90.0",
        "queue.depth": "256",
        "queue.fragmentationenable": "on",
        "queue.strictdequeueenable": "off",
    }
    body = "\n".join(f'  <param name="{k}" value={quoteattr(v)}/>' for k, v in params.items())
    return (HEADER + '<!DOCTYPE mac SYSTEM "file:///usr/share/emane/dtd/mac.dtd">\n'
            '<mac library="tdmaeventschedulerradiomodel">\n' + body + "\n</mac>\n")


def phy_xml(a):
    params = {
        "fixedantennagainenable": "on", "fixedantennagain": "0.0",
        "bandwidth": a.bandwidth, "noisemode": "outofband",
        "propagationmodel": "precomputed", "subid": "1", "systemnoisefigure": "4.0", "txpower": "0.0",
    }
    body = "\n".join(f'  <param name="{k}" value="{v}"/>' for k, v in params.items())
    return (HEADER + '<!DOCTYPE phy SYSTEM "file:///usr/share/emane/dtd/phy.dtd">\n<phy>\n'
            + body + "\n</phy>\n")


def transport_xml(nem_id, a):
    return (HEADER + '<!DOCTYPE transport SYSTEM "file:///usr/share/emane/dtd/transport.dtd">\n'
            '<transport library="transvirtual">\n'
            '  <param name="device" value="emane0"/>\n'
            f'  <param name="address" value="{a.subnet}.{nem_id}"/>\n'
            '  <param name="mask" value="255.255.255.0"/>\n'
            "</transport>\n")


def nem_xml(nem_id):
    return (HEADER + '<!DOCTYPE nem SYSTEM "file:///usr/share/emane/dtd/nem.dtd">\n<nem>\n'
            f'  <transport definition="transport{nem_id}.xml"/>\n'
            '  <mac definition="tdmamac.xml"/>\n'
            '  <phy definition="phy.xml"/>\n'
            "</nem>\n")


def platform_xml(nem_id, a):
    return (HEADER + '<!DOCTYPE platform SYSTEM "file:///usr/share/emane/dtd/platform.dtd">\n<platform>\n'
            f'  <param name="otamanagergroup" value="{a.ota_group}"/>\n'
            '  <param name="otamanagerdevice" value="eth0"/>\n'
            '  <param name="otamanagerchannelenable" value="on"/>\n'
            f'  <param name="eventservicegroup" value="{a.event_group}"/>\n'
            '  <param name="eventservicedevice" value="eth0"/>\n'
            f'  <param name="controlportendpoint" value="0.0.0.0:{47000}"/>\n'
            f'  <nem id="{nem_id}" definition="nem{nem_id}.xml"/>\n'
            "</platform>\n")


def eventservice_xml(a):
    return (HEADER + '<!DOCTYPE eventservice SYSTEM "file:///usr/share/emane/dtd/eventservice.dtd">\n'
            "<eventservice>\n"
            f'  <param name="eventservicegroup" value="{a.event_group}"/>\n'
            '  <param name="eventservicedevice" value="eth0"/>\n'
            '  <generator definition="eelgenerator.xml"/>\n'
            "</eventservice>\n")


def eelgenerator_xml():
    return (HEADER + '<!DOCTYPE eventgenerator SYSTEM "file:///usr/share/emane/dtd/eventgenerator.dtd">\n'
            '<eventgenerator library="eelgenerator">\n'
            '  <paramlist name="inputfile"><item value="scenario.eel"/></paramlist>\n'
            '  <paramlist name="loader"><item value="commeffect:eelloadercommeffect:delta"/>'
            '<item value="pathloss:eelloaderpathloss:delta"/></paramlist>\n'
            "</eventgenerator>\n")


def check_schedule(sched):
    """Refuse to emit a schedule that violates the distance-2 rule."""
    pos, rng = sched["positions"], sched["radio_range_m"]
    slot = sched["node_to_slot"]
    names = list(pos)
    near = {a: {b for b in names if b != a and math.dist(pos[a], pos[b]) <= rng} for a in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if slot[a] == slot[b] and (b in near[a] or near[a] & near[b]):
                raise SystemExit(f"refusing to export: {a} and {b} share slot {slot[a]} within two hops")


def main(argv=None):
    p = argparse.ArgumentParser(description="Convert a TDMA schedule JSON into EMANE configuration files.")
    p.add_argument("schedule", help="JSON written by schedule_optimizer.py --json-out")
    p.add_argument("--out", default="emane/build", help="output directory (default: %(default)s)")
    p.add_argument("--slot-us", type=int, default=1000, help="slot duration in microseconds (default: 1000 = 1 ms)")
    p.add_argument("--slot-overhead-us", type=int, default=0)
    p.add_argument("--frequency", default="2.4G")
    p.add_argument("--datarate", default="1M")
    p.add_argument("--bandwidth", default="1M")
    p.add_argument("--power", default="0")
    p.add_argument("--subnet", default="10.100.0", help="virtual transport /24 prefix (default: %(default)s)")
    p.add_argument("--ota-group", default="224.1.2.8:45702")
    p.add_argument("--event-group", default="224.1.2.8:45703")
    p.add_argument("--loss-in-range", type=float, default=80.0, help="pathloss (dB) for linked pairs")
    p.add_argument("--loss-out-of-range", type=float, default=250.0, help="pathloss (dB) for unlinked pairs")
    p.add_argument("--pcr-curve",
                   default="/usr/share/emane/xml/models/mac/tdmaeventscheduler/tdmabasemodelpcr.xml")
    p.add_argument("--allow-collisions", action="store_true",
                   help="export even if the schedule violates the two-hop rule (baseline experiments only)")
    a = p.parse_args(argv)

    with open(a.schedule, encoding="utf-8") as fh:
        sched = json.load(fh)
    if not a.allow_collisions:
        check_schedule(sched)

    names = list(sched["positions"])
    ids = nem_ids(names)
    os.makedirs(a.out, exist_ok=True)

    files = {
        "tdmaschedule.xml": schedule_xml(sched, ids, a),
        "scenario.eel": eel(sched, ids, a),
        "tdmamac.xml": mac_xml(a),
        "phy.xml": phy_xml(a),
        "eventservice.xml": eventservice_xml(a),
        "eelgenerator.xml": eelgenerator_xml(),
        "nems.json": json.dumps({n: {"nem_id": ids[n], "ip": f"{a.subnet}.{ids[n]}",
                                     "slot": sched["node_to_slot"][n]} for n in names}, indent=2) + "\n",
    }
    for n in names:
        i = ids[n]
        files[f"transport{i}.xml"] = transport_xml(i, a)
        files[f"nem{i}.xml"] = nem_xml(i)
        files[f"platform{i}.xml"] = platform_xml(i, a)

    for name, text in files.items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print(f"wrote {len(files)} files to {a.out} ({len(names)} NEMs, "
          f"{sched['frame_length']} slots x {a.slot_us} us per frame)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
