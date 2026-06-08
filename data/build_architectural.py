"""
Script dựng chi tiết kiến trúc hành lang, phòng học, cầu thang
cho cả khu Trung tâm (A2-A5) và khu A cũ (Dãy trái, phải, ngang).
Chạy: blender --background data/Untitled.blend --python data/build_architectural.py
"""
import bpy
import bmesh
from mathutils import Vector

# ─── MATERIALS ───────────────────────────────────────────────────────────────
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

mat_glass    = make_material("Mat_Glass",    0.2, 0.5, 0.7, roughness=0.1)
mat_wall     = make_material("Mat_Wall",     0.9, 0.9, 0.88, roughness=0.9)
mat_slab     = make_material("Mat_Slab",     0.7, 0.7, 0.7, roughness=0.8)
mat_column   = make_material("Mat_Column",   0.8, 0.8, 0.78, roughness=0.9)
mat_railing  = make_material("Mat_Railing",  0.3, 0.3, 0.3, metallic=0.6, roughness=0.4)
mat_door     = make_material("Mat_Door",     0.4, 0.2, 0.1, roughness=0.7)
mat_window   = make_material("Mat_WinFrame", 0.1, 0.1, 0.1, roughness=0.5)
mat_stair    = make_material("Mat_Stair",    0.6, 0.6, 0.6, roughness=0.8)
mat_louver   = make_material("Mat_Louver",   0.85, 0.85, 0.85, roughness=0.5)

# ─── UTILS ───────────────────────────────────────────────────────────────────
def add_box(name, cx, cy, cz, sx, sy, sz, mat, col):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    # Set location and scale directly (no ops needed)
    obj.location = (cx, cy, cz)
    obj.scale = (sx/2, sy/2, sz/2)
    # Build the cube geometry
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2)
    bm.to_mesh(mesh)
    bm.free()
    # Apply scale into mesh
    import mathutils
    scale_m = mathutils.Matrix.Diagonal((sx/2, sy/2, sz/2, 1))
    mesh.transform(scale_m)
    obj.scale = (1, 1, 1)
    assign_mat(obj, mat)
    return obj

col_arch = bpy.data.collections.new("KhuA_Architectural")
bpy.context.scene.collection.children.link(col_arch)

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

def build_staircase(prefix, cx, cy, z_base, z_top, width, depth, floor_h=4.0, open_side='S'):
    """
    open_side: phía hành lang sẽ không có tường lõi ('S'=Nam, 'N'=Bắc, 'E'=Đông, 'W'=Tây)
    """
    num_floors = int(round((z_top - z_base) / floor_h))
    if num_floors <= 0: return
    flight_w = width / 2.2
    run_d = depth - 1.5
    h_total = z_top - z_base

    # Tường lõi: chỉ vẽ 3 cạnh, BỎ cạnh hướng về hành lang (open_side)
    if open_side != 'W':  # Tường trái (x-)
        add_box(f"{prefix}_Wall_L", cx - width/2, cy, (z_base+z_top)/2, 0.2, depth, h_total, mat_wall, col_arch)
    if open_side != 'E':  # Tường phải (x+)
        add_box(f"{prefix}_Wall_R", cx + width/2, cy, (z_base+z_top)/2, 0.2, depth, h_total, mat_wall, col_arch)
    if open_side != 'S':  # Tường hậu (y-)
        add_box(f"{prefix}_Wall_F", cx, cy - depth/2, (z_base+z_top)/2, width, 0.2, h_total, mat_wall, col_arch)
    if open_side != 'N':  # Tường hậu (y+)
        add_box(f"{prefix}_Wall_B", cx, cy + depth/2, (z_base+z_top)/2, width, 0.2, h_total, mat_wall, col_arch)
    
    num_steps = 10 # 10 steps per flight
    step_d = run_d / num_steps
    step_h = (floor_h / 2) / num_steps
    
    for f in range(num_floors):
        zf = z_base + f * floor_h
        
        # Main floor landing (kết nối F2 của tầng dưới với F1 của tầng này)
        add_box(f"{prefix}_F{f}_MainLanding", cx, cy - depth/2 + 0.75, zf - step_h/2, width, 1.5, step_h, mat_stair, col_arch)
        
        # Flight 1 (đi lên chiếu nghỉ giữa tầng)
        start_y = cy - depth/2 + 1.5 + step_d/2
        for s in range(num_steps):
            add_box(f"{prefix}_F{f}_F1_{s}", cx - flight_w/2, start_y + s*step_d, zf + (s+0.5)*step_h, flight_w, step_d, step_h, mat_stair, col_arch)
            
        # Mid Landing (chiếu nghỉ giữa tầng)
        add_box(f"{prefix}_F{f}_MidLanding", cx, cy + depth/2 - 0.75, zf + floor_h/2 - step_h/2, width, 1.5, step_h, mat_stair, col_arch)
        
        # Flight 2 (từ chiếu nghỉ giữa tầng lên tầng tiếp)
        start_y = cy + depth/2 - 1.5 - step_d/2
        for s in range(num_steps):
            add_box(f"{prefix}_F{f}_F2_{s}", cx + flight_w/2, start_y - s*step_d, zf + floor_h/2 + (s+0.5)*step_h, flight_w, step_d, step_h, mat_stair, col_arch)

