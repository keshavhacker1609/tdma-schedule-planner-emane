import json
import random

import pytest

from tdma_planner import cli, coloring, topology, verify


def plan(coords, radio_range=500.0, **kw):
    nodes = topology.parse_nodes(json.dumps(coords))
    g = topology.build_connectivity_graph(nodes, radio_range)
    res = coloring.optimise(topology.build_conflict_graph(g), **kw)
    return nodes, res


def chain(n, spacing=400.0):
    return {f"Node_{i + 1:02d}": [i * spacing, 0.0] for i in range(n)}


def test_direct_neighbours_get_different_slots():
    _, res = plan({"A": [0, 0], "B": [300, 0]})
    assert res.colors["A"] != res.colors["B"]


def test_hidden_terminal_gets_different_slots():
    # A and C are 800 m apart (no link) but both reach B.
    _, res = plan({"A": [0, 0], "B": [400, 0], "C": [800, 0]})
    assert len({res.colors[n] for n in "ABC"}) == 3


def test_three_hops_apart_reuse_the_slot():
    nodes, res = plan(chain(4))
    assert res.colors["Node_01"] == res.colors["Node_04"]
    assert res.num_slots == 3


def test_long_chain_uses_three_slots_only():
    nodes, res = plan(chain(16))
    assert res.num_slots == 3
    assert verify.find_violations(nodes, res.colors, 500.0) == []


def test_range_boundary_is_inclusive():
    _, res = plan({"A": [0, 0], "B": [500, 0]})
    assert res.num_slots == 2
    _, res = plan({"A": [0, 0], "B": [500.01, 0]})
    assert res.num_slots == 1


def test_isolated_nodes_share_one_slot():
    _, res = plan({"A": [0, 0], "B": [5000, 0], "C": [0, 5000]})
    assert res.num_slots == 1


def test_full_mesh_needs_one_slot_per_node():
    pts = {f"N{i}": [i * 10.0, 0.0] for i in range(8)}
    _, res = plan(pts)
    assert res.num_slots == 8 and res.optimal


def test_single_node():
    _, res = plan({"Only": [1, 2]})
    assert res.colors == {"Only": 0}


def test_random_topologies_are_collision_free():
    rng = random.Random(2024)
    for trial in range(40):
        n = rng.randint(2, 30)
        side = rng.choice([500, 1000, 2000])
        coords = {f"Node_{i + 1:02d}": [rng.uniform(0, side), rng.uniform(0, side)]
                  for i in range(n)}
        nodes, res = plan(coords, seed=trial, time_limit=3.0)
        assert verify.find_violations(nodes, res.colors, 500.0) == [], trial
        assert res.lower_bound <= res.num_slots


def test_result_never_worse_than_plain_dsatur():
    rng = random.Random(5)
    coords = {f"Node_{i + 1:02d}": [rng.uniform(0, 1500), rng.uniform(0, 1500)] for i in range(40)}
    nodes = topology.parse_nodes(json.dumps(coords))
    c = topology.build_conflict_graph(topology.build_connectivity_graph(nodes, 500.0))
    _, adj = coloring._adjacency(c)
    baseline = len(set(coloring._dsatur(adj)))
    assert coloring.optimise(c, time_limit=5.0).num_slots <= baseline


def test_same_seed_same_schedule():
    coords = {f"Node_{i + 1:02d}": [(i * 137) % 900, (i * 311) % 900] for i in range(16)}
    _, a = plan(coords, seed=3)
    _, b = plan(coords, seed=3)
    assert a.colors == b.colors


def test_verifier_catches_a_bad_schedule():
    nodes = {"A": (0, 0), "B": (400, 0), "C": (800, 0)}
    bad = verify.find_violations(nodes, {"A": 0, "B": 1, "C": 0}, 500.0)
    assert len(bad) == 1 and "hidden terminal" in bad[0][2]
    bad = verify.find_violations(nodes, {"A": 0, "B": 0, "C": 1}, 500.0)
    assert "direct" in bad[0][2]


@pytest.mark.parametrize("text", [
    "not json", "[]", "{}", '{"A": [1]}', '{"A": ["x", 2]}', '{"A": [1, 2, 3, 4]}',
    '{"A": [NaN, 2]}', '{"A": [1, Infinity]}',
])
def test_bad_input_rejected(text):
    with pytest.raises(topology.TopologyError):
        topology.parse_nodes(text)


def test_nodes_sorted_naturally():
    nodes = topology.parse_nodes('{"Node_10": [0,0], "Node_2": [1,1], "Node_1": [2,2]}')
    assert list(nodes) == ["Node_1", "Node_2", "Node_10"]


def test_cli_end_to_end(tmp_path, capsys):
    out = tmp_path / "s.json"
    code = cli.main(["--nodes", json.dumps(chain(6)), "--json-out", str(out)])
    text = capsys.readouterr().out
    assert code == 0
    assert "TDMA TOPOLOGY OPTIMIZATION REPORT" in text
    assert "verified conflict-free" in text
    data = json.loads(out.read_text())
    assert data["frame_length"] == 3
    assert len(data["matrix"]["rows"]) == 3


def test_cli_reports_bad_input(capsys):
    assert cli.main(["--nodes", "oops"]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_custom_range(capsys):
    cli.main(["--nodes", json.dumps(chain(3)), "--range", "100"])
    assert "1 unique timeslots" in capsys.readouterr().out
