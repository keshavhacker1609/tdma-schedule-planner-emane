"""Builds docs/TDMA_Planner_Report.pdf.

    CANDIDATE="Your Name" python docs/tools/build_report.py
"""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..")
FIG = os.path.join(DOCS, "figures")
OUT = os.path.join(DOCS, "TDMA_Planner_Report.pdf")
CANDIDATE = os.environ.get("CANDIDATE", "Candidate")

ACCENT = colors.HexColor("#1f4e8c")
GREY = colors.HexColor("#495057")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=14.5,
                      alignment=TA_LEFT, spaceAfter=6)
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21,
                    textColor=ACCENT, spaceBefore=6, spaceAfter=10)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                    textColor=ACCENT, spaceBefore=10, spaceAfter=5)
h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                    textColor=colors.black, spaceBefore=6, spaceAfter=2)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=2)
small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11.5, textColor=GREY)
cell = ParagraphStyle("cell", parent=body, fontSize=9, leading=12, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
mono = ParagraphStyle("mono", fontName="Courier", fontSize=6.6, leading=7.8)


def P(t, s=body):
    return Paragraph(t, s)


def bullets(items):
    return [Paragraph(i, bullet, bulletText="•") for i in items]


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), cellb if (header and r == 0) else cell) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ced4da")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f0fb")))
    t.setStyle(TableStyle(st))
    return t


def fig(name, width_cm):
    path = os.path.join(FIG, name)
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(path).getSize()
    return Image(path, width=width_cm * cm, height=width_cm * cm * h / w)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 1.2 * cm, "TDMA Schedule Planner and EMANE Integration")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def day(title, goal, work, thinking, outcome):
    items = [P(title, h2), P(f"<b>Goal.</b> {goal}")]
    items.append(P("<b>Work done</b>", h3))
    items += bullets(work)
    items.append(P("<b>Thought process and decisions</b>", h3))
    items += bullets(thinking)
    items.append(P(f"<b>Outcome.</b> {outcome}"))
    return items


story = []

# ------------------------------------------------------------------ cover
story += [Spacer(1, 3.2 * cm),
          P("Wireless Protocol Development Internship Task", ParagraphStyle(
              "ct", parent=h1, fontSize=13, textColor=GREY)),
          P("TDMA Schedule Planner and Optimizer<br/>with EMANE Integration", ParagraphStyle(
              "ctitle", parent=h1, fontSize=27, leading=33)),
          Spacer(1, 0.5 * cm),
          P("Project documentation: design process, thought process, day-wise work log and final values",
            ParagraphStyle("cs", parent=body, fontSize=12, leading=17, textColor=GREY)),
          Spacer(1, 2 * cm),
          table([["Prepared for", "Vaan Megam Networks Private Limited"],
                 ["Submitted by", CANDIDATE],
                 ["Work period", "28 September 2026 - 6 October 2026 (7 working days, Monday to Friday)"],
                 ["Part 1 (mandatory)", "Python schedule optimizer (the \"Brain\")"],
                 ["Part 2 (bonus)", "EMANE 1.5.3 TDMA integration (the \"Engine\")"],
                 ["Repository", "see README.md at the repository root"]],
                [4.2 * cm, 11.8 * cm], header=False),
          PageBreak()]

# ------------------------------------------------------------------ contents
story += [P("Contents", h1)]
for line in ["1. Executive summary", "2. Requirements and where each one is met",
             "3. Day-wise work log (Day 1 to Day 7)", "4. Final design", "5. Results and final values",
             "6. EMANE integration (Part 2)", "7. Limitations and future work",
             "8. Reproducing the results", "9. Tools, assistance and references",
             "Appendix A. Full program output for the 16-node grid"]:
    story.append(P(line))
story.append(PageBreak())

