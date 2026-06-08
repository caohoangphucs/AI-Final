"""
Script render preview Khu A (Dãy chữ U) và khu Chính.
"""
import bpy, math

for obj in list(bpy.data.objects):
    if obj.type in ['CAMERA', 'LIGHT']:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16 # RẤT THẤP ĐỂ REVIEW NHANH
scene.cycles.use_denoising = True
scene.render.resolution_x = 800
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# Ánh sáng
world = scene.world
world.use_nodes = True
tree = world.node_tree
for node in tree.nodes: tree.nodes.remove(node)

sky = tree.nodes.new(type="ShaderNodeTexSky")
sky.sky_type = 'PREETHAM'
sky.sun_elevation = math.radians(45)
sky.sun_rotation = math.radians(135)
sky.sun_intensity = 0.5
bg = tree.nodes.new(type="ShaderNodeBackground")
bg.inputs['Strength'].default_value = 1.0
out = tree.nodes.new(type="ShaderNodeOutputWorld")
tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
tree.links.new(bg.outputs['Background'], out.inputs['Surface'])

# Cam 1: Nhìn toàn cảnh Khu A (chữ U)
cam_data = bpy.data.cameras.new("Cam_KhuA")
cam_data.type = 'PERSP'
cam_data.lens = 24
cam_obj = bpy.data.objects.new("Cam_KhuA", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (-40, 5, 20)
cam_obj.rotation_euler = (math.radians(70), 0, math.radians(-45))
scene.camera = cam_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_khua_preview.png"
bpy.ops.render.render(write_still=True)
print("✅ Khu A preview rendered")

# Cam 2: Nhìn trực diện sảnh cầu thang từ ngoài vào
cam2_data = bpy.data.cameras.new("Cam_Corridor")
cam2_data.type = 'PERSP'
cam2_data.lens = 18
cam2_obj = bpy.data.objects.new("Cam_Corridor", cam2_data)
scene.collection.objects.link(cam2_obj)
cam2_obj.location = (-17.74, -92, 1.5)

# Track to target
target = bpy.data.objects.new("Target", None)
scene.collection.objects.link(target)
target.location = (-17.74, -85, 3.5)

ttc = cam2_obj.constraints.new(type='TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

scene.camera = cam2_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_stair_open.png"
bpy.ops.render.render(write_still=True)
print("✅ Corridor to stair view rendered")
