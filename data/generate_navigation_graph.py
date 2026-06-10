"""
Sinh navigation graph từ mô hình kiến trúc trong Blender.

Output:
- data/navigation_graph.json
- data/navigation_graph_adjacency.txt
- data/navigation_graph.obj (+ .mtl)

Chạy:
  blender --background data/Untitled_arch.blend --python data/generate_navigation_graph.py
"""

import bpy
import bmesh
import json
import math
from mathutils import Vector


OUT_DIR = "/home/phuchoangsrc/AI/final/data"
OBJ_PATH = f"{OUT_DIR}/navigation_graph.obj"
JSON_PATH = f"{OUT_DIR}/navigation_graph.json"
TXT_PATH = f"{OUT_DIR}/navigation_graph_adjacency.txt"
BLEND_PATH = f"{OUT_DIR}/Untitled_arch_navigation.blend"
COLLECTION_NAME = "NavigationGraph"
NODE_TOLERANCE = 0.15
GROUND_Z = 0.0
GROUND_PATH_SEGMENT_MAX = 3.0
GROUND_LINK_RADIUS = 6.5
GROUND_LINKS_PER_NODE = 4


def get_block_profile(prefix):
    profile = {
        "corridor_width": 2.2,
        "bay_spacing": 4.5,
        "stair_clear_bays": 2,
    }

    classroom_keys = ("Phong_Hoc", "Giang_Duong", "Lop_Hoc")
    office_keys = ("Van_Phong", "Trung_Tam_Hanh_Chinh")
    workshop_keys = ("Xuong_", "Xuong", "Thu_Vien", "Hoi_Truong", "Trung_Tam_Viet_Duc")

    if any(key in prefix for key in classroom_keys):
        profile.update({"corridor_width": 2.4, "bay_spacing": 4.2})
    elif any(key in prefix for key in office_keys):
        profile.update({"corridor_width": 2.0, "bay_spacing": 3.6})
    elif any(key in prefix for key in workshop_keys):
        profile.update({"corridor_width": 2.8, "bay_spacing": 5.8})

    if "Thu_Vien" in prefix:
        profile.update({"corridor_width": 3.0, "bay_spacing": 6.0})
    if "Hoi_Truong" in prefix:
        profile.update({"corridor_width": 3.2, "bay_spacing": 6.5})

    return profile


BLOCK_SPECS = [
    ("Khoi_A.2_Phong_Hoc", "S", 6, 4.0),
    ("Khoi_A.3_Giang_Duong", "S", 6, 4.0),
    ("Khoi_A.4_Phong_Hoc", "S", 6, 4.0),
    ("Khoi_A.5_Giang_Duong", "S", 6, 4.0),
    ("Khoi_A_Day_Trai", "E", 5, 4.0),
    ("Khoi_A_Day_Phai", "W", 5, 4.0),
    ("Khoi_B_Ngang", "S", 5, 4.0),
    ("Khoi_C_Phong_Hoc_Dien", "S", 4, 4.2),
    ("Khoi_D_Phong_Hoc_Dien", "S", 4, 4.2),
    ("Khoi_E.0_Van_Phong_Co_Khi", "S", 3, 4.0),
    ("Khoi_E.1_Xuong_Chat_Luong_Cao", "S", 3, 4.0),
    ("Khoi_E.2_Can_Tin_Sieu_Thi", "S", 3, 4.0),
    ("Khoi_E.3_Xuong_Co_Khi", "S", 3, 4.0),
    ("Khoi_E.4_Lop_Hoc_Bat_Giac", "S", 3, 4.0),
    ("Khoi_F.1_Phong_Hoc_Xuong", "S", 4, 4.0),
    ("Khoi_G_Trung_Tam_Viet_Duc", "S", 4, 4.0),
    ("Khoi_Thu_Vien", "S", 5, 4.2),
    ("Hoi_Truong_Lon", "S", 3, 4.5),
    ("Xuong_Bien_O_To", "S", 3, 4.0),
    ("Xuong_Chung_Gam", "S", 3, 4.0),
    ("Xuong_Dong_Co", "S", 3, 4.0),
    ("Xuong_Nhiet_Dien_Lanh", "S", 3, 4.0),
    ("Xuong_Thuc_Tap_Go", "S", 3, 4.0),
]

EXTRA_COMPLEXES = [
    ("Khoi_H_Trung_Tam_Nghien_Cuu", 76.0, 102.0, 18.0, 42.0, 2.5, "S", 8, 4.5),
    ("Khoi_I_Hoc_Lieu_So", 106.0, 136.0, 10.0, 34.0, 2.5, "S", 7, 4.5),
    ("Khoi_J_Ky_Tuc_Xa_Tay", -112.0, -84.0, 22.0, 56.0, 5.0, "E", 8, 4.2),
    ("Khoi_K_Phong_Thi_Nghiem", 82.0, 112.0, -54.0, -18.0, 0.0, "N", 9, 4.4),
    ("Khoi_L_Xuong_Sang_Tao", -118.0, -86.0, -36.0, -8.0, 0.0, "S", 4, 4.2),
    ("Khoi_M_Hanh_Chinh_Mo_Rong", 118.0, 148.0, -48.0, -16.0, 5.0, "N", 6, 4.2),
    ("Khoi_N_Thap_Dong", 154.0, 176.0, 4.0, 26.0, 2.5, "W", 11, 4.6),
    ("Khoi_O_Thap_Tay", 184.0, 206.0, 4.0, 26.0, 2.5, "E", 10, 4.6),
]

