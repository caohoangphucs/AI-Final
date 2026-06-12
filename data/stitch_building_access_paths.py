"""
Hậu xử lý navigation_graph.json để nối các cụm lối đi công trình về mạng chính.

Chạy:
  python3 data/stitch_building_access_paths.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path


BASE_DIR = Path("/home/phuchoangsrc/AI/final/data")
JSON_PATH = BASE_DIR / "navigation_graph.json"
TXT_PATH = BASE_DIR / "navigation_graph_adjacency.txt"
BUILDING_ACCESS_MAX_PLANAR = 24.0
BUILDING_ACCESS_GROUND_Z_TOLERANCE = 1.0
BUILDING_ACCESS_ELEVATED_Z_TOLERANCE = 3.0


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


def compute_components(data):
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    seen = set()
    components = []

    for node_id in nodes_by_id:
        if node_id in seen:
            continue
        stack = [node_id]
        seen.add(node_id)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for neighbor_id in nodes_by_id[current].get("neighbors", []):
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    stack.append(neighbor_id)
        components.append(comp)

    return sorted(components, key=len, reverse=True)


def is_building_access_anchor(node):
    anchor_kinds = {
        "ground_access",
        "access",
        "ground_path",
        "outdoor_stair",
        "entry_stair",
        "skybridge",
        "corridor",
        "stair_access",
        "stair_landing",
        "stair_step",
    }
    return any(kind in anchor_kinds for kind in node["kinds"])


def building_access_z_tolerance(node_a, node_b):
    if "ground_path" in node_a["kinds"] or "ground_path" in node_b["kinds"]:
        return BUILDING_ACCESS_GROUND_Z_TOLERANCE
    return BUILDING_ACCESS_ELEVATED_Z_TOLERANCE


def stitch_building_access_components(data):
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    edge_keys = {(min(edge["a"], edge["b"]), max(edge["a"], edge["b"])) for edge in data.get("edges", [])}
    stitched = 0

    while True:
        components = compute_components(data)
        if len(components) <= 1:
            break

        main_component = set(components[0])
        main_anchor_ids = [node_id for node_id in main_component if is_building_access_anchor(nodes_by_id[node_id])]
        if not main_anchor_ids:
            break

        best = None
        for comp in components[1:]:
            comp_anchor_ids = [node_id for node_id in comp if is_building_access_anchor(nodes_by_id[node_id])]
            if not comp_anchor_ids:
                continue

            for a_id in comp_anchor_ids:
                pa = nodes_by_id[a_id]["position"]
                for b_id in main_anchor_ids:
                    pb = nodes_by_id[b_id]["position"]
                    if abs(pa[2] - pb[2]) > building_access_z_tolerance(nodes_by_id[a_id], nodes_by_id[b_id]):
                        continue
                    planar = math.dist((pa[0], pa[1]), (pb[0], pb[1]))
                    if planar <= 0.05 or planar > BUILDING_ACCESS_MAX_PLANAR:
                        continue
                    dist = math.dist(pa, pb)
                    if best is None or dist < best[0]:
                        best = (dist, planar, a_id, b_id)

        if best is None:
            break

        _dist, planar, a_id, b_id = best
        if not add_edge(data, nodes_by_id, edge_keys, a_id, b_id, "building_access_stitch"):
            break
        stitched += 1
        print(f"[access] stitched {a_id} <-> {b_id} planar={planar:.2f}")

    return stitched


def main():
    data = load_graph()
    before = len(compute_components(data))
    stitched = stitch_building_access_components(data)
    after = len(compute_components(data))
    write_outputs(data)
    print(f"[OK] components {before} -> {after}")
    print(f"[OK] building_access_stitch edges added={stitched}")


if __name__ == "__main__":
    main()