# ─── PROCEDURAL BUILDING GENERATOR ───────────────────────────────────────────
def build_detailed_block(prefix, x_min, x_max, y_min, y_max, z_min, z_max, corridor_side='S', num_floors=4):
    width_x = x_max - x_min
    depth_y = y_max - y_min
    height  = z_max - z_min
    floor_h = height / num_floors if num_floors > 0 else 4.0

    profile = get_block_profile(prefix)
    corr_width = profile["corridor_width"]
    bay_spacing = profile["bay_spacing"]
    col_size   = 0.4
    slab_thick = 0.2
    
    # Trục dài của tòa nhà
    is_x_long = width_x >= depth_y
    
    if corridor_side == 'S':
        corr_y_min, corr_y_max = y_min, y_min + corr_width
        room_y_min, room_y_max = corr_y_max, y_max
        room_x_min, room_x_max = x_min, x_max
    elif corridor_side == 'N':
        corr_y_min, corr_y_max = y_max - corr_width, y_max
        room_y_min, room_y_max = y_min, corr_y_min
        room_x_min, room_x_max = x_min, x_max
    elif corridor_side == 'E':
        corr_x_min, corr_x_max = x_max - corr_width, x_max
        room_x_min, room_x_max = x_min, corr_x_min
        room_y_min, room_y_max = y_min, y_max
    elif corridor_side == 'W':
        corr_x_min, corr_x_max = x_min, x_min + corr_width
        room_x_min, room_x_max = corr_x_max, x_max
        room_y_min, room_y_max = y_min, y_max

    # Xác định bước cột
    if is_x_long:
        num_cols = max(3, int(width_x / bay_spacing) + 1)
        dx = (width_x - col_size) / (num_cols - 1)
    else:
        num_cols = max(3, int(depth_y / bay_spacing) + 1)
        dy = (depth_y - col_size) / (num_cols - 1)
    
    # Để chừa lõi cầu thang ở khoang giữa
    stair_index = num_cols // 2

    for f in range(num_floors + 1):
        z_slab = z_min + f * floor_h
        
        # Floor slab (Đục lỗ chỗ cầu thang bằng cách tạo 2 tấm slab rời nếu là các khối A)
        if f > 0 and f < num_floors:
            if is_x_long:
                stair_x_min = x_min + col_size/2 + stair_index * dx
                stair_x_max = x_min + col_size/2 + (stair_index + 1) * dx
                add_box(f"{prefix}_F{f}_SlabL", (x_min+stair_x_min)/2, (y_min+y_max)/2, z_slab - slab_thick/2, stair_x_min-x_min, depth_y, slab_thick, mat_slab, col_arch)
                add_box(f"{prefix}_F{f}_SlabR", (stair_x_max+x_max)/2, (y_min+y_max)/2, z_slab - slab_thick/2, x_max-stair_x_max, depth_y, slab_thick, mat_slab, col_arch)
                # Connector across the stair void along the corridor edge so
                # corridor circulation remains continuous on each floor.
                bridge_y = y_min + corr_width/2 if corridor_side == 'S' else y_max - corr_width/2
                add_box(
                    f"{prefix}_F{f}_Passage",
                    (stair_x_min + stair_x_max) / 2,
                    bridge_y,
                    z_slab - slab_thick/2,
                    stair_x_max - stair_x_min,
                    corr_width,
                    slab_thick,
                    mat_slab,
                    col_arch,
                )
            else:
                stair_y_min = y_min + col_size/2 + stair_index * dy
                stair_y_max = y_min + col_size/2 + (stair_index + 1) * dy
                add_box(f"{prefix}_F{f}_SlabB", (x_min+x_max)/2, (y_min+stair_y_min)/2, z_slab - slab_thick/2, width_x, stair_y_min-y_min, slab_thick, mat_slab, col_arch)
                add_box(f"{prefix}_F{f}_SlabT", (x_min+x_max)/2, (stair_y_max+y_max)/2, z_slab - slab_thick/2, width_x, y_max-stair_y_max, slab_thick, mat_slab, col_arch)
                # Same idea for narrow buildings: keep a floor-level connector
                # at the corridor edge so both slab halves are reachable.
                bridge_x = x_max - corr_width/2 if corridor_side == 'E' else x_min + corr_width/2
                add_box(
                    f"{prefix}_F{f}_Passage",
                    bridge_x,
                    (stair_y_min + stair_y_max) / 2,
                    z_slab - slab_thick/2,
                    corr_width,
                    stair_y_max - stair_y_min,
                    slab_thick,
                    mat_slab,
                    col_arch,
                )
        else:
            add_box(f"{prefix}_F{f}_Slab", (x_min+x_max)/2, (y_min+y_max)/2, z_slab - slab_thick/2, width_x, depth_y, slab_thick, mat_slab, col_arch)
        
        if f == num_floors: break
        
        # Columns & Walls
        if is_x_long:
            col_y = y_min + col_size/2 if corridor_side == 'S' else y_max - col_size/2
            wall_y = room_y_min + 0.1 if corridor_side == 'S' else room_y_max - 0.1
            back_y = y_max - 0.1 if corridor_side == 'S' else y_min + 0.1
            rail_y = y_min + 0.1 if corridor_side == 'S' else y_max - 0.1
            
            for i in range(num_cols):
                cx = x_min + col_size/2 + i * dx
                cz = z_slab + floor_h/2
                add_box(f"{prefix}_F{f}_Col_{i}", cx, col_y, cz, col_size, col_size, floor_h, mat_column, col_arch)
                if i not in (stair_index, stair_index + 1):
                    add_box(f"{prefix}_F{f}_Part_{i}", cx, (room_y_min+room_y_max)/2, cz, 0.2, (room_y_max-room_y_min), floor_h, mat_wall, col_arch)
                
            stair_x_min = x_min + col_size/2 + stair_index * dx
            stair_x_max = x_min + col_size/2 + (stair_index + 1) * dx
            
            # Segment 1 (Left of stair)
            add_box(f"{prefix}_F{f}_Rail_1", (x_min+stair_x_min)/2, rail_y, z_slab + 0.5, stair_x_min-x_min, 0.2, 1.0, mat_railing, col_arch)
            add_box(f"{prefix}_F{f}_WallCorr_1", (x_min+stair_x_min)/2, wall_y, z_slab + floor_h/2, stair_x_min-x_min, 0.2, floor_h, mat_wall, col_arch)
            add_box(f"{prefix}_F{f}_WallBack_1", (x_min+stair_x_min)/2, back_y, z_slab + floor_h/2, stair_x_min-x_min, 0.2, floor_h, mat_wall, col_arch)
            
            # Segment 2 (Right of stair)
            add_box(f"{prefix}_F{f}_Rail_2", (stair_x_max+x_max)/2, rail_y, z_slab + 0.5, x_max-stair_x_max, 0.2, 1.0, mat_railing, col_arch)
            add_box(f"{prefix}_F{f}_WallCorr_2", (stair_x_max+x_max)/2, wall_y, z_slab + floor_h/2, x_max-stair_x_max, 0.2, floor_h, mat_wall, col_arch)
            add_box(f"{prefix}_F{f}_WallBack_2", (stair_x_max+x_max)/2, back_y, z_slab + floor_h/2, x_max-stair_x_max, 0.2, floor_h, mat_wall, col_arch)
            
            for i in range(num_cols - 1):
                if i == stair_index: continue # Bỏ trống chỗ cầu thang
                cx = x_min + col_size/2 + (i + 0.5) * dx
                add_box(f"{prefix}_F{f}_Door_{i}", cx - 1.0, wall_y, z_slab + 1.1, 1.2, 0.3, 2.2, mat_door, col_arch)
                add_box(f"{prefix}_F{f}_Win_{i}", cx + 1.0, wall_y, z_slab + 1.5, 2.0, 0.3, 1.4, mat_glass, col_arch)
        
        else:
            col_x = x_max - col_size/2 if corridor_side == 'E' else x_min + col_size/2
            wall_x = room_x_max - 0.1 if corridor_side == 'E' else room_x_min + 0.1
            back_x = x_min + 0.1 if corridor_side == 'E' else x_max - 0.1
            rail_x = x_max - 0.1 if corridor_side == 'E' else x_min + 0.1
            
            for i in range(num_cols):
                cy = y_min + col_size/2 + i * dy
                cz = z_slab + floor_h/2
                add_box(f"{prefix}_F{f}_Col_{i}", col_x, cy, cz, col_size, col_size, floor_h, mat_column, col_arch)
                if i not in (stair_index, stair_index + 1):
                    add_box(f"{prefix}_F{f}_Part_{i}", (room_x_min+room_x_max)/2, cy, cz, (room_x_max-room_x_min), 0.2, floor_h, mat_wall, col_arch)
                
            stair_y_min = y_min + col_size/2 + stair_index * dy
            stair_y_max = y_min + col_size/2 + (stair_index + 1) * dy
            
            # Segment 1 (Bottom of stair)
            add_box(f"{prefix}_F{f}_Rail_1", rail_x, (y_min+stair_y_min)/2, z_slab + 0.5, 0.2, stair_y_min-y_min, 1.0, mat_railing, col_arch)
            add_box(f"{prefix}_F{f}_WallCorr_1", wall_x, (y_min+stair_y_min)/2, z_slab + floor_h/2, 0.2, stair_y_min-y_min, floor_h, mat_wall, col_arch)
            add_box(f"{prefix}_F{f}_WallBack_1", back_x, (y_min+stair_y_min)/2, z_slab + floor_h/2, 0.2, stair_y_min-y_min, floor_h, mat_wall, col_arch)
            
            # Segment 2 (Top of stair)
            add_box(f"{prefix}_F{f}_Rail_2", rail_x, (stair_y_max+y_max)/2, z_slab + 0.5, 0.2, y_max-stair_y_max, 1.0, mat_railing, col_arch)
            add_box(f"{prefix}_F{f}_WallCorr_2", wall_x, (stair_y_max+y_max)/2, z_slab + floor_h/2, 0.2, y_max-stair_y_max, floor_h, mat_wall, col_arch)
            add_box(f"{prefix}_F{f}_WallBack_2", back_x, (stair_y_max+y_max)/2, z_slab + floor_h/2, 0.2, y_max-stair_y_max, floor_h, mat_wall, col_arch)
            
            for i in range(num_cols - 1):
                if i == stair_index: continue
                cy = y_min + col_size/2 + (i + 0.5) * dy
                add_box(f"{prefix}_F{f}_Door_{i}", wall_x, cy - 1.0, z_slab + 1.1, 0.3, 1.2, 2.2, mat_door, col_arch)
                add_box(f"{prefix}_F{f}_Win_{i}", wall_x, cy + 1.0, z_slab + 1.5, 0.3, 2.0, 1.4, mat_glass, col_arch)

    # Build integrated stair — open_side = phía hành lang
    if is_x_long:
        stair_cx = x_min + col_size/2 + (stair_index + 0.5) * dx
        open_s = 'S' if corridor_side == 'S' else 'N'
        build_staircase(f"{prefix}_Stair", stair_cx, (y_min+y_max)/2, z_min, z_max, dx-0.5, depth_y, floor_h, open_side=open_s)
    else:
        stair_cy = y_min + col_size/2 + (stair_index + 0.5) * dy
        open_s = 'E' if corridor_side == 'E' else 'W'
        build_staircase(f"{prefix}_Stair", (x_min+x_max)/2, stair_cy, z_min, z_max, width_x, dy-0.5, floor_h, open_side=open_s)