SKYBRIDGES = [
    ("Bridge_A_L_Lib", (-15.0, 15.0), (0.0, -10.0), 10.0),
    ("Bridge_A_R_Lib", (15.0, 15.0), (0.0, -10.0), 5.0),
    ("Bridge_A_L_C", (-15.0, 15.0), (-35.0, 30.0), 10.0),
    ("Bridge_C_D", (-35.0, 30.0), (-48.0, 10.0), 5.0),
    ("Bridge_D_E2", (-48.0, 10.0), (-55.0, -5.0), 5.0),
    ("Bridge_Lib_E2", (0.0, -10.0), (-55.0, -5.0), 5.0),
    ("Bridge_E2_E3", (-55.0, -5.0), (-70.0, -25.0), 4.0),
    ("Bridge_A4_F1", (25.0, -85.0), (55.0, -35.0), 12.0),
    ("Bridge_F1_G", (55.0, -35.0), (55.0, -58.0), 6.0),
    ("Bridge_H_I", (102.0, 30.0), (106.0, 22.0), 18.0),
    ("Bridge_H_K", (90.0, 18.0), (96.0, -18.0), 13.5),
    ("Bridge_J_C", (-84.0, 36.0), (-35.0, 30.0), 10.0),
    ("Bridge_L_E3", (-86.0, -22.0), (-70.0, -25.0), 8.0),
    ("Bridge_K_F1", (82.0, -32.0), (55.0, -35.0), 12.0),
    ("Bridge_M_K", (118.0, -26.0), (112.0, -30.0), 12.6),
    ("Bridge_M_N", (148.0, -22.0), (154.0, 10.0), 18.4),
    ("Bridge_N_O_L3", (176.0, 10.0), (184.0, 10.0), 16.3),
    ("Bridge_N_O_L5", (176.0, 16.0), (184.0, 16.0), 25.5),
    ("Bridge_N_O_L7", (176.0, 22.0), (184.0, 22.0), 34.7),
]

OUTDOOR_STAIRS = [
    ("OutStair_AL_up", -15.0, 12.0, 0.0, 10.0, "S", 3.5),
    ("OutStair_AL_side", -19.0, 15.0, 0.0, 10.0, "E", 3.5),
    ("OutStair_AR_up", 15.0, 12.0, 0.0, 5.0, "S", 3.5),
    ("OutStair_AR_side", 19.0, 15.0, 0.0, 10.0, "W", 3.5),
    ("OutStair_Lib_N", 0.0, -7.0, 0.0, 5.0, "S", 3.5),
    ("OutStair_Lib_S", 0.0, -13.0, 0.0, 10.0, "N", 3.5),
    ("OutStair_E2_E", -51.0, -5.0, 0.0, 4.0, "W", 3.5),
    ("OutStair_E2_W", -59.0, -5.0, 0.0, 8.0, "E", 3.5),
    ("OutStair_E3", -70.0, -21.0, 0.0, 8.0, "S", 3.5),
    ("OutStair_F1_N", 55.0, -31.0, 0.0, 6.0, "S", 3.5),
    ("OutStair_F1_S", 55.0, -39.0, 0.0, 12.0, "N", 3.5),
    ("OutStair_G", 55.0, -54.0, 0.0, 12.0, "S", 3.5),
    ("OutStair_C", -35.0, 26.0, 0.0, 5.0, "S", 3.5),
    ("OutStair_D", -48.0, 6.0, 0.0, 10.0, "S", 3.5),
    ("OutStair_A1_L", -8.0, -78.0, 0.0, 20.0, "N", 2.5),
    ("OutStair_A1_R", 18.0, -78.0, 0.0, 20.0, "N", 2.5),
    ("OutStair_H_S", 88.0, 18.0, 2.5, 18.0, "S", 3.5),
    ("OutStair_I_S", 120.0, 10.0, 2.5, 13.5, "S", 3.5),
    ("OutStair_J_E", -84.0, 40.0, 5.0, 10.0, "W", 3.5),
    ("OutStair_K_N", 96.0, -18.0, 0.0, 13.5, "S", 3.5),
    ("OutStair_L_E", -86.0, -20.0, 0.0, 8.0, "W", 3.5),
    ("OutStair_M_W", 118.0, -28.0, 5.0, 12.6, "E", 3.5),
    ("OutStair_N_S", 165.0, 4.0, 2.5, 16.3, "S", 3.5),
    ("OutStair_O_S", 195.0, 4.0, 2.5, 16.3, "S", 3.5),
]

