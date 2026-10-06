"""Text report and JSON export of a finished schedule."""

import json

BAR = "=" * 64
RULE = "-" * 65


def short_label(name):
    return name[5:] if name.startswith("Node_") else name


def slot_matrix(slots, num_slots):
    """Boolean matrix: matrix[s][i] is 1 when node i (sorted order) owns slot s."""
    names = list(slots)
    return names, [[1 if slots[n] == s else 0 for n in names] for s in range(num_slots)]


def render_report(nodes, slots, num_slots, radio_range, result, edges, verified):
    names, matrix = slot_matrix(slots, num_slots)
    labels = [short_label(n) for n in names]
    width = max(2, *(len(l) for l in labels))
    out = [BAR, "               TDMA TOPOLOGY OPTIMIZATION REPORT", BAR,
           f"Total Nodes Processed   : {len(names)}",
           f"Configured Radio Range  : {radio_range:.1f} meters",
           f"Radio Links (1-hop)     : {edges}",
           f"Optimized Frame Length  : {num_slots} unique timeslots (Lower is better)"]
    if result.optimal:
        out.append(f"Lower Bound             : {result.lower_bound} (frame length is provably optimal)")
    else:
        out.append(f"Lower Bound             : {result.lower_bound} (optimum lies between "
                   f"{result.lower_bound} and {num_slots})")
    out += [RULE, " NODE -> SLOT ASSIGNMENTS:"]
    out += [f"  {n}: Slot {slots[n]}" for n in names]

    out += ["", " SLOT -> NODES (spatial reuse):"]
    for s in range(num_slots):
        members = [n for n in names if slots[n] == s]
        out.append(f"  Slot {s}: {len(members)} node(s) transmit together  [{', '.join(members)}]")

    out += ["", " STRUCTURAL TDMA SCHEDULE MATRIX (Slot x Node Boolean Matrix):"]
    head = "Slot \\ Node | " + " | ".join(l.rjust(width) for l in labels)
    out += [head, "-" * len(head)]
    for s, row in enumerate(matrix):
        cells = " | ".join(str(v).rjust(width) for v in row)
        out.append(f" Slot {s:02d}".ljust(12) + "| " + cells)
    out.append("-" * len(head))

    if verified:
        out.append("Execution finalized cleanly. Schedule verified conflict-free.")
    else:
        out.append("WARNING: verification found collisions (see below).")
    out.append(BAR)
    return "\n".join(out)


def schedule_to_dict(nodes, slots, num_slots, radio_range, result):
    names, matrix = slot_matrix(slots, num_slots)
    return {
        "radio_range_m": radio_range,
        "frame_length": num_slots,
        "lower_bound": result.lower_bound,
        "provably_optimal": result.optimal,
        "positions": {n: list(nodes[n]) for n in names},
        "node_to_slot": {n: slots[n] for n in names},
        "slot_to_nodes": {str(s): [n for n in names if slots[n] == s] for s in range(num_slots)},
        "matrix": {"nodes": names, "rows": matrix},
    }


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
