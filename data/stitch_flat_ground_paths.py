"""
Hậu xử lý navigation_graph.json để nối mọi component đường phẳng với nhau.

Chạy:
  python3 data/stitch_flat_ground_paths.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path


BASE_DIR = Path("/home/phuchoangsrc/AI/final/data")
JSON_PATH = BASE_DIR / "navigation_graph.json"
TXT_PATH = BASE_DIR / "navigation_graph_adjacency.txt"
GROUND_Z = 0.0
FLAT_GROUND_STITCH_Z_TOLERANCE = 0.25


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


def flat_ground_components(data):
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    ground_ids = {
        node["id"]
        for node in data["nodes"]
        if "ground_path" in node["kinds"] and abs(node["position"][2] - GROUND_Z) <= FLAT_GROUND_STITCH_Z_TOLERANCE
    }
    seen = set()
    components = []

    for node_id in ground_ids:
        if node_id in seen:
            continue
        stack = [node_id]
        seen.add(node_id)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for neighbor_id in nodes_by_id[current].get("neighbors", []):
                if neighbor_id in ground_ids and neighbor_id not in seen:
                    seen.add(neighbor_id)
                    stack.append(neighbor_id)
        components.append(comp)
    return components


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


def stitch_flat_ground_components(data):
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    edge_keys = {(min(edge["a"], edge["b"]), max(edge["a"], edge["b"])) for edge in data.get("edges", [])}
    stitched = 0

    while True:
        components = sorted(flat_ground_components(data), key=len, reverse=True)
        if len(components) <= 1:
            break

        best = None
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                for a_id in components[i]:
                    pa = nodes_by_id[a_id]["position"]
                    for b_id in components[j]:
                        pb = nodes_by_id[b_id]["position"]
                        if abs(pa[2] - pb[2]) > FLAT_GROUND_STITCH_Z_TOLERANCE:
                            continue
                        planar = math.dist((pa[0], pa[1]), (pb[0], pb[1]))
                        if best is None or planar < best[0]:
                            best = (planar, a_id, b_id)

        if best is None:
            break

        planar, a_id, b_id = best
        if add_edge(data, nodes_by_id, edge_keys, a_id, b_id, "ground_flat_stitch"):
            stitched += 1
            print(f"[flat] stitched {a_id} <-> {b_id} planar={planar:.2f}")
        else:
            break

    return stitched


def main():
    data = load_graph()
    before = len(flat_ground_components(data))
    stitched = stitch_flat_ground_components(data)
    after = len(flat_ground_components(data))
    write_outputs(data)
    print(f"[OK] flat components {before} -> {after}")
    print(f"[OK] ground_flat_stitch edges added={stitched}")


if __name__ == "__main__":
    main()