A1_FRONT_STAIRS = [
    ("Stair_Main", 5.0, -69.0, 6, 16.0, 1.5, 0.2),
    ("Stair_A23_Left", -20.0, -69.0, 6, 4.0, 1.0, 0.27),
    ("Stair_A45_Right", 25.0, -69.0, 6, 4.0, 1.0, 0.27),
    ("Stair_A23_South", -20.0, -89.0, 4, 4.0, 1.0, 0.25),
    ("Stair_A45_South", 25.0, -89.0, 4, 4.0, 1.0, 0.25),
]

GROUND_PATHS = [
    ("Walk_A_Front", [(-35.0, -92.0, 0.0), (45.0, -92.0, 0.0)]),
    ("Walk_A_Mid_Front", [(-35.0, -84.0, 0.0), (45.0, -84.0, 0.0)]),
    ("Walk_A_Mid_Back", [(-35.0, -78.0, 0.0), (45.0, -78.0, 0.0)]),
    ("Walk_A_Back", [(-35.0, -66.0, 0.0), (45.0, -66.0, 0.0)]),
    ("Walk_A23_Left", [(-33.5, -90.0, 0.0), (-33.5, -68.0, 0.0)]),
    ("Walk_A23_Inner_Left", [(-8.0, -92.0, 0.0), (-8.0, -66.0, 0.0)]),
    ("Walk_A45_Inner_Right", [(18.0, -92.0, 0.0), (18.0, -66.0, 0.0)]),
    ("Walk_A45_Right", [(43.0, -90.0, 0.0), (43.0, -68.0, 0.0)]),
    ("Walk_Main_Path", [(5.0, -93.0, 0.0), (5.0, -78.0, 0.0)]),
    ("Walk_Front_To_A23", [(-20.0, -92.0, 0.0), (-20.0, -69.0, 0.0)]),
    ("Walk_Front_To_A45", [(25.0, -92.0, 0.0), (25.0, -69.0, 0.0)]),
    ("Walk_Back_Left_Connector", [(-33.5, -66.0, 0.0), (-20.0, -66.0, 0.0), (-20.0, -69.0, 0.0)]),
    ("Walk_Back_Right_Connector", [(43.0, -66.0, 0.0), (25.0, -66.0, 0.0), (25.0, -69.0, 0.0)]),
    ("Walk_A1_Front_Plaza", [(5.0, -92.0, 0.0), (5.0, -78.0, 0.0), (5.0, -69.0, 0.0)]),
    ("Road_East_Spine", [(30.0, -5.0, 0.0), (62.0, -5.0, 0.0), (90.0, -5.0, 0.0), (118.0, -5.0, 0.0)]),
    ("Road_East_North", [(90.0, -5.0, 0.0), (90.0, 16.0, 0.8), (90.0, 30.0, 2.5), (120.0, 30.0, 2.5)]),
    ("Road_East_South", [(90.0, -5.0, 0.0), (96.0, -20.0, 0.0), (96.0, -36.0, 0.0), (128.0, -36.0, 5.0)]),
    ("Road_West_Spine", [(-35.0, 10.0, 0.0), (-62.0, 10.0, 0.0), (-90.0, 10.0, 2.5), (-90.0, 38.0, 5.0)]),
    ("Road_West_South", [(-55.0, -5.0, 0.0), (-82.0, -10.0, 0.0), (-102.0, -10.0, 0.0), (-102.0, -22.0, 0.0)]),
    ("Walk_HI_Plaza", [(82.0, 24.0, 2.5), (104.0, 24.0, 2.5), (126.0, 24.0, 2.5)]),
    ("Walk_HK_Ramp", [(92.0, 18.0, 2.5), (94.0, 2.0, 6.0), (96.0, -18.0, 10.5)]),
    ("Walk_JTerrace", [(-90.0, 26.0, 5.0), (-90.0, 40.0, 5.0), (-84.0, 40.0, 5.0)]),
    ("Walk_MK_Upper", [(128.0, -28.0, 5.0), (120.0, -28.0, 5.0), (112.0, -28.0, 5.0), (102.0, -28.0, 5.0)]),
    ("Road_Tower_Axis", [(118.0, -5.0, 0.0), (146.0, -5.0, 1.2), (166.0, 0.0, 2.5), (196.0, 0.0, 2.5)]),
    ("Walk_Tower_Podium", [(160.0, 10.0, 2.5), (170.0, 10.0, 2.5), (190.0, 10.0, 2.5), (200.0, 10.0, 2.5)]),
]


def ensure_collection(name):
    old = bpy.data.collections.get(name)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def ensure_red_material():
    name = "NavGraph_Red"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.05, 0.05, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_box(name, center, size, mat, collection):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = center
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(mesh)
    bm.free()
    mesh.transform(
        mathutils_matrix_scale(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)
    )
    assign_material(obj, mat)
    return obj


def mathutils_matrix_scale(sx, sy, sz):
    import mathutils
    return mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))


def get_bounds(obj):
    wc = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [v.x for v in wc]
    ys = [v.y for v in wc]
    zs = [v.z for v in wc]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