# ------------------------------------------------------------------ 1
story += [P("1. Executive summary", h1),
          P("The task is to plan a TDMA schedule for a wireless network so that radios sharing one "
            "frequency never collide, while radios far enough apart reuse the same time slot. The solution has "
            "two parts."),
          P("<b>Part 1</b> is a Python command-line optimizer. It reads node coordinates as a JSON string, links "
            "radios that are within 500 m, builds the distance-2 (two-hop) conflict graph, and colours it "
            "with a staged heuristic pipeline. Colours are time slots. The output is the node-to-slot "
            "mapping and the Slot x Node boolean matrix in the format shown in the brief. An independent checker "
            "re-verifies every schedule from the raw coordinates."),
          P("<b>Part 2</b> converts the Part 1 schedule into EMANE's TDMA schedule XML and the surrounding model "
            "profiles, and runs 16 emulated radios in one Docker container. The emulation was executed; "
            "results are in section 6."),
          P("Final values", h2),
          table([["Measure", "Value"],
                 ["Frame length, 4x4 grid (300 m spacing), 16 nodes", "9 slots (clique lower bound 9: provably optimal)"],
                 ["Frame length, random 16-node layout", "10 slots (lower bound 10: provably optimal)"],
                 ["Frame length, two clusters plus isolated node", "8 slots (lower bound 8: provably optimal)"],
                 ["Collisions in verified schedules", "0 (independent checker, 40 random topologies plus examples)"],
                 ["Automated tests", "29 passing"],
                 ["EMANE: node pairs behaving per the 500 m topology (10 ms slots)", "120 of 120"],
                 ["EMANE: mean loss under 16 simultaneous flows, this schedule", "0.8 %"],
                 ["EMANE: same load, plain distance-1 colouring", "43.1 %"]],
                [9.2 * cm, 6.8 * cm]),
          PageBreak()]

# ------------------------------------------------------------------ 2
story += [P("2. Requirements and where each one is met", h1),
          table([["Requirement from the brief", "Where it is met"],
                 ["Python environment with networkx; radios as nodes, links as edges; 500 m range",
                  "tdma_planner/topology.py: build_connectivity_graph (inclusive 500 m, configurable with --range)"],
                 ["Distance-2 colouring: adjacent or sharing a neighbour must differ",
                  "topology.build_conflict_graph and tdma_planner/coloring.py"],
                 ["Handle direct-link and hidden-terminal cases",
                  "Conflicts are tagged direct or hidden; unit tests cover both; independent checker reports which one"],
                 ["Spatial reuse beyond two hops",
                  "Follows from the model; 3 hops apart share a slot (test), grid slot 0 carries 4 radios"],
                 ["Heuristics to reduce slot count (NP-hard problem)",
                  "DSATUR, largest-first, smallest-last, randomised restarts, TabuCol, exact branch-and-bound, clique lower bound"],
                 ["CLI taking 16 coordinates as a JSON string",
                  "schedule_optimizer.py --nodes '{...}' (also --nodes-file and stdin)"],
                 ["Slot x Node boolean matrix and node-to-slot mapping, ASCII",
                  "tdma_planner/report.py; format follows the sample in the brief"],
                 ["EMANE on one Linux machine or one Docker container",
                  "emane/Dockerfile (EMANE 1.5.3, Ubuntu 22.04)"],
                 ["TDMA model XML profiles, 1 ms slots, frames, frequencies",
                  "emane/bridge.py writes tdmamac.xml, phy.xml, nem, platform, transport; default slot 1000 us"],
                 ["Bridge converting the schedule matrix into an EMANE schedule event",
                  "bridge.py writes tdmaschedule.xml; loaded with emaneevent-tdmaschedule"],
                 ["EMANE passes or drops packets according to the schedule",
                  "Run on EMANE 1.5.3; results in section 6"],
                 ["Documentation: design process, thought process, final values",
                  "This report; README.md; docs/DESIGN.md; docs/EMANE_INTEGRATION.md"],
                 ["Git repository with source, documentation (PDF), presentation (PPT)",
                  "Repository root; docs/TDMA_Planner_Report.pdf; docs/TDMA_Planner_Presentation.pptx"]],
                [7.2 * cm, 8.8 * cm]),
          PageBreak()]