# ─── PASSAGEWAYS (BOOLEAN CUTTERS) ───────────────────────────────────
print("Setting up boolean cutters...")
cutters = []
def add_cutter(name, cx, cy, cz, sx, sy, sz):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    c = bpy.context.active_object
    c.name = name
    c.scale = (sx, sy, sz)
    c.display_type = 'WIRE'
    c.hide_render = True
    bpy.ops.object.transform_apply(scale=True)
    for coll in c.users_collection: coll.objects.unlink(c)
    col_arch.objects.link(c)
    cutters.append(c)

def add_rotated_cutter(name, cx, cy, cz, sx, sy, sz, angle):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    c = bpy.context.active_object
    c.name = name
    c.rotation_euler = (0, 0, angle)
    c.scale = (sx, sy, sz)
    c.display_type = 'WIRE'
    c.hide_render = True
    for coll in c.users_collection: coll.objects.unlink(c)
    col_arch.objects.link(c)
    cutters.append(c)

# ─── SKYBRIDGES (CẦU NỐI) ────────────────────────────────────────────────────
def add_rotated_box(name, cx, cy, cz, length, width, height, angle, mat, col):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.location = (cx, cy, cz)
    obj.rotation_euler = (0, 0, angle)
    
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bm.to_mesh(mesh)
    bm.free()
    
    import mathutils
    scale_m = mathutils.Matrix.Diagonal((length, width, height, 1))
    mesh.transform(scale_m)
    assign_mat(obj, mat)
    return obj