class GraphBuilder:
    def __init__(self):
        self.nodes = []
        self.node_keys = {}
        self.adjacency = {}
        self.edge_keys = set()
        self.edges = []

    def _key(self, pos):
        return tuple(round(c / NODE_TOLERANCE) for c in pos)

    def add_node(self, pos, kind, label):
        key = self._key(pos)
        existing = self.node_keys.get(key)
        if existing is not None:
            node = self.nodes[existing]
            if label not in node["labels"]:
                node["labels"].append(label)
            if kind not in node["kinds"]:
                node["kinds"].append(kind)
            return existing

        node_id = len(self.nodes)
        self.node_keys[key] = node_id
        self.nodes.append(
            {
                "id": node_id,
                "x": round(pos[0], 4),
                "y": round(pos[1], 4),
                "z": round(pos[2], 4),
                "kinds": [kind],
                "labels": [label],
            }
        )
        self.adjacency[node_id] = set()
        return node_id

    def add_edge(self, a, b, kind):
        if a == b:
            return
        key = (min(a, b), max(a, b))
        if key in self.edge_keys:
            return
        self.edge_keys.add(key)
        self.adjacency[a].add(b)
        self.adjacency[b].add(a)
        pa = self.nodes[a]
        pb = self.nodes[b]
        self.edges.append(
            {
                "a": a,
                "b": b,
                "kind": kind,
                "length": round(
                    math.dist((pa["x"], pa["y"], pa["z"]), (pb["x"], pb["y"], pb["z"])), 4
                ),
            }
        )

    def add_polyline(self, name, points, kind):
        node_ids = []
        for i, point in enumerate(points):
            node_ids.append(self.add_node(point, kind, f"{name}:{i}"))
        for i in range(len(node_ids) - 1):
            self.add_edge(node_ids[i], node_ids[i + 1], kind)
        return node_ids

    def attach(self, a_pos, b_pos, kind, a_label, b_label):
        a = self.add_node(a_pos, kind, a_label)
        b = self.add_node(b_pos, kind, b_label)
        self.add_edge(a, b, kind)

    def nearest_node(self, pos, z_tolerance=None, max_distance=None, exclude=None):
        best_id = None
        best_dist = None
        exclude = exclude or set()
        for node in self.nodes:
            if node["id"] in exclude:
                continue
            if z_tolerance is not None and abs(node["z"] - pos[2]) > z_tolerance:
                continue
            dist = math.dist((node["x"], node["y"], node["z"]), pos)
            if max_distance is not None and dist > max_distance:
                continue
            if best_dist is None or dist < best_dist:
                best_id = node["id"]
                best_dist = dist
        return best_id, best_dist


def add_corridor_graph(graph, name, bounds, corridor_side, num_floors):
    x_min, x_max, y_min, y_max, z_min, z_max = bounds
    width_x = x_max - x_min
    depth_y = y_max - y_min
    floor_h = (z_max - z_min) / num_floors
    profile = get_block_profile(name)
    corr_width = profile["corridor_width"]
    bay_spacing = profile["bay_spacing"]
    col_size = 0.4
    is_x_long = width_x >= depth_y

    if is_x_long:
        num_cols = max(3, int(width_x / bay_spacing) + 1)
        dx = (width_x - col_size) / (num_cols - 1)
        stair_index = num_cols // 2
        stair_x_min = x_min + col_size / 2 + stair_index * dx
        stair_x_max = x_min + col_size / 2 + (stair_index + 1) * dx
        stair_cx = x_min + col_size / 2 + (stair_index + 0.5) * dx
        corr_y = y_min + corr_width / 2 if corridor_side == "S" else y_max - corr_width / 2
        stair_entry_y = y_min + 0.75 if corridor_side == "S" else y_max - 0.75
        left_end = (x_min, corr_y)
        left_gap = (stair_x_min, corr_y)
        center_gap = (stair_cx, corr_y)
        right_gap = (stair_x_max, corr_y)
        right_end = (x_max, corr_y)

        for f in range(num_floors + 1):
            z = z_min + f * floor_h
            if f < num_floors:
                graph.add_polyline(
                    f"{name}_Corridor_F{f}",
                    [
                        (left_end[0], left_end[1], z),
                        (left_gap[0], left_gap[1], z),
                        (center_gap[0], center_gap[1], z),
                        (right_gap[0], right_gap[1], z),
                        (right_end[0], right_end[1], z),
                    ],
                    "corridor",
                )
                graph.attach(
                    (stair_cx, corr_y, z),
                    (stair_cx, stair_entry_y, z),
                    "stair_access",
                    f"{name}_StairCorridor_F{f}",
                    f"{name}_StairLanding_F{f}",
                )
            else:
                graph.add_polyline(
                    f"{name}_RoofLine_F{f}",
                    [
                        (left_end[0], left_end[1], z),
                        (center_gap[0], center_gap[1], z),
                        (right_end[0], right_end[1], z),
                    ],
                    "roof_access",
                )
    else:
        num_cols = max(3, int(depth_y / bay_spacing) + 1)
        dy = (depth_y - col_size) / (num_cols - 1)
        stair_index = num_cols // 2
        stair_y_min = y_min + col_size / 2 + stair_index * dy
        stair_y_max = y_min + col_size / 2 + (stair_index + 1) * dy
        stair_cy = y_min + col_size / 2 + (stair_index + 0.5) * dy
        corr_x = x_max - corr_width / 2 if corridor_side == "E" else x_min + corr_width / 2
        stair_entry_x = x_max - 0.75 if corridor_side == "E" else x_min + 0.75
        low_end = (corr_x, y_min)
        low_gap = (corr_x, stair_y_min)
        center_gap = (corr_x, stair_cy)
        high_gap = (corr_x, stair_y_max)
        high_end = (corr_x, y_max)

        for f in range(num_floors + 1):
            z = z_min + f * floor_h
            if f < num_floors:
                graph.add_polyline(
                    f"{name}_Corridor_F{f}",
                    [
                        (low_end[0], low_end[1], z),
                        (low_gap[0], low_gap[1], z),
                        (center_gap[0], center_gap[1], z),
                        (high_gap[0], high_gap[1], z),
                        (high_end[0], high_end[1], z),
                    ],
                    "corridor",
                )
                graph.attach(
                    (corr_x, stair_cy, z),
                    (stair_entry_x, stair_cy, z),
                    "stair_access",
                    f"{name}_StairCorridor_F{f}",
                    f"{name}_StairLanding_F{f}",
                )
            else:
                graph.add_polyline(
                    f"{name}_RoofLine_F{f}",
                    [
                        (low_end[0], low_end[1], z),
                        (center_gap[0], center_gap[1], z),
                        (high_end[0], high_end[1], z),
                    ],
                    "roof_access",
                )


