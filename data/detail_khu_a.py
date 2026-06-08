"""
Script chi tiết hóa Khu A - HCMUTE
Chạy: blender --background data/Untitled.blend --python data/detail_khu_a.py
"""
import bpy
import bmesh
from mathutils import Vector

# ─── UTILS ───────────────────────────────────────────────────────────────────

def new_mesh_obj(name, collection=None):
    mesh = bpy.data.meshes.new(name)
    obj  = bpy.data.objects.new(name, mesh)
    col  = collection or bpy.context.scene.collection
    col.objects.link(obj)
    return obj, mesh

def make_material(name, r, g, b, a=1.0, metallic=0.0, roughness=0.5):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (r, g, b, a)
    bsdf.inputs["Metallic"].default_value   = metallic
    bsdf.inputs["Roughness"].default_value  = roughness
    return mat

def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def box_bmesh(bm, cx, cy, cz, sx, sy, sz):
    """Add a box into bmesh at center (cx,cy,cz) with half-sizes sx,sy,sz."""
    bmesh.ops.create_cube(bm, size=1.0)
    # bmesh.ops.create_cube places at origin, we translate afterwards – instead
    # use transform matrix
    # Actually simpler: use separate objects per box
    pass

def add_box(name, cx, cy, cz, sx, sy, sz, mat=None):
    """Create a box object centered at (cx,cy,cz) with full dimensions sx,sy,sz."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        assign_mat(obj, mat)
    return obj

# ─── MATERIALS ───────────────────────────────────────────────────────────────

mat_glass     = make_material("Mat_Glass",     0.3, 0.6, 0.8, metallic=0.1, roughness=0.05)
mat_concrete  = make_material("Mat_Concrete",  0.75, 0.75, 0.72, roughness=0.9)
mat_wall      = make_material("Mat_Wall",      0.92, 0.91, 0.88, roughness=0.8)
mat_basement  = make_material("Mat_Basement",  0.4, 0.4, 0.38, roughness=0.95)
mat_road      = make_material("Mat_Road",      0.25, 0.25, 0.25, roughness=1.0)
mat_sidewalk  = make_material("Mat_Sidewalk",  0.82, 0.80, 0.75, roughness=0.9)
mat_window    = make_material("Mat_Window",    0.5, 0.75, 0.9,  metallic=0.0, roughness=0.05)
mat_railing   = make_material("Mat_Railing",   0.6, 0.6, 0.6,  metallic=0.5, roughness=0.3)
mat_stair     = make_material("Mat_Stair",     0.65, 0.63, 0.60, roughness=0.85)
mat_stripe    = make_material("Mat_Stripe",    0.95, 0.95, 0.95, roughness=0.8)

# ─── APPLY MATERIALS TO EXISTING BLOCKS ──────────────────────────────────────

def apply_existing_materials():
    mapping = {
        "Khoi_A.1_Trung_Tam_Hanh_Chinh": mat_glass,
        "Khoi_A.2_Phong_Hoc":            mat_wall,
        "Khoi_A.3_Giang_Duong":          mat_wall,
        "Khoi_A.4_Phong_Hoc":            mat_wall,
        "Khoi_A.5_Giang_Duong":          mat_wall,
        "Khoi_A_Day_Phai":               mat_wall,
        "Khoi_A_Day_Trai":               mat_wall,
        "Road_Main_Entrance":            mat_road,
        "Road_Ring_Left":                mat_road,
        "Road_Ring_Right":               mat_road,
        "Road_Cross_North":              mat_road,
        "Hoi_Truong_Lon":                mat_concrete,
        "Khoi_Thu_Vien":                 mat_wall,
    }
    for name, mat in mapping.items():
        obj = bpy.data.objects.get(name)
        if obj:
            assign_mat(obj, mat)

apply_existing_materials()

# ─── 1. BASEMENT dưới Khoi_A.1 ───────────────────────────────────────────────
# A1: X[-7.5,17.5] Y[-81,-69] → center (5,-75), size 25x12x44
# Hầm: rộng 25m, sâu 12m, cao 4m, chìm xuống -4m..0

add_box("Basement_A1", 5, -75, -2, 25, 12, 4, mat_basement)

# Cửa vào hầm – tường dày 0.5m, cao 2.5m, rộng 4m ở mặt trước (Y=-69)
add_box("Basement_Door_Frame", 5, -69.25, -0.5, 4.2, 0.3, 3, mat_concrete)
add_box("Basement_Ramp_Left",  3, -68,    -2,   0.5, 6,   0.2, mat_concrete)
add_box("Basement_Ramp_Right", 7, -68,    -2,   0.5, 6,   0.2, mat_concrete)
# Dốc xuống hầm (đơn giản = mặt phẳng nghiêng → dùng box mỏng)
add_box("Basement_Ramp_Floor", 5, -65.5, -1.0, 4, 7, 0.15, mat_concrete)

# ─── 2. CẦU THANG CHÍNH trước A1 ─────────────────────────────────────────────
# Trước A1: mặt tiền Y=-69, trung tâm X=5
# Cầu thang 6 bậc, mỗi bậc rộng 16m, sâu 1.5m, cao 0.2m

STAIR_CX   = 5.0
STAIR_Y0   = -69.0   # mép ngoài tòa nhà
N_STEPS    = 6
STEP_W     = 16.0
STEP_D     = 1.5
STEP_H     = 0.2

for i in range(N_STEPS):
    h   = STEP_H * (i + 1)
    cy  = STAIR_Y0 - STEP_D * (i + 0.5)
    cz  = h / 2.0
    add_box(f"Stair_Main_{i}", STAIR_CX, cy, cz, STEP_W, STEP_D, h, mat_stair)

# Tay vịn trái/phải cầu thang chính
for side, sx in [("L", STAIR_CX - STEP_W/2 - 0.15),
                 ("R", STAIR_CX + STEP_W/2 + 0.15)]:
    railing_cy = STAIR_Y0 - (N_STEPS * STEP_D) / 2
    add_box(f"Railing_Main_{side}", sx, railing_cy,
            N_STEPS * STEP_H / 2 + 0.5,
            0.12, N_STEPS * STEP_D, 1.0, mat_railing)

# ─── 3. CẦU THANG BÊN A2-A3 (trái) ──────────────────────────────────────────
# A2: X[-32.5,-7.5] Y[-89,-81], A3: X[-32.5,-7.5] Y[-81,-69]
# Cầu thang nối A2→A3 đặt ở X=-7.5 (mép phải), Y=-81 (biên chung)
# 4 bậc lên tầng 2 (4m)

def add_stair_set(prefix, cx, cy, n=8, sw=4.0, sd=0.8, sh=0.2, mat=None):
    mat = mat or mat_stair
    for i in range(n):
        h  = sh * (i + 1)
        oy = cy - sd * (i + 0.5)
        cz = h / 2.0
        add_box(f"{prefix}_{i}", cx, oy, cz, sw, sd, h, mat)
    # Tay vịn
    total_d = n * sd
    total_h = n * sh
    for side, dx in [("L", -sw/2 - 0.1), ("R", sw/2 + 0.1)]:
        add_box(f"{prefix}_Rail_{side}",
                cx + dx, cy - total_d/2,
                total_h/2 + 0.5,
                0.1, total_d, 1.0, mat_railing)

# A2-A3 phía trái, cầu thang ở đầu bắc (Y=-69 side)
add_stair_set("Stair_A23_Left",  cx=-20, cy=-69, n=6, sw=4, sd=1.0, sh=0.27)
# A4-A5 phía phải
add_stair_set("Stair_A45_Right", cx=25,  cy=-69, n=6, sw=4, sd=1.0, sh=0.27)

# Cầu thang phía nam A2-A3 (Y=-89 side)
add_stair_set("Stair_A23_South", cx=-20, cy=-89, n=4, sw=4, sd=1.0, sh=0.25)
add_stair_set("Stair_A45_South", cx=25,  cy=-89, n=4, sw=4, sd=1.0, sh=0.25)

# ─── 4. KHUNG CỬA SỔ FACADE ──────────────────────────────────────────────────
# Mỗi khối A2/A3/A4/A5 cao 16m → 4 tầng, mỗi tầng 4m
# Cửa sổ: rộng 2m, cao 1.6m, sâu 0.1m (nổi trên mặt)

WIN_W  = 2.0
WIN_H  = 1.6
WIN_D  = 0.08   # độ nổi ra ngoài
FLOOR_H = 4.0
SILL_Z  = 1.0   # chiều cao từ sàn tầng đến mép dưới cửa

def add_windows_on_face(prefix, face_axis, face_val, cz_base,
                        row_min, row_max, n_floors, n_per_floor, mat_w):
    """
    face_axis: 'x' or 'y'
    face_val : coordinate of the face
    cz_base  : Z of ground floor bottom
    row_min, row_max: range along the OTHER horizontal axis
    """
    span  = row_max - row_min
    gap   = span / n_per_floor
    for floor in range(n_floors):
        floor_z = cz_base + floor * FLOOR_H
        win_cz  = floor_z + SILL_Z + WIN_H / 2
        for col in range(n_per_floor):
            rc = row_min + gap * (col + 0.5)
            name = f"{prefix}_F{floor}_W{col}"
            if face_axis == 'y':
                # face parallel to X axis: windows along X
                offset_y = face_val + (WIN_D/2 if face_val > 0 else -WIN_D/2)
                add_box(name, rc, offset_y, win_cz, WIN_W, WIN_D, WIN_H, mat_w)
            else:
                offset_x = face_val + (WIN_D/2 if face_val > 0 else -WIN_D/2)
                add_box(name, offset_x, rc, win_cz, WIN_D, WIN_W, WIN_H, mat_w)

# A2: X[-32.5,-7.5] Y[-89,-81] Z[0,16]
add_windows_on_face("Win_A2_Front", 'y', -89.0+WIN_D/2, 0, -32.5, -7.5, 4, 8, mat_window)
add_windows_on_face("Win_A2_Back",  'y', -81.0-WIN_D/2, 0, -32.5, -7.5, 4, 8, mat_window)

# A3: X[-32.5,-7.5] Y[-81,-69] Z[0,16]
add_windows_on_face("Win_A3_Front", 'y', -81.0+WIN_D/2, 0, -32.5, -7.5, 4, 8, mat_window)
add_windows_on_face("Win_A3_Back",  'y', -69.0-WIN_D/2, 0, -32.5, -7.5, 4, 8, mat_window)

# A4: X[10,40] Y[-89,-81] Z[0,16]
add_windows_on_face("Win_A4_Front", 'y', -89.0+WIN_D/2, 0, 10, 40, 4, 9, mat_window)
add_windows_on_face("Win_A4_Back",  'y', -81.0-WIN_D/2, 0, 10, 40, 4, 9, mat_window)

# A5: X[17.5,42.5] Y[-81,-69] Z[0,16]
add_windows_on_face("Win_A5_Front", 'y', -81.0+WIN_D/2, 0, 17.5, 42.5, 4, 8, mat_window)
add_windows_on_face("Win_A5_Back",  'y', -69.0-WIN_D/2, 0, 17.5, 42.5, 4, 8, mat_window)

# A1 (tháp kính): cửa sổ mặt trước và mặt sau (cao 44m, 11 tầng)
add_windows_on_face("Win_A1_Front", 'y', -69.0-WIN_D/2, 0, -7.5, 17.5, 11, 6, mat_window)
add_windows_on_face("Win_A1_Back",  'y', -81.0+WIN_D/2, 0, -7.5, 17.5, 11, 6, mat_window)

# ─── 5. VỈA HÈ & KẺ ĐƯỜNG ───────────────────────────────────────────────────

# Vỉa hè trước mặt tiền Khu A (Y=-69, trải rộng từ X=-35 đến X=45)
add_box("Sidewalk_A_Front", 5, -92, 0.05, 80, 6, 0.1, mat_sidewalk)
add_box("Sidewalk_A_Back",  5, -66, 0.05, 80, 4, 0.1, mat_sidewalk)

# Vỉa hè dọc bên trái nối A2-A3
add_box("Sidewalk_A23_Left",  -33.5, -79, 0.05, 3, 22, 0.1, mat_sidewalk)
# Vỉa hè dọc bên phải nối A4-A5
add_box("Sidewalk_A45_Right",  43, -79, 0.05, 3, 22, 0.1, mat_sidewalk)

# Vỉa hè kết nối Road_Main_Entrance đến A1
add_box("Sidewalk_Main_Path", 5, -87, 0.05, 12, 12, 0.1, mat_sidewalk)

# Vạch kẻ đường (zebra crossing) tại ngã tư vào cổng X=5, Y=-95
for i in range(7):
    zx = 5 + (i - 3) * 1.2
    add_box(f"Zebra_{i}", zx, -95, 0.06, 0.7, 3.5, 0.05, mat_stripe)

# ─── 6. COLLECTION DETAIL ────────────────────────────────────────────────────
# Gom tất cả object mới vào collection "Khu_A_Details"

col_detail = bpy.data.collections.new("Khu_A_Details")
bpy.context.scene.collection.children.link(col_detail)

detail_keywords = [
    "Basement", "Stair", "Railing", "Win_", "Sidewalk", "Zebra"
]
for obj in bpy.data.objects:
    for kw in detail_keywords:
        if obj.name.startswith(kw):
            # Move from master collection to detail collection
            for c in obj.users_collection:
                c.objects.unlink(obj)
            col_detail.objects.link(obj)
            break

# ─── 7. SAVE ─────────────────────────────────────────────────────────────────

out_path = "/home/phuchoangsrc/AI/final/data/Untitled_detailed.blend"
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print(f"\n✅ Saved: {out_path}\n")

# ─── 8. RENDER TOP-DOWN ──────────────────────────────────────────────────────

scene = bpy.context.scene
scene.render.engine            = 'CYCLES'
scene.cycles.samples           = 32
scene.render.resolution_x      = 2400
scene.render.resolution_y      = 2000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# Camera orthographic top-down (khu A: center ≈ (5,-79))
cam_data = bpy.data.cameras.new("Cam_Top")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 120
cam_obj  = bpy.data.objects.new("Cam_Top", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (5, -79, 150)
cam_obj.rotation_euler = (0, 0, 0)
scene.camera = cam_obj

scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_top.png"
bpy.ops.render.render(write_still=True)
print("✅ Rendered top view")

# Camera perspective
cam_data2 = bpy.data.cameras.new("Cam_Persp")
cam_data2.type = 'PERSP'
cam_data2.lens = 28
cam_obj2 = bpy.data.objects.new("Cam_Persp", cam_data2)
scene.collection.objects.link(cam_obj2)
import math
cam_obj2.location = (-80, -130, 60)
cam_obj2.rotation_euler = (math.radians(65), 0, math.radians(-35))
scene.camera = cam_obj2

scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_perspective.png"
bpy.ops.render.render(write_still=True)
print("✅ Rendered perspective view")

print("\n=== DONE ===")