def build_skybridge(name, pt1, pt2, z_base, width=2.5, height=3.5, closed=True):
    import math
    x1, y1 = pt1
    x2, y2 = pt2
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 0.1: return
    angle = math.atan2(y2 - y1, x2 - x1)
    
    # Floor slab
    add_rotated_box(f"{name}_Slab", cx, cy, z_base - 0.1, length, width, 0.2, angle, mat_slab, col_arch)
    
    # Columns for long spans
    if length > 15:
        num_cols = int(length / 12)
        for i in range(1, num_cols + 1):
            t = i / (num_cols + 1)
            col_x = x1 + t * (x2 - x1)
            col_y = y1 + t * (y2 - y1)
            add_box(f"{name}_Col_{i}", col_x, col_y, z_base/2, 0.6, 0.6, z_base, mat_column, col_arch)
            
    # Railings & Walls (Rename to avoid being cut by booleans, use "Side" instead of "Rail", "Panel" instead of "Glass")
    dx = math.sin(angle) * (width/2)
    dy = -math.cos(angle) * (width/2)
    
    add_rotated_box(f"{name}_SideL", cx - dx, cy - dy, z_base + 0.5, length, 0.2, 1.0, angle, mat_wall, col_arch)
    add_rotated_box(f"{name}_SideR", cx + dx, cy + dy, z_base + 0.5, length, 0.2, 1.0, angle, mat_wall, col_arch)
    
    if closed:
        add_rotated_box(f"{name}_PanelL", cx - dx, cy - dy, z_base + 1.75, length, 0.1, 1.5, angle, mat_glass, col_arch)
        add_rotated_box(f"{name}_PanelR", cx + dx, cy + dy, z_base + 1.75, length, 0.1, 1.5, angle, mat_glass, col_arch)
        add_rotated_box(f"{name}_Roof", cx, cy, z_base + height, length, width + 0.4, 0.2, angle, mat_slab, col_arch)
        
    # Cutter for opening walls at ends
    # Kích thước cutter: Dọc theo cầu dài bằng length, rộng hơn 1 chút (width), cao 2.5m (bằng cửa đi)
    add_rotated_cutter(f"{name}_Cutter", cx, cy, z_base + 1.25, length, width - 0.2, 2.5, angle)


def build_field_fence(field_obj, inset=1.2, fence_h=4.0, post_spacing=6.0):
    """
    Dựng hàng rào bao quanh sân bóng và lùi nhẹ vào trong mép sân
    để hàng rào nằm gọn trong footprint của sân thay vì tràn ra ngoài.
    """
    bb = field_obj.bound_box
    wc = [field_obj.matrix_world @ Vector(c) for c in bb]
    xs = [c.x for c in wc]
    ys = [c.y for c in wc]
    zs = [c.z for c in wc]

    x_min = min(xs) + inset
    x_max = max(xs) - inset
    y_min = min(ys) + inset
    y_max = max(ys) - inset
    z_top = max(zs)

    if x_max <= x_min or y_max <= y_min:
        return

    rail_t = 0.12
    post_w = 0.18
    fence_cz = z_top + fence_h / 2

    # 4 cạnh hàng rào
    add_box("FieldFence_N", (x_min + x_max) / 2, y_max, fence_cz, x_max - x_min, rail_t, fence_h, mat_railing, col_arch)
    add_box("FieldFence_S", (x_min + x_max) / 2, y_min, fence_cz, x_max - x_min, rail_t, fence_h, mat_railing, col_arch)
    add_box("FieldFence_W", x_min, (y_min + y_max) / 2, fence_cz, rail_t, y_max - y_min, fence_h, mat_railing, col_arch)
    add_box("FieldFence_E", x_max, (y_min + y_max) / 2, fence_cz, rail_t, y_max - y_min, fence_h, mat_railing, col_arch)

    # Cọc hàng rào tại góc và dọc các cạnh dài
    post_positions = {
        (x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)
    }

    x_span = x_max - x_min
    y_span = y_max - y_min
    x_posts = max(0, int(x_span / post_spacing) - 1)
    y_posts = max(0, int(y_span / post_spacing) - 1)

    for i in range(1, x_posts + 1):
        t = i / (x_posts + 1)
        px = x_min + t * x_span
        post_positions.add((px, y_min))
        post_positions.add((px, y_max))

    for i in range(1, y_posts + 1):
        t = i / (y_posts + 1)
        py = y_min + t * y_span
        post_positions.add((x_min, py))
        post_positions.add((x_max, py))

    for idx, (px, py) in enumerate(sorted(post_positions)):
        add_box(f"FieldFence_Post_{idx}", px, py, z_top + fence_h / 2, post_w, post_w, fence_h, mat_column, col_arch)


