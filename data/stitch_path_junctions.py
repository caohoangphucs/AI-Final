"""
Hậu xử lý navigation_graph.json để nối các node đường đi đang sát nhau.

Chạy:
  python3 data/stitch_path_junctions.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path


BASE_DIR = Path("/home/phuchoangsrc/AI/final/data")
JSON_PATH = BASE_DIR / "navigation_graph.json"
TXT_PATH = BASE_DIR / "navigation_graph_adjacency.txt"
GROUND_JUNCTION_RADIUS = 1.1
GROUND_JUNCTION_Z_TOLERANCE = 0.2


def load_graph():
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def write_outputs(data):
    nodes = sorted(data["nodes"], key=lambda node: node["id"])
    for node in nodes:
        node["neighbors"] = sorted(set(node.get("neighbors", [])))
    data["nodes"] = nodes
    data["node_count"] = len(nodes)
    data["edge_count"] = len(data.get("edges", []))
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    for node in nodes:
        lines.append(
            "node {id}: pos=({x:.3f}, {y:.3f}, {z:.3f}) kinds={kinds} neighbors={neighbors}".format(
                id=node["id"],
                x=node["position"][0],
                y=node["position"][1],
                z=node["position"][2],
                kinds=",".join(node["kinds"]),
                neighbors=node["neighbors"],
            )
        )
    TXT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_edge(data, nodes_by_id, edge_keys, a_id, b_id, kind):
    if a_id == b_id:
        return False
    key = (min(a_id, b_id), max(a_id, b_id))
    if key in edge_keys:
        return False
    edge_keys.add(key)
    nodes_by_id[a_id]["neighbors"].append(b_id)
    nodes_by_id[b_id]["neighbors"].append(a_id)
    pa = nodes_by_id[a_id]["position"]
    pb = nodes_by_id[b_id]["position"]
    data["edges"].append(
        {
            "a": a_id,
            "b": b_id,
            "kind": kind,
            "length": round(math.dist(pa, pb), 4),
        }
    )
    return True


def stitch_path_junctions(data):
    nodes = [node for node in data["nodes"] if "ground_path" in node["kinds"]]
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    edge_keys = {(min(edge["a"], edge["b"]), max(edge["a"], edge["b"])) for edge in data.get("edges", [])}
    added = 0

    for i, node in enumerate(nodes):
        pa = node["position"]
        for other in nodes[i + 1 :]:
            if other["id"] in node.get("neighbors", []):
                continue
            pb = other["position"]
            if abs(pa[2] - pb[2]) > GROUND_JUNCTION_Z_TOLERANCE:
                continue
            planar = math.dist((pa[0], pa[1]), (pb[0], pb[1]))
            if planar <= 0.05 or planar > GROUND_JUNCTION_RADIUS:
                continue
            if add_edge(data, nodes_by_id, edge_keys, node["id"], other["id"], "ground_junction"):
                added += 1
                if added <= 40:
                    print(f"[junction] stitched {node['id']} <-> {other['id']} planar={planar:.2f}")

    return added


def main():
    data = load_graph()
    added = stitch_path_junctions(data)
    write_outputs(data)
    print(f"[OK] ground_junction edges added={added}")


if __name__ == "__main__":
    main()
