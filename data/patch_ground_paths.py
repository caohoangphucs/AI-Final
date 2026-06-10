"""
Patch navigation_graph.json with denser flat-ground routes around block A.

Run:
  python3 data/patch_ground_paths.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "navigation_graph.json"
TXT_PATH = BASE_DIR / "navigation_graph_adjacency.txt"
NODE_TOLERANCE = 0.15
MAX_SEGMENT = 3.0

EXTRA_PATHS = [
    ("Walk_A_Mid_Front", [(-35.0, -84.0, 0.0), (45.0, -84.0, 0.0)]),
    ("Walk_A_Mid_Back", [(-35.0, -78.0, 0.0), (45.0, -78.0, 0.0)]),
    ("Walk_A23_Inner_Left", [(-8.0, -92.0, 0.0), (-8.0, -66.0, 0.0)]),
    ("Walk_A45_Inner_Right", [(18.0, -92.0, 0.0), (18.0, -66.0, 0.0)]),
]

REINFORCE_PATH_LABELS = {
    "Walk_A_Front",
    "Walk_A_Back",
    "Walk_A23_Left",
    "Walk_A45_Right",
    "Walk_Main_Path",
    "Walk_Front_To_A23",
    "Walk_Front_To_A45",
    "Walk_Back_Left_Connector",
    "Walk_Back_Right_Connector",
    "Walk_A1_Front_Plaza",
}


def node_key(position):
    return tuple(round(value / NODE_TOLERANCE) for value in position)


def subdivide_polyline(points):
    dense = [points[0]]
    for start, end in zip(points, points[1:]):
        dist = math.dist(start, end)
        steps = max(1, int(math.ceil(dist / MAX_SEGMENT)))
        for step in range(1, steps + 1):
            t = step / steps
            dense.append(
                (
                    round(start[0] + (end[0] - start[0]) * t, 4),
                    round(start[1] + (end[1] - start[1]) * t, 4),
                    round(start[2] + (end[2] - start[2]) * t, 4),
                )
            )
    return dense


def load_graph():
    with JSON_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_graph(data):
    nodes = sorted(data["nodes"], key=lambda node: node["id"])
    edges = sorted(
        data["edges"],
        key=lambda edge: (min(edge["a"], edge["b"]), max(edge["a"], edge["b"]), edge["kind"]),
    )
    data["nodes"] = nodes
    data["edges"] = edges
    data["node_count"] = len(nodes)
    data["edge_count"] = len(edges)

    with JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

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
    TXT_PATH.write_text("\n".join(lines), encoding="utf-8")


def patch_graph(data):
    nodes = data["nodes"]
    node_by_key = {node_key(node["position"]): node for node in nodes}
    edge_keys = {
        (min(edge["a"], edge["b"]), max(edge["a"], edge["b"]))
        for edge in data["edges"]
    }

    def ensure_node(position, kind, label):
        key = node_key(position)
        node = node_by_key.get(key)
        if node is None:
            node = {
                "id": len(nodes),
                "position": [round(position[0], 4), round(position[1], 4), round(position[2], 4)],
                "kinds": [kind],
                "labels": [label],
                "neighbors": [],
            }
            nodes.append(node)
            node_by_key[key] = node
        else:
            if kind not in node["kinds"]:
                node["kinds"].append(kind)
            if label not in node["labels"]:
                node["labels"].append(label)
        return node["id"]

    def ensure_edge(a_id, b_id, kind):
        if a_id == b_id:
            return
        key = (min(a_id, b_id), max(a_id, b_id))
        if key in edge_keys:
            return
        edge_keys.add(key)
        a = nodes[a_id]
        b = nodes[b_id]
        a["neighbors"].append(b_id)
        b["neighbors"].append(a_id)
        a["neighbors"].sort()
        b["neighbors"].sort()
        data["edges"].append(
            {
                "a": a_id,
                "b": b_id,
                "kind": kind,
                "length": round(math.dist(a["position"], b["position"]), 4),
            }
        )

    def add_polyline(name, points):
        point_ids = []
        for index, position in enumerate(subdivide_polyline(points)):
            point_ids.append(ensure_node(position, "ground_path", f"{name}:{index}"))
        for a_id, b_id in zip(point_ids, point_ids[1:]):
            ensure_edge(a_id, b_id, "ground_path")

    existing_ground_lines = []
    seen_base_labels = set()
    for node in list(nodes):
        for label in node.get("labels", []):
            base = label.split(":", 1)[0]
            if base in REINFORCE_PATH_LABELS and base not in seen_base_labels:
                seen_base_labels.add(base)
                path_nodes = [
                    other for other in nodes
                    if any(other_label.startswith(base + ":") for other_label in other.get("labels", []))
                ]
                path_nodes.sort(key=lambda item: min(
                    int(lbl.split(":", 1)[1]) for lbl in item["labels"] if lbl.startswith(base + ":")
                ))
                existing_ground_lines.append((base, [tuple(n["position"]) for n in path_nodes]))

    for name, points in existing_ground_lines:
        add_polyline(name + "_Dense", points)
    for name, points in EXTRA_PATHS:
        add_polyline(name, points)

    return data


def main():
    data = load_graph()
    before_nodes = data["node_count"]
    before_edges = data["edge_count"]
    patch_graph(data)
    save_graph(data)
    print(f"[OK] nodes {before_nodes} -> {data['node_count']}")
    print(f"[OK] edges {before_edges} -> {data['edge_count']}")
    print(f"[OK] wrote {JSON_PATH}")


if __name__ == "__main__":
    main()