def relocate_field_clear_of_buildings(field_obj, blocker_names, clearance=8.0):
    """
    Dời sân bóng theo trục X nếu nó đang chồng vào các khối lân cận.
    Hiện trạng file gốc đặt sân dính F1/G, nên đẩy sân sang phải
    tới khi mép trái của sân cách mép phải của các khối này một khoảng an toàn.
    """
    bb = [field_obj.matrix_world @ Vector(c) for c in field_obj.bound_box]
    field_x_min = min(c.x for c in bb)
    field_y_min = min(c.y for c in bb)
    field_y_max = max(c.y for c in bb)

    max_blocker_x = None
    for name in blocker_names:
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        wc = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [c.x for c in wc]
        ys = [c.y for c in wc]
        overlaps_y = not (max(ys) <= field_y_min or min(ys) >= field_y_max)
        if not overlaps_y:
            continue
        blocker_x_max = max(xs)
        max_blocker_x = blocker_x_max if max_blocker_x is None else max(max_blocker_x, blocker_x_max)

    if max_blocker_x is None:
        return

    target_x_min = max_blocker_x + clearance
    delta_x = target_x_min - field_x_min
    if delta_x > 0:
        field_obj.location.x += delta_x


# ─── REPLACE BLOCKS ──────────────────────────────────────────────────────────
blocks_to_replace = [
    ("Khoi_A.2_Phong_Hoc", 'S', 4),
    ("Khoi_A.3_Giang_Duong", 'S', 4),
    ("Khoi_A.4_Phong_Hoc", 'S', 4),
    ("Khoi_A.5_Giang_Duong", 'S', 4),
    # Khu A thực sự và Khu B
    ("Khoi_A_Day_Trai", 'E', 3),  # Left wing, corridor faces East (center)
    ("Khoi_A_Day_Phai", 'W', 3),  # Right wing, corridor faces West (center)
    ("Khoi_B_Ngang", 'S', 3),     # Base of U, corridor faces South
    # Các khu còn lại (1 lầu -> 2 tầng / 3 tầng)
    ("Khoi_C_Phong_Hoc_Dien", 'S', 3), # Tăng lên 3 tầng (mỗi tầng 5m) để khớp Khu A
    ("Khoi_D_Phong_Hoc_Dien", 'S', 3), # Tăng lên 3 tầng để khớp Khu A
    ("Khoi_E.0_Van_Phong_Co_Khi", 'S', 2),
    ("Khoi_E.1_Xuong_Chat_Luong_Cao", 'S', 2),
    ("Khoi_E.2_Can_Tin_Sieu_Thi", 'S', 2),
    ("Khoi_E.3_Xuong_Co_Khi", 'S', 2),
    ("Khoi_E.4_Lop_Hoc_Bat_Giac", 'S', 2),
    ("Khoi_F.1_Phong_Hoc_Xuong", 'S', 2),
    ("Khoi_G_Trung_Tam_Viet_Duc", 'S', 2),
    ("Khoi_Thu_Vien", 'S', 3),         # Tăng lên 3 tầng để khớp Khu A
    ("Hoi_Truong_Lon", 'S', 2),
    ("Xuong_Bien_O_To", 'S', 2),
    ("Xuong_Chung_Gam", 'S', 2),
    ("Xuong_Dong_Co", 'S', 2),
    ("Xuong_Nhiet_Dien_Lanh", 'S', 2),
    ("Xuong_Thuc_Tap_Go", 'S', 2)
]

for name, side, fl in blocks_to_replace:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True
        obj.hide_viewport = True
        bb = obj.bound_box
        wc = [obj.matrix_world @ Vector(c) for c in bb]
        xs = [c.x for c in wc]
        ys = [c.y for c in wc]
        zs = [c.z for c in wc]
        build_detailed_block(name, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), side, fl)

# ─── BUILD SKYBRIDGES ────────────────────────────────────────────────────────
skybridges = [
    ("Bridge_A_L_Lib", (-15, 15), (0, -10), 10.0), # Kết nối tầng 2 (10m) của Dãy Trái và Thư Viện
    ("Bridge_A_R_Lib", (15, 15), (0, -10), 5.0),   # Kết nối tầng 1 (5m) của Dãy Phải và Thư Viện
    ("Bridge_A_L_C", (-15, 15), (-35, 30), 10.0),  # Kết nối tầng 2 (10m) của Dãy Trái và Dãy C
    ("Bridge_C_D", (-35, 30), (-48, 10), 5.0),     # Kết nối tầng 1 (5m) của Dãy C và Dãy D
    ("Bridge_D_E2", (-48, 10), (-55, -5), 5.0),    # Kết nối tầng 1 (5m) của Dãy D và Căn tin E2 (cao độ thực 4m + độ dốc)
    ("Bridge_Lib_E2", (0, -10), (-55, -5), 5.0),   # Kết nối tầng 1 (5m) của Thư Viện và Căn tin E2 (cao độ thực 4m)
    ("Bridge_E2_E3", (-55, -5), (-70, -25), 4.0),  # Kết nối tầng 1 (4m) của E2 và E3
    ("Bridge_A4_F1", (25, -85), (55, -35), 12.0),  # Kết nối tầng 3 (12m) của A4 và F1 (tầng 2)
    ("Bridge_F1_G", (55, -35), (55, -58), 6.0)     # Kết nối tầng 1 (6m) của F1 và G
]
for sb in skybridges:
    build_skybridge(sb[0], sb[1], sb[2], sb[3])