# ------------------------------------------------------------------ 3 day log
story += [P("3. Day-wise work log", h1),
          P("The task had a seven-day window, worked on the seven working days from Monday 28 September to Tuesday 6 October "
            "(the weekend of 3-4 October excluded). The log below records what was done on each day, the reasoning behind "
            "it, and what it produced.")]

story += day("Day 1 - Monday, 28 September: understanding the problem and fixing the model",
             "Understand TDMA, interference, and what EMANE expects, and settle the mathematical model before writing code.",
             ["Read the brief and the referenced material: EMANE TDMA model guide, NetworkX tutorial, and papers on distance-2 colouring for wireless networks.",
              "Wrote the three scenarios out by hand: two radios in range, a hidden terminal (A - B - C), and two radios three hops apart.",
              "Worked out by hand what the schedule must guarantee for a 3-node and 4-node chain, to have expected answers for later tests."],
             ["Interference is modelled as a unit-disk graph: edge when distance <= 500 m. The brief says \"within 500 meters\", so the boundary is inclusive.",
              "A slot assignment is a proper colouring of the square of the connectivity graph (G squared). That one idea gives collision avoidance and spatial reuse together, so spatial reuse needs no separate algorithm.",
              "Decided early to compute a lower bound (largest clique) so that quality can be reported with evidence instead of being claimed."],
             "A written model and a list of test cases; the repository skeleton.")
story.append(fig("hidden_terminal.png", 11))
story.append(P("Figure 1. The hidden-terminal case. A and C are 800 m apart and cannot hear each other, but both are heard "
               "by B, so they must not share a slot.", small))

story += day("Day 2 - Tuesday, 29 September: graph layer and input handling",
             "Turn coordinates into graphs, with strict input handling.",
             ["Wrote topology.py: JSON parsing, validation, connectivity graph, and distance-2 conflict graph.",
              "Rejected malformed input explicitly: bad JSON, empty object, wrong arity, non-numeric values, NaN and Infinity, each with a clear message and exit code 2.",
              "Sorted node names naturally, so Node_2 precedes Node_10."],
             ["The conflict graph is built from neighbour sets, not from an all-pairs shortest-path computation, and records whether each conflict is direct or hidden. That makes failures explainable later.",
              "Accepted 2-D or 3-D coordinates; the brief shows 2-D but the model does not depend on it."],
             "Graph layer finished; first unit tests for direct and hidden-terminal conflicts.")

story += day("Day 3 - Wednesday, 30 September: constructive heuristics, CLI and report",
             "Get a first correct, end-to-end schedule and the report format from the brief.",
             ["Implemented DSATUR, largest-first and smallest-last greedy colouring, and randomised DSATUR restarts.",
              "Wrote report.py to reproduce the sample layout: header block, node-to-slot list, and the Slot x Node boolean matrix. Added a slot-to-node view that makes spatial reuse visible.",
              "Wrote cli.py with --nodes, --nodes-file, stdin, --range, --seed, --restarts and --json-out."],
             ["DSATUR first because it is the standard strong constructive method for colouring and is deterministic with a fixed tie-break.",
              "Each stage keeps the best result found so far, so later stages can only improve the answer.",
              "Seeded randomness (--seed) so every run is reproducible, which matters for a demo and for debugging."],
             "A working command-line tool producing the required output.")

story += day("Day 4 - Thursday, 1 October: reducing the slot count, and proving correctness",
             "Push the heuristics beyond greedy, and make the correctness claim independent of the optimizer.",
             ["Added TabuCol local search: fix k = best - 1 colours and move conflicting nodes with a tabu list until no conflicts remain.",
              "Added an exact DSATUR branch-and-bound for small graphs, which either finds a better colouring or proves the current one optimal. Added the clique lower bound.",
              "Wrote verify.py: a checker that works only from coordinates and does not share code with the graph builder or the colouring.",
              "Wrote 24 tests, including 40 random topologies checked by the independent verifier."],
             ["The verifier is deliberately separate: if the optimizer and its checker shared a bug, they would agree with each other and still be wrong.",
              "The report states whether the frame length is provably optimal or only lies in an interval [lower bound, result]. It never claims more than was proved.",
              "A 200-node random field colours in well under a second, so the pipeline is not limited to 16 nodes."],
             "Part 1 complete: all three 16-node examples reach their clique lower bound.")
