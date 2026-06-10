"""
Kiểm tra các cạnh trong navigation graph có bị mesh chắn hay không.

Chạy:
  blender --background data/Untitled_arch.blend --python data/validate_navigation_graph.py

Output:
- data/navigation_blockers_report.json
- data/navigation_blockers_report.txt
"""

import bpy
import json
from collections import Counter
from mathutils import Vector


BASE_DIR = "/home/phuchoangsrc/AI/final/data"
GRAPH_PATH = f"{BASE_DIR}/navigation_graph.json"
REPORT_JSON_PATH = f"{BASE_DIR}/navigation_blockers_report.json"
REPORT_TXT_PATH = f"{BASE_DIR}/navigation_blockers_report.txt"

HELPER_PREFIXES = ("StairEntry_", "BridgeEntry_", "Cut_")
IGNORE_NAME_PARTS = (
    "_Slab",
    "_Passage",
    "_Step_",
    "_F1_",
    "_F2_",
    "Terrain_",
    "Road_",
    "Walk_",
    "FieldFence_",
)
RAY_HEIGHTS = (0.6, 1.1, 1.6)
SIDE_OFFSETS = (0.0, -0.18, 0.18)
MIN_EDGE_LENGTH = 0.05
END_MARGIN = 0.04
MAX_REPORTED_BLOCKERS = 300


def load_graph():
    with open(GRAPH_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def is_helper_object(obj):
    return obj.name.startswith(HELPER_PREFIXES)


def is_ignored_hit_object(obj):
    if obj is None:
        return True
    if obj.type != "MESH":
        return True
    if obj.hide_render or obj.hide_viewport:
        return True
    if is_helper_object(obj):
        return True
    return any(part in obj.name for part in IGNORE_NAME_PARTS)


def make_side_vector(start, end):
    flat = Vector((end.x - start.x, end.y - start.y, 0.0))
    if flat.length <= 1e-6:
        return Vector((0.0, 0.0, 0.0))
    flat = flat.normalized()
    return Vector((-flat.y, flat.x, 0.0))


def edge_samples(start, end):
    direction = end - start
    length = direction.length
    if length < MIN_EDGE_LENGTH:
        return []

    direction = direction.normalized()
    side = make_side_vector(start, end)
    samples = []
    for height in RAY_HEIGHTS:
        vertical = Vector((0.0, 0.0, height))
        for side_offset in SIDE_OFFSETS:
            lateral = side * side_offset
            ray_start = start + vertical + lateral + direction * END_MARGIN
            ray_end = end + vertical + lateral - direction * END_MARGIN
            ray_vec = ray_end - ray_start
            if ray_vec.length >= MIN_EDGE_LENGTH:
                samples.append((height, side_offset, ray_start, ray_end, ray_vec))
    return samples


def cast_until_blocked(scene, depsgraph, ray_start, ray_vec):
    direction = ray_vec.normalized()
    remaining = ray_vec.length
    origin = ray_start

    while remaining > MIN_EDGE_LENGTH:
        hit, location, _normal, _face_index, obj, _matrix = scene.ray_cast(
            depsgraph,
            origin,
            direction,
            distance=remaining,
        )
        if not hit:
            return None

        distance = (location - origin).length
        if distance >= remaining - END_MARGIN:
            return None

        if not is_ignored_hit_object(obj):
            return {
                "object_name": obj.name,
                "hit_position": [round(v, 4) for v in location],
                "hit_distance": round(distance, 4),
            }

        step = max(distance + 0.02, 0.02)
        origin = origin + direction * step
        remaining -= step

    return None


def validate_graph(graph):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    nodes = {node["id"]: node for node in graph["nodes"]}
    checked_edges = set()
    blocked = []

    for node in graph["nodes"]:
        start_id = node["id"]
        start_pos = Vector(node["position"])
        for neighbor_id in node.get("neighbors", []):
            edge_key = tuple(sorted((start_id, neighbor_id)))
            if edge_key in checked_edges:
                continue
            checked_edges.add(edge_key)

            other = nodes.get(neighbor_id)
            if other is None:
                continue
            end_pos = Vector(other["position"])
            samples = edge_samples(start_pos, end_pos)
            if not samples:
                continue

            for height, side_offset, ray_start, _ray_end, ray_vec in samples:
                hit = cast_until_blocked(scene, depsgraph, ray_start, ray_vec)
                if hit is None:
                    continue

                blocked.append(
                    {
                        "edge": [start_id, neighbor_id],
                        "from": [round(v, 4) for v in start_pos],
                        "to": [round(v, 4) for v in end_pos],
                        "distance": round((end_pos - start_pos).length, 4),
                        "ray_height": height,
                        "side_offset": side_offset,
                        "blocker": hit["object_name"],
                        "hit_position": hit["hit_position"],
                        "start_labels": node.get("labels", [])[:3],
                        "end_labels": other.get("labels", [])[:3],
                    }
                )
                break

            if len(blocked) >= MAX_REPORTED_BLOCKERS:
                return checked_edges, blocked

    return checked_edges, blocked


def write_reports(graph, checked_edges, blocked):
    blocker_counts = Counter(item["blocker"] for item in blocked)
    report = {
        "node_count": graph.get("node_count", len(graph.get("nodes", []))),
        "edge_count": graph.get("edge_count", len(graph.get("edges", []))),
        "checked_edge_count": len(checked_edges),
        "blocked_edge_count": len(blocked),
        "top_blockers": blocker_counts.most_common(30),
        "blocked_edges": blocked,
    }

    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    lines = [
        f"Checked edges: {len(checked_edges)}",
        f"Blocked edges: {len(blocked)}",
        "",
        "Top blockers:",
    ]
    for name, count in blocker_counts.most_common(30):
        lines.append(f"- {name}: {count}")

    lines.append("")
    lines.append("Blocked edge samples:")
    for item in blocked[:80]:
        lines.append(
            f"- edge {item['edge'][0]} <-> {item['edge'][1]} blocked by {item['blocker']} "
            f"at {item['hit_position']} height={item['ray_height']} offset={item['side_offset']}"
        )
        if item["start_labels"] or item["end_labels"]:
            lines.append(
                f"  from {item['start_labels']} to {item['end_labels']}"
            )

    with open(REPORT_TXT_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    graph = load_graph()
    checked_edges, blocked = validate_graph(graph)
    write_reports(graph, checked_edges, blocked)
    print(f"[OK] checked_edges={len(checked_edges)} blocked_edges={len(blocked)}")
    if blocked:
        print("[INFO] top blockers:")
        counts = Counter(item["blocker"] for item in blocked)
        for name, count in counts.most_common(15):
            print(f"  - {name}: {count}")


if __name__ == "__main__":
    main()
