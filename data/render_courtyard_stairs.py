import bpy, math

# Remove existing cameras and lights to have a clean render setup
for obj in list(bpy.data.objects):
    if obj.type in ['CAMERA', 'LIGHT']:
        bpy.data.objects.remove(obj, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32  # Low samples for fast high-quality review
scene.cycles.use_denoising = True
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.image_settings.file_format = 'PNG'

# Sun light
sun_data = bpy.data.lights.new("Sun_Main", type='SUN')
sun_data.energy = 4.0
sun_data.angle  = math.radians(5)
sun_obj = bpy.data.objects.new("Sun_Main", sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(55), 0, math.radians(-35))

# Fill light
fill_data = bpy.data.lights.new("Fill_Top", type='AREA')
fill_data.energy = 500
fill_data.size   = 100
fill_obj = bpy.data.objects.new("Fill_Top", fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (0, 0, 80)
fill_obj.rotation_euler = (0, 0, 0)

# World background
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.6, 0.75, 0.85, 1.0)
    bg.inputs["Strength"].default_value = 1.0

# Camera overlooking the courtyard towards the library and wings
cam_data = bpy.data.cameras.new("Cam_Courtyard")
cam_data.type = 'PERSP'
cam_data.lens = 24
cam_obj = bpy.data.objects.new("Cam_Courtyard", cam_data)
scene.collection.objects.link(cam_obj)

# Position camera South-East overlooking North-West
cam_obj.location = (25, -35, 18)

# Target at courtyard center / library edge
target = bpy.data.objects.new("Target", None)
scene.collection.objects.link(target)
target.location = (0, 2, 5)

ttc = cam_obj.constraints.new(type='TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

scene.camera = cam_obj
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_courtyard_new.png"

bpy.ops.render.render(write_still=True)
print("✅ Courtyard render done!")