field_obj = bpy.data.objects.get("San_Bong_Da_Ngoai_Troi")
if field_obj:
    relocate_field_clear_of_buildings(
        field_obj,
        ["Khoi_F.1_Phong_Hoc_Xuong", "Khoi_G_Trung_Tam_Viet_Duc"],
    )
    bpy.context.view_layer.update()
    build_field_fence(field_obj)

# ─── OUTDOOR STAIRCASES ───────────────────────────────────────────────────────
# Cầu thang ngoài trời kết nối mặt đất ↔ skybridge / lầu 2
# build_outdoor_stair(name, cx, cy, z_bottom, z_top, facing='N'/'S'/'E'/'W', w=3.5)
def build_outdoor_stair(name, cx, cy, z_bottom, z_top, facing='N', w=3.5):
    """
    Xây cầu thang ngoài trời thẳng (straight-run) từ z_bottom đến z_top.
    facing: hướng đi lên ('N' = bước về phía y+, 'S'=y-, 'E'=x+, 'W'=x-)
    """
    h = z_top - z_bottom
    if h <= 0: return
    n_steps = max(6, int(h / 0.18))   # ~18cm mỗi bậc
    step_h = h / n_steps
    run    = h * 1.8                   # tỷ lệ chiều ngang/chiều cao ~1.8
    step_r = run / n_steps

    dx_step = 0.0; dy_step = 0.0
    if facing == 'N':  dy_step =  step_r
    elif facing == 'S': dy_step = -step_r
    elif facing == 'E': dx_step =  step_r
    elif facing == 'W': dx_step = -step_r

    for s in range(n_steps):
        bx = cx + dx_step * (s + 0.5)
        by = cy + dy_step * (s + 0.5)
        bz = z_bottom + step_h * s + step_h / 2
        # kích thước bậc theo hướng đi
        if facing in ('N', 'S'):
            add_box(f"{name}_S{s}", bx, by, bz, w, step_r * 1.02, step_h, mat_stair, col_arch)
        else:
            add_box(f"{name}_S{s}", bx, by, bz, step_r * 1.02, w, step_h, mat_stair, col_arch)

    # Lan can 2 bên
    total_run_x = dx_step * n_steps
    total_run_y = dy_step * n_steps
    rail_cx = cx + total_run_x / 2
    rail_cy = cy + total_run_y / 2
    rail_cz = z_bottom + h / 2 + 0.5
    if facing in ('N', 'S'):
        add_box(f"{name}_RailA", rail_cx - w/2, rail_cy, rail_cz, 0.15, abs(total_run_y), 1.0, mat_railing, col_arch)
        add_box(f"{name}_RailB", rail_cx + w/2, rail_cy, rail_cz, 0.15, abs(total_run_y), 1.0, mat_railing, col_arch)
    else:
        add_box(f"{name}_RailA", rail_cx, rail_cy - w/2, rail_cz, abs(total_run_x), 0.15, 1.0, mat_railing, col_arch)
        add_box(f"{name}_RailB", rail_cx, rail_cy + w/2, rail_cz, abs(total_run_x), 0.15, 1.0, mat_railing, col_arch)

# ── Cầu thang nối mặt đất → tầng lầu khớp cao độ ──
# 1. Đầu Dãy Trái Khu A (x=-15,y=15) – lên z=10.0 (tầng 2)
build_outdoor_stair("OutStair_AL_up",   -15,  12,  0, 10.0, facing='S')
build_outdoor_stair("OutStair_AL_side", -19,  15,  0, 10.0, facing='E')

# 2. Đầu Dãy Phải Khu A (x=15,y=15) – lên z=5.0 (tầng 1) và z=10.0 (tầng 2)
build_outdoor_stair("OutStair_AR_up",    15,  12,  0, 5.0, facing='S')
build_outdoor_stair("OutStair_AR_side",  19,  15,  0, 10.0, facing='W')

# 3. Thư Viện (x=0, y=-10) – lên tầng 1 (5m) và tầng 2 (10m)
build_outdoor_stair("OutStair_Lib_N",    0,   -7,  0, 5.0, facing='S')
build_outdoor_stair("OutStair_Lib_S",    0,  -13,  0, 10.0, facing='N')

# 4. Căn Tin E.2 (x=-55, y=-5) – lên tầng 1 (4m) và tầng 2 (8m)
build_outdoor_stair("OutStair_E2_E",   -51,   -5,  0, 4.0, facing='W')
build_outdoor_stair("OutStair_E2_W",   -59,   -5,  0, 8.0, facing='E')

# 5. Xưởng E.3 (x=-70, y=-25) – cuối chuỗi skybridge lên tầng 2 (8m)
build_outdoor_stair("OutStair_E3",     -70,  -21,  0, 8.0, facing='S')

# 6. Khối F.1 (x=55, y=-35) – lên tầng 1 (6m) và tầng 2 (12m)
build_outdoor_stair("OutStair_F1_N",    55,  -31,  0, 6.0, facing='S')
build_outdoor_stair("OutStair_F1_S",    55,  -39,  0, 12.0, facing='N')

# 7. Trung tâm Việt Đức G (x=55, y=-58) – lên tầng 2 (12m)
build_outdoor_stair("OutStair_G",       55,  -54,  0, 12.0, facing='S')

