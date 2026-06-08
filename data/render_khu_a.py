"""
Script render với ánh sáng tốt hơn + camera đúng góc nhìn Khu A
"""
import bpy, math

# Load file đã chi tiết hóa
# (Script này chạy SAU khi đã load file Untitled_detailed.blend)

scene = bpy.context.scene

# ─── XÓA CAMERA CŨ ───
for obj in list(bpy.data.objects):
    if obj.type == 'CAMERA':
        bpy.data.objects.remove(obj, do_unlink=True)

# ─── ÁNH SÁNG ────────────────────────────────────────────────────────────────

# Xóa light cũ nếu có
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# Sun light chính
sun_data = bpy.data.lights.new("Sun_Main", type='SUN')
sun_data.energy = 5.0
sun_data.angle  = math.radians(5)
sun_obj = bpy.data.objects.new("Sun_Main", sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(45), 0, math.radians(-45))

# Ambient fill (Area light từ trên)
fill_data = bpy.data.lights.new("Fill_Top", type='AREA')
fill_data.energy = 800
fill_data.size   = 200
fill_obj = bpy.data.objects.new("Fill_Top", fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (5, -79, 120)
fill_obj.rotation_euler = (0, 0, 0)

# World background sáng hơn
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.5, 0.6, 0.7, 1.0)
    bg.inputs["Strength"].default_value = 1.5

# ─── RENDER SETTINGS ─────────────────────────────────────────────────────────
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 2400
scene.render.resolution_y = 1600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# ─── CAMERA 1: NHÌ NHƯ ĐI BỘ VÀO CỔNG TRƯỜNG ─────────────────────────────

cam1_data = bpy.data.cameras.new("Cam_Gate")
cam1_data.type = 'PERSP'
cam1_data.lens = 24
cam1_obj = bpy.data.objects.new("Cam_Gate", cam1_data)
scene.collection.objects.link(cam1_obj)
# Đứng ở phía nam cổng nhìn lên phía Bắc về Khu A
cam1_obj.location = (5, -125, 8)
cam1_obj.rotation_euler = (math.radians(78), 0, math.radians(0))
scene.camera = cam1_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_gate_view.png"
bpy.ops.render.render(write_still=True)
print("✅ Gate view rendered")

# ─── CAMERA 2: NHÌN NGHIÊNG KHU A TỪ GÓC TÂY-NAM ──────────────────────────

cam2_data = bpy.data.cameras.new("Cam_SW")
cam2_data.type = 'PERSP'
cam2_data.lens = 28
cam2_obj = bpy.data.objects.new("Cam_SW", cam2_data)
scene.collection.objects.link(cam2_obj)
cam2_obj.location = (-70, -120, 55)
cam2_obj.rotation_euler = (math.radians(58), 0, math.radians(-35))
scene.camera = cam2_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_sw_view.png"
bpy.ops.render.render(write_still=True)
print("✅ SW view rendered")

# ─── CAMERA 3: NHÌN THẲNG MẶT TIỀN KHU A ───────────────────────────────────

cam3_data = bpy.data.cameras.new("Cam_Front")
cam3_data.type = 'PERSP'
cam3_data.lens = 35
cam3_obj = bpy.data.objects.new("Cam_Front", cam3_data)
scene.collection.objects.link(cam3_obj)
cam3_obj.location = (5, -115, 18)
cam3_obj.rotation_euler = (math.radians(85), 0, 0)
scene.camera = cam3_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_front_view.png"
bpy.ops.render.render(write_still=True)
print("✅ Front view rendered")

# ─── CAMERA 4: TOP-DOWN VỚI ÁNH SÁNG TỐT ────────────────────────────────────

cam4_data = bpy.data.cameras.new("Cam_Top2")
cam4_data.type = 'ORTHO'
cam4_data.ortho_scale = 110
cam4_obj = bpy.data.objects.new("Cam_Top2", cam4_data)
scene.collection.objects.link(cam4_obj)
cam4_obj.location = (5, -79, 200)
cam4_obj.rotation_euler = (0, 0, 0)
scene.camera = cam4_obj
scene.render.resolution_x = 2000
scene.render.resolution_y = 2000
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_top2.png"
bpy.ops.render.render(write_still=True)
print("✅ Top-down view rendered")

print("\n=== ALL RENDERS DONE ===")