def add_internal_stair_graph(graph, name, bounds, corridor_side, num_floors):
    x_min, x_max, y_min, y_max, z_min, z_max = bounds
    width_x = x_max - x_min
    depth_y = y_max - y_min
    floor_h = (z_max - z_min) / num_floors
    profile = get_block_profile(name)
    bay_spacing = profile["bay_spacing"]
    col_size = 0.4
    is_x_long = width_x >= depth_y

    if is_x_long:
        num_cols = max(3, int(width_x / bay_spacing) + 1)
        dx = (width_x - col_size) / (num_cols - 1)
        stair_index = num_cols // 2
        cx = x_min + col_size / 2 + (stair_index + 0.5) * dx
        cy = (y_min + y_max) / 2
        width = dx - 0.5
        depth = depth_y
    else:
        num_cols = max(3, int(depth_y / bay_spacing) + 1)
        dy = (depth_y - col_size) / (num_cols - 1)
        stair_index = num_cols // 2
        cx = (x_min + x_max) / 2
        cy = y_min + col_size / 2 + (stair_index + 0.5) * dy
        width = width_x
        depth = dy - 0.5

    flight_w = width / 2.2
    run_d = depth - 1.5
    num_steps = 10
    step_d = run_d / num_steps
    step_h = (floor_h / 2.0) / num_steps
    num_levels = int(round((z_max - z_min) / floor_h))
    main_landing_y = cy - depth / 2.0 + 0.75
    mid_landing_y = cy + depth / 2.0 - 0.75
    previous_top_id = None

    for f in range(num_levels):
        zf = z_min + f * floor_h
        chain = []
        chain.append((cx, main_landing_y, zf))
        start_y = cy - depth / 2.0 + 1.5 + step_d / 2.0
        for s in range(num_steps):
            chain.append((cx - flight_w / 2.0, start_y + s * step_d, zf + (s + 1) * step_h))
        chain.append((cx, mid_landing_y, zf + floor_h / 2.0))
        start_y = cy + depth / 2.0 - 1.5 - step_d / 2.0
        for s in range(num_steps):
            chain.append((cx + flight_w / 2.0, start_y - s * step_d, zf + floor_h / 2.0 + (s + 1) * step_h))

        ids = graph.add_polyline(f"{name}_StairRun_F{f}", chain, "stair_step")
        main_id = graph.add_node(chain[0], "stair_landing", f"{name}_MainLanding_F{f}")
        top_id = graph.add_node(chain[-1], "stair_step", f"{name}_TopStep_F{f}")
        if previous_top_id is not None:
            graph.add_edge(previous_top_id, main_id, "stair_landing")
        previous_top_id = top_id


def add_a1_front_stair_graph(graph, name, cx, cy, n_steps, step_w, step_d, step_h):
    points = [(cx, cy - step_d * n_steps, GROUND_Z)]
    for i in range(n_steps):
        points.append((cx, cy - step_d * (i + 0.5), step_h * (i + 1)))
    points.append((cx, cy, step_h * n_steps))
    graph.add_polyline(name, points, "entry_stair")


def add_outdoor_stair_graph(graph, name, cx, cy, z_bottom, z_top, facing, width):
    h = z_top - z_bottom
    if h <= 0:
        return
    n_steps = max(6, int(h / 0.18))
    step_h = h / n_steps
    run = h * 1.8
    step_r = run / n_steps
    dx_step = 0.0
    dy_step = 0.0
    if facing == "N":
        dy_step = step_r
    elif facing == "S":
        dy_step = -step_r
    elif facing == "E":
        dx_step = step_r
    elif facing == "W":
        dx_step = -step_r

    points = [(cx, cy, z_bottom)]
    for s in range(n_steps):
        points.append(
            (
                cx + dx_step * (s + 0.5),
                cy + dy_step * (s + 0.5),
                z_bottom + step_h * (s + 1),
            )
        )
    points.append((cx + dx_step * n_steps, cy + dy_step * n_steps, z_top))
    graph.add_polyline(name, points, "outdoor_stair")


