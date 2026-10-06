import importlib.util
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bridge", ROOT / "emane" / "bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

from tdma_planner import cli


@pytest.fixture
def schedule(tmp_path):
    out = tmp_path / "s.json"
    cli.main(["--nodes-file", str(ROOT / "examples" / "grid_16.json"), "--json-out", str(out)])
    return out


def test_bridge_files_are_wellformed(schedule, tmp_path):
    out = tmp_path / "build"
    assert bridge.main([str(schedule), "--out", str(out)]) == 0
    for f in out.glob("*.xml"):
        ET.parse(f)


def test_schedule_xml_matches_python_schedule(schedule, tmp_path):
    out = tmp_path / "build"
    bridge.main([str(schedule), "--out", str(out)])
    data = json.loads(schedule.read_text())
    root = ET.parse(out / "tdmaschedule.xml").getroot()
    structure = root.find("structure")
    assert int(structure.get("slots")) == data["frame_length"]
    assert structure.get("slotduration") == "1000"
    tx = {}
    for slot in root.iter("slot"):
        if slot.find("tx") is not None:
            for nem in slot.get("nodes").split(","):
                tx[int(nem)] = int(slot.get("index"))
    expected = {int(n.split("_")[1]): s for n, s in data["node_to_slot"].items()}
    assert tx == expected


def test_every_node_listens_in_other_slots(schedule, tmp_path):
    out = tmp_path / "build"
    bridge.main([str(schedule), "--out", str(out)])
    root = ET.parse(out / "tdmaschedule.xml").getroot()
    per_slot = {}
    for slot in root.iter("slot"):
        kind = "tx" if slot.find("tx") is not None else "rx"
        per_slot.setdefault(int(slot.get("index")), []).extend(
            (kind, int(n)) for n in slot.get("nodes").split(","))
    for entries in per_slot.values():
        assert sorted(n for _, n in entries) == list(range(1, 17))


def test_bridge_refuses_colliding_schedule(tmp_path):
    bad = {"radio_range_m": 500.0, "frame_length": 2,
           "positions": {"Node_01": [0, 0], "Node_02": [400, 0]},
           "node_to_slot": {"Node_01": 0, "Node_02": 0}}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(SystemExit):
        bridge.main([str(path), "--out", str(tmp_path / "o")])


def test_compact_nem_ids():
    assert bridge.nem_ids(["Node_01", "Node_02"]) == {"Node_01": 1, "Node_02": 2}
    assert bridge.nem_ids(["a", "b"]) == {"a": 1, "b": 2}