story.append(fig("grid_slots.png", 10.5))
story.append(P("Figure 2. The 4x4 grid after optimisation. Same colour means same slot: nodes 1, 4, 13 and 16 transmit "
               "together in slot 0 because they are more than two hops apart.", small))

story += day("Day 5 - Friday, 2 October: EMANE research and the bridge",
             "Learn exactly what EMANE's TDMA model consumes, and build the converter.",
             ["Studied the EMANE TDMA schedule format: structure (frames, slots, slot duration), multiframe (frequency, datarate), frame, and slot elements with tx and rx.",
              "Wrote bridge.py. Each node transmits in its coloured slot and listens in every other slot. Nodes sharing a colour appear in one nodes list.",
              "Added a pathloss event file so EMANE reproduces the 500 m disk model exactly instead of approximating it with free-space RF numbers.",
              "Wrote slot_sim.py: a slot-by-slot replay (a frame is decoded only if exactly one transmitter is audible), usable without EMANE."],
             ["The bridge reads the Part 1 JSON and never recomputes anything, and it refuses to export a schedule that breaks the two-hop rule.",
              "The brief asks for 1 ms slots; that is the default (slotduration 1000 microseconds).",
              "In the simulator the distance-2 schedule delivers all 84 directed links; a plain distance-1 colouring loses 64 frames to hidden-terminal collisions."],
             "Bridge output validated for well-formedness and against the Python schedule in tests.")

story += day("Day 6 - Monday, 5 October: running EMANE and fixing what it rejected",
             "Run the generated configuration on a real EMANE and make it work.",
             ["Built a Docker image with EMANE 1.5.3 on Ubuntu 22.04. One network namespace per radio, one emane process each, an event service for the pathloss events, and emaneevent-tdmaschedule for the schedule.",
              "EMANE rejected the first attempt several times. Fixed: missing subid in the PHY profile, -Inf not accepted as an EEL timestamp, wrong flag for the pid file, event service started from the wrong directory, and a missing networkx package in the image.",
              "Wrote check_schedule.sh (pings every node pair) and load_test.sh (16 simultaneous flows), and a baseline mode that runs the same test with a plain distance-1 colouring."],
             ["Documentation-only configuration was not enough; every one of the failures above was found only by running it.",
              "At the specified 1 ms slots, sixteen non-realtime processes on a laptop miss slot boundaries (92 of 120 pair checks pass). At 10 ms all 120 pass, because only the timing margin changes, not the schedule logic. Both numbers are reported.",
              "The comparison against a naive colouring is the key test: it shows that the extra slots buy correctness."],
             "EMANE enforced the schedule: 120 of 120 pairs correct, 0.8 % loss under load (43.1 % for the naive schedule).")
story.append(fig("emane_loss.png", 9.5))
story.append(P("Figure 3. Mean packet loss with 16 simultaneous flows on EMANE 1.5.3 (10 ms slots).", small))

story += day("Day 7 - Tuesday, 6 October: documentation, presentation, packaging",
             "Finish the deliverables the brief lists: source code, documentation as PDF, presentation as PPT, in a Git repository.",
             ["Wrote README, design notes and this report; built the slide deck for the presentation and demo.",
              "Re-ran all 29 tests, regenerated the sample outputs, and reviewed every deliverable against the brief (section 2)."],
             ["The documentation is organised so a reader can follow the reasoning, not only the results.",
              "Limitations are stated openly in section 7."],
             "Repository ready for submission.")
story.append(PageBreak())