def add_skybridge_graph(graph, name, pt1, pt2, z):
    x1, y1 = pt1
    x2, y2 = pt2
    mid = ((x1 + x2) / 2.0, (y1 + y2) / 2.0, z)
    graph.add_polyline(name, [(x1, y1, z), mid, (x2, y2, z)], "skybridge")


def add_a1_internal_graph(graph):
    a1 = bpy.data.objects.get("Khoi_A.1_Trung_Tam_Hanh_Chinh")
    if not a1:
        return
    x_min, x_max, y_min, y_max, z_min, z_max = get_bounds(a1)
    num_floors = 8
    floor_h = (z_max - z_min) / num_floors
    cx = (x_min + x_max) / 2.0
    corridor_y = y_min + 1.1
    left_x = x_min
    right_x = x_max

    for f in range(num_floors):
        z = z_min + f * floor_h
        graph.add_polyline(
            f"A1_Tower_Corridor_F{f}",
            [(left_x, corridor_y, z), (cx, corridor_y, z), (right_x, corridor_y, z)],
            "corridor",
        )

    for s in range(3):
        sw = 12.0 - s * 2.0
        graph.add_polyline(
            f"A1_Tower_FrontStep_{s}",
            [(cx, y_min - 1.2 - s * 1.2, max(z_min - s * 0.15, 0.0)), (cx, y_min - 0.6 - s * 0.6, max(z_min - s * 0.15, 0.0))],
            "entry_stair",
        )


def subdivide_polyline(points, max_segment_length):
    if len(points) <= 1:
        return list(points)

    dense = [points[0]]
    for start, end in zip(points, points[1:]):
        dist = math.dist(start, end)
        steps = max(1, int(math.ceil(dist / max_segment_length)))
        for step in range(1, steps + 1):
            t = step / steps
            dense.append(
                (
                    start[0] + (end[0] - start[0]) * t,
                    start[1] + (end[1] - start[1]) * t,
                    start[2] + (end[2] - start[2]) * t,
                )
            )
    return dense


def add_ground_paths(graph):
    for name, points in GROUND_PATHS:
        graph.add_polyline(name, subdivide_polyline(points, GROUND_PATH_SEGMENT_MAX), "ground_path")


def ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(a, b, c, d):
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


def point_in_rect(p, rect):
    x_min, x_max, y_min, y_max = rect
    return x_min < p[0] < x_max and y_min < p[1] < y_max


def segment_intersects_rect(p1, p2, rect):
    x_min, x_max, y_min, y_max = rect
    corners = [
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    ]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    if point_in_rect(p1, rect) or point_in_rect(p2, rect):
        return True
    for a, b in edges:
        if segments_intersect(p1, p2, a, b):
            return True
    return False


def connect_access_points(graph, block_bounds):
    elevated_points = []
    ground_points = []

    for name, pt1, pt2, z in SKYBRIDGES:
        elevated_points.append(((pt1[0], pt1[1], z), f"{name}_P1"))
        elevated_points.append(((pt2[0], pt2[1], z), f"{name}_P2"))

    for name, cx, cy, z_bottom, z_top, facing, width in OUTDOOR_STAIRS:
        elevated_points.append(((cx, cy, z_bottom), f"{name}_Bottom"))
        ground_points.append(((cx, cy, z_bottom), f"{name}_Bottom"))
        h = z_top - z_bottom
        n_steps = max(6, int(h / 0.18))
        run = h * 1.8
        step_r = run / n_steps
        dx_step = 0.0
        dy_step = 0.0
        if facing == "N":
            dy_step = step_r
        elif facing == "S":
            dy_step = -step_r
        elif facing == "E":
            dx_step = step_r
        elif facing == "W":
            dx_step = -step_r
        elevated_points.append(((cx + dx_step * n_steps, cy + dy_step * n_steps, z_top), f"{name}_Top"))

    obstacles = []
    for bounds in block_bounds.values():
        x_min, x_max, y_min, y_max, _, _ = bounds
        obstacles.append((x_min + 0.5, x_max - 0.5, y_min + 0.5, y_max - 0.5))

    for pos, label in elevated_points:
        node_id = graph.add_node(pos, "access", label)
        nearest_id, nearest_dist = graph.nearest_node(
            pos,
            z_tolerance=0.6,
            max_distance=12.0,
            exclude={node_id},
        )
        if nearest_id is not None and nearest_dist and nearest_dist > 0.01:
            graph.add_edge(node_id, nearest_id, "access")

    ground_ids = []
    for pos, label in ground_points:
        ground_ids.append(graph.add_node(pos, "ground_access", label))

    for node_id in ground_ids:
        node = graph.nodes[node_id]
        candidate_ids = []
        for other in graph.nodes:
            if other["id"] == node_id or abs(other["z"] - node["z"]) > 0.75:
                continue
            dist = math.dist((node["x"], node["y"], 0.0), (other["x"], other["y"], 0.0))
            if dist <= 40.0:
                candidate_ids.append((dist, other["id"]))
        candidate_ids.sort(key=lambda item: item[0])
        added = 0
        for dist, other_id in candidate_ids:
            if added >= 3:
                break
            other = graph.nodes[other_id]
            p1 = (node["x"], node["y"])
            p2 = (other["x"], other["y"])
            blocked = False
            for rect in obstacles:
                if segment_intersects_rect(p1, p2, rect):
                    blocked = True
                    break
            if blocked:
                continue
            graph.add_edge(node_id, other_id, "ground_access")
            added += 1


