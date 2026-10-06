"""Command line entry point."""

import argparse
import sys

from . import coloring, report, topology, verify


def build_parser():
    p = argparse.ArgumentParser(
        prog="schedule_optimizer",
        description="Generate a conflict-free TDMA slot schedule (distance-2 colouring) "
                    "from static node coordinates.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--nodes", metavar="JSON",
                     help='coordinates as a JSON string, e.g. \'{"Node_01":[0,0],"Node_02":[300,0]}\'')
    src.add_argument("--nodes-file", metavar="PATH", help="read the same JSON from a file ('-' for stdin)")
    p.add_argument("--range", type=float, default=topology.DEFAULT_RANGE_M, dest="radio_range",
                   help="radio range in metres (default: %(default)s)")
    p.add_argument("--seed", type=int, default=0, help="random seed for the heuristics (default: %(default)s)")
    p.add_argument("--restarts", type=int, default=300, help="randomised DSATUR restarts (default: %(default)s)")
    p.add_argument("--time-limit", type=float, default=20.0,
                   help="soft time budget for the search in seconds (default: %(default)s)")
    p.add_argument("--json-out", metavar="PATH", help="also write the schedule as JSON (input for the EMANE bridge)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        if args.nodes is not None:
            text = args.nodes
        elif args.nodes_file == "-" or (args.nodes_file is None and not sys.stdin.isatty()):
            text = sys.stdin.read()
        elif args.nodes_file:
            with open(args.nodes_file, encoding="utf-8") as fh:
                text = fh.read()
        else:
            build_parser().error("provide --nodes, --nodes-file, or pipe JSON on stdin")
        nodes = topology.parse_nodes(text)
        g = topology.build_connectivity_graph(nodes, args.radio_range)
    except (topology.TopologyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    conflict = topology.build_conflict_graph(g)
    result = coloring.optimise(conflict, seed=args.seed, restarts=args.restarts,
                               time_limit=args.time_limit)
    slots = {n: result.colors[n] for n in nodes}

    violations = verify.find_violations(nodes, slots, args.radio_range)
    print(report.render_report(nodes, slots, result.num_slots, args.radio_range,
                               result, g.number_of_edges(), not violations))
    if violations:
        for a, b, why in violations:
            print(f"  COLLISION: {a} and {b} share slot {slots[a]} - {why}", file=sys.stderr)
        return 1

    if args.json_out:
        report.write_json(args.json_out,
                          report.schedule_to_dict(nodes, slots, result.num_slots,
                                                  args.radio_range, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