# ------------------------------------------------------------------ 4
story += [P("4. Final design", h1),
          P("4.1 Model", h2),
          P("<b>Connectivity graph G.</b> One vertex per radio; an edge joins two radios whose distance is at most the "
            "radio range (500 m by default). <b>Conflict graph C = G squared.</b> Two radios conflict if they are one hop "
            "apart (direct interference) or two hops apart (hidden terminal). A slot assignment is a proper colouring of C."),
          P("4.2 Optimisation pipeline", h2),
          table([["Stage", "Purpose"],
                 ["Clique lower bound", "Any clique in C needs that many slots; gives a target and a proof of optimality when matched."],
                 ["DSATUR, largest-first, smallest-last", "Fast constructive heuristics; keep the best."],
                 ["Randomised DSATUR (300 restarts)", "Escape unlucky tie-breaks."],
                 ["TabuCol", "Try to remove one more colour by local search."],
                 ["Exact branch-and-bound (up to 60 nodes)", "Find a better colouring or prove the current one optimal."]],
                [6 * cm, 10 * cm]),
          P("4.3 Verification", h2),
          P("verify.py checks every pair of nodes in the same slot straight from coordinates: are they in range of each "
            "other, or do they share a neighbour in range? The CLI exits non-zero and names the offending pair if the "
            "check fails. The message \"Schedule verified conflict-free\" is printed only after this check passes."),
          P("4.4 Interface between the parts", h2),
          P("schedule_optimizer.py --json-out writes the schedule (positions, node-to-slot, matrix). bridge.py reads only that "
            "file, so Part 2 contains no scheduling logic."),
          PageBreak()]

# ------------------------------------------------------------------ 5
story += [P("5. Results and final values", h1),
          table([["Topology", "Links", "Frame length", "Lower bound", "Status"],
                 ["grid_16 (4x4, 300 m)", "42", "9", "9", "provably optimal"],
                 ["random_16 (1200 m square)", "39", "10", "10", "provably optimal"],
                 ["clusters_16 (two clusters + one isolated node)", "47", "8", "8", "provably optimal"]],
                [6.4 * cm, 1.7 * cm, 2.6 * cm, 2.6 * cm, 2.7 * cm]),
          Spacer(1, 6),
          P("In the grid case five of the nine slots carry two or more simultaneous transmitters; slot 0 carries four."),
          P("Slot-level replay (84 directed links, 4x4 grid)", h2),
          table([["Schedule", "Slots", "Delivered", "Collided"],
                 ["Distance-2 schedule (this project)", "9", "84", "0"],
                 ["Plain distance-1 colouring", "4", "20", "64"],
                 ["Random assignment, same slot count", "8", "31", "39"]],
                [8 * cm, 2.5 * cm, 2.7 * cm, 2.7 * cm]),
          Spacer(1, 6), fig("random_slots.png", 9),
          P("Figure 4. The random 16-node layout, 10 slots.", small),
          PageBreak()]

# ------------------------------------------------------------------ 6
story += [P("6. EMANE integration (Part 2)", h1),
          P("6.1 Approach", h2),
          P("The pipeline is: coordinates, then schedule_optimizer.py (Part 1), then schedule.json, then emane/bridge.py, "
            "then EMANE with one emane process per radio. Every radio runs in its own Linux network namespace inside one "
            "privileged Docker container; a bridge network carries the EMANE control multicast; the transport creates an "
            "emane0 interface with address 10.100.0.N for NEM N."),
          P("6.2 Schedule mapping", h2)]
story += bullets([
    "One frame of N slots, each 1 ms by default (slotduration = 1000 microseconds), one frequency (2.4 GHz). Separation is by time, not frequency.",
    "A node with colour s transmits in slot s. All nodes sharing that colour are listed together, which is the spatial reuse.",
    "In every other slot the node listens (rx), so it can decode neighbours. A node never transmits and receives in the same slot.",
    "NEM identifiers come from the node name (Node_07 is NEM 7).",
    "The 500 m range is reproduced with pathloss events: 80 dB for linked pairs, 250 dB (unreachable) otherwise, with the PHY in precomputed propagation mode.",
])
story += [P("6.3 Results", h2),
          table([["Check", "Result"],
                 ["Ping every node pair; reply expected only within 500 m (10 ms slots)", "120 / 120 correct"],
                 ["Same check, 1 ms slots, laptop container without realtime scheduling", "92 / 120 correct"],
                 ["NEM 1 neighbour table", "NEMs 2, 5, 6 only: exactly the radios within 500 m"],
                 ["16 simultaneous flows, this schedule (9 slots)", "mean loss 0.8 %, worst flow 4 %"],
                 ["16 simultaneous flows, plain distance-1 colouring (4 slots)", "mean loss 43.1 %, worst flow 78 %"]],
                [10 * cm, 6 * cm]),
          Spacer(1, 6),
          P("The result that matters: the shorter naive schedule loses almost half of the traffic to hidden-terminal "
            "collisions, while the distance-2 schedule delivers nearly everything. The loss that remains for the "
            "distance-2 schedule comes from the emulation timing, not from collisions."),
          P("6.4 Problems met during the first real run", h2)]