def compute_connected_components(graph):
    seen = set()
    components = []
    for node in graph.nodes:
        node_id = node["id"]
        if node_id in seen:
            continue
        stack = [node_id]
        seen.add(node_id)
        comp = []
        while stack:
            current = stack.pop()
            comp.append(current)
            for neighbor_id in graph.adjacency[current]:
                if neighbor_id not in seen:
                    seen.add(neighbor_id)
                    stack.append(neighbor_id)
        components.append(comp)
    return components


def build_obstacle_rects(block_bounds):
    obstacles = []
    for bounds in block_bounds.values():
        x_min, x_max, y_min, y_max, _, _ = bounds
        obstacles.append((x_min + 0.5, x_max - 0.5, y_min + 0.5, y_max - 0.5))
    return obstacles


def connect_ground_path_network(graph, block_bounds):
    obstacles = build_obstacle_rects(block_bounds)
    ground_node_ids = [
        node["id"]
        for node in graph.nodes
        if "ground_path" in node["kinds"] and abs(node["z"] - GROUND_Z) <= 0.25
    ]

    for node_id in ground_node_ids:
        node = graph.nodes[node_id]
        candidates = []
        for other_id in ground_node_ids:
            if other_id == node_id or other_id in graph.adjacency[node_id]:
                continue
            other = graph.nodes[other_id]
            if abs(other["z"] - node["z"]) > 0.2:
                continue
            dist = math.dist((node["x"], node["y"]), (other["x"], other["y"]))
            if dist <= 0.05 or dist > GROUND_LINK_RADIUS:
                continue
            p1 = (node["x"], node["y"])
            p2 = (other["x"], other["y"])
            blocked = False
            for rect in obstacles:
                if segment_intersects_rect(p1, p2, rect):
                    blocked = True
                    break
            if blocked:
                continue
            candidates.append((dist, other_id))

        candidates.sort(key=lambda item: item[0])
        added = 0
        for _dist, other_id in candidates:
            if added >= GROUND_LINKS_PER_NODE:
                break
            if other_id in graph.adjacency[node_id]:
                continue
            graph.add_edge(node_id, other_id, "ground_path_link")
            added += 1


