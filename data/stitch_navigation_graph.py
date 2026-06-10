"""
Hậu xử lý navigation_graph.json để nối các component gần nhau.

Chạy:
  python3 data/stitch_navigation_graph.py
"""

import json
import math
from pathlib import Path


BASE_DIR = Path("/home/phuchoangsrc/AI/final/data")
JSON_PATH = BASE_DIR / "navigation_graph.json"
TXT_PATH = BASE_DIR / "navigation_graph_adjacency.txt"

LOCAL_KINDS = {
    "corridor",
    "stair_access",
    "stair_landing",
    "stair_step",
    "access",
    "outdoor_stair",
}

CONNECTOR_KINDS = {
    "access",
    "ground_access",
    "ground_path",
    "skybridge",
    "outdoor_stair",
    "entry_stair",
    "corridor",
    "stair_access",
    "stair_landing",
    "stair_step",
}


def load_graph():
    return json.loads(JSON_PATH.read_text())


def connected_components(nodes_by_id):
    seen = set()
    comps = []
    for node_id in nodes_by_id:
        if node_id in seen:
            continue
        stack = [node_id]
        seen.add(node_id)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for neighbor_id in nodes_by_id[current]["neighbors"]:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    stack.append(neighbor_id)
        comps.append(comp)
    return comps


def build_spatial_buckets(nodes_by_id, cell_size=4.0):
    buckets = {}
    for node_id, node in nodes_by_id.items():
        x, y, z = node["position"]
        key = (int(x // cell_size), int(y // cell_size), int(z // 1.0))
        buckets.setdefault(key, []).append(node_id)
    return buckets


def is_local(node):
    return any(kind in LOCAL_KINDS for kind in node["kinds"])


def is_connector(node):
    return any(kind in CONNECTOR_KINDS for kind in node["kinds"])


def add_edge(data, nodes_by_id, edge_keys, a, b, kind):
    if a == b:
        return False
    key = (min(a, b), max(a, b))
    if key in edge_keys:
        return False
    edge_keys.add(key)
    nodes_by_id[a]["neighbors"].append(b)
    nodes_by_id[b]["neighbors"].append(a)
    pa = nodes_by_id[a]["position"]
    pb = nodes_by_id[b]["position"]
    data["edges"].append(
        {
            "a": a,
            "b": b,
            "kind": kind,
            "length": round(math.dist(pa, pb), 4),
        }
    )
    return True


def stitch_graph(data):
    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    edge_keys = {(min(e["a"], e["b"]), max(e["a"], e["b"])) for e in data.get("edges", [])}
    buckets = build_spatial_buckets(nodes_by_id)

    comps = connected_components(nodes_by_id)
    before = len(comps)

    while True:
        comps = connected_components(nodes_by_id)
        if len(comps) <= 1:
            break
        comp_index = {}
        for idx, comp in enumerate(comps):
            for node_id in comp:
                comp_index[node_id] = idx

        best = None
        best_dist = None
        for node_id, node in nodes_by_id.items():
            if not is_connector(node):
                continue
            x, y, z = node["position"]
            key = (int(x // 4.0), int(y // 4.0), int(z // 1.0))
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    for dz in (-1, 0, 1):
                        for other_id in buckets.get((key[0] + dx, key[1] + dy, key[2] + dz), []):
                            if other_id <= node_id or comp_index[other_id] == comp_index[node_id]:
                                continue
                            other = nodes_by_id[other_id]
                            if not is_connector(other):
                                continue
                            pa = node["position"]
                            pb = other["position"]
                            z_diff = abs(pa[2] - pb[2])
                            planar = math.dist((pa[0], pa[1]), (pb[0], pb[1]))
                            dist = math.dist(pa, pb)

                            valid = False
                            if is_local(node) and is_local(other) and z_diff <= 0.75 and dist <= 3.6:
                                valid = True
                            elif z_diff <= 1.5 and planar <= 8.5 and dist <= 9.0:
                                valid = True

                            if not valid:
                                continue
                            if best_dist is None or dist < best_dist:
                                best_dist = dist
                                best = (node_id, other_id)

        if best is None:
            break
        add_edge(data, nodes_by_id, edge_keys, best[0], best[1], "component_stitch")

    after = len(connected_components(nodes_by_id))
    for node in data["nodes"]:
        node["neighbors"] = sorted(set(node["neighbors"]))
    data["edge_count"] = len(data["edges"])
    data["node_count"] = len(data["nodes"])
    return before, after


def write_outputs(data):
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    lines = []
    for node in data["nodes"]:
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
    TXT_PATH.write_text("\n".join(lines) + "\n")


def main():
    data = load_graph()
    before, after = stitch_graph(data)
    write_outputs(data)
    stitch_edges = sum(1 for edge in data["edges"] if edge.get("kind") == "component_stitch")
    print(f"[OK] components {before} -> {after}")
    print(f"[OK] stitch_edges={stitch_edges}")


if __name__ == "__main__":
    main()
