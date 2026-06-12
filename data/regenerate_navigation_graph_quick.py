"""
Regenerate navigation graph JSON/TXT from Untitled_arch.blend,
skipping the expensive global component stitch pass.

Run:
  blender --background data/Untitled_arch.blend --python data/regenerate_navigation_graph_quick.py
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

import generate_navigation_graph as g


def main():
    graph = g.GraphBuilder()

    block_bounds = {}
    for name, side, floors, floor_h in g.BLOCK_SPECS:
        obj = g.bpy.data.objects.get(name)
        if not obj:
            print(f"[WARN] Missing block: {name}")
            continue
        x_min, x_max, y_min, y_max, z_min, _ = g.get_bounds(obj)
        bounds = (x_min, x_max, y_min, y_max, z_min, z_min + floors * floor_h)
        block_bounds[name] = bounds
        g.add_corridor_graph(graph, name, bounds, side, floors)
        g.add_internal_stair_graph(graph, name, bounds, side, floors)

    for name, x_min, x_max, y_min, y_max, z_min, side, floors, floor_h in g.EXTRA_COMPLEXES:
        bounds = (x_min, x_max, y_min, y_max, z_min, z_min + floors * floor_h)
        block_bounds[name] = bounds
        g.add_corridor_graph(graph, name, bounds, side, floors)
        g.add_internal_stair_graph(graph, name, bounds, side, floors)

    g.add_a1_internal_graph(graph)

    for name, pt1, pt2, z in g.SKYBRIDGES:
        g.add_skybridge_graph(graph, name, pt1, pt2, z)

    for name, cx, cy, z_bottom, z_top, facing, width in g.OUTDOOR_STAIRS:
        g.add_outdoor_stair_graph(graph, name, cx, cy, z_bottom, z_top, facing, width)

    for name, cx, cy, n_steps, step_w, step_d, step_h in g.A1_FRONT_STAIRS:
        g.add_a1_front_stair_graph(graph, name, cx, cy, n_steps, step_w, step_d, step_h)

    g.add_ground_paths(graph)
    ground_junction_edges = g.connect_ground_path_junctions(graph, block_bounds)
    g.connect_ground_path_network(graph, block_bounds)
    flat_stitched_edges = g.stitch_flat_ground_components(graph)
    g.connect_access_points(graph, block_bounds)
    building_access_stitched_edges = g.stitch_building_access_components(graph, block_bounds)
    components = len(g.compute_connected_components(graph))
    g.export_graph_text(graph)

    print(f"[OK] quick nodes={len(graph.nodes)} edges={len(graph.edges)}")
    print(f"[OK] ground_junction_edges={ground_junction_edges}")
    print(f"[OK] flat_ground_stitched_edges={flat_stitched_edges}")
    print(f"[OK] building_access_stitched_edges={building_access_stitched_edges}")
    print(f"[OK] components={components}")
    print(f"[OK] wrote {g.JSON_PATH}")
    print(f"[OK] wrote {g.TXT_PATH}")


if __name__ == "__main__":
    main()