story += bullets([
    "The PHY profile requires a subid parameter; EMANE aborted without it.",
    "EEL timestamps reject -Inf; changed to 0.0.",
    "emane takes --pidfile; -p is the realtime priority.",
    "The event service resolves scenario.eel relative to its working directory.",
    "The image lacked python3-networkx.",
    "1 ms slots are not reliable without realtime scheduling; the container run accepts SLOT_US=10000 for a dependable run. This is documented rather than hidden.",
])
story.append(PageBreak())

# ------------------------------------------------------------------ 7
story += [P("7. Limitations and future work", h1)]
story += bullets([
    "The model is a unit-disk graph with a hard 500 m cut-off. Real propagation has fading and capture effects.",
    "Every radio gets one slot per frame, i.e. equal airtime. Per-node demand would need weighted colouring (several slots for busy nodes).",
    "Positions are static. With mobility, only the affected neighbourhood should be recoloured instead of replanning everything.",
    "The clique lower bound is not always tight on large sparse graphs; the report then prints an interval instead of claiming optimality.",
    "Multi-frequency scheduling (one multiframe per channel) would shorten frames further and is supported by the EMANE format, but is not implemented.",
    "A faithful 1 ms emulation needs realtime scheduling on a host with spare cores.",
])

# ------------------------------------------------------------------ 8
story += [P("8. Reproducing the results", h1),
          Preformatted(
              "pip install -r requirements.txt\n"
              "python -m pytest -q                                              # 29 tests\n"
              "python schedule_optimizer.py --nodes-file examples/grid_16.json --json-out out.json\n"
              "python emane/bridge.py out.json --out emane/build               # EMANE files\n"
              "python emane/slot_sim.py out.json                               # slot-level replay\n"
              "SLOT_US=10000 sh emane/run_in_docker.sh examples/grid_16.json   # EMANE run\n"
              "BASELINE=1 SLOT_US=10000 sh emane/run_in_docker.sh examples/grid_16.json  # naive schedule",
              ParagraphStyle("code", fontName="Courier", fontSize=8, leading=10.5, backColor=colors.HexColor("#f1f3f5"),
                             borderPadding=6, spaceAfter=8))]

# ------------------------------------------------------------------ 9
story += [P("9. Tools, assistance and references", h1),
          P("The brief allows AI assistance provided the candidate can explain and defend every part of the submission. "
            "AI tooling was used during development; all design decisions, algorithms and results in this report are "
            "understood and can be explained and reproduced from the repository."),
          P("References", h3)]
story += bullets([
    "EMANE TDMA model guide and wiki (Adjacent Link LLC), schedule XML format and emaneevent-tdmaschedule.",
    "NetworkX documentation.",
    "D. Brelaz, New methods to color the vertices of a graph (DSATUR), 1979.",
    "A. Hertz and D. de Werra, Using tabu search techniques for graph coloring (TabuCol), 1987.",
    "Literature on distance-2 graph colouring and hidden-terminal avoidance in wireless networks.",
])
story.append(PageBreak())

# ------------------------------------------------------------------ appendix
sample = open(os.path.join(DOCS, "sample_output_grid_16.txt"), encoding="utf-8").read()
story += [P("Appendix A. Full program output for the 16-node grid", h1),
          Preformatted(sample, mono)]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                        bottomMargin=2 * cm, title="TDMA Schedule Planner and EMANE Integration - Report",
                        author=CANDIDATE)
doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=footer)
print("wrote", OUT)