# 8. Bỏ cặp cầu thang giữa sân cũ vì đứng rời và tạo hình khối bất thường.

# 9. Góc Khu C-D (x=-35,y=30 → x=-48,y=10) – lên tầng 1 (5m) và tầng 2 (10m)
build_outdoor_stair("OutStair_C",      -35,   26,  0, 5.0, facing='S')
build_outdoor_stair("OutStair_D",      -48,    6,  0, 10.0, facing='S')

# 10. A1 Tower – cầu thang thoát hiểm ngoài (cạnh bên tòa chính, lên 20m)
build_outdoor_stair("OutStair_A1_L",   -8,  -78,  0, 20.0, facing='N', w=2.5)
build_outdoor_stair("OutStair_A1_R",   18,  -78,  0, 20.0, facing='N', w=2.5)



# ─── A1 CENTRAL TOWER DETAILS ────────────────────────────────────────────────
def build_a1_tower(name, a1_obj):
    a1_obj.hide_render = True
    a1_obj.hide_viewport = True
    bb = a1_obj.bound_box
    wc = [a1_obj.matrix_world @ Vector(c) for c in bb]
    x_min, x_max = min([c.x for c in wc]), max([c.x for c in wc])
    y_min, y_max = min([c.y for c in wc]), max([c.y for c in wc])
    z_min, z_max = min([c.z for c in wc]), max([c.z for c in wc])
    
    num_floors = 5
    floor_h = 4.0
    
    cx, cy = (x_min + x_max)/2, (y_min + y_max)/2
    width_x = x_max - x_min
    depth_y = y_max - y_min
    
    for f in range(num_floors + 1):
        z_slab = z_min + f * floor_h
        
        # Sàn
        add_box(f"{name}_F{f}_Slab", cx, cy, z_slab - 0.1, width_x, depth_y, 0.2, mat_slab, col_arch)
        
        if f == num_floors: break
        
        # Lõi thang máy
        core_size = 4.0
        add_box(f"{name}_F{f}_ElevatorCore", cx, cy + 2.0, z_slab + floor_h/2, core_size, core_size, floor_h, mat_wall, col_arch)
        add_box(f"{name}_F{f}_ElevatorDoor", cx, cy + 2.0 - core_size/2 - 0.1, z_slab + 1.25, 2.0, 0.2, 2.5, mat_door, col_arch)
        
        # Kính mặt trước & sau
        if f > 0:
            add_box(f"{name}_F{f}_GlassFront", cx, y_min + 0.1, z_slab + floor_h/2, width_x, 0.2, floor_h, mat_glass, col_arch)
        else:
            # Tầng trệt: Kính TOÀN BỘ rồi dùng cutter đục lỗ cửa
            add_box(f"{name}_F{f}_GlassFront", cx, y_min + 0.1, z_slab + floor_h/2, width_x, 0.2, floor_h, mat_glass, col_arch)
            
            # Boolean cutter đục lỗ cửa chính (3 cánh rộng 2m, cao 3.2m)
            door_w = 8.0   # tổng chiều rộng cụm cửa
            door_h = 3.2   # chiều cao cửa
            add_cutter(f"Cut_{name}_MainDoor", cx, y_min + 0.1, z_slab + door_h/2, door_w, 1.0, door_h)
            
            # Khung cửa (door frame) xung quanh lỗ
            frame_t = 0.25
            # Hai đứng bên
            add_box(f"{name}_DoorFrameL", cx - door_w/2 - frame_t/2, y_min + 0.05, z_slab + door_h/2, frame_t, 0.4, door_h + frame_t, mat_column, col_arch)
            add_box(f"{name}_DoorFrameR", cx + door_w/2 + frame_t/2, y_min + 0.05, z_slab + door_h/2, frame_t, 0.4, door_h + frame_t, mat_column, col_arch)
            # Thanh ngang trên
            add_box(f"{name}_DoorFrameTop", cx, y_min + 0.05, z_slab + door_h + frame_t/2, door_w + frame_t*2, 0.4, frame_t, mat_column, col_arch)
            
            # 4 cánh cửa kính (lùi vào 0.3m so với mặt ngoài)
            panel_w = door_w / 4
            for p in range(4):
                px = cx - door_w/2 + panel_w/2 + p * panel_w
                add_box(f"{name}_DoorPanel_{p}", px, y_min + 0.35, z_slab + door_h/2, panel_w - 0.1, 0.1, door_h - 0.1, mat_glass, col_arch)
            
            # Bậc thềm (steps) trước cửa
            for s in range(3):
                sw = door_w + 4.0 - s * 2.0
                add_box(f"{name}_Step_{s}", cx, y_min - 0.6 - s * 0.6, z_min - s * 0.15, sw, 1.2, 0.15, mat_slab, col_arch)

            
        add_box(f"{name}_F{f}_GlassBack", cx, y_max - 0.1, z_slab + floor_h/2, width_x, 0.2, floor_h, mat_glass, col_arch)
        
        # Tường 2 bên
        add_box(f"{name}_F{f}_WallL", x_min + 0.1, cy, z_slab + floor_h/2, 0.2, depth_y, floor_h, mat_wall, col_arch)
        add_box(f"{name}_F{f}_WallR", x_max - 0.1, cy, z_slab + floor_h/2, 0.2, depth_y, floor_h, mat_wall, col_arch)
        
        # Lối đi cắt thông 2 bên lầu (Chỉ từ tầng 1 đến 4)
        # Đặt theo đúng dải hành lang phía trước để thông với A3/A5,
        # thay vì cắt giữa nhà khiến lối ra bị lệch khỏi corridor.
        if f < 4:
            corridor_y = y_min + 1.1
            add_cutter(f"Cut_A1_Left_F{f}", x_min, corridor_y, z_slab + 1.25, 2.0, 3.0, 2.5)
            add_cutter(f"Cut_A1_Right_F{f}", x_max, corridor_y, z_slab + 1.25, 2.0, 3.0, 2.5)

    # Mái hiên
    add_box(f"{name}_Canopy", cx, y_min - 4, z_min + 5, width_x + 4, 8, 0.5, mat_slab, col_arch)
    add_box(f"{name}_Canopy_ColL", x_min - 1, y_min - 7, z_min + 2.5, 0.6, 0.6, 5, mat_column, col_arch)
    add_box(f"{name}_Canopy_ColR", x_max + 1, y_min - 7, z_min + 2.5, 0.6, 0.6, 5, mat_column, col_arch)