def is_connector_kind(node):
    connector_kinds = {
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
    return any(kind in connector_kinds for kind in node["kinds"])


def can_stitch_pair(node_a, node_b, obstacles):
    pos_a = (node_a["x"], node_a["y"], node_a["z"])
    pos_b = (node_b["x"], node_b["y"], node_b["z"])
    z_diff = abs(pos_a[2] - pos_b[2])
    planar_dist = math.dist((pos_a[0], pos_a[1]), (pos_b[0], pos_b[1]))
    dist = math.dist(pos_a, pos_b)

    local_kinds = {"corridor", "stair_access", "stair_landing", "stair_step", "access", "outdoor_stair"}
    node_a_local = any(kind in local_kinds for kind in node_a["kinds"])
    node_b_local = any(kind in local_kinds for kind in node_b["kinds"])
    if node_a_local and node_b_local and z_diff <= 0.75 and dist <= 3.6:
        return True

    if not (is_connector_kind(node_a) and is_connector_kind(node_b)):
        return False
    if z_diff > 1.5 or planar_dist > 8.5 or dist > 9.0:
        return False

    p1 = (pos_a[0], pos_a[1])
    p2 = (pos_b[0], pos_b[1])
    for rect in obstacles:
        if segment_intersects_rect(p1, p2, rect):
            return False
    return True


def stitch_graph_components(graph, block_bounds):
    obstacles = build_obstacle_rects(block_bounds)
    total_added = 0

    while True:
        components = sorted(compute_connected_components(graph), key=len, reverse=True)
        if len(components) <= 1:
            break

        comp_index_by_node = {}
        for comp_index, comp in enumerate(components):
            for node_id in comp:
                comp_index_by_node[node_id] = comp_index

        best_pair = None
        best_dist = None
        for node in graph.nodes:
            node_id = node["id"]
            if not is_connector_kind(node):
                continue
            comp_a = comp_index_by_node[node_id]
            for other in graph.nodes:
                other_id = other["id"]
                if comp_index_by_node[other_id] == comp_a or not is_connector_kind(other):
                    continue
                if not can_stitch_pair(node, other, obstacles):
                    continue
                dist = math.dist((node["x"], node["y"], node["z"]), (other["x"], other["y"], other["z"]))
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_pair = (node_id, other_id)

        if best_pair is None:
            break

        graph.add_edge(best_pair[0], best_pair[1], "component_stitch")
        total_added += 1

    return total_added


def export_graph_text(graph):
    data = {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "nodes": [],
        "edges": graph.edges,
    }
    lines = []
    for node in graph.nodes:
        neigh = sorted(graph.adjacency[node["id"]])
        data["nodes"].append(
            {
                "id": node["id"],
                "position": [node["x"], node["y"], node["z"]],
                "kinds": node["kinds"],
                "labels": node["labels"],
                "neighbors": neigh,
            }
        )
        lines.append(
            "node {id}: pos=({x:.3f}, {y:.3f}, {z:.3f}) kinds={kinds} neighbors={neighbors}".format(
                id=node["id"],
                x=node["x"],
                y=node["y"],
                z=node["z"],
                kinds=",".join(node["kinds"]),
                neighbors=neigh,
            )
        )

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def build_visual_overlay(graph):
    collection = ensure_collection(COLLECTION_NAME)
    mat = ensure_red_material()

    node_size = 0.22
    edge_thickness = 0.08

    for node in graph.nodes:
        add_box(
            f"NavNode_{node['id']}",
            (node["x"], node["y"], node["z"]),
            (node_size, node_size, node_size),
            mat,
            collection,
        )

    for idx, edge in enumerate(graph.edges):
        a = graph.nodes[edge["a"]]
        b = graph.nodes[edge["b"]]
        pa = Vector((a["x"], a["y"], a["z"]))
        pb = Vector((b["x"], b["y"], b["z"]))
        direction = pb - pa
        length = direction.length
        if length == 0:
            continue
        mid = (pa + pb) / 2.0
        mesh = bpy.data.meshes.new(f"NavEdge_{idx}")
        obj = bpy.data.objects.new(f"NavEdge_{idx}", mesh)
        collection.objects.link(obj)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        bm.to_mesh(mesh)
        bm.free()
        mesh.transform(mathutils_matrix_scale(length / 2.0, edge_thickness / 2.0, edge_thickness / 2.0))
        obj.location = mid
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((1.0, 0.0, 0.0)).rotation_difference(direction.normalized())
        assign_material(obj, mat)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in collection.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(collection.objects), None)
    if hasattr(bpy.ops.wm, "obj_export"):
        bpy.ops.wm.obj_export(filepath=OBJ_PATH, export_selected_objects=True, export_materials=True)
    else:
        bpy.ops.export_scene.obj(filepath=OBJ_PATH, use_selection=True, use_materials=True)


def main():
    graph = GraphBuilder()

    block_bounds = {}
    for name, side, floors, floor_h in BLOCK_SPECS:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"[WARN] Missing block: {name}")
            continue
        x_min, x_max, y_min, y_max, z_min, _ = get_bounds(obj)
        bounds = (x_min, x_max, y_min, y_max, z_min, z_min + floors * floor_h)
        block_bounds[name] = bounds
        add_corridor_graph(graph, name, bounds, side, floors)
        add_internal_stair_graph(graph, name, bounds, side, floors)

    for name, x_min, x_max, y_min, y_max, z_min, side, floors, floor_h in EXTRA_COMPLEXES:
        bounds = (x_min, x_max, y_min, y_max, z_min, z_min + floors * floor_h)
        block_bounds[name] = bounds
        add_corridor_graph(graph, name, bounds, side, floors)
        add_internal_stair_graph(graph, name, bounds, side, floors)

    add_a1_internal_graph(graph)

    for name, pt1, pt2, z in SKYBRIDGES:
        add_skybridge_graph(graph, name, pt1, pt2, z)

    for name, cx, cy, z_bottom, z_top, facing, width in OUTDOOR_STAIRS:
        add_outdoor_stair_graph(graph, name, cx, cy, z_bottom, z_top, facing, width)

    for name, cx, cy, n_steps, step_w, step_d, step_h in A1_FRONT_STAIRS:
        add_a1_front_stair_graph(graph, name, cx, cy, n_steps, step_w, step_d, step_h)

    add_ground_paths(graph)
    connect_ground_path_network(graph, block_bounds)
    connect_access_points(graph, block_bounds)
    before_components = len(compute_connected_components(graph))
    stitched_edges = stitch_graph_components(graph, block_bounds)
    after_components = len(compute_connected_components(graph))
    export_graph_text(graph)
    build_visual_overlay(graph)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    print(f"[OK] nodes={len(graph.nodes)} edges={len(graph.edges)}")
    print(f"[OK] stitched_edges={stitched_edges} components {before_components} -> {after_components}")
    print(f"[OK] wrote {JSON_PATH}")
    print(f"[OK] wrote {TXT_PATH}")
    print(f"[OK] wrote {OBJ_PATH}")
    print(f"[OK] wrote {BLEND_PATH}")


if __name__ == "__main__":
    main()
