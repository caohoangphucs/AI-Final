"""Render front & side view of A1 tower with 5 floors."""
import bpy, math

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

world = scene.world
world.use_nodes = True
tree = world.node_tree
for node in tree.nodes: tree.nodes.remove(node)
sky = tree.nodes.new(type="ShaderNodeTexSky")
sky.sky_type = 'PREETHAM'
sky.sun_elevation = math.radians(45)
sky.sun_rotation   = math.radians(135)
bg  = tree.nodes.new(type="ShaderNodeBackground")
bg.inputs['Strength'].default_value = 1.0
out = tree.nodes.new(type="ShaderNodeOutputWorld")
tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
tree.links.new(bg.outputs['Background'], out.inputs['Surface'])

def add_light(loc, energy=3000):
    l_data = bpy.data.lights.new("Sun", type='POINT')
    l_data.energy = energy
    l_obj = bpy.data.objects.new("Sun", l_data)
    scene.collection.objects.link(l_obj)
    l_obj.location = loc

add_light((5, -120, 40), 6000)
add_light((-30, -100, 30), 3000)

# --- Cam 1: Mặt trước tòa A1 từ xa ---
cam1 = bpy.data.cameras.new("Cam_A1_Front")
cam1.type = 'PERSP'
cam1.lens = 35
c1 = bpy.data.objects.new("Cam_A1_Front", cam1)
scene.collection.objects.link(c1)
c1.location = (5, -120, 12)
target = bpy.data.objects.new("T1", None)
scene.collection.objects.link(target)
target.location = (5, -75, 12)
ttc = c1.constraints.new('TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'
scene.camera = c1
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_a1_front.png"
bpy.ops.render.render(write_still=True)
print("✅ A1 front view rendered")

# --- Cam 2: Góc chéo nhìn vào sảnh chính ---
cam2 = bpy.data.cameras.new("Cam_A1_Lobby")
cam2.type = 'PERSP'
cam2.lens = 28
c2 = bpy.data.objects.new("Cam_A1_Lobby", cam2)
scene.collection.objects.link(c2)
c2.location = (-20, -110, 8)
target2 = bpy.data.objects.new("T2", None)
scene.collection.objects.link(target2)
target2.location = (5, -78, 10)
ttc2 = c2.constraints.new('TRACK_TO')
ttc2.target = target2
ttc2.track_axis = 'TRACK_NEGATIVE_Z'
ttc2.up_axis = 'UP_Y'
scene.camera = c2
scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_a1_lobby.png"
bpy.ops.render.render(write_still=True)
print("✅ A1 lobby view rendered")