a1 = bpy.data.objects.get("Khoi_A.1_Trung_Tam_Hanh_Chinh")
if a1:
    build_a1_tower("A1_Tower", a1)

# Save
out_path = "/home/phuchoangsrc/AI/final/data/Untitled_arch.blend"

# 1. Cắt thông hành lang chữ U (Khu A)
add_cutter("Cut_U_Left",  -12.1, 39.1, 7.5, 3.0, 3.0, 16.0)
add_cutter("Cut_U_Right",  12.1, 39.1, 7.5, 3.0, 3.0, 16.0)

# 2. Cắt thông lối giữa A2-A3 và A4-A5
add_cutter("Cut_A2_A3",  -20.0, -81.0, 10.0, 5.0, 3.0, 25.0)
add_cutter("Cut_A4_A5",   27.5, -81.0, 10.0, 8.0, 3.0, 25.0)

# 3. Tự động cắt lỗ ở 2 đầu mỗi skybridge (BridgeEntry cutters)
import math as _math
_door_h   = 2.8   # chiều cao lỗ cửa tại đầu cầu
_door_w   = 2.8   # chiều rộng lỗ (hơi nhỏ hơn cầu để còn khung)
_cut_deep = 3.0   # đủ xuyên qua tường 0.2m + vùng đệm

for _sb_name, _pt1, _pt2, _z_base in skybridges:
    _x1, _y1 = _pt1
    _x2, _y2 = _pt2
    _dx = _x2 - _x1
    _dy = _y2 - _y1
    _len = _math.hypot(_dx, _dy)
    _nx  = _dx / _len   # unit vector dọc cầu
    _ny  = _dy / _len

    # Cutter tại đầu pt1 — lùi nhẹ vào trong tòa (~1.5m)
    add_rotated_cutter(
        f"BridgeEntry_{_sb_name}_P1",
        _x1 - _nx * 1.5,  _y1 - _ny * 1.5,
        _z_base + _door_h / 2,
        _cut_deep, _door_w, _door_h,
        _math.atan2(_dy, _dx)
    )
    # Cutter tại đầu pt2
    add_rotated_cutter(
        f"BridgeEntry_{_sb_name}_P2",
        _x2 + _nx * 1.5,  _y2 + _ny * 1.5,
        _z_base + _door_h / 2,
        _cut_deep, _door_w, _door_h,
        _math.atan2(_dy, _dx)
    )

# 4. Cắt lỗ tại điểm cầu thang ngoài trời chạm vào tường tòa nhà
# (Mỗi cầu thang đặt ngay cạnh tường → cutter mỏng theo trục ngắn)
_stair_entries = [
    # (cx, cy, z_top, facing, w)
    (-15, 12,  10.0, 'S', 3.5),
    (-19, 15,  10.0, 'E', 3.5),
    ( 15, 12,   5.0, 'S', 3.5),
    ( 19, 15,  10.0, 'W', 3.5),
    (  0,  -7,   5.0, 'S', 3.5),
    (  0, -13,  10.0, 'N', 3.5),
    (-51,  -5,   4.0, 'W', 3.5),
    (-59,  -5,   8.0, 'E', 3.5),
    (-70, -21,   8.0, 'S', 3.5),
    ( 55, -31,   6.0, 'S', 3.5),
    ( 55, -39,  12.0, 'N', 3.5),
    ( 55, -54,  12.0, 'S', 3.5),
    (-35,  26,   5.0, 'S', 3.5),
    (-48,   6,  10.0, 'S', 3.5),
]
for _cx, _cy, _zt, _face, _w in _stair_entries:
    _off = 1.5
    if _face == 'S': _ey = _cy - _off; _ex = _cx
    elif _face == 'N': _ey = _cy + _off; _ex = _cx
    elif _face == 'E': _ex = _cx + _off; _ey = _cy
    else:              _ex = _cx - _off; _ey = _cy
    add_cutter(f"StairEntry_{_cx}_{_cy}", _ex, _ey, _zt - _door_h/2, _w, _cut_deep, _door_h)

# Apply booleans — rộng hơn: bắt cả tường ngang và tường dọc các tòa
cutter_set = set(c.name for c in cutters)
WALL_KEYWORDS = [
    "_WallL", "_WallR", "_WallCorr", "_WallBack",
    "_GlassFront", "_GlassBack",
    "_Rail_", "_Part_",
]
for obj in col_arch.objects:
    if obj.type == 'MESH' and obj.name not in cutter_set:
        if any(k in obj.name for k in WALL_KEYWORDS):
            for cut in cutters:
                if cut.name == obj.name:
                    continue
                mod = obj.modifiers.new(name="Passageway", type='BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.solver = 'FLOAT'
                mod.object = cut

bpy.ops.wm.save_as_mainfile(filepath=out_path)
print(f"\n✅ Saved detailed architecture to: {out_path}\n")
